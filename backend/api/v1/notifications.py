"""
Notifications API endpoints.
"""
from typing import List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger

from core.database import get_session
from core.security import get_current_user
from models.user import User
from models.summary import MeetingSummary

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
async def get_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
) -> List[dict]:
    """
    Get recent notifications for the current user.
    This includes meeting summaries, task updates, and system notifications.
    """
    try:
        notifications = []
        
        # Get recent meeting summaries as notifications
        stmt = (
            select(MeetingSummary)
            .where(MeetingSummary.user_id == current_user.id)
            .order_by(desc(MeetingSummary.created_at))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        recent_summaries = result.scalars().all()
        
        for summary in recent_summaries:
            # Check if it's recent (within last 7 days)
            created_time = summary.created_at.replace(tzinfo=timezone.utc) if summary.created_at.tzinfo is None else summary.created_at

            # Compare aware datetimes
            time_diff = datetime.now(timezone.utc) - created_time
            is_recent = time_diff <= timedelta(days=7)
            
            # Count tasks for this summary
            task_count = len(summary.tasks) if summary.tasks else 0
            
            notification = {
                "id": f"summary_{summary.id}",
                "type": "meeting_summary",
                "title": "New meeting summary generated",
                "message": f"'{summary.title}' has been processed with {task_count} action items",
                "timestamp": created_time.isoformat(),
                "read": not is_recent,  # Mark as unread if recent
                "metadata": {
                    "summaryId": summary.id,
                    "summaryTitle": summary.title,
                    "taskCount": task_count
                }
            }
            notifications.append(notification)
        
        # Add system notifications for successful integrations
        if len(recent_summaries) > 0:
            latest_summary = recent_summaries[0]
            latest_created = latest_summary.created_at.replace(tzinfo=timezone.utc) if latest_summary.created_at.tzinfo is None else latest_summary.created_at
            time_diff = datetime.now(timezone.utc) - latest_created
            
            # Add Google Tasks sync notification if recent
            if time_diff <= timedelta(hours=1):
                notifications.append({
                    "id": f"tasks_sync_{latest_summary.id}",
                    "type": "tasks_sync",
                    "title": "Tasks synced to Google Tasks",
                    "message": f"Action items from '{latest_summary.title}' have been added to your Google Tasks",
                    "timestamp": (latest_created + timedelta(minutes=1)).isoformat(),
                    "read": False,
                    "metadata": {
                        "summaryId": latest_summary.id,
                        "summaryTitle": latest_summary.title
                    }
                })
                
                # Add calendar sync notification if recent
                notifications.append({
                    "id": f"calendar_sync_{latest_summary.id}",
                    "type": "calendar_sync", 
                    "title": "Calendar events created",
                    "message": f"Due dates from '{latest_summary.title}' have been added to your Google Calendar",
                    "timestamp": (latest_created + timedelta(minutes=2)).isoformat(),
                    "read": False,
                    "metadata": {
                        "summaryId": latest_summary.id,
                        "summaryTitle": latest_summary.title
                    }
                })
        
        # Sort by timestamp (newest first)
        notifications.sort(key=lambda x: x["timestamp"], reverse=True)
        
        logger.info("Retrieved {} notifications for user {}", len(notifications), current_user.email)
        return notifications[:limit]
    
    except Exception as e:
        logger.exception("Error fetching notifications for user {}: {}", current_user.email, e)
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.post("/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Mark a notification as read.
    """
    try:
        # For now, we'll just return success since we're generating notifications dynamically
        # In a production system, you'd store read states in the database
        
        logger.info("Marked notification {} as read for user {}", notification_id, current_user.email)
        return {"success": True, "message": "Notification marked as read"}
    
    except Exception as e:
        logger.exception("Error marking notification {} as read for user {}: {}", notification_id, current_user.email, e)
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get count of unread notifications.
    """
    try:
        # Get recent meeting summaries (last 24 hours = unread)
        stmt = (
            select(MeetingSummary)
            .where(MeetingSummary.user_id == current_user.id)
            .order_by(desc(MeetingSummary.created_at))
            .limit(10)
        )
        
        result = await session.execute(stmt)
        recent_summaries = result.scalars().all()
        
        unread_count = 0
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for summary in recent_summaries:
            created_time = summary.created_at.replace(tzinfo=timezone.utc) if summary.created_at.tzinfo is None else summary.created_at

            if created_time > cutoff_time:
                # Each recent summary is considered to generate 3 unread notifications
                unread_count += 2
        
        return {"unreadCount": min(unread_count, 99)}  # Cap at 99 for UI purposes
    
    except Exception as e:
        logger.exception("Error getting unread count for user {}: {}", current_user.email, e)
        return {"unreadCount": 0} 