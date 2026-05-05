"""Pydantic request/response schemas for the listing API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ListingStatus = Literal["new", "reviewing", "passed", "tracking", "loi", "closed"]


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
