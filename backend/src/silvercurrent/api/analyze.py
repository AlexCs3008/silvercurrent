"""HTTP routes for the Analyst (Deal Sheet) API.

Phase 3 slice 3: persist each Deal Sheet to the `deal_sheet` table so the
listing detail page can show prior analyses without re-running. Append-only —
re-running creates a new row, the user can compare across criteria changes
or new disclosures.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.analyst import AnalystAgent
from silvercurrent.db.models import DealSheet, Listing
from silvercurrent.db.session import get_session
from silvercurrent.schemas.analyze import AnalyzeResponse, AnalyzeUsage, DealSheetRead

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/{listing_id}", response_model=AnalyzeResponse)
async def post_analyze(listing_id: UUID, session: SessionDep) -> AnalyzeResponse:
    """Run the Analyst against a listing, persist the Deal Sheet, return it."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail=f"listing {listing_id} not found")

    agent = AnalystAgent(session=session)
    result = await agent.analyze(listing_id=listing_id)

    deal_sheet = DealSheet(
        listing_id=listing_id,
        markdown=result.deal_sheet,
        model=result.usage.model,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        iterations=result.iterations,
    )
    session.add(deal_sheet)
    await session.commit()
    await session.refresh(deal_sheet)

    return AnalyzeResponse(
        deal_sheet=DealSheetRead.model_validate(deal_sheet),
        usage=AnalyzeUsage(
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            model=result.usage.model,
            iterations=result.iterations,
        ),
    )


@router.get("/{listing_id}", response_model=list[DealSheetRead])
async def list_deal_sheets(listing_id: UUID, session: SessionDep) -> list[DealSheet]:
    """Return all Deal Sheets for a listing, newest first."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail=f"listing {listing_id} not found")

    stmt = select(DealSheet).where(DealSheet.listing_id == listing_id).order_by(DealSheet.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())
