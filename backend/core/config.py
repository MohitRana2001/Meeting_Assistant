"""
Centralised settings using `pydantic-settings`.

All env-vars are loaded once at import time.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from pydantic import HttpUrl

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Phase 1 ---
class _Settings(BaseSettings):
    # environment
    ENV: str = "development"  # development | staging | production

    # CORS
    CORS_ALLOW_ORIGINS: List[str] = ["*"]

    # Security / JWT (Phase 2 will add OAUTH_GOOGLE_CLIENT_ID/SECRET)
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    # e.g. "http://localhost:8000"  (no trailing slash)
    API_BASE_URL: HttpUrl = "http://localhost:8000"
    # Frontend URL for redirects after OAuth
    FRONTEND_URL: HttpUrl = "http://localhost:3000"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Gemini
    GEMINI_API_KEY: str | None = None          # set this in .env / secrets manager
    GEMINI_MODEL: str = "gemini-1.5-pro-latest"  # or "gemini-pro"

    # Database (Phase 2)
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # Log level (DEBUG/INFO/WARNING/ERROR)
    LOG_LEVEL: str = "INFO"

    # Feature flags
    ENABLE_GMAIL: bool = True

    # --- internal ---
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

     # ─── Drive push – channel lasts up to 7 days ────────────────
    DRIVE_CHANNEL_TTL_HOURS: int = 168         # 7 days
    DRIVE_WEBHOOK_PATH: str = "/api/v1/webhooks/drive"  # local path

    @property
    def drive_webhook_address(self) -> str:    # full public URL
        return f"{self.API_BASE_URL}{self.DRIVE_WEBHOOK_PATH}"


settings = _Settings()  # Singleton
