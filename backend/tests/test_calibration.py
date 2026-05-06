"""Tests for the calibration rollup endpoint."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_calibration_empty_db_returns_zeros(client: AsyncClient) -> None:
    response = await client.get("/api/calibration")
    assert response.status_code == 200
    body = response.json()
    assert body["n_total"] == 0
    assert body["n_reviewed"] == 0
    assert all(count == 0 for count in body["status_mix"].values())
    assert all(b["count"] == 0 for b in body["sde_histogram"])
    assert body["decision_reasons"] == []
    assert body["broker_top"] == []


@pytest.mark.asyncio
async def test_calibration_aggregates_status_and_source_mix(
    client: AsyncClient,
) -> None:
    payloads = [
        {"business_name": "A", "status": "new", "source": "manual"},
        {"business_name": "B", "status": "passed", "source": "manual"},
        {"business_name": "C", "status": "passed", "source": "url"},
        {"business_name": "D", "status": "tracking", "source": "pdf"},
    ]
    for p in payloads:
        await client.post("/api/listings", json=p)

    body: dict[str, Any] = (await client.get("/api/calibration")).json()
    assert body["n_total"] == 4
    # passed × 2 + tracking × 1 = 3 reviewed
    assert body["n_reviewed"] == 3
    assert body["status_mix"]["passed"] == 2
    assert body["status_mix"]["tracking"] == 1
    assert body["status_mix"]["new"] == 1
    assert body["source_mix"]["manual"] == 2
    assert body["source_mix"]["url"] == 1
    assert body["source_mix"]["pdf"] == 1


@pytest.mark.asyncio
async def test_calibration_decision_reasons_surfaced(
    client: AsyncClient,
) -> None:
    created = (await client.post("/api/listings", json={"business_name": "A", "status": "new"})).json()
    await client.post(
        f"/api/listings/{created['id']}/decisions",
        json={
            "previous_status": "new",
            "new_status": "passed",
            "reason": "Asking too high.",
        },
    )
    body = (await client.get("/api/calibration")).json()
    assert len(body["decision_reasons"]) == 1
    assert body["decision_reasons"][0]["status"] == "passed"
    assert body["decision_reasons"][0]["snippet"] == "Asking too high."


@pytest.mark.asyncio
async def test_time_to_decision_null_under_threshold(client: AsyncClient) -> None:
    """Fewer than 5 decisions → percentiles are null, not nan."""
    created = (await client.post("/api/listings", json={"business_name": "A", "status": "new"})).json()
    await client.post(
        f"/api/listings/{created['id']}/decisions",
        json={"new_status": "passed", "reason": "x"},
    )
    body = (await client.get("/api/calibration")).json()
    assert body["time_to_decision_days"]["n"] == 1
    assert body["time_to_decision_days"]["p50"] is None
    assert body["time_to_decision_days"]["p90"] is None
