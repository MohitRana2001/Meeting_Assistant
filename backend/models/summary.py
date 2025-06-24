from datetime import datetime
from typing import Optional, List

from sqlmodel import Field, SQLModel, Column, DateTime, JSON, ForeignKey

class MeetingSummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id")
    drive_file_id: str = Field(index=True)
    title: Optional[str] = None

    summary_text: str
    tasks: List[str] = Field(sa_column=Column(JSON))

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=datetime.utcnow,
    )
