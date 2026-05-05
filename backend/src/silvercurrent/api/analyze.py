"""HTTP routes for the Analyst (Deal Sheet) API.

Phase 3 slice 1: a single non-conversational endpoint. The buyer clicks
"Run Analysis" on a listing in the UI; this route runs the Analyst agent
and returns the Deal Sheet markdown.

Persistence of the Deal Sheet (so a listing detail page can show the most
recent analysis without re-running) lands in slice 3.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.analyst import AnalystAgent
from silvercurrent.db.models import Listing
from silvercurrent.db.session import get_session
from silvercurrent.schemas.analyze import AnalyzeResponse, AnalyzeUsage

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/{listing_id}", response_model=AnalyzeResponse)
async def post_analyze(listing_id: UUID, session: SessionDep) -> AnalyzeResponse:
    """Run the Analyst agent against a listing and return its Deal Sheet."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail=f"listing {listing_id} not found")

    agent = AnalystAgent(session=session)
    result = await agent.analyze(listing_id=listing_id)

    return AnalyzeResponse(
        deal_sheet=result.deal_sheet,
        usage=AnalyzeUsage(
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            model=result.usage.model,
            iterations=result.iterations,
        ),
    )
