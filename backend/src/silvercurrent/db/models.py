"""SQLAlchemy 2.0 ORM models for Silvercurrent's persistent state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all Silvercurrent ORM models."""


def _utcnow() -> datetime:
    """Return the current UTC datetime; isolated for easier patching in tests."""
    return datetime.now(UTC)


class Listing(Base):
    """A small-business listing entered manually or ingested from URL/PDF/email."""

    __tablename__ = "listing"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    # Provenance
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Identity
    business_name: Mapped[str] = mapped_column(String(256), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    naics_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Financials — whole dollars, integer. Nullable since not every listing discloses each.
    asking_price: Mapped[int | None] = mapped_column(nullable=True)
    sde: Mapped[int | None] = mapped_column(nullable=True)
    cash_flow: Mapped[int | None] = mapped_column(nullable=True)
    revenue: Mapped[int | None] = mapped_column(nullable=True)

    # Narrative
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_for_selling: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Original ingested text — kept so we can re-extract with tuned prompts later.
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Broker
    broker_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    broker_contact: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Workflow
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class ChatTurn(Base):
    """A single turn in a chat conversation, scoped to global or a specific listing."""

    __tablename__ = "chat_turn"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DealSheet(Base):
    """A single Run Analysis output for a listing (Phase 3 slice 3).

    Persisted so the listing page can show prior analyses without re-running.
    Append-only — re-running creates a new row rather than overwriting, so the
    user can compare across criteria changes or new disclosures.
    """

    __tablename__ = "deal_sheet"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("listing.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    markdown: Mapped[str] = mapped_column(Text, nullable=False)

    # Usage at the time of the run — kept so the user can see what each
    # analysis cost and which model produced it.
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    iterations: Mapped[int] = mapped_column(Integer, nullable=False)
