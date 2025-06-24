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
from services import drive_client
from services.summarizer import summarise_transcript
from services.task_extractor import process_meeting_for_tasks

router = APIRouter(prefix="/meetings", tags=["Meetings"])

class TaskUpdateRequest(BaseModel):
    task_id: str
    completed: bool

@router.get("/summaries", response_model=List[dict])
async def list_summaries(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[dict]:
    """Get meeting summaries for the authenticated user"""
    # Filter summaries by the current user's ID
    result = await session.execute(
        select(MeetingSummary).where(MeetingSummary.user_id == current_user.id)
    )
    rows = result.scalars().all()
    logger.info("[API] GET /summaries for user {} returned {} rows", current_user.email, len(rows))
    return [
        {
            "id": r.id,
            "title": r.title,
            "summary": r.summary_text,
            "tasks": r.tasks,
            "createdAt": r.created_at,
        }
        for r in rows
    ]

@router.post("/refresh")
async def refresh_summaries(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Manually refresh and process new files from Google Drive Meet Recordings folder"""
    try:
        logger.info("[API] Manual refresh requested by user {}", current_user.email)
        
        # Use sync session for this operation (similar to worker)
        with Session(sync_engine) as session:
            user = session.exec(
                select(User).where(User.id == current_user.id)
            ).one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get credentials and check for new files
            creds = drive_client._credentials_from_user(user)
            changes, new_token = drive_client.list_changes(user)
            
            logger.info(
                "[API] Manual refresh for user={} pageToken={} changes={}",
                user.email,
                user.drive_page_token,
                len(changes),
            )
            
            if not changes:
                logger.info("No new changes found")
                user.drive_page_token = new_token
                session.commit()
                return {"success": True, "message": "No new files found", "summaries_created": 0}
            
            summaries_created = []
            processed_count = 0
            
            for change in changes:
                file = change.get("file")
                if not file or file.get("trashed"):
                    continue
                    
                parents = file.get("parents", [])
                if user.meet_folder_id and user.meet_folder_id not in parents:
                    continue 
                    
                mime = file["mimeType"]
                if mime not in ("text/plain", "application/vnd.google-apps.document", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
                    continue
                
                # Check if we already have this file processed
                existing = session.exec(
                    select(MeetingSummary).where(
                        MeetingSummary.drive_file_id == file["id"],
                        MeetingSummary.user_id == user.id
                    )
                ).first()
                
                if existing:
                    logger.info("File {} already processed, skipping", file["id"])
                    continue
                
                try:
                    title, content = drive_client.download_plain_text(file["id"], creds)
                except Exception as exc:
                    logger.exception("Failed download {}", file["id"])
                    continue
                
                # Create basic summary
                summary_dict = summarise_transcript(content)
                formatted_tasks = []
                
                # Process for Google Tasks and Calendar integration
                try:
                    google_result = process_meeting_for_tasks(content, creds, user.email)
                    
                    logger.info(
                        "[API] Google integration results: tasks_extracted={}, tasks_created={}, events_created={}",
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
                
                # Store the summary
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
                processed_count += 1
                
                logger.info(
                    "[API] ✅ Processed new file: id={} title='{}' tasks={}",
                    summary_row.id,
                    title,
                    len(summary_dict['tasks']),
                )
            
            # Update user's page token
            user.drive_page_token = new_token
            session.commit()
            
            logger.info("[API] Manual refresh completed: {} new summaries created", processed_count)
            
            return {
                "success": True,
                "message": f"Successfully processed {processed_count} new files",
                "summaries_created": processed_count,
                "summary_ids": summaries_created
            }
            
    except Exception as e:
        logger.exception("Error during manual refresh: {}", e)
        raise HTTPException(status_code=500, detail=f"Failed to refresh summaries: {str(e)}")

@router.patch("/summaries/{summary_id}/tasks/{task_id}")
async def update_task_status(
    summary_id: int,
    task_id: str,
    task_update: TaskUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update the completion status of a specific task"""
    # Get the summary for the current user
    result = await session.execute(
        select(MeetingSummary).where(
            MeetingSummary.id == summary_id,
            MeetingSummary.user_id == current_user.id
        )
    )
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    # Find and update the specific task
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
    session.add(summary)
    await session.commit()
    
    logger.info(
        "Updated task {} in summary {} for user {} - completed: {}",
        task_id, summary_id, current_user.email, task_update.completed
    )
    
    return {"success": True, "message": "Task updated successfully"}
