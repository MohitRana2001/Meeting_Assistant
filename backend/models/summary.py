from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlmodel import Field, SQLModel, Column, DateTime, JSON, ForeignKey

class MeetingSummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id")
    drive_file_id: str = Field(index=True)
    title: Optional[str] = None

    summary_text: str
    # Store tasks as array of objects with id, text, completed fields
    tasks: List[Dict[str, Any]] = Field(sa_column=Column(JSON), default=[])

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=datetime.utcnow,
    )
