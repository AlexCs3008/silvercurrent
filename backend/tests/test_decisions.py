"""Tests for the decision-journal endpoints (Phase B)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_creates_decision_entry(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    """POST writes a row, GET returns it, the reason persists."""
    created = (await client.post("/api/listings", json=listing_payload)).json()
    response = await client.post(
        f"/api/listings/{created['id']}/decisions",
        json={
            "previous_status": "new",
            "new_status": "passed",
            "reason": "Asking is 5× SDE, no path to negotiate down.",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["new_status"] == "passed"
    assert body["previous_status"] == "new"
    assert body["reason"].startswith("Asking is 5× SDE")
    assert body["listing_id"] == created["id"]


@pytest.mark.asyncio
async def test_post_with_empty_reason_returns_422(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    created = (await client.post("/api/listings", json=listing_payload)).json()
    response = await client.post(
        f"/api/listings/{created['id']}/decisions",
        json={"previous_status": "new", "new_status": "passed", "reason": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_against_unknown_listing_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/listings/{uuid4()}/decisions",
        json={"new_status": "passed", "reason": "test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_decisions_returns_newest_first(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    created = (await client.post("/api/listings", json=listing_payload)).json()
    await client.post(
        f"/api/listings/{created['id']}/decisions",
        json={"new_status": "tracking", "reason": "first"},
    )
    await client.post(
        f"/api/listings/{created['id']}/decisions",
        json={"new_status": "passed", "reason": "second"},
    )
    response = await client.get(f"/api/listings/{created['id']}/decisions")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert rows[0]["reason"] == "second"
    assert rows[1]["reason"] == "first"


@pytest.mark.asyncio
async def test_listing_read_includes_latest_decision(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    """`GET /api/listings/{id}` surfaces the most-recent journal entry."""
    created = (await client.post("/api/listings", json=listing_payload)).json()
    await client.post(
        f"/api/listings/{created['id']}/decisions",
        json={
            "previous_status": "new",
            "new_status": "tracking",
            "reason": "Worth a closer look.",
        },
    )
    detail = (await client.get(f"/api/listings/{created['id']}")).json()
    assert detail["latest_decision"] is not None
    assert detail["latest_decision"]["new_status"] == "tracking"
    assert detail["latest_decision"]["reason"] == "Worth a closer look."


@pytest.mark.asyncio
async def test_listing_with_no_decisions_has_null_latest(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    created = (await client.post("/api/listings", json=listing_payload)).json()
    detail = (await client.get(f"/api/listings/{created['id']}")).json()
    assert detail["latest_decision"] is None
