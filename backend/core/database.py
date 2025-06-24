"""
Async SQLModel engine and session maker.
"""

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "development",
    pool_pre_ping=True,
)

# Add this for sync usage:
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+aiosqlite", ""),  # for SQLite, remove 'aiosqlite'
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
