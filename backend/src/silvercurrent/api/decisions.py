"""HTTP routes for the decision journal (Phase B).

Append-only record of why the buyer changed a listing's status. The frontend
prompts for a reason on transitions to `passed`, `tracking`, or `loi`; on
submit it POSTs here. The journal is user-owned — agents don't read or write
it (charter §6: surface, never decide).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.db.models import DecisionJournalEntry, Listing
from silvercurrent.db.session import get_session
from silvercurrent.schemas.listings import DecisionJournalCreate, DecisionJournalRead

router = APIRouter(prefix="/api/listings", tags=["decisions"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/{listing_id}/decisions",
    response_model=DecisionJournalRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_decision(
    listing_id: UUID,
    payload: DecisionJournalCreate,
    session: SessionDep,
) -> DecisionJournalEntry:
    """Append a decision-journal entry for `listing_id`."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")

    entry = DecisionJournalEntry(
        listing_id=listing_id,
        previous_status=payload.previous_status,
        new_status=payload.new_status,
        reason=payload.reason,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.get("/{listing_id}/decisions", response_model=list[DecisionJournalRead])
async def list_decisions(
    listing_id: UUID,
    session: SessionDep,
) -> list[DecisionJournalEntry]:
    """List decision-journal entries for a listing, newest-first."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")

    stmt = (
        select(DecisionJournalEntry)
        .where(DecisionJournalEntry.listing_id == listing_id)
        .order_by(DecisionJournalEntry.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
