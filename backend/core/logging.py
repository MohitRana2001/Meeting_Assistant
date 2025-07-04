"""
Thin wrapper around Loguru so every module can simply:

    from loguru import logger
"""

import sys
from loguru import logger
from core.config import settings


def configure_logging() -> None:
    # Remove existing handlers (FastAPI / Uvicorn adds its own)
    logger.remove()

    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        diagnose=False,  # pretty tracebacks off in prod
        backtrace=settings.ENV == "development",
        enqueue=True,  # multiprocess‑safe
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
               "| <level>{level: <8}</level> "
               "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
               "- <level>{message}</level>",
    )

    logger.add(
        "logs/meetingmate_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # midnight
        retention="7 days",
        compression="zip",
        level="DEBUG",      # keep everything for post-mortem
        enqueue=True,
        backtrace=False,
    )
