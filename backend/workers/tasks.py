"""
Celery app & placeholder task for Phase 1.

Run worker locally after installing Redis:
    celery -A workers.tasks worker --loglevel=info
"""

from __future__ import annotations

import os

from celery import Celery
from loguru import logger

from core.config import settings

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "meeting‑assistant",
    broker=redis_url,
    backend=redis_url,
)

celery_app.conf.update(task_serializer="json", result_serializer="json")


@celery_app.task
def echo(message: str) -> str:
    logger.info(f"Celery echo: {message}")
    return message
