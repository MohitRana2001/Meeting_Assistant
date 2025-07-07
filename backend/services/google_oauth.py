"""
Thin wrapper around google-auth-oauthlib flow utilities.
"""

from __future__ import annotations

from typing import Tuple, Dict, Any

from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests

from core.config import settings

# --- OAuth Scopes ----------------------------------------------------------
# Build the scope list dynamically so Gmail can be disabled via env-flag.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/gmail.readonly",
]

def _client_config() -> Dict[str, Any]:
    """
    Construct the minimal JSON structure expected by Flow.from_client_config.
    """
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{str(settings.API_BASE_URL).rstrip('/')}/api/v1/auth/google/callback"],
        }
    }


def build_flow(state: str | None = None) -> Flow:
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=f"{str(settings.API_BASE_URL).rstrip('/')}/api/v1/auth/google/callback",
        state=state,
    )
    flow.include_granted_scopes = True
    flow.prompt = "consent"
    return flow


def get_user_info(credentials) -> Tuple[str, str | None, str | None]:
    """
    Return (email, name, picture) from the ID token.
    """
    id_info = id_token.verify_oauth2_token(
        credentials._id_token,  # pyright: ignore [protected‑access]
        requests.Request(),
        settings.GOOGLE_CLIENT_ID,
    )
    return (
        id_info["email"],
        id_info.get("name"),
        id_info.get("picture"),
    )
