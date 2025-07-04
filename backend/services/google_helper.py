"""
Centralized helper for creating Google API credentials.
"""

from __future__ import annotations

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from core.config import settings
from core.crypto import decrypt
from models.user import User

# All scopes the application might need for its backend services.
# This should be the union of all scopes required by different services.
ALL_APP_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
]

def credentials_from_user(user: User) -> Credentials:
    """
    Creates a comprehensive, multi-scope Credentials object from a user's
    stored refresh token. This object can be used for Drive, Tasks, Calendar,
    and Gmail APIs.
    """
    refresh_token = decrypt(user.refresh_token_enc)
    creds = Credentials(
        token=None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID, client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=ALL_APP_SCOPES,
    )
    # Force refresh to ensure we have a valid access token.
    creds.refresh(Request())
    return creds