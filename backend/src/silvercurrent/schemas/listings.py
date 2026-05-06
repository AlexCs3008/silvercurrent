"""Pydantic request/response schemas for the listing API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ListingStatus = Literal["new", "reviewing", "passed", "tracking", "loi", "closed"]
FitBand = Literal["strong", "partial", "weak", "mismatch", "unknown"]


class ListingCreate(BaseModel):
    """Request body for `POST /api/listings`."""

    source: str = "manual"
    source_url: str | None = None

    business_name: str = Field(..., min_length=1, max_length=256)
    industry: str | None = Field(default=None, max_length=128)
    naics_code: str | None = Field(default=None, max_length=8)
    location: str | None = Field(default=None, max_length=256)

    asking_price: int | None = Field(default=None, ge=0)
    sde: int | None = None
    cash_flow: int | None = None
    revenue: int | None = Field(default=None, ge=0)

    narrative: str | None = None
    reason_for_selling: str | None = None
    raw_text: str | None = None

    broker_name: str | None = Field(default=None, max_length=256)
    broker_contact: str | None = None

    status: ListingStatus = "new"
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class ListingUpdate(BaseModel):
    """Request body for `PATCH /api/listings/{id}`. Every field optional."""

    model_config = ConfigDict(extra="forbid")

    source: str | None = None
    source_url: str | None = None

    business_name: str | None = Field(default=None, min_length=1, max_length=256)
    industry: str | None = Field(default=None, max_length=128)
    naics_code: str | None = Field(default=None, max_length=8)
    location: str | None = Field(default=None, max_length=256)

    asking_price: int | None = Field(default=None, ge=0)
    sde: int | None = None
    cash_flow: int | None = None
    revenue: int | None = Field(default=None, ge=0)

    narrative: str | None = None
    reason_for_selling: str | None = None
    raw_text: str | None = None

    broker_name: str | None = Field(default=None, max_length=256)
    broker_contact: str | None = None

    status: ListingStatus | None = None
    notes: str | None = None
    tags: list[str] | None = None


class ListingRead(BaseModel):
    """Response shape for listing reads. Loaded from ORM via `from_attributes`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

    source: str
    source_url: str | None

    business_name: str
    industry: str | None
    naics_code: str | None
    location: str | None

    asking_price: int | None
    sde: int | None
    cash_flow: int | None
    revenue: int | None

    narrative: str | None
    reason_for_selling: str | None
    raw_text: str | None

    broker_name: str | None
    broker_contact: str | None

    status: ListingStatus
    notes: str | None
    tags: list[str]

    # Computed at read-time from `docs/criteria.md` via `criteria.scorer`. Not
    # persisted — recomputed on every read so criteria edits propagate without
    # a backfill. ADR 0008.
    fit_band: FitBand | None = None
    fit_summary: str | None = None

    # Latest decision-journal entry for this listing, or null if no journal
    # entries exist. Computed at read-time alongside fit fields.
    latest_decision: DecisionJournalRead | None = None


class DecisionJournalRead(BaseModel):
    """Response shape for a single decision journal entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    listing_id: UUID
    previous_status: str | None
    new_status: str
    reason: str
    created_at: datetime


class DecisionJournalCreate(BaseModel):
    """Body for `POST /api/listings/{id}/decisions`."""

    previous_status: str | None = Field(default=None, max_length=32)
    new_status: str = Field(..., min_length=1, max_length=32)
    reason: str = Field(..., min_length=1, max_length=500)


class ListingUpdateResponse(BaseModel):
    """Wrapper around `ListingRead` that adds `requires_decision`.

    Set when a status change moved the listing into a decision-worthy bucket
    (`passed`, `tracking`, `loi`). The frontend uses this to open the reason
    modal. The state change still persists either way — the journal is
    best-effort capture, not a gate.
    """

    listing: ListingRead
    requires_decision: bool = False
    decision_previous_status: str | None = None
    decision_new_status: str | None = None


# Re-resolve forward reference now that DecisionJournalRead is defined.
ListingRead.model_rebuild()
