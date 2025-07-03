"""
Gmail helpers for scanning meeting summaries shared via email.
"""

from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from loguru import logger

from models.user import User
from services import drive_client


def scan_gmail_for_meeting_summaries(user: User, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Scan Gmail for meeting summaries shared via email.
    Returns list of meeting summaries found in emails.
    """
    try:
        creds = drive_client._credentials_from_user(user)
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        
        # Calculate date range
        since_date = datetime.now() - timedelta(days=days_back)
        
        # Enhanced query to specifically look for "Notes:" emails and other patterns
        query_parts = [
            f'after:{since_date.strftime("%Y/%m/%d")}',
            '(',
            'subject:Notes:',  # Specific pattern for meeting notes
            'OR subject:(meeting summary)',
            'OR subject:(meeting notes)', 
            'OR subject:(transcript)',
            'OR subject:(recording)',
            'OR subject:(action items)',
            'OR subject:(meeting minutes)',
            ')'
        ]
        query = ' '.join(query_parts)
        
        # Search for relevant emails
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=100  # Increased limit to catch more Notes: emails
        ).execute()
        
        messages = results.get('messages', [])
        meeting_summaries = []
        
        for message in messages:
            try:
                # Get full message details
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract meeting summary data
                summary_data = extract_meeting_summary_from_email(msg)
                if summary_data:
                    summary_data['source'] = 'gmail'
                    summary_data['email_id'] = message['id']
                    
                    # Check for attachments if this is a Notes: email
                    headers = msg['payload'].get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    
                    if subject.startswith('Notes:'):
                        attachments = get_gmail_attachment_links(user, message['id'])
                        if attachments:
                            summary_data['attachments'] = attachments
                            logger.info(f"Found {len(attachments)} attachments in Notes: email")
                    
                    meeting_summaries.append(summary_data)
                    
            except Exception as e:
                logger.error(f"Failed to process email {message['id']}: {e}")
                continue
        
        logger.info(f"Found {len(meeting_summaries)} meeting summaries in Gmail for user {user.email}")
        return meeting_summaries
        
    except HttpError as e:
        logger.error(f"Gmail API error for user {user.email}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error scanning Gmail for user {user.email}: {e}")
        return []


def extract_meeting_summary_from_email(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract meeting summary data from a Gmail message.
    """
    try:
        headers = message['payload'].get('headers', [])
        
        # Extract basic email info
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Parse date
        try:
            email_date = datetime.strptime(date_str.split(' (')[0], '%a, %d %b %Y %H:%M:%S %z')
        except:
            email_date = datetime.now()
        
        # Extract email body
        body = extract_email_body(message['payload'])
        
        if not body:
            return None
        
        # Look for meeting summary patterns
        if not is_meeting_summary_email(subject, body, sender):
            return None
        
        # Extract meeting title from subject
        meeting_title = extract_meeting_title_from_subject(subject)
        
        # Extract summary text and tasks
        summary_text, tasks = parse_meeting_content_from_email(body)
        
        if not summary_text and not tasks:
            return None
        
        return {
            'title': meeting_title,
            'summary': summary_text,
            'tasks': tasks,
            'created_at': email_date,
            'sender': sender,
            'subject': subject
        }
        
    except Exception as e:
        logger.error(f"Failed to extract meeting summary from email: {e}")
        return None


def extract_email_body(payload: Dict[str, Any]) -> str:
    """Extract the body text from an email payload."""
    body = ""
    
    if payload.get('body', {}).get('data'):
        # Single part message
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif payload.get('parts'):
        # Multi-part message
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if part.get('body', {}).get('data'):
                    part_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    body += part_body
            elif part['mimeType'] == 'text/html' and not body:
                # Fallback to HTML if no plain text
                if part.get('body', {}).get('data'):
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    # Basic HTML to text conversion
                    body = re.sub(r'<[^>]+>', '', html_body)
    
    return body.strip()


def is_meeting_summary_email(subject: str, body: str, sender: str) -> bool:
    """
    Determine if an email contains a meeting summary.
    Enhanced to prioritize "Notes:" emails.
    """
    subject_lower = subject.lower()
    body_lower = body.lower()
    
    # Priority check for "Notes:" emails
    if subject.startswith('Notes:'):
        return True
    
    # Check for meeting summary indicators in subject
    summary_keywords = [
        'meeting summary', 'meeting notes', 'meeting transcript', 
        'meeting recording', 'action items', 'meeting minutes',
        'zoom recording', 'teams recording', 'google meet recording'
    ]
    
    # Check for meeting content indicators in body
    content_keywords = [
        'action items', 'next steps', 'follow up', 'decisions made',
        'meeting attendees', 'agenda', 'discussion points',
        'transcript', 'recording', 'summary'
    ]
    
    # Check subject
    has_summary_subject = any(keyword in subject_lower for keyword in summary_keywords)
    
    # Check body content
    has_content_indicators = any(keyword in body_lower for keyword in content_keywords)
    
    # Check if it's from a likely meeting platform or colleague
    is_from_meeting_platform = any(platform in sender.lower() for platform in [
        'zoom', 'teams', 'meet', 'webex', 'google.com'
    ])
    
    # Must have at least subject keywords and some content, or be from meeting platform
    return (has_summary_subject and has_content_indicators) or (is_from_meeting_platform and has_summary_subject)


def extract_meeting_title_from_subject(subject: str) -> str:
    """
    Extract a clean meeting title from the email subject.
    Enhanced to handle "Notes:" prefix.
    """
    title = subject
    
    # Handle "Notes:" prefix specifically
    if title.startswith('Notes:'):
        title = title[6:].strip()  # Remove "Notes:" and whitespace
    
    # Remove common prefixes
    prefixes_to_remove = [
        'meeting summary:', 'meeting notes:', 'meeting transcript:',
        'recording:', 'summary:', 'notes:', 'fwd:', 're:'
    ]
    
    for prefix in prefixes_to_remove:
        if title.lower().startswith(prefix.lower()):
            title = title[len(prefix):].strip()
    
    # Remove meeting platform indicators
    patterns_to_remove = [
        r'\[zoom\]', r'\[teams\]', r'\[meet\]', r'\[recording\]',
        r'- recording', r'recording -', r'transcript -'
    ]
    
    for pattern in patterns_to_remove:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
    
    return title if title else "Meeting Summary"


def parse_meeting_content_from_email(body: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Parse meeting summary text and action items from email body.
    """
    lines = body.split('\n')
    summary_lines = []
    tasks = []
    current_section = None
    
    # Common section headers
    action_headers = ['action items', 'next steps', 'follow up', 'tasks', 'to do', 'action points']
    summary_headers = ['summary', 'overview', 'discussion', 'meeting notes', 'notes']
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        line_lower = line.lower()
        
        # Check if this line is a section header
        if any(header in line_lower for header in action_headers):
            current_section = 'actions'
            continue
        elif any(header in line_lower for header in summary_headers):
            current_section = 'summary'
            continue
        
        # Parse content based on current section
        if current_section == 'actions':
            # Look for action items (bullets, numbers, dashes)
            if re.match(r'^[\-\*\•\d\.\)]\s*', line) or line.lower().startswith(('- ', '* ', '• ')):
                task_text = re.sub(r'^[\-\*\•\d\.\)\s]+', '', line).strip()
                if len(task_text) > 5:  # Ignore very short items
                    tasks.append({
                        'id': str(len(tasks) + 1),
                        'text': task_text,
                        'completed': False
                    })
        elif current_section == 'summary':
            # Add to summary if it's substantial content
            if len(line) > 20 and not line.lower().startswith(('from:', 'to:', 'subject:', 'date:')):
                summary_lines.append(line)
        else:
            # If no section identified, try to auto-detect content
            if re.match(r'^[\-\*\•\d\.\)]\s*', line):
                task_text = re.sub(r'^[\-\*\•\d\.\)\s]+', '', line).strip()
                if len(task_text) > 5 and any(keyword in task_text.lower() for keyword in ['will', 'should', 'need', 'action', 'follow', 'complete']):
                    tasks.append({
                        'id': str(len(tasks) + 1),
                        'text': task_text,
                        'completed': False
                    })
            elif len(line) > 30:
                summary_lines.append(line)
    
    # Clean up summary
    summary = '\n'.join(summary_lines[:10])  # Limit to first 10 substantial lines
    if len(summary) > 1000:
        summary = summary[:1000] + "..."
    
    return summary, tasks


def get_gmail_attachment_links(user: User, email_id: str) -> List[Dict[str, Any]]:
    """
    Get attachment download links from a Gmail message.
    Enhanced to handle meeting summary attachments.
    """
    try:
        creds = drive_client._credentials_from_user(user)
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        
        message = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        attachments = []
        payload = message['payload']
        
        def extract_attachments(part):
            if part.get('filename'):
                attachment_id = part['body'].get('attachmentId')
                if attachment_id:
                    # Filter for likely meeting summary attachments
                    filename = part['filename'].lower()
                    mime_type = part['mimeType']
                    
                    # Check if this is likely a meeting summary attachment
                    is_meeting_attachment = (
                        # Document files
                        mime_type in [
                            'application/pdf',
                            'application/vnd.google-apps.document',
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            'text/plain'
                        ] or
                        # Filenames suggesting meeting content
                        any(keyword in filename for keyword in [
                            'notes', 'summary', 'transcript', 'meeting', 'minutes'
                        ])
                    )
                    
                    if is_meeting_attachment:
                        attachments.append({
                            'filename': part['filename'],
                            'attachment_id': attachment_id,
                            'mime_type': part['mimeType'],
                            'size': part['body'].get('size', 0)
                        })
            
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_attachments(subpart)
        
        extract_attachments(payload)
        return attachments
        
    except Exception as e:
        logger.error(f"Failed to get attachments for email {email_id}: {e}")
        return []


def download_gmail_attachment(user: User, email_id: str, attachment_id: str) -> Optional[bytes]:
    """
    Download a specific attachment from a Gmail message.
    """
    try:
        creds = drive_client._credentials_from_user(user)
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=email_id,
            id=attachment_id
        ).execute()
        
        # Decode the attachment data
        data = attachment['data']
        # Gmail uses URL-safe base64 encoding
        file_data = base64.urlsafe_b64decode(data)
        
        return file_data
        
    except Exception as e:
        logger.error(f"Failed to download attachment {attachment_id} from email {email_id}: {e}")
        return None 