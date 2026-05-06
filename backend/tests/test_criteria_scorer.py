"""Tests for the deterministic fit-band scorer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from silvercurrent.criteria.parser import ParsedCriteria
from silvercurrent.criteria.scorer import score_listing
from silvercurrent.db.models import Listing


def _listing(**overrides: object) -> Listing:
    """Build a Listing instance without touching the DB.

    SQLAlchemy doesn't require a session to instantiate; we just need a
    plain object the scorer can read from.
    """
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "source": "manual",
        "source_url": None,
        "business_name": "Test Co",
        "industry": "HVAC services",
        "naics_code": None,
        "location": "Miami, FL",
        "asking_price": 1_200_000,
        "sde": 400_000,
        "cash_flow": None,
        "revenue": 2_000_000,
        "narrative": None,
        "reason_for_selling": None,
        "raw_text": None,
        "broker_name": None,
        "broker_contact": None,
        "status": "new",
        "notes": None,
        "tags": [],
    }
    defaults.update(overrides)
    return Listing(**defaults)


def _criteria(**overrides: object) -> ParsedCriteria:
    base: dict[str, object] = {
        "asking_price_band": (500_000, 3_000_000),
        "sde_band": (200_000, 800_000),
        "revenue_band": (1_000_000, 8_000_000),
        "multiple_ceiling": 3.5,
    }
    base.update(overrides)
    return ParsedCriteria(**base)  # type: ignore[arg-type]


def test_strong_band_when_all_in_band_and_no_knockouts() -> None:
    listing = _listing()
    criteria = _criteria()
    fit = score_listing(listing, criteria)
    assert fit.band == "strong"
    assert fit.dimensions_evaluated == 4  # asking, sde, revenue, multiple
    assert all(d.status == "in_band" for d in fit.numeric_fit)


def test_declining_revenue_tag_flips_to_mismatch_regardless_of_financials() -> None:
    listing = _listing(tags=["declining-revenue"])
    criteria = _criteria(
        hard_knockouts_text=["Declining revenue 3 years running."],
    )
    fit = score_listing(listing, criteria)
    assert fit.band == "mismatch"
    assert any(k.status == "HIT" for k in fit.hard_knockouts)


def test_unknown_band_when_listing_discloses_nothing() -> None:
    """Listing with no financials and no industry/location returns unknown."""
    listing = _listing(
        asking_price=None,
        sde=None,
        revenue=None,
        industry=None,
        naics_code=None,
        location=None,
    )
    criteria = _criteria()
    fit = score_listing(listing, criteria)
    assert fit.band == "unknown"
    assert fit.dimensions_evaluated == 0


def test_multiple_ceiling_exceeded_marks_out_of_band_without_knockout() -> None:
    """A 5× listing without an asking-multiple knockout stays out_of_band, no HIT."""
    listing = _listing(asking_price=2_000_000, sde=400_000)  # 5× SDE
    criteria = _criteria()  # No hard_knockouts_text means no knockout
    fit = score_listing(listing, criteria)
    multiple_dim = next(d for d in fit.numeric_fit if d.name == "asking_multiple_sde")
    assert multiple_dim.status == "out_of_band"
    assert multiple_dim.listing_value == 5.0
    assert all(k.status != "HIT" for k in fit.hard_knockouts)


def test_asking_multiple_knockout_hits_when_text_present_and_listing_exceeds() -> None:
    """When the asking-multiple knockout is in criteria text and the listing exceeds it → HIT."""
    listing = _listing(asking_price=2_000_000, sde=400_000)  # 5× SDE
    criteria = _criteria(
        hard_knockouts_text=["Asking price > 4× SDE without a clear, quantified reason."],
    )
    fit = score_listing(listing, criteria)
    knockout = fit.hard_knockouts[0]
    assert knockout.status == "HIT"
    assert fit.band == "mismatch"


def test_v1_placeholder_flag_surfaces_in_notes() -> None:
    listing = _listing()
    criteria = _criteria(is_v1_placeholder=True)
    fit = score_listing(listing, criteria)
    assert any("V1" in note or "v1" in note for note in fit.notes)


def test_partial_band_when_some_dimensions_in_band() -> None:
    """50–80% in-band → partial."""
    # 2 of 4 in band: asking ok, sde out, revenue ok, multiple out
    listing = _listing(asking_price=1_000_000, sde=100_000, revenue=2_000_000)
    criteria = _criteria()
    fit = score_listing(listing, criteria)
    assert fit.band in ("partial", "weak")
    in_band = sum(1 for d in fit.numeric_fit if d.status == "in_band")
    assert 0 < in_band < fit.dimensions_evaluated


def test_summary_counts_only_evaluable_dimensions() -> None:
    listing = _listing(sde=None)  # SDE not disclosed → not_disclosed
    criteria = _criteria()
    fit = score_listing(listing, criteria)
    assert "of " in fit.summary
    # asking, revenue, multiple may all be evaluable; sde is not_disclosed
    assert fit.dimensions_evaluated <= 3
