"""Async SQLAlchemy engine, session factory, and schema initialization.

Provides a single shared async engine + sessionmaker for the SQLite database.
Repository adapters depend on the sessionmaker rather than importing the engine
directly, keeping the persistence wiring centralized here.
"""
import logging
import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger("kompass.db")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# Shared async engine + session factory. `check_same_thread` is disabled because
# the async SQLite driver may touch the connection from different threads.
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


def _ensure_sqlite_dir() -> None:
    """Create the parent directory for a file-based SQLite database if needed."""
    url = settings.database_url
    prefix = "sqlite+aiosqlite:///"
    if url.startswith(prefix):
        db_path = url[len(prefix):]
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)


async def init_db() -> None:
    """Create all tables that do not yet exist.

    Imports the models module for its side effect of registering tables on the
    shared `Base.metadata`, then issues `create_all`. Safe to call repeatedly.
    """
    _ensure_sqlite_dir()
    # Import for side effect: registers Trip/Message/UserProfile on Base.metadata.
    from app.domain import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized at %s", settings.database_url)
