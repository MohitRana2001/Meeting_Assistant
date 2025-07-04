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
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from dateutil import parser as dateparse
from loguru import logger

from core.config import settings
from models.user import User
from services.google_helper import credentials_from_user

MIME_TEXT = "text/plain"


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


def list_changes(user: User) -> Tuple[List[dict[str, Any]], str]:
    """
    Return a list of all Drive changes since the last `drive_page_token`
    and the new startPageToken to save for the next run.

    This function correctly handles initial sync and pagination.
    """
    creds = credentials_from_user(user)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    page_token = user.drive_page_token

    # --- 1. Handle Initial Sync ---
    # If the user has no token, we must get a starting point.
    if not page_token:
        logger.info("No page token for user {}, performing first-time sync setup.", user.email)
        
        initial_changes: List[dict[str, Any]] = []
        
        if user.meet_folder_id:
            query = f"'{user.meet_folder_id}' in parents and trashed = false"
            next_page_token: str | None = None
            
            while True:
                file_resp = (
                    service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name, mimeType, trashed, modifiedTime, parents)",
                        pageToken=next_page_token,
                    )
                    .execute()
                )
                
                for f in file_resp.get("files", []):
                    initial_changes.append({"file": f})
                    
                next_page_token = file_resp.get("nextPageToken")
                if not next_page_token:
                    break
        else:
            # If no meet_folder_id, we can't list files, so we just return empty.
            logger.warning(
                "User {} does not have a meet_folder_id set. Initial sync will skip existing files.",
                user.email,
            )
        
        response = service.changes().getStartPageToken().execute()
        
        start_token = response.get('startPageToken')

        logger.info("Initial sync for user {} found {} existing files in 'Meet Recordings' folder.", user.email, len(initial_changes))
        return initial_changes, start_token

    # --- 2. Fetch Changes with Pagination ---
    all_changes = []
    logger.info("Fetching changes for user {} starting from token: {}", user.email, page_token)
    
    while page_token:
        try:
            response = (
                service.changes()
                .list(
                    pageToken=page_token,
                    spaces="drive",
                    # Add 'parents' to fields since your refresh function uses it.
                    fields="nextPageToken, newStartPageToken, changes(file(id, name, mimeType, trashed, modifiedTime, parents))",
                )
                .execute()
            )
            
            all_changes.extend(response.get("changes", []))
            
            # Move to the next page if one exists
            if "nextPageToken" in response:
                page_token = response["nextPageToken"]
            else:
                # This was the last page. Get the final token for the next sync.
                page_token = response.get("newStartPageToken")
                # The loop will naturally end here as page_token might be None
                # or it will be the newStartPageToken which we want to return.
                break

        except HttpError as error:
            logger.error("An HttpError occurred: {}. Token may be invalid.", error)
            # This can happen if the token expires. Resetting by getting a new start token.
            response = service.changes().getStartPageToken().execute()
            new_token = response.get('startPageToken')
            return [], new_token # Reset the process

    final_token = page_token or user.drive_page_token
    return all_changes, final_token


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


# ─── internal helpers ─────────────────────────────────────────────────────────


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
