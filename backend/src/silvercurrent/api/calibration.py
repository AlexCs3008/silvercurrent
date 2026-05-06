"""HTTP route for the calibration / inventory rollup (Phase F).

Mirror, not advice. Aggregates listings + decision-journal data into a single
JSON payload for the calibration page. The frontend gates the view behind a
"requires ≥20 reviewed listings" empty state — surface, never decide.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from statistics import quantiles
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.criteria import parse_criteria, score_listing
from silvercurrent.db.models import DecisionJournalEntry, Listing
from silvercurrent.db.session import get_session

router = APIRouter(prefix="/api", tags=["calibration"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Histogram buckets (whole dollars). Open-ended top bucket via `+inf`.
_SDE_BUCKETS: list[tuple[int, float]] = [
    (0, 100_000),
    (100_000, 250_000),
    (250_000, 500_000),
    (500_000, 1_000_000),
    (1_000_000, 2_000_000),
    (2_000_000, float("inf")),
]
_ASKING_BUCKETS: list[tuple[int, float]] = [
    (0, 250_000),
    (250_000, 500_000),
    (500_000, 1_000_000),
    (1_000_000, 2_000_000),
    (2_000_000, 5_000_000),
    (5_000_000, float("inf")),
]

# Statuses that count as "reviewed" — the user looked at the deal and made a
# call. `new` is the inbox; `reviewing` is in-flight.
_REVIEWED_STATUSES: frozenset[str] = frozenset({"passed", "tracking", "loi", "closed"})

# Minimum decision-count before percentile metrics become meaningful.
_TIME_TO_DECISION_MIN_SAMPLES = 5


def _histogram(
    values: list[int | None],
    buckets: list[tuple[int, float]],
) -> list[dict[str, Any]]:
    """Bucket non-null values into `buckets`. Skips None entries silently."""
    counts: list[int] = [0 for _ in buckets]
    for v in values:
        if v is None:
            continue
        for i, (lo, hi) in enumerate(buckets):
            if lo <= v < hi:
                counts[i] += 1
                break
    out: list[dict[str, Any]] = []
    for (lo, hi), count in zip(buckets, counts, strict=True):
        out.append(
            {
                "bucket_low": lo,
                "bucket_high": None if hi == float("inf") else int(hi),
                "count": count,
            }
        )
    return out


def _percentiles(samples: list[float], probs: list[float]) -> list[float | None]:
    """Empirical percentiles via `statistics.quantiles`. Returns None when sample is too small."""
    if len(samples) < _TIME_TO_DECISION_MIN_SAMPLES:
        return [None for _ in probs]
    cuts = quantiles(samples, n=100, method="inclusive")
    return [cuts[int(p * 100) - 1] for p in probs]


@router.get("/calibration")
async def get_calibration(session: SessionDep) -> dict[str, Any]:
    """Return the inventory rollup. Empty/zero-shaped when the DB is empty."""
    listings = list((await session.execute(select(Listing))).scalars().all())
    n_total = len(listings)
    n_reviewed = sum(1 for listing in listings if listing.status in _REVIEWED_STATUSES)

    # status mix — every documented status gets a key, zero by default.
    status_mix: dict[str, int] = dict.fromkeys(["new", "reviewing", "passed", "tracking", "loi", "closed"], 0)
    for listing in listings:
        status_mix[listing.status] = status_mix.get(listing.status, 0) + 1

    # source mix.
    source_counts = Counter(listing.source for listing in listings)
    source_mix: dict[str, int] = dict(source_counts)

    # broker top — most-frequent named brokers (case-preserving).
    broker_counts = Counter(listing.broker_name for listing in listings if listing.broker_name)
    broker_top = [{"name": name, "count": count} for name, count in broker_counts.most_common(5)]

    # histograms.
    sde_histogram = _histogram([listing.sde for listing in listings], _SDE_BUCKETS)
    asking_histogram = _histogram([listing.asking_price for listing in listings], _ASKING_BUCKETS)

    # fit_band_mix — recompute per listing; criteria.md is small.
    try:
        from pathlib import Path

        criteria_path = Path(__file__).resolve().parents[4] / "docs" / "criteria.md"
        criteria = parse_criteria(criteria_path.read_text(encoding="utf-8"))
    except OSError:
        criteria = None

    fit_band_mix: dict[str, int] = dict.fromkeys(["strong", "partial", "weak", "mismatch", "unknown"], 0)
    if criteria is not None:
        for listing in listings:
            band = score_listing(listing, criteria).band
            fit_band_mix[band] = fit_band_mix.get(band, 0) + 1

    # time-to-decision distribution.
    decisions = list(
        (
            await session.execute(
                select(DecisionJournalEntry).order_by(
                    DecisionJournalEntry.listing_id,
                    DecisionJournalEntry.created_at.asc(),
                )
            )
        )
        .scalars()
        .all()
    )
    seen_listings: set[str] = set()
    listing_created_at: dict[str, datetime] = {str(listing.id): listing.created_at for listing in listings}
    deltas: list[float] = []
    for entry in decisions:
        key = str(entry.listing_id)
        if key in seen_listings:
            continue
        seen_listings.add(key)
        created = listing_created_at.get(key)
        if created is None:
            continue
        deltas.append((entry.created_at - created).total_seconds() / 86_400.0)

    p50, p90 = _percentiles(deltas, [0.5, 0.9])

    # Most-recent 20 decisions.
    recent_decisions = sorted(decisions, key=lambda e: e.created_at, reverse=True)[:20]
    decision_reasons = [
        {
            "snippet": entry.reason[:200],
            "listing_id": str(entry.listing_id),
            "decided_at": entry.created_at.isoformat(),
            "status": entry.new_status,
        }
        for entry in recent_decisions
    ]

    return {
        "n_total": n_total,
        "n_reviewed": n_reviewed,
        "status_mix": status_mix,
        "fit_band_mix": fit_band_mix,
        "sde_histogram": sde_histogram,
        "asking_histogram": asking_histogram,
        "source_mix": source_mix,
        "broker_top": broker_top,
        "time_to_decision_days": {
            "p50": p50,
            "p90": p90,
            "n": len(deltas),
        },
        "decision_reasons": decision_reasons,
    }
