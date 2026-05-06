"""Pytest fixtures for the FastAPI backend test suite.

Each test gets a fresh in-memory SQLite DB and an `httpx.AsyncClient` wired up
to the FastAPI app with `get_session` overridden to use the test session.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from silvercurrent.db.models import Base
from silvercurrent.db.session import get_session
from silvercurrent.main import app

# FTS5 virtual table for `listing_document_chunk_fts` — Alembic creates this in
# the real DB; tests need to create it alongside the ORM tables since
# `metadata.create_all` doesn't model virtual tables.
_FTS5_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS listing_document_chunk_fts USING fts5(
    document_id UNINDEXED,
    listing_id UNINDEXED,
    chunk_index UNINDEXED,
    page_hint UNINDEXED,
    content,
    tokenize='porter unicode61'
)
"""


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Yield an `AsyncSession` bound to a fresh in-memory SQLite DB with schema applied."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(_FTS5_DDL))

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Yield an `AsyncClient` against the FastAPI app, sharing the test `session`."""

    async def _override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def listing_payload() -> dict[str, object]:
    """Minimal valid `ListingCreate` body — only `business_name` is required."""
    return {"business_name": "Acme HVAC"}


@pytest.fixture
def full_listing_payload() -> dict[str, object]:
    """Full `ListingCreate` body covering every field, used to assert round-trip fidelity."""
    return {
        "source": "bizbuysell",
        "source_url": "https://example.com/listings/123",
        "business_name": "Acme HVAC",
        "industry": "HVAC services",
        "naics_code": "238220",
        "location": "Miami, FL",
        "asking_price": 1_200_000,
        "sde": 350_000,
        "cash_flow": 380_000,
        "revenue": 2_400_000,
        "narrative": "Established 22-year HVAC company with recurring service contracts.",
        "reason_for_selling": "Owner retiring.",
        "broker_name": "Jane Broker",
        "broker_contact": "jane@example.com / (305) 555-0100",
        "status": "reviewing",
        "notes": "Asked about customer concentration.",
        "tags": ["fl", "service", "established"],
    }
