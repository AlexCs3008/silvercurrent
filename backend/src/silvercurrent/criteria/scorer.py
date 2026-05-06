"""Score a `Listing` against a `ParsedCriteria` to produce a `FitResult`.

Banding rule (deterministic, ADR 0008):

- Any `HIT` knockout → `mismatch`.
- Else, of the dimensions actually evaluated (data present on both sides):
  >=80% in_band → `strong`; >=50% → `partial`; <50% → `weak`.
  If 0 dimensions evaluated → `unknown`.

This scoring is intentionally coarse. It produces a *band*, not a 0–100 score —
fit-to-criteria is not the same as deal quality (charter §6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from silvercurrent.criteria.parser import ParsedCriteria
from silvercurrent.db.models import Listing

NumericStatus = Literal["in_band", "out_of_band", "not_disclosed"]
KnockoutStatus = Literal["HIT", "PASS", "NOT_DISCLOSED", "MANUAL_REVIEW"]
FitBand = Literal["strong", "partial", "weak", "mismatch", "unknown"]


@dataclass(frozen=True)
class NumericDim:
    """One numeric dimension's evaluation: value, band, in/out/not-disclosed."""

    name: str
    listing_value: float | int | str | None
    band_low: float | int | None
    band_high: float | int | None
    status: NumericStatus


@dataclass(frozen=True)
class Knockout:
    """One hard-knockout criterion's evaluation against the listing."""

    text: str
    status: KnockoutStatus


@dataclass(frozen=True)
class FitResult:
    """The Analyst's fit-band for a listing.

    `dimensions_evaluated` is the count of NumericDim entries with status
    `in_band` or `out_of_band` (i.e., we had data on both sides).
    `dimensions_total` is the count of dimensions we *attempted* (including
    `not_disclosed`). The summary string and band derive from this.
    """

    band: FitBand
    summary: str
    numeric_fit: list[NumericDim] = field(default_factory=list)
    hard_knockouts: list[Knockout] = field(default_factory=list)
    dimensions_evaluated: int = 0
    dimensions_total: int = 0
    notes: list[str] = field(default_factory=list)


# --- helpers ------------------------------------------------------------------


def _band_check(
    value: int | float | None,
    band: tuple[int | None, int | None],
) -> NumericStatus:
    """Return `in_band` / `out_of_band` / `not_disclosed` for a numeric value."""
    if value is None:
        return "not_disclosed"
    low, high = band
    if low is None and high is None:
        return "not_disclosed"
    if low is not None and value < low:
        return "out_of_band"
    if high is not None and value > high:
        return "out_of_band"
    return "in_band"


def _industry_status(listing: Listing, criteria: ParsedCriteria) -> NumericStatus:
    """Categorical industry match: hard-no → out_of_band, target → in_band, else not_disclosed."""
    haystack_parts = [listing.industry or "", listing.naics_code or ""]
    haystack = " ".join(haystack_parts).lower()
    if not haystack.strip():
        return "not_disclosed"
    for term in criteria.industry_hard_nos:
        if term and term in haystack:
            return "out_of_band"
    for term in criteria.industry_targets:
        if term and term in haystack:
            return "in_band"
    for term in criteria.industry_open_with_reservations:
        if term and term in haystack:
            return "in_band"
    return "out_of_band"


def _geography_status(listing: Listing, criteria: ParsedCriteria) -> NumericStatus:
    """Categorical geography match: hard-no → out_of_band, primary/secondary → in_band."""
    location = (listing.location or "").lower()
    if not location.strip():
        return "not_disclosed"
    for term in criteria.geography_hard_nos:
        if term and term in location:
            return "out_of_band"
    for term in criteria.geography_primary:
        if term and term in location:
            return "in_band"
    for term in criteria.geography_secondary:
        if term and term in location:
            return "in_band"
    return "out_of_band"


def _has_tag(listing: Listing, *needles: str) -> bool:
    """True iff any tag on the listing contains any of the given needles (case-insensitive)."""
    tags = [t.lower() for t in (listing.tags or [])]
    return any(n in t for t in tags for n in needles)


def _classify_knockout(text: str, listing: Listing) -> KnockoutStatus:
    """Map a knockout text line to HIT / PASS / NOT_DISCLOSED / MANUAL_REVIEW.

    Recognized well-known knockouts (matched on phrase):

    - declining revenue → HIT iff a tag contains "declining" / "decline"
    - customer concentration over X% → MANUAL_REVIEW (data not on the model)
    - asking price > N× SDE → computable: HIT/PASS/NOT_DISCLOSED
    - owner is the only person who can do the technical work → MANUAL_REVIEW
    - requires a license → MANUAL_REVIEW
    - dependent on a single third-party platform → MANUAL_REVIEW
    - pending litigation / IRS lien / environmental issue → MANUAL_REVIEW

    Anything else → MANUAL_REVIEW. The user sees the text either way; the
    distinction only affects whether the knockout flips the band to
    `mismatch`.
    """
    lower = text.lower()

    # Declining revenue — tag-driven.
    if "declining revenue" in lower or "revenue decline" in lower:
        if _has_tag(listing, "declining", "decline"):
            return "HIT"
        return "MANUAL_REVIEW"

    # Asking price multiple ceiling — derive from asking/sde.
    if "asking price" in lower and ("× sde" in lower or "x sde" in lower or "× sde" in text.lower()):
        m = re.search(r"(\d+(?:\.\d+)?)\s*[×x]\s*sde", lower)
        if m is None:
            return "MANUAL_REVIEW"
        cap = float(m.group(1))
        if listing.asking_price is None or listing.sde is None or listing.sde <= 0:
            return "NOT_DISCLOSED"
        actual = listing.asking_price / listing.sde
        return "HIT" if actual > cap else "PASS"

    # Single customer concentration — model doesn't carry concentration data.
    if "single customer" in lower or "customer concentration" in lower:
        # Tag-based optional signal: a curator could mark "concentration-risk".
        if _has_tag(listing, "concentration-risk", "single-customer"):
            return "HIT"
        return "MANUAL_REVIEW"

    # Owner-only / technical-work knockout.
    if "owner is the only" in lower or "only person who can do the technical" in lower:
        if _has_tag(listing, "owner-only", "owner-dependent"):
            return "HIT"
        return "MANUAL_REVIEW"

    # License-required knockout.
    if "requires a license" in lower or "regulated license" in lower:
        return "MANUAL_REVIEW"

    # Single-platform dependency.
    if "single third-party platform" in lower or "single-platform" in lower:
        return "MANUAL_REVIEW"

    # Litigation / lien / environmental.
    if "litigation" in lower or "lien" in lower or "environmental" in lower:
        if _has_tag(listing, "litigation", "lien", "environmental"):
            return "HIT"
        return "MANUAL_REVIEW"

    return "MANUAL_REVIEW"


# --- main ---------------------------------------------------------------------


def score_listing(listing: Listing, criteria: ParsedCriteria) -> FitResult:
    """Score `listing` against `criteria` and return a deterministic FitResult."""
    numeric_fit: list[NumericDim] = []

    # Asking price band.
    if criteria.asking_price_band != (None, None):
        status = _band_check(listing.asking_price, criteria.asking_price_band)
        numeric_fit.append(
            NumericDim(
                name="asking_price",
                listing_value=listing.asking_price,
                band_low=criteria.asking_price_band[0],
                band_high=criteria.asking_price_band[1],
                status=status,
            )
        )

    # SDE band.
    if criteria.sde_band != (None, None):
        status = _band_check(listing.sde, criteria.sde_band)
        numeric_fit.append(
            NumericDim(
                name="sde",
                listing_value=listing.sde,
                band_low=criteria.sde_band[0],
                band_high=criteria.sde_band[1],
                status=status,
            )
        )

    # Revenue band.
    if criteria.revenue_band != (None, None):
        status = _band_check(listing.revenue, criteria.revenue_band)
        numeric_fit.append(
            NumericDim(
                name="revenue",
                listing_value=listing.revenue,
                band_low=criteria.revenue_band[0],
                band_high=criteria.revenue_band[1],
                status=status,
            )
        )

    # Asking multiple ceiling.
    if criteria.multiple_ceiling is not None:
        if listing.asking_price is None or listing.sde is None or listing.sde <= 0:
            numeric_fit.append(
                NumericDim(
                    name="asking_multiple_sde",
                    listing_value=None,
                    band_low=None,
                    band_high=criteria.multiple_ceiling,
                    status="not_disclosed",
                )
            )
        else:
            actual_multiple = round(listing.asking_price / listing.sde, 2)
            status = "in_band" if actual_multiple <= criteria.multiple_ceiling else "out_of_band"
            numeric_fit.append(
                NumericDim(
                    name="asking_multiple_sde",
                    listing_value=actual_multiple,
                    band_low=None,
                    band_high=criteria.multiple_ceiling,
                    status=status,
                )
            )

    # Industry — categorical, only score if criteria has any preference.
    if criteria.industry_targets or criteria.industry_hard_nos or criteria.industry_open_with_reservations:
        numeric_fit.append(
            NumericDim(
                name="industry",
                listing_value=listing.industry or listing.naics_code,
                band_low=None,
                band_high=None,
                status=_industry_status(listing, criteria),
            )
        )

    # Geography — categorical.
    if criteria.geography_primary or criteria.geography_secondary or criteria.geography_hard_nos:
        numeric_fit.append(
            NumericDim(
                name="geography",
                listing_value=listing.location,
                band_low=None,
                band_high=None,
                status=_geography_status(listing, criteria),
            )
        )

    # Hard knockouts.
    knockouts: list[Knockout] = [
        Knockout(text=text, status=_classify_knockout(text, listing)) for text in criteria.hard_knockouts_text
    ]

    # Banding.
    notes: list[str] = []
    if criteria.is_v1_placeholder:
        notes.append("criteria are V1 placeholders — fit-band is illustrative")

    any_hit = any(k.status == "HIT" for k in knockouts)
    dimensions_total = len(numeric_fit)
    dimensions_evaluated = sum(1 for d in numeric_fit if d.status in ("in_band", "out_of_band"))
    in_band_count = sum(1 for d in numeric_fit if d.status == "in_band")

    band: FitBand
    if any_hit:
        band = "mismatch"
    elif dimensions_evaluated == 0:
        band = "unknown"
    else:
        ratio = in_band_count / dimensions_evaluated
        if ratio >= 0.8:
            band = "strong"
        elif ratio >= 0.5:
            band = "partial"
        else:
            band = "weak"

    if band == "unknown":
        summary = "no evaluable dimensions — listing didn't disclose enough to score"
    else:
        summary = f"matches {in_band_count} of {dimensions_evaluated} evaluable criteria"

    return FitResult(
        band=band,
        summary=summary,
        numeric_fit=numeric_fit,
        hard_knockouts=knockouts,
        dimensions_evaluated=dimensions_evaluated,
        dimensions_total=dimensions_total,
        notes=notes,
    )
