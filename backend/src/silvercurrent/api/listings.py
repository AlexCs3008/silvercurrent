"""HTTP routes for the listing CRUD API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.db.models import Listing
from silvercurrent.db.session import get_session
from silvercurrent.schemas.listings import ListingCreate, ListingRead, ListingStatus, ListingUpdate

router = APIRouter(prefix="/api/listings", tags=["listings"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[ListingRead])
async def list_listings(
    session: SessionDep,
    status_filter: ListingStatus | None = None,
) -> list[Listing]:
    """List all listings, optionally filtered by `status`."""
    stmt = select(Listing).order_by(Listing.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Listing.status == status_filter)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
async def create_listing(payload: ListingCreate, session: SessionDep) -> Listing:
    """Create a new listing. Only `business_name` is required."""
    listing = Listing(**payload.model_dump())
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing


@router.get("/{listing_id}", response_model=ListingRead)
async def get_listing(listing_id: UUID, session: SessionDep) -> Listing:
    """Fetch a single listing by id. 404 if missing."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    return listing


@router.patch("/{listing_id}", response_model=ListingRead)
async def update_listing(listing_id: UUID, payload: ListingUpdate, session: SessionDep) -> Listing:
    """Partial update; only fields present in the body are written."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(listing, field, value)

    await session.commit()
    await session.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(listing_id: UUID, session: SessionDep) -> None:
    """Hard delete. 404 if the listing doesn't exist."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    await session.delete(listing)
    await session.commit()
