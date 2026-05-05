"""`get_active_listing` — fetch a listing by id when the chat is scoped to one."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.tools._envelope import Envelope, fail, ok
from silvercurrent.db.models import Listing


async def get_active_listing(
    *,
    listing_id: UUID | None,
    session: AsyncSession,
) -> Envelope:
    """Look up a listing by id. Returns `null` when the chat scope has no listing.

    Used by the Operator and (later) Analyst agents. Global chat scope passes
    `listing_id=None`; listing chat scope passes the listing's id.
    """
    if listing_id is None:
        return ok({"listing": None})

    listing = await session.get(Listing, listing_id)
    if listing is None:
        return fail(f"listing {listing_id} not found")

    snapshot: dict[str, Any] = {
        "id": str(listing.id),
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
        "broker_name": listing.broker_name,
        "broker_contact": listing.broker_contact,
        "status": listing.status,
        "tags": list(listing.tags),
        "source": listing.source,
        "source_url": listing.source_url,
    }
    return ok({"listing": snapshot})
