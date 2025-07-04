"""
Task extraction and Google Tasks/Calendar integration service.
"""

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from loguru import logger
import google.generativeai as genai
from core.config import settings

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(settings.GEMINI_MODEL)

TASK_EXTRACTION_PROMPT = """
You are an expert task extractor from meeting transcriptions. 
Analyze the following meeting transcript and extract actionable tasks.

For each task, identify:
1. The task description
2. Who is assigned (if mentioned)
3. Due date/deadline (if mentioned)
4. Priority (high/medium/low based on context)

Return ONLY a valid JSON array with this structure:
[
  {
    "description": "Task description",
    "assignee": "person name or 'me' if assigned to the speaker",
    "due_date": "YYYY-MM-DD or null if not specified",
    "priority": "high/medium/low",
    "context": "Brief context from the conversation"
  }
]

If no tasks are found, return an empty array [].
"""

def extract_tasks_from_transcript(transcript: str) -> List[Dict[str, Any]]:
    """
    Extract tasks from meeting transcript using AI.
    """
    try:
        # Use Gemini to extract tasks
        result = model.generate_content(
            TASK_EXTRACTION_PROMPT + "\n\nTranscript:\n" + transcript,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 1024,
            },
        )
        
        content = result.text.strip()
        
        # Handle markdown-formatted JSON responses
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        
        # Try to parse JSON from the response
        tasks = json.loads(content)
        
        if not isinstance(tasks, list):
            logger.warning("AI returned non-list format, treating as empty")
            return []
            
        logger.info(f"Extracted {len(tasks)} tasks from transcript")
        return tasks
        
    except Exception as e:
        logger.exception(f"Failed to extract tasks: {e}")
        return []

def create_google_task(creds: Credentials, task_data: Dict[str, Any], user_email: str) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Create a Google Task from extracted task data.
    Returns the task ID if successful, None otherwise.
    """
    try:
        service = build('tasks', 'v1', credentials=creds)
        
        # Get the default task list
        tasklists = service.tasklists().list().execute()
        task_list_id = tasklists['items'][0]['id']  # Use the first task list
        
        # Prepare task body
        task_body = {
            'title': task_data['description'],
            'notes': f"From meeting: {task_data.get('context', 'No context provided')}",
        }
        
        # Add due date if specified
        if task_data.get('due_date'):
            try:
                due_date = datetime.strptime(task_data['due_date'], '%Y-%m-%d')
                task_body['due'] = due_date.isoformat() + 'Z'
            except ValueError:
                logger.warning(f"Invalid due date format: {task_data['due_date']}")
        
        # Create the task
        task = service.tasks().insert(
            tasklist=task_list_id,
            body=task_body
        ).execute()
        
        logger.info(f"Created Google Task: {task['id']} - {task_data['description']}")
        return task, task_list_id
        
    except Exception as e:
        logger.exception(f"Failed to create Google Task: {e}")
        return None

def create_calendar_event(creds: Credentials, task_data: Dict[str, Any], user_email: str) -> Optional[str]:
    """
    Create a Google Calendar event for tasks with deadlines.
    Returns the event ID if successful, None otherwise.
    """
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Only create calendar events for tasks with due dates
        if not task_data.get('due_date'):
            return None
            
        # Parse due date
        due_date = datetime.strptime(task_data['due_date'], '%Y-%m-%d')
        
        # Create event body
        event_body = {
            'summary': f"Task: {task_data['description']}",
            'description': f"Task from meeting: {task_data.get('context', 'No context provided')}",
            'start': {
                'date': due_date.strftime('%Y-%m-%d'),
                'timeZone': 'UTC',
            },
            'end': {
                'date': (due_date + timedelta(days=1)).strftime('%Y-%m-%d'),
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 60},       # 1 hour before
                ],
            },
        }
        
        # Insert the event
        event = service.events().insert(
            calendarId='primary',
            body=event_body
        ).execute()
        
        logger.info(f"Created Calendar Event: {event['id']} - {task_data['description']}")
        return event['id']
        
    except Exception as e:
        logger.exception(f"Failed to create Calendar Event: {e}")
        return None

def process_meeting_for_tasks(transcript: str, creds: Credentials, user_email: str) -> Dict[str, Any]:
    """
    Main function to process meeting transcript and create Google Tasks/Calendar events.
    """
    logger.info("Processing meeting transcript for task extraction...")
    
    # Extract tasks using AI
    extracted_tasks = extract_tasks_from_transcript(transcript)
    
    if not extracted_tasks:
        logger.info("No tasks found in transcript")
        return {
            "tasks_extracted": 0,
            "tasks_created": 0,
            "events_created": 0,
            "errors": [],
            "extracted_tasks": []
        }
    
    # Process each extracted task
    tasks_created = 0
    events_created = 0
    errors = []
    processed_tasks = []
    
    for task_data in extracted_tasks:
        try:
            # Create Google Task
            task_result = create_google_task(creds, task_data, user_email)
            if task_result:
                task, task_list_id = task_result
                tasks_created += 1
                task_data['google_task_id'] = task['id']
                task_data['google_tasklist_id'] = task_list_id
            
            # Create Calendar Event (if due date exists)
            event_id = create_calendar_event(creds, task_data, user_email)
            if event_id:
                events_created += 1
                
        except Exception as e:
            error_msg = f"Failed to process task '{task_data.get('description', 'Unknown')}': {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        processed_tasks.append(task_data)
    
    result = {
        "tasks_extracted": len(extracted_tasks),
        "tasks_created": tasks_created,
        "events_created": events_created,
        "errors": errors,
        "processed_tasks": processed_tasks
    }
    
    logger.info(f"Task processing complete: {tasks_created} tasks created, {events_created} events created")
    return result 


def update_google_task_status(creds: Credentials, task_id: str, tasklist_id: str, completed: bool) -> bool:
    """Update the completion status of a Google Task."""
    try:
        service = build('tasks', 'v1', credentials=creds, cache_discovery=False)
        
        # Get the current task
        task = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
        
        # Update the status
        task['status'] = 'completed' if completed else 'needsAction'
        
        # Update the task
        service.tasks().update(
            tasklist=tasklist_id,
            task=task_id,
            body=task
        ).execute()
        
        logger.info(f"Updated Google Task {task_id} status to {'completed' if completed else 'active'}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update Google Task {task_id} status: {e}")
        return False


def get_all_google_tasks_status(creds: Credentials) -> Dict[str, bool]:
    """
    Fetches all tasks from all task lists and returns their completion status.
    Returns a dictionary mapping task_id to a boolean (True if completed).
    """
    all_tasks_status = {}
    try:
        service = build('tasks', 'v1', credentials=creds, cache_discovery=False)
        tasklists = service.tasklists().list().execute().get('items', [])
        
        for tasklist in tasklists:
            tasks_result = service.tasks().list(tasklist=tasklist['id'], showCompleted=True, showHidden=True).execute()
            for task in tasks_result.get('items', []):
                all_tasks_status[task['id']] = task.get('status') == 'completed'

    except HttpError as e:
        logger.error(f"Google Tasks API error while fetching all tasks: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error fetching all Google Tasks status: {e}")
        
    return all_tasks_status