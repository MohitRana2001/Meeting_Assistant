from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column, String, DateTime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column=Column("email", String, unique=True, index=True))
    full_name: Optional[str] = None
    picture: Optional[str] = None

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
