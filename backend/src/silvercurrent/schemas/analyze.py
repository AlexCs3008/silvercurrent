"""Pydantic schemas for the analyze API."""

from __future__ import annotations

from pydantic import BaseModel


class AnalyzeUsage(BaseModel):
    """Cumulative LLM usage for an Analyst run (across all tool-loop iterations)."""

    input_tokens: int
    output_tokens: int
    model: str
    iterations: int


class AnalyzeResponse(BaseModel):
    """Response body for `POST /api/analyze/{listing_id}`."""

    deal_sheet: str
    usage: AnalyzeUsage
