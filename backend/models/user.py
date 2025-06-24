from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column, String, DateTime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column=Column("email", String, unique=True, index=True))
    full_name: Optional[str] = None
    picture: Optional[str] = None
    meet_folder_id: Optional[str] = Field(default=None, index=True)

    # Encrypted Google refresh token (Fernet)
    refresh_token_enc: str

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=datetime.utcnow,
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=datetime.utcnow,
    )

    drive_channel_id: Optional[str] = Field(default=None, index=True)
    drive_page_token: Optional[str] = None
    drive_channel_expire_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True)), default=None
    )
