from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlmodel import Field, SQLModel, Column, DateTime, JSON, ForeignKey

class MeetingSummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    
    # Source of the summary ('drive' or 'gmail')
    source: str = Field(index=True)
    # Unique ID from the source (drive_file_id or gmail_message_id)
    source_id: str = Field(index=True)
    
    # Kept for backwards compatibility, but source_id is the new primary key
    drive_file_id: Optional[str] = Field(default=None, index=True)

    title: Optional[str] = None
    summary_text: str
    # Store tasks as array of objects with id, text, completed, google_task_id, google_tasklist_id fields
    tasks: List[Dict[str, Any]] = Field(sa_column=Column(JSON), default=[])

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=datetime.utcnow,
    )
