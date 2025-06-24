"""
Google Drive helpers: registering push channels and retrieving transcript
content triggered by webhook events.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Tuple, List

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dateutil import parser as dateparse
from loguru import logger

from core.config import settings
from core.crypto import decrypt
from models.user import User

MIME_TEXT = "text/plain"
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar"
]


# ─── Public helpers ──────────────────────────────────────────────────────────


async def ensure_drive_watch(user: User) -> None:
    """
    Idempotently ensure there is a valid watch channel for the given user.
    Stores channel info back to the user object if it had to renew.
    
    NOTE: Commented out for local development - no webhooks needed.
    """
    # Webhook functionality disabled for local development
    # No ngrok or public URL required
    logger.info("Drive watch disabled for local development (user: {})", user.email)
    return
    
    # ORIGINAL WEBHOOK CODE (commented out for local development):
    # if (
    #     user.drive_channel_id
    #     and user.drive_channel_expire_at
    #     and user.drive_channel_expire_at > datetime.utcnow() + timedelta(hours=24)
    # ):
    #     return  # still valid for >24 h

    # creds = _credentials_from_user(user)
    # service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # # 1. get latest page token
    # start_page_token = (
    #     service.changes().getStartPageToken().execute().get("startPageToken")
    # )

    # # 2. create channel
    # channel_id = str(uuid.uuid4())
    # body = {
    #     "id": channel_id,
    #     "type": "web_hook",
    #     "address": settings.drive_webhook_address,
    #     "token": str(user.id),  # echoed in notifications for easy lookup
    #     "payload": False,
    # }
    # resp = service.changes().watch(body=body, pageToken=start_page_token).execute()
    # logger.info("Registered Drive watch for user {} (channel {})", user.email, channel_id)

    # # 3. update user
    # user.drive_channel_id = resp["id"]
    # user.drive_page_token = start_page_token
    # # `expiration` is ms‑since‑epoch string
    # user.drive_channel_expire_at = datetime.fromtimestamp(
    #     int(resp["expiration"]) / 1000, tz=timezone.utc
    # )


def parse_drive_headers(headers: dict[str, str]) -> dict[str, str]:
    """Extract the handful of headers we care about (case‑insensitive)."""
    wanted = (
        "x-goog-resource-id",
        "x-goog-resource-state",
        "x-goog-channel-id",
        "x-goog-message-number",
        "x-goog-resource-uri",
        "x-goog-changed",
        "x-goog-channel-token",
    )
    return {k.lower(): v for k, v in headers.items() if k.lower() in wanted}


def list_changes(
    user: User,
) -> Tuple[List[dict[str, Any]], str]:
    """
    Return list of Drive changes since last `drive_page_token`
    and the new startPageToken to save.
    """
    creds = _credentials_from_user(user)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    results = (
        service.changes()
        .list(
            pageToken=user.drive_page_token,
            spaces="drive",
            fields="nextPageToken,newStartPageToken,changes(file(id,name,mimeType,trashed,modifiedTime))",
        )
        .execute()
    )
    changes = results.get("changes", [])
    new_token = results.get("newStartPageToken") or user.drive_page_token
    return changes, new_token


def download_plain_text(file_id: str, creds: Credentials) -> Tuple[str, str]:
    """
    Returns (file_name, str_content). Handles plain text, Google Docs, and .docx files.
    """
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    meta = (
        service.files()
        .get(fileId=file_id, fields="name,mimeType,modifiedTime")
        .execute()
    )
    name = meta["name"]
    mime = meta["mimeType"]

    if mime == MIME_TEXT:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        content = fh.getvalue().decode()
        return name, content
    elif mime == "application/vnd.google-apps.document":
        # Export Google Doc as plain text
        request = service.files().export_media(fileId=file_id, mimeType=MIME_TEXT)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        content = fh.getvalue().decode()
        return name, content
    elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        # Download .docx and extract text
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        fh.seek(0)
        try:
            from docx import Document
            doc = Document(fh)
            text = "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            text = f"[Error reading .docx: {e}]"
        return name, text
    else:
        raise ValueError(f"Unsupported mime type: {mime}")


# ─── internal helpers ────────────────────────────────────────────────────────


def _credentials_from_user(user: User) -> Credentials:
    refresh_token = decrypt(user.refresh_token_enc)
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    # force refresh so we have an access token
    creds.refresh(Request())
    return creds

def find_meet_folder_id(creds) -> str | None:
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    resp = (
        service.files()
        .list(
            q="name = 'Meet Recordings' "
              "and mimeType = 'application/vnd.google-apps.folder' "
              "and trashed = false",
            spaces="drive",
            fields="files(id)",
            pageSize=1,
        )
        .execute()
    )
    files = resp.get("files", [])
    return files[0]["id"] if files else None
