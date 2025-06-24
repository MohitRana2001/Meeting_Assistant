from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.summary import MeetingSummary
from core.logging import logger

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("/summaries", response_model=List[dict])
async def list_summaries(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(select(MeetingSummary))
    rows = result.scalars().all()
    logger.info("[API] GET /summaries  returned {} rows", len(rows))
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
