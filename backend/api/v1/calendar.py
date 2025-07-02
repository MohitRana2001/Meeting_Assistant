"""
Google Calendar API endpoints.
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from core.database import get_session
from core.security import get_current_user
from models.user import User
from services import drive_client

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events")
async def get_calendar_events(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[dict]:
    """
    Get upcoming calendar events from user's Google Calendar.
    """
    try:
        creds = drive_client._credentials_from_user(current_user)
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        # Get events from primary calendar for the next 30 days
        now = datetime.utcnow()
        time_max = now + timedelta(days=30)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now.isoformat() + "Z",
                timeMax=time_max.isoformat() + "Z",
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
                fields="items(id,summary,start,end,attendees,conferenceData,hangoutLink)",
            )
            .execute()
        )

        events = events_result.get("items", [])
        formatted_events = []

        for event in events:
            # Extract start and end times
            start = event.get("start", {})
            end = event.get("end", {})
            
            # Handle both datetime and date-only events
            start_time = start.get("dateTime", start.get("date"))
            end_time = end.get("dateTime", end.get("date"))
            
            if not start_time or not end_time:
                continue

            # Check if it's a Google Meet
            is_meet = False
            meeting_link = None
            
            conference_data = event.get("conferenceData", {})
            if conference_data:
                entry_points = conference_data.get("entryPoints", [])
                for entry in entry_points:
                    if entry.get("entryPointType") == "video":
                        is_meet = True
                        meeting_link = entry.get("uri")
                        break
            
            # Fallback to hangoutLink for older events
            if not is_meet and event.get("hangoutLink"):
                is_meet = True
                meeting_link = event.get("hangoutLink")

            # Count attendees
            attendees = event.get("attendees", [])
            attendee_count = len([a for a in attendees if a.get("responseStatus") != "declined"])

            formatted_event = {
                "id": event["id"],
                "title": event.get("summary", "Untitled Event"),
                "start": start_time,
                "end": end_time,
                "attendees": attendee_count if attendee_count > 0 else None,
                "meetingType": "Google Meet" if is_meet else None,
                "hasRecording": False,  # We'll enhance this later with Drive integration
                "meetingLink": meeting_link,
            }
            
            formatted_events.append(formatted_event)

        logger.info("Retrieved {} calendar events for user {}", len(formatted_events), current_user.email)
        return formatted_events

    except HttpError as e:
        logger.error("Google Calendar API error for user {}: {}", current_user.email, e)
        if e.resp.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Calendar access not granted. Please reauthorize the application."
            )
        raise HTTPException(status_code=500, detail="Failed to fetch calendar events")
    
    except Exception as e:
        logger.exception("Unexpected error fetching calendar events for user {}: {}", current_user.email, e)
        raise HTTPException(status_code=500, detail="Failed to fetch calendar events")


@router.post("/events")
async def create_calendar_event(
    event_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Create a new calendar event.
    """
    try:
        creds = drive_client._credentials_from_user(current_user)
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        # Validate required fields
        if not event_data.get("title") or not event_data.get("start") or not event_data.get("end"):
            raise HTTPException(status_code=400, detail="Missing required fields: title, start, end")

        # Build event body
        event_body = {
            "summary": event_data["title"],
            "start": {"dateTime": event_data["start"], "timeZone": "UTC"},
            "end": {"dateTime": event_data["end"], "timeZone": "UTC"},
        }

        # Add description if provided
        if event_data.get("description"):
            event_body["description"] = event_data["description"]

        # Add attendees if provided
        if event_data.get("attendees"):
            event_body["attendees"] = [
                {"email": email} for email in event_data["attendees"] if email
            ]

        # Create the event
        created_event = (
            service.events()
            .insert(calendarId="primary", body=event_body)
            .execute()
        )

        logger.info("Created calendar event {} for user {}", created_event["id"], current_user.email)
        
        return {
            "success": True,
            "eventId": created_event["id"],
            "htmlLink": created_event.get("htmlLink"),
        }

    except HttpError as e:
        logger.error("Google Calendar API error creating event for user {}: {}", current_user.email, e)
        if e.resp.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Calendar write access not granted. Please reauthorize the application."
            )
        raise HTTPException(status_code=500, detail="Failed to create calendar event")
    
    except Exception as e:
        logger.exception("Unexpected error creating calendar event for user {}: {}", current_user.email, e)
        raise HTTPException(status_code=500, detail="Failed to create calendar event")


@router.get("/events/{event_id}")
async def get_calendar_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get a specific calendar event by ID.
    """
    try:
        creds = drive_client._credentials_from_user(current_user)
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        event = (
            service.events()
            .get(calendarId="primary", eventId=event_id)
            .execute()
        )

        return {
            "id": event["id"],
            "title": event.get("summary", "Untitled Event"),
            "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
            "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date")),
            "description": event.get("description"),
            "attendees": [a.get("email") for a in event.get("attendees", [])],
            "htmlLink": event.get("htmlLink"),
        }

    except HttpError as e:
        logger.error("Google Calendar API error getting event {} for user {}: {}", event_id, current_user.email, e)
        if e.resp.status == 404:
            raise HTTPException(status_code=404, detail="Event not found")
        if e.resp.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Calendar access not granted. Please reauthorize the application."
            )
        raise HTTPException(status_code=500, detail="Failed to fetch calendar event")
    
    except Exception as e:
        logger.exception("Unexpected error fetching calendar event {} for user {}: {}", event_id, current_user.email, e)
        raise HTTPException(status_code=500, detail="Failed to fetch calendar event") 