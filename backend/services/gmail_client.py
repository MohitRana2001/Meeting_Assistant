"""
Gmail helpers for scanning meeting summaries shared via email.
"""

from __future__ import annotations

import base64
import re
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from loguru import logger
from dateutil import parser as dateparse
from docx import Document

from core.config import settings
from models.user import User
from services import google_helper, summarizer, task_extractor

# --- Constants for Keyword Matching ---

SUMMARY_SUBJECT_KEYWORDS = [
    "meeting summary", "meeting notes", "meeting transcript",
    "meeting recording", "action items", "meeting minutes",
    "zoom recording", "teams recording", "google meet recording",
    "Notes:"
]

SUBJECT_KEYWORDS = [
    "Meeting Notes", "Meeting Summary", "Meeting Transcript", "Action Items", "Meeting Minutes"
]

SUMMARY_BODY_KEYWORDS = [
    "action items", "next steps", "follow up", "decisions made",
    "meeting attendees", "agenda", "discussion points",
    "transcript", "recording", "summary"
]

ACTION_ITEM_HEADERS = ['action items', 'next steps', 'follow up', 'tasks', 'to do', 'action points']
SUMMARY_SECTION_HEADERS = ['summary', 'overview', 'discussion', 'meeting notes', 'notes']


def _extract_text_from_attachment(content_bytes: bytes, mime_type: str) -> Optional[str]:
    """Extracts text from attachment bytes based on mime type."""
    if mime_type == 'text/plain':
        return content_bytes.decode('utf-8', errors='ignore')
    
    if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        try:
            fh = io.BytesIO(content_bytes)
            doc = Document(fh)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error("Failed to read .docx attachment: {}", e)
            return None
            
    logger.warning("Unsupported attachment mime type for text extraction: {}", mime_type)
    return None


def scan_gmail_for_meeting_summaries(user: User, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Scan Gmail for emails with meeting summary attachments based on subject keywords.
    """
    if not settings.ENABLE_GMAIL:
        logger.info("Gmail integration disabled via config; skipping Gmail scan.")
        return []

    try:
        creds = google_helper.credentials_from_user(user)
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)

        # Calculate date range
        since_date = datetime.now() - timedelta(days=days_back)

        # 1. Search only in subjects for specific keywords and ensure it has an attachment.
        query = f'after:{since_date.strftime("%Y/%m/%d")} has:attachment ('
        # Remove quotes from keywords to allow for broader matching (e.g., "Meeting Notes for Project X")
        # instead of exact phrase match "Meeting Notes".
        query += ' OR '.join([f'subject:({k})' for k in SUBJECT_KEYWORDS])
        query += ')'
        logger.info("Gmail search query: {}", query)

        # Search for relevant emails
        results = service.users().messages().list(
            userId='me', q=query, maxResults=50
        ).execute()

        messages = results.get('messages', [])
        all_summaries = []

        if not messages:
            logger.info("No emails with meeting summary subjects and attachments found.")
            return []

        logger.info("Found {} potentially relevant emails. Starting processing...", len(messages))

        for i, message_header in enumerate(messages):
            try:
                # Get full message details
                msg = service.users().messages().get(userId='me', id=message_header['id'], format='full').execute()

                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                # Log the subject of the first 10 emails found for debugging
                if i < 10:
                    logger.info(f"  [Scan Log] Checking email {i+1}/{len(messages)}: '{subject}'")

                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                email_date = dateparse.parse(date_str)

                # 2. Get attachments for the found email.
                attachments = get_gmail_attachment_links(user, msg['id'])
                if not attachments:
                    continue

                for attachment_meta in attachments:
                    # 3. Download and process each attachment.
                    logger.info("Processing attachment '{}' from email '{}'", attachment_meta['filename'], subject)
                    content_bytes = download_gmail_attachment(user, msg['id'], attachment_meta['attachment_id'])
                    if not content_bytes:
                        continue

                    content_text = _extract_text_from_attachment(content_bytes, attachment_meta['mime_type'])
                    if not content_text or len(content_text) < 50:
                        logger.warning("Could not extract meaningful text from attachment '{}'", attachment_meta['filename'])
                        continue

                    # 4. Give it to the summarizer and task extractor
                    summary_dict = summarizer.summarise_transcript(content_text)
                    google_result = task_extractor.process_meeting_for_tasks(content_text, creds, user.email)

                    formatted_tasks = []
                    processed_tasks = google_result.get('processed_tasks', [])
                    if processed_tasks:
                        for i, task in enumerate(processed_tasks):
                            formatted_tasks.append({
                                "id": str(i + 1), "text": task['description'], "completed": False,
                                "google_task_id": task.get("google_task_id"),
                                "google_tasklist_id": task.get("google_tasklist_id"),
                            })

                    final_summary = {
                        'title': summary_dict.get('title') or extract_meeting_title_from_subject(subject),
                        'summary': summary_dict.get('summary', ''),
                        'tasks': formatted_tasks,
                        'created_at': email_date, 'sender': sender, 'source': 'gmail',
                        'email_id': msg['id'], 'attachment_filename': attachment_meta['filename'],
                    }
                    all_summaries.append(final_summary)
                    logger.info("Successfully created summary from attachment '{}'", attachment_meta['filename'])

            except Exception as e:
                logger.error(f"Failed to process email {message_header['id']}: {e}")
                continue

        logger.info(f"Found {len(all_summaries)} meeting summaries in Gmail for user {user.email}")
        return all_summaries

    except HttpError as e:
        logger.error(f"Gmail API error for user {user.email}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error scanning Gmail for user {user.email}: {e}")
        return []


def extract_email_body(payload: Dict[str, Any]) -> str:
    """Extract the body text from an email payload."""
    body_parts = []
    html_parts = []

    def _recursive_extract(part):
        mime_type = part.get('mimeType', '')
        if 'text/plain' in mime_type:
            if part.get('body', {}).get('data'):
                body_parts.append(base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore'))
        elif 'text/html' in mime_type:
            if part.get('body', {}).get('data'):
                html_parts.append(base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore'))
        elif 'multipart' in mime_type and part.get('parts'):
            for sub_part in part['parts']:
                _recursive_extract(sub_part)

    _recursive_extract(payload)

    body = "\n".join(body_parts)
    if not body and html_parts:
        # Basic HTML to text conversion as a fallback
        body = re.sub(r'<[^>]+>', '', "\n".join(html_parts))
    
    return body.strip()


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


def get_gmail_attachment_links(user: User, email_id: str) -> List[Dict[str, Any]]:
    """
    Get attachment download links from a Gmail message.
    Enhanced to handle meeting summary attachments.
    """
    if not settings.ENABLE_GMAIL:
        logger.info("Gmail integration disabled via config; skipping attachment retrieval.")
        return []

    try:
        creds = google_helper.credentials_from_user(user)
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
    if not settings.ENABLE_GMAIL:
        logger.info("Gmail integration disabled via config; skipping attachment download.")
        return None

    try:
        creds = google_helper.credentials_from_user(user)
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