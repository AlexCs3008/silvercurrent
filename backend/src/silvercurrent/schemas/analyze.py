"""Pydantic schemas for the analyze API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalyzeUsage(BaseModel):
    """Cumulative LLM usage for an Analyst run (across all tool-loop iterations)."""

    input_tokens: int
    output_tokens: int
    model: str
    iterations: int


class DealSheetRead(BaseModel):
    """One persisted Deal Sheet for a listing."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    listing_id: UUID
    created_at: datetime
    markdown: str
    model: str
    input_tokens: int
    output_tokens: int
    iterations: int


class AnalyzeResponse(BaseModel):
    """Response body for `POST /api/analyze/{listing_id}`."""

    deal_sheet: DealSheetRead
    usage: AnalyzeUsage
