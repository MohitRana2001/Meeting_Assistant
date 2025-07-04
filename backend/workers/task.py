"""
Celery app & placeholder task for Phase 1.

Run worker locally after installing Redis:
    celery -A workers.tasks worker --loglevel=info
"""

from __future__ import annotations

import json
from typing import Any, List

from celery import Celery
from loguru import logger
from sqlmodel import Session, select


from core.config import settings
from core.database import async_session_factory, sync_engine
from models.user import User
from models.summary import MeetingSummary
from services import drive_client, google_helper
from services.summarizer import summarise_transcript
from services.task_extractor import process_meeting_for_tasks

import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "meeting-assistant",
    broker=redis_url,
    backend=redis_url,
)

celery_app.conf.update(task_serializer="json", result_serializer="json")


@celery_app.task
def echo(message: str) -> str:
    logger.info(f"Celery echo: {message}")
    return message

@celery_app.task(name="process_drive_notification")
def process_drive_notification(header_map: dict[str, str]) -> str:
    """
    Called for every Drive webhook POST.
    """
    channel_id = header_map.get("x-goog-channel-id")
    user_id_str = header_map.get("x-goog-channel-token")  # we stored it earlier

    if not channel_id or not user_id_str:
        logger.warning("Drive webhook missing channel_id / token")
        return "ignored"

    logger.info("Drive event channel={} user={}", channel_id, user_id_str)

    # run sync SQLModel session inside celery worker
    with Session(sync_engine) as session:
        user = session.exec(
            select(User).where(User.id == int(user_id_str))
        ).one_or_none()
        if not user:
            logger.error("User not found for Drive event")
            return "user_not_found"

        # list drive changes since last token
        changes, new_token = drive_client.list_changes(user)

        logger.info(
            "[Celery] user={} pageToken={}  changes={}",
            user.email,
            user.drive_page_token,
            len(changes),
        )

        if not changes:
            logger.info("No relevant changes")
            user.drive_page_token = new_token
            session.commit()
            return "no_changes"

        summaries_created: List[int] = []
        for change in changes:
            file = change.get("file")
            if not file or file.get("trashed"):
                continue
                
            parents = file.get("parents", [])
            if user.meet_folder_id and user.meet_folder_id not in parents:
                continue 
                
            mime = file["mimeType"]
            if mime not in ("text/plain", "application/vnd.google-apps.document", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
                continue  # skip non‑transcript files

            try:
                title, content = drive_client.download_plain_text(
                    file["id"], google_helper.credentials_from_user(user)
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed download {}", file["id"])
                continue

            # First, create basic summary for database storage
            summary_dict = summarise_transcript(content)
            
            # Initialize tasks in the correct format
            formatted_tasks = []
            
            # Then, process for Google Tasks and Calendar integration
            try:
                creds = google_helper.credentials_from_user(user)
                google_result = process_meeting_for_tasks(content, creds, user.email)
                
                logger.info(
                    "[Celery] Google integration results: tasks_extracted={}, tasks_created={}, events_created={}",
                    google_result['tasks_extracted'],
                    google_result['tasks_created'],
                    google_result['events_created']
                )
                
                # Use tasks from Google integration if available
                if google_result['extracted_tasks']:
                    for i, task in enumerate(google_result['extracted_tasks']):
                        formatted_tasks.append({
                            "id": str(i + 1),
                            "text": task['description'],
                            "completed": False
                        })
                else:
                    # Fallback to basic summarizer tasks if no Google tasks
                    basic_tasks = summary_dict.get('tasks', [])
                    for i, task_text in enumerate(basic_tasks):
                        formatted_tasks.append({
                            "id": str(i + 1),
                            "text": task_text,
                            "completed": False
                        })
                    
            except Exception as e:
                logger.exception("Failed to process Google integration: {}", e)
                # Fallback to basic summarizer tasks if Google integration fails
                basic_tasks = summary_dict.get('tasks', [])
                for i, task_text in enumerate(basic_tasks):
                    formatted_tasks.append({
                        "id": str(i + 1),
                        "text": task_text,
                        "completed": False
                    })

            # Always ensure tasks are in the correct format
            summary_dict['tasks'] = formatted_tasks

            summary_row = MeetingSummary(
                user_id=user.id,
                drive_file_id=file["id"],
                title=title,
                summary_text=summary_dict["summary"],
                tasks=summary_dict["tasks"],
            )
            session.add(summary_row)
            session.commit()
            session.refresh(summary_row)
            summaries_created.append(summary_row.id)

            # Log successful processing
            logger.info(
                "[Celery] ✅ stored summary id={} title='{}' tasks={} chars={}",
                summary_row.id,
                title,
                len(summary_dict['tasks']),
                len(content),
            )

        # update user's pageToken
        user.drive_page_token = new_token
        session.commit()

        # at the very end
        logger.debug("[Celery] Finished channel={} newToken={}", channel_id, new_token)

    return f"created {len(summaries_created)} summaries"
