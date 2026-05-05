"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from silvercurrent.config import get_settings

_settings = get_settings()

engine = create_async_engine(_settings.database_url, future=True, echo=False)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a transactional async session; intended for FastAPI dependencies."""
    async with async_session_factory() as session:
        yield session
