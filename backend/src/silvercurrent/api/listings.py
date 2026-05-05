"""HTTP routes for the listing CRUD API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.config import get_settings
from silvercurrent.db.models import Listing
from silvercurrent.db.session import get_session
from silvercurrent.ingestion.listings import (
    ExtractionError,
    ExtractionResult,
    extract_listing,
    fetch_url,
)
from silvercurrent.ingestion.pdfs import PDFParseError, extract_text_from_pdf
from silvercurrent.schemas.listings import ListingCreate, ListingRead, ListingStatus, ListingUpdate

router = APIRouter(prefix="/api/listings", tags=["listings"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class ListingExtractionRequest(BaseModel):
    """Body for `POST /api/listings/extract`. Exactly one of url or text must be set."""

    source_url: str | None = None
    source_text: str | None = None

    @model_validator(mode="after")
    def _require_one(self) -> ListingExtractionRequest:
        if not (self.source_url or self.source_text):
            raise ValueError("provide either source_url or source_text")
        return self


@router.post("/extract", response_model=ExtractionResult)
async def extract_from_source(payload: ListingExtractionRequest) -> ExtractionResult:
    """Extract listing fields from a URL or pasted text via the LLM.

    Does not save. The frontend uses the response to populate the form, then
    the user reviews and POSTs to `/api/listings` to actually persist.
    """
    if payload.source_text:
        text = payload.source_text
        url = payload.source_url
    else:
        # source_url must be set per the validator
        assert payload.source_url is not None
        url = payload.source_url
        try:
            text = await fetch_url(url)
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"failed to fetch {url}: {e}. "
                    "Many aggregator sites block automated fetches — try pasting the page text instead."
                ),
            ) from e

    try:
        return await extract_listing(source_text=text, source_url=url)
    except ExtractionError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/extract-pdf", response_model=ExtractionResult)
async def extract_from_pdf(file: Annotated[UploadFile, File()]) -> ExtractionResult:
    """Extract listing fields from an uploaded PDF (broker teaser, CIM excerpt).

    Parses the PDF server-side via pymupdf, then runs the same `extract_listing()`
    pipeline as the URL/text endpoint. Does not save. Does not store the binary —
    only the extracted text travels onward as `raw_text`.
    """
    settings = get_settings()
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > settings.pdf_max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"PDF is {len(content):,} bytes; the cap is {settings.pdf_max_bytes:,}. "
                "Trim the document or paste the relevant section as text instead."
            ),
        )

    try:
        text = extract_text_from_pdf(content)
    except PDFParseError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        return await extract_listing(source_text=text, source_url=None)
    except ExtractionError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


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
