"""
Application entry-point.

Run locally:
    uvicorn main:app --reload
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.config import settings
from core.logging import configure_logging
from api import router as api_router

configure_logging()  # sets loguru as global logger

app = FastAPI(
    title="Meeting Assistant API",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs" if settings.ENV != "production" else None,
)

# CORS – open in dev, tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned routes
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def _startup() -> None:
    from core.database import init_db
    await init_db()  # dev‑only convenience



@app.get("/health", tags=["Health"])
async def healthcheck() -> dict[str, str]:
    """Kubernetes / Docker health probe."""
    return {"status": "ok"}
