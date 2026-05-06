"""HTTP routes for the listing CRUD API."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.config import get_settings
from silvercurrent.criteria import ParsedCriteria, parse_criteria, score_listing
from silvercurrent.db.models import DecisionJournalEntry, Listing
from silvercurrent.db.session import get_session
from silvercurrent.ingestion.listings import (
    ExtractionError,
    ExtractionResult,
    extract_listing,
    fetch_url,
)
from silvercurrent.ingestion.pdfs import PDFParseError, extract_text_from_pdf
from silvercurrent.schemas.listings import (
    ListingCreate,
    ListingRead,
    ListingStatus,
    ListingUpdate,
    ListingUpdateResponse,
)

# Status transitions that should prompt the user for a decision-journal reason.
# `passed`, `tracking`, and `loi` are decision-worthy — `new` and `reviewing`
# are passive states. `closed` is a downstream-of-LOI label that follows from
# events outside the cockpit, so we don't prompt there.
_DECISION_WORTHY_STATUSES: frozenset[ListingStatus] = frozenset({"passed", "tracking", "loi"})

# Resolve once per process; criteria.md is small and re-read inside `_load_criteria`
# so user edits propagate without a server restart.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_CRITERIA_PATH = _REPO_ROOT / "docs" / "criteria.md"


def _load_criteria() -> ParsedCriteria | None:
    """Read and parse `docs/criteria.md`, or return None if it's unreadable.

    Errors are swallowed so a malformed criteria file doesn't take down the
    listings list — fit fields just come back as null instead.
    """
    try:
        markdown = _CRITERIA_PATH.read_text(encoding="utf-8")
    except OSError:
        return None
    return parse_criteria(markdown)


async def _latest_decision(session: AsyncSession, listing_id: UUID) -> dict[str, Any] | None:
    """Return the most-recent DecisionJournalEntry for a listing as a dict, or None."""
    stmt = (
        select(DecisionJournalEntry)
        .where(DecisionJournalEntry.listing_id == listing_id)
        .order_by(DecisionJournalEntry.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    entry = result.scalars().first()
    if entry is None:
        return None
    return {
        "id": entry.id,
        "listing_id": entry.listing_id,
        "previous_status": entry.previous_status,
        "new_status": entry.new_status,
        "reason": entry.reason,
        "created_at": entry.created_at,
    }


async def _to_listing_read(
    listing: Listing,
    criteria: ParsedCriteria | None,
    session: AsyncSession,
) -> dict[str, Any]:
    """Serialize a `Listing` ORM row into a `ListingRead`-shaped dict with fit + decision fields."""
    payload: dict[str, Any] = {
        "id": listing.id,
        "created_at": listing.created_at,
        "updated_at": listing.updated_at,
        "source": listing.source,
        "source_url": listing.source_url,
        "business_name": listing.business_name,
        "industry": listing.industry,
        "naics_code": listing.naics_code,
        "location": listing.location,
        "asking_price": listing.asking_price,
        "sde": listing.sde,
        "cash_flow": listing.cash_flow,
        "revenue": listing.revenue,
        "narrative": listing.narrative,
        "reason_for_selling": listing.reason_for_selling,
        "raw_text": listing.raw_text,
        "broker_name": listing.broker_name,
        "broker_contact": listing.broker_contact,
        "status": listing.status,
        "notes": listing.notes,
        "tags": listing.tags,
        "fit_band": None,
        "fit_summary": None,
        "latest_decision": await _latest_decision(session, listing.id),
    }
    if criteria is not None:
        fit = score_listing(listing, criteria)
        payload["fit_band"] = fit.band
        payload["fit_summary"] = fit.summary
    return payload


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
) -> list[dict[str, Any]]:
    """List all listings, optionally filtered by `status`. Fit fields are computed per-listing."""
    stmt = select(Listing).order_by(Listing.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Listing.status == status_filter)
    result = await session.execute(stmt)
    listings = list(result.scalars().all())
    criteria = _load_criteria()
    return [await _to_listing_read(listing, criteria, session) for listing in listings]


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
async def create_listing(payload: ListingCreate, session: SessionDep) -> dict[str, Any]:
    """Create a new listing. Only `business_name` is required."""
    listing = Listing(**payload.model_dump())
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return await _to_listing_read(listing, _load_criteria(), session)


@router.get("/{listing_id}", response_model=ListingRead)
async def get_listing(listing_id: UUID, session: SessionDep) -> dict[str, Any]:
    """Fetch a single listing by id. 404 if missing."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    return await _to_listing_read(listing, _load_criteria(), session)


@router.patch("/{listing_id}", response_model=ListingUpdateResponse)
async def update_listing(
    listing_id: UUID,
    payload: ListingUpdate,
    session: SessionDep,
) -> dict[str, Any]:
    """Partial update; only fields present in the body are written.

    Status transitions to `passed`, `tracking`, or `loi` set `requires_decision`
    in the response so the frontend can prompt for a journal entry. The state
    change still persists either way — the journal is best-effort capture.
    """
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")

    previous_status = listing.status
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(listing, field, value)

    await session.commit()
    await session.refresh(listing)

    requires_decision = (
        "status" in changes and listing.status != previous_status and listing.status in _DECISION_WORTHY_STATUSES
    )

    return {
        "listing": await _to_listing_read(listing, _load_criteria(), session),
        "requires_decision": requires_decision,
        "decision_previous_status": previous_status if requires_decision else None,
        "decision_new_status": listing.status if requires_decision else None,
    }


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(listing_id: UUID, session: SessionDep) -> None:
    """Hard delete. 404 if the listing doesn't exist."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    await session.delete(listing)
    await session.commit()
