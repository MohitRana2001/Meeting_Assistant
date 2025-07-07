"""
Async SQLModel engine and session maker.
"""

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from core.config import settings

# Use cloud-ready database URL in production
database_url = settings.database_url_for_cloud_sql if settings.ENV == "production" else settings.DATABASE_URL

engine = create_async_engine(
    database_url,
    echo=settings.ENV == "development",
    pool_pre_ping=True,
)

# Add this for sync usage (Celery workers):
sync_database_url = database_url
if settings.ENV != "production":
    # For local SQLite, remove aiosqlite for sync engine
    sync_database_url = settings.DATABASE_URL.replace("+aiosqlite", "")
else:
    # For production PostgreSQL, use psycopg2 for sync
    sync_database_url = database_url.replace("+asyncpg", "+psycopg2")

sync_engine = create_engine(
    sync_database_url,
    echo=settings.ENV == "development",
    pool_pre_ping=True,
)

async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """
    Called once at startup (**dev only**) to create tables.
    In production you should run Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:  # FastAPI dependency
    async with async_session_factory() as session:
        yield session
