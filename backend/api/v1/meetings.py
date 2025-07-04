from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_session, sync_engine
from core.security import get_current_user
from models.summary import MeetingSummary
from models.user import User
from core.logging import logger
from services import drive_client, gmail_client, google_helper
from services import summarizer
from services import task_extractor

router = APIRouter(prefix="/meetings", tags=["Meetings"])

class TaskUpdateRequest(BaseModel):
    task_id: str
    completed: bool

@router.get("/summaries")
async def get_summaries(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[dict]:
    """Get all meeting summaries for the current user"""
    stmt = select(MeetingSummary).where(MeetingSummary.user_id == current_user.id).order_by(MeetingSummary.created_at.desc())
    result = await session.execute(stmt)
    summaries = result.scalars().all()
    
    return [
        {
            "id": summary.id,
            "title": summary.title,
            "summary": summary.summary_text,
            "tasks": summary.tasks,
            "createdAt": summary.created_at.isoformat(),
            "source": "drive"  # All database summaries are from drive
        }
        for summary in summaries
    ]

@router.get("/summaries/{summary_id}")
async def get_summary(
    summary_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get a specific meeting summary"""
    stmt = select(MeetingSummary).where(
        MeetingSummary.id == summary_id,
        MeetingSummary.user_id == current_user.id
    )
    result = await session.execute(stmt)
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    return {
        "id": summary.id,
        "title": summary.title,
        "summary": summary.summary_text,
        "tasks": summary.tasks,
        "createdAt": summary.created_at.isoformat(),
        "source": "drive"
    }

@router.post("/refresh")
async def refresh_summaries(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Manually refresh and process new files from Google Drive Meet Recordings folder"""
    
    with Session(sync_engine) as session:
        user = session.get(User, current_user.id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.meet_folder_id:
            raise HTTPException(
                status_code=400, 
                detail="Meet Recordings folder not found. Please ensure you have a 'Meet Recordings' folder in your Google Drive."
            )

        try:
            creds = google_helper.credentials_from_user(user)
            changes, new_token = drive_client.list_changes(user)
            
            logger.info(
                "[API] Manual refresh for user={} found {} changes",
                user.email,
                len(changes),
            )

            if not changes:
                return {
                    "success": True,
                    "message": "No new meeting recordings found",
                    "summaries_created": 0
                }

            summaries_created = 0
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
                        file["id"], creds
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Failed download {}", file["id"])
                    continue

                # Check if summary already exists
                existing_summary = session.exec(
                    select(MeetingSummary).where(
                        MeetingSummary.source_id == file["id"],
                        MeetingSummary.user_id == user.id
                    )
                ).first()
                
                if existing_summary:
                    logger.info("Summary already exists for file {}", file["id"])
                    continue

                # First, create basic summary for database storage
                summary_dict = summarizer.summarise_transcript(content)
                
                # Initialize tasks in the correct format
                formatted_tasks = []
                
                # Then, process for Google Tasks and Calendar integration
                try:
                    google_result = task_extractor.process_meeting_for_tasks(content, creds, user.email)
                    
                    logger.info(
                        "[API] Google integration results: tasks_extracted={}, tasks_created={}, events_created={}",
                        google_result['tasks_extracted'],
                        google_result['tasks_created'],
                        google_result['events_created']
                    )
                    
                    # Use tasks from Google integration if available
                    if google_result.get('processed_tasks'):
                        for i, task in enumerate(google_result['processed_tasks']):
                            formatted_tasks.append({
                                "id": str(i + 1),
                                "text": task['description'],
                                "completed": False
                            })
                    else:
                        # Fallback to basic summarizer tasks
                        basic_tasks = summary_dict.get('tasks', [])
                        for i, task_text in enumerate(basic_tasks):
                            formatted_tasks.append({
                                "id": str(i + 1),
                                "text": task_text,
                                "completed": False
                            })
                        
                except Exception as e:
                    logger.exception("Failed to process Google integration: {}", e)
                    # Fallback to basic summarizer tasks
                    basic_tasks = summary_dict.get('tasks', [])
                    for i, task_text in enumerate(basic_tasks):
                        formatted_tasks.append({
                            "id": str(i + 1),
                            "text": task_text,
                            "completed": False
                        })

                # Create summary in database
                summary = MeetingSummary(
                    user_id=user.id,
                    source='drive',
                    source_id=file["id"],
                    drive_file_id=file["id"], # for compatibility
                    title=summary_dict.get('title', title),
                    summary_text=summary_dict.get('summary', ''),
                    tasks=formatted_tasks
                )
                session.add(summary)
                summaries_created += 1

            # Update token
            user.drive_page_token = new_token
            session.commit()

            return {
                "success": True,
                "message": f"Successfully processed {summaries_created} new meeting recordings",
                "summaries_created": summaries_created
            }

        except Exception as e:
            logger.exception("Error during manual refresh: {}", e)
            raise HTTPException(
                status_code=500,
                detail="Failed to refresh summaries from Google Drive"
            )

@router.post("/scan-gmail")
async def scan_gmail_summaries(
    current_user: User = Depends(get_current_user),
    days_back: int = 7
) -> dict:
    """Scan Gmail for meeting summaries and save them to the database."""
    with Session(sync_engine) as session:
        user = session.get(User, current_user.id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            gmail_results = gmail_client.scan_gmail_for_meeting_summaries(user, days_back)
            
            if not gmail_results:
                return {"success": True, "message": "No new meeting summaries found in Gmail.", "summaries_found": 0}

            summaries_created = 0
            for summary_data in gmail_results:
                email_id = summary_data['email_id']
                
                # Check if summary already exists for this user
                existing_summary = session.exec(
                    select(MeetingSummary).where(
                        MeetingSummary.source_id == email_id,
                        MeetingSummary.user_id == user.id
                    )
                ).first()
                
                if existing_summary:
                    logger.info("Summary from email {} already exists.", email_id)
                    continue

                # Create summary in database
                summary = MeetingSummary(
                    user_id=user.id,
                    source='gmail',
                    source_id=email_id,
                    title=summary_data.get('title'),
                    summary_text=summary_data.get('summary'),
                    tasks=summary_data.get('tasks', []),
                    created_at=summary_data.get('created_at')
                )
                session.add(summary)
                summaries_created += 1
                logger.info("Created new summary from email {}", email_id)

            session.commit()

            return {
                "success": True,
                "message": f"Successfully processed {summaries_created} new summaries from Gmail.",
                "summaries_found": summaries_created
            }

        except Exception as e:
            logger.exception(f"Error scanning Gmail for user {user.email}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to scan Gmail for meeting summaries"
            )

@router.get("/combined-summaries")
async def get_combined_summaries(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    search: str | None = None,
) -> dict:
    """Get all meeting summaries from both Drive and Gmail"""
    try:
        # Get all summaries from database
        stmt = select(MeetingSummary).where(MeetingSummary.user_id == current_user.id).order_by(MeetingSummary.created_at.desc())
        result = await session.execute(stmt)
        all_db_summaries = result.scalars().all()

        # Filter based on search query if provided
        if search:
            search_lower = search.lower()
            all_db_summaries = [
                s for s in all_db_summaries if
                (s.title and search_lower in s.title.lower()) or
                (s.summary_text and search_lower in s.summary_text.lower()) or
                (s.tasks and any(search_lower in task.get('text', '').lower() for task in s.tasks))
            ]
        
        all_summaries = []
        drive_count = 0
        gmail_count = 0
        
        for summary in all_db_summaries:
            all_summaries.append({
                "id": str(summary.id),
                "title": summary.title,
                "summary": summary.summary_text,
                "tasks": summary.tasks,
                "createdAt": summary.created_at.isoformat(),
                "source": summary.source
            })
            if summary.source == 'drive':
                drive_count += 1
            elif summary.source == 'gmail':
                gmail_count += 1
        
        return {
            "success": True,
            "total_summaries": len(all_summaries),
            "gmail_summaries": gmail_count,
            "drive_summaries": drive_count,
            "summaries": all_summaries
        }
        
    except Exception as e:
        logger.exception(f"Error getting combined summaries for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get meeting summaries"
        )

@router.patch("/summaries/{summary_id}/tasks/{task_id}")
async def update_task_status(
    summary_id: int,
    task_id: str,
    task_update: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update task completion status"""
    stmt = select(MeetingSummary).where(
        MeetingSummary.id == summary_id,
        MeetingSummary.user_id == current_user.id
    )
    result = await session.execute(stmt)
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    # Find and update the task
    tasks = summary.tasks or []
    task_found = False
    
    for task in tasks:
        if task.get("id") == task_id:
            task["completed"] = task_update.completed
            task_found = True
            break
    
    if not task_found:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update the summary with modified tasks
    summary.tasks = tasks
    await session.commit()
    
    return {
        "success": True,
        "message": f"Task {'completed' if task_update.completed else 'marked incomplete'}"
    }
