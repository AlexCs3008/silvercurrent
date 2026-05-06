"""`score_against_criteria` — deterministic fit-band tool for the Analyst agent.

The Analyst quotes this tool's output verbatim in the Deal Sheet's "Hard
knockouts" and "Numeric fit" sections, replacing the previous LLM-reasoning-
over-criteria-text approach. Numerical claims always come from tools
(CLAUDE.md hard rule 5); fit-band membership now joins them.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.tools._envelope import Envelope, fail, ok
from silvercurrent.criteria import parse_criteria, score_listing
from silvercurrent.db.models import Listing

_REPO_ROOT = Path(__file__).resolve().parents[5]
_CRITERIA_PATH = _REPO_ROOT / "docs" / "criteria.md"


async def score_against_criteria(
    *,
    listing_id: UUID,
    session: AsyncSession,
) -> Envelope:
    """Compute the fit-band for a listing against `docs/criteria.md`.

    Returns an envelope wrapping a serialized `FitResult` dict — `band`,
    `summary`, `numeric_fit`, `hard_knockouts`, `dimensions_evaluated`,
    `dimensions_total`, `notes`.
    """
    listing = await session.get(Listing, listing_id)
    if listing is None:
        return fail(f"listing {listing_id} not found")

    if not _CRITERIA_PATH.exists():
        return fail(f"criteria file not found at {_CRITERIA_PATH}")
    try:
        markdown = _CRITERIA_PATH.read_text(encoding="utf-8")
    except OSError as e:
        return fail(f"failed to read criteria file: {e}")

    criteria = parse_criteria(markdown)
    fit = score_listing(listing, criteria)

    return ok(
        {
            "listing_id": str(listing.id),
            "fit_result": asdict(fit),
        }
    )
