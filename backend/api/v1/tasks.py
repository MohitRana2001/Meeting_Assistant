"""
Google Tasks API endpoints for task synchronization.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from core.database import get_session
from core.security import get_current_user
from models.user import User
from models.summary import MeetingSummary
from services import drive_client
from services.task_extractor import create_google_task, create_calendar_event

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_existing_google_tasks(tasks_service, task_list_id: str) -> List[Dict[str, Any]]:
    """Get all existing tasks from a Google Tasks list."""
    try:
        tasks_result = tasks_service.tasks().list(tasklist=task_list_id).execute()
        return tasks_result.get('items', [])
    except Exception as e:
        logger.error(f"Failed to get existing Google Tasks: {e}")
        return []


def is_task_duplicate(task_text: str, existing_tasks: List[Dict[str, Any]], meeting_title: str) -> bool:
    """Check if a task already exists in Google Tasks."""
    task_text_lower = task_text.lower().strip()
    
    for existing_task in existing_tasks:
        existing_title = existing_task.get('title', '').lower().strip()
        existing_notes = existing_task.get('notes', '').lower()
        
        # Check if task title matches exactly
        if existing_title == task_text_lower:
            return True
        
        # Check if task is very similar (80% match) and from same meeting
        if (len(task_text_lower) > 10 and 
            task_text_lower in existing_title and 
            meeting_title.lower() in existing_notes):
            return True
            
    return False


@router.post("/sync/{summary_id}")
async def sync_tasks_to_google(
    summary_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Sync tasks from a specific meeting summary to Google Tasks.
    """
    try:
        # Get the meeting summary
        stmt = (
            select(MeetingSummary)
            .where(MeetingSummary.id == summary_id)
            .where(MeetingSummary.user_id == current_user.id)
        )
        result = await session.execute(stmt)
        summary = result.scalar_one_or_none()
        
        if not summary:
            raise HTTPException(status_code=404, detail="Meeting summary not found")
        
        if not summary.tasks or len(summary.tasks) == 0:
            return {
                "success": True,
                "message": "No tasks to sync",
                "tasks_synced": 0,
                "tasks_skipped": 0,
                "calendar_events_created": 0
            }
        
        # Get Google credentials
        creds = drive_client._credentials_from_user(current_user)
        
        # Get the default task list ID
        tasks_service = build('tasks', 'v1', credentials=creds, cache_discovery=False)
        tasklists = tasks_service.tasklists().list().execute()
        
        if not tasklists.get('items'):
            raise HTTPException(status_code=500, detail="No Google Tasks lists found")
        
        task_list_id = tasklists['items'][0]['id']
        task_list_title = tasklists['items'][0]['title']
        
        # Create a dedicated task list for this meeting if we have many tasks
        if len(summary.tasks) >= 3:
            meeting_list_body = {
                'title': f"Meeting: {summary.title[:50]}"
            }
            
            # Check if this meeting list already exists
            existing_list = None
            for tasklist in tasklists.get('items', []):
                if tasklist['title'] == meeting_list_body['title']:
                    existing_list = tasklist
                    break
            
            if existing_list:
                task_list_id = existing_list['id']
                task_list_title = existing_list['title']
                logger.info(f"Using existing task list: {task_list_title}")
            else:
                try:
                    meeting_list = tasks_service.tasklists().insert(body=meeting_list_body).execute()
                    task_list_id = meeting_list['id']
                    task_list_title = meeting_list['title']
                    logger.info(f"Created dedicated task list: {task_list_title}")
                except Exception as e:
                    logger.warning(f"Failed to create dedicated task list, using default: {e}")
        
        # Get existing tasks to check for duplicates
        existing_tasks = get_existing_google_tasks(tasks_service, task_list_id)
        
        # Sync tasks to Google Tasks
        tasks_synced = 0
        tasks_skipped = 0
        calendar_events_created = 0
        sync_errors = []
        
        for task in summary.tasks:
            try:
                # Check for duplicates
                if is_task_duplicate(task['text'], existing_tasks, summary.title):
                    tasks_skipped += 1
                    logger.info(f"Skipped duplicate task: {task['text']}")
                    continue
                
                # Create Google Task
                task_body = {
                    'title': task['text'],
                    'notes': f"From meeting: {summary.title}\nMeeting Date: {summary.created_at.strftime('%Y-%m-%d %H:%M')}\nSync ID: meeting_{summary.id}_task_{task['id']}"
                }
                
                # Set task status based on completion
                if task.get('completed', False):
                    task_body['status'] = 'completed'
                
                google_task = tasks_service.tasks().insert(
                    tasklist=task_list_id,
                    body=task_body
                ).execute()
                
                tasks_synced += 1
                logger.info(f"Synced task to Google Tasks: {task['text']}")
                
            except Exception as e:
                error_msg = f"Failed to sync task '{task['text']}': {str(e)}"
                sync_errors.append(error_msg)
                logger.error(error_msg)
        
        # Generate task list URL
        task_list_url = f"https://tasks.google.com/embed/?origin=https://calendar.google.com&fullWidth=1"
        
        # Create success message
        if tasks_synced > 0 and tasks_skipped > 0:
            message = f"Successfully synced {tasks_synced} new tasks to Google Tasks (skipped {tasks_skipped} duplicates)"
        elif tasks_synced > 0:
            message = f"Successfully synced {tasks_synced} tasks to Google Tasks"
        elif tasks_skipped > 0:
            message = f"All {tasks_skipped} tasks were already synced to Google Tasks"
        else:
            message = "No tasks were synced"
        
        logger.info(
            f"Sync completed for summary {summary_id}: {tasks_synced} tasks synced, {tasks_skipped} skipped, {calendar_events_created} events created"
        )
        
        return {
            "success": True,
            "message": message,
            "tasks_synced": tasks_synced,
            "tasks_skipped": tasks_skipped,
            "calendar_events_created": calendar_events_created,
            "task_list_title": task_list_title,
            "task_list_url": task_list_url,
            "errors": sync_errors if sync_errors else None
        }
        
    except HttpError as e:
        logger.error(f"Google Tasks API error for user {current_user.email}: {e}")
        if e.resp.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Google Tasks access not granted. Please reauthorize the application."
            )
        raise HTTPException(status_code=500, detail="Failed to sync tasks to Google Tasks")
    
    except Exception as e:
        logger.exception(f"Unexpected error syncing tasks for user {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync tasks to Google Tasks")


@router.post("/sync-all")
async def sync_all_tasks_to_google(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Sync tasks from recent meeting summaries to Google Tasks.
    """
    try:
        # Get recent meeting summaries
        stmt = (
            select(MeetingSummary)
            .where(MeetingSummary.user_id == current_user.id)
            .order_by(desc(MeetingSummary.created_at))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        summaries = result.scalars().all()
        
        if not summaries:
            return {
                "success": True,
                "message": "No meeting summaries found",
                "summaries_processed": 0,
                "total_tasks_synced": 0
            }
        
        # Process each summary
        summaries_processed = 0
        total_tasks_synced = 0
        sync_errors = []
        
        for summary in summaries:
            if not summary.tasks or len(summary.tasks) == 0:
                continue
                
            try:
                # Call the single summary sync function
                sync_result = await sync_tasks_to_google(
                    str(summary.id), current_user, session
                )
                
                if sync_result['success']:
                    summaries_processed += 1
                    total_tasks_synced += sync_result['tasks_synced']
                else:
                    sync_errors.append(f"Failed to sync summary '{summary.title}'")
                    
            except Exception as e:
                error_msg = f"Failed to sync summary '{summary.title}': {str(e)}"
                sync_errors.append(error_msg)
                logger.error(error_msg)
        
        logger.info(
            f"Bulk sync completed for user {current_user.email}: {summaries_processed} summaries, {total_tasks_synced} tasks"
        )
        
        return {
            "success": True,
            "message": f"Synced tasks from {summaries_processed} meeting summaries",
            "summaries_processed": summaries_processed,
            "total_tasks_synced": total_tasks_synced,
            "errors": sync_errors if sync_errors else None
        }
        
    except Exception as e:
        logger.exception(f"Unexpected error in bulk sync for user {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync tasks")


@router.get("/")
async def get_user_tasks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[Dict[str, Any]]:
    """
    Get all tasks from user's meeting summaries.
    """
    try:
        # Get all meeting summaries with tasks
        stmt = (
            select(MeetingSummary)
            .where(MeetingSummary.user_id == current_user.id)
            .order_by(desc(MeetingSummary.created_at))
        )
        
        result = await session.execute(stmt)
        summaries = result.scalars().all()
        
        all_tasks = []
        for summary in summaries:
            if summary.tasks:
                for task in summary.tasks:
                    all_tasks.append({
                        "id": f"{summary.id}_{task['id']}",
                        "text": task['text'],
                        "completed": task.get('completed', False),
                        "summary_id": summary.id,
                        "summary_title": summary.title,
                        "created_at": summary.created_at.isoformat()
                    })
        
        logger.info(f"Retrieved {len(all_tasks)} tasks for user {current_user.email}")
        return all_tasks
        
    except Exception as e:
        logger.exception(f"Error retrieving tasks for user {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks")


@router.get("/google-tasks")
async def get_google_tasks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[Dict[str, Any]]:
    """
    Get tasks directly from Google Tasks API.
    """
    try:
        creds = drive_client._credentials_from_user(current_user)
        service = build('tasks', 'v1', credentials=creds, cache_discovery=False)
        
        # Get all task lists
        tasklists = service.tasklists().list().execute()
        
        all_google_tasks = []
        for tasklist in tasklists.get('items', []):
            # Get tasks from this list
            tasks_result = service.tasks().list(tasklist=tasklist['id']).execute()
            
            for task in tasks_result.get('items', []):
                all_google_tasks.append({
                    "id": task['id'],
                    "title": task['title'],
                    "notes": task.get('notes', ''),
                    "status": task['status'],
                    "due": task.get('due'),
                    "updated": task['updated'],
                    "tasklist_id": tasklist['id'],
                    "tasklist_title": tasklist['title']
                })
        
        logger.info(f"Retrieved {len(all_google_tasks)} Google Tasks for user {current_user.email}")
        return all_google_tasks
        
    except HttpError as e:
        logger.error(f"Google Tasks API error for user {current_user.email}: {e}")
        if e.resp.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Google Tasks access not granted. Please reauthorize the application."
            )
        raise HTTPException(status_code=500, detail="Failed to fetch Google Tasks")
    
    except Exception as e:
        logger.exception(f"Unexpected error fetching Google Tasks for user {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch Google Tasks")


def find_google_task_by_sync_id(tasks_service, sync_id: str) -> Optional[Dict[str, Any]]:
    """Find a Google Task by its sync ID in the notes."""
    try:
        # Get all task lists
        tasklists = tasks_service.tasklists().list().execute()
        
        for tasklist in tasklists.get('items', []):
            # Get tasks from this list
            tasks_result = tasks_service.tasks().list(tasklist=tasklist['id']).execute()
            
            for task in tasks_result.get('items', []):
                notes = task.get('notes', '')
                if sync_id in notes:
                    return {
                        'task': task,
                        'tasklist_id': tasklist['id']
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to find Google Task by sync ID {sync_id}: {e}")
        return None


def update_google_task_status(tasks_service, task_id: str, tasklist_id: str, completed: bool) -> bool:
    """Update the completion status of a Google Task."""
    try:
        # Get the current task
        task = tasks_service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
        
        # Update the status
        task['status'] = 'completed' if completed else 'needsAction'
        
        # Update the task
        tasks_service.tasks().update(
            tasklist=tasklist_id,
            task=task_id,
            body=task
        ).execute()
        
        logger.info(f"Updated Google Task {task_id} status to {'completed' if completed else 'active'}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update Google Task {task_id} status: {e}")
        return False


@router.patch("/update-google-task-status/{summary_id}/{task_id}")
async def update_google_task_completion(
    summary_id: str,
    task_id: str,
    completed: bool,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Update task completion status in both local database and Google Tasks.
    """
    try:
        # Get the meeting summary
        stmt = (
            select(MeetingSummary)
            .where(MeetingSummary.id == summary_id)
            .where(MeetingSummary.user_id == current_user.id)
        )
        result = await session.execute(stmt)
        summary = result.scalar_one_or_none()
        
        if not summary:
            raise HTTPException(status_code=404, detail="Meeting summary not found")
        
        # Find the task in the summary
        task_found = False
        for task in summary.tasks or []:
            if task.get('id') == task_id:
                task['completed'] = completed
                task_found = True
                break
        
        if not task_found:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update local database
        await session.commit()
        
        # Update Google Tasks
        try:
            creds = drive_client._credentials_from_user(current_user)
            tasks_service = build('tasks', 'v1', credentials=creds, cache_discovery=False)
            
            # Look for the corresponding Google Task using sync ID
            sync_id = f"meeting_{summary.id}_task_{task_id}"
            google_task_info = find_google_task_by_sync_id(tasks_service, sync_id)
            
            if google_task_info:
                google_task = google_task_info['task']
                tasklist_id = google_task_info['tasklist_id']
                
                success = update_google_task_status(
                    tasks_service, 
                    google_task['id'], 
                    tasklist_id, 
                    completed
                )
                
                if success:
                    return {
                        "success": True,
                        "message": f"Task {'completed' if completed else 'reopened'} in both local and Google Tasks",
                        "google_task_updated": True
                    }
                else:
                    return {
                        "success": True,
                        "message": f"Task {'completed' if completed else 'reopened'} locally, but failed to update Google Tasks",
                        "google_task_updated": False
                    }
            else:
                return {
                    "success": True,
                    "message": f"Task {'completed' if completed else 'reopened'} locally. No corresponding Google Task found.",
                    "google_task_updated": False
                }
                
        except Exception as e:
            logger.warning(f"Failed to update Google Tasks for user {current_user.email}: {e}")
            return {
                "success": True,
                "message": f"Task {'completed' if completed else 'reopened'} locally, but Google Tasks update failed",
                "google_task_updated": False
            }
        
    except Exception as e:
        logger.exception(f"Unexpected error updating task status for user {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update task status") 