"""End-to-end tests for the listing CRUD endpoints."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_listings_empty(client: AsyncClient) -> None:
    """`GET /api/listings` returns an empty list when no listings exist."""
    response = await client.get("/api/listings")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_minimal_listing(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    """`POST /api/listings` with only `business_name` succeeds and returns the created listing."""
    response = await client.post("/api/listings", json=listing_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["business_name"] == "Acme HVAC"
    assert body["status"] == "new"
    assert body["source"] == "manual"
    assert body["tags"] == []
    assert body["asking_price"] is None
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_full_listing_round_trip(client: AsyncClient, full_listing_payload: dict[str, Any]) -> None:
    """Every field on a full payload survives the round trip through DB and back."""
    response = await client.post("/api/listings", json=full_listing_payload)
    assert response.status_code == 201
    body = response.json()
    for field, expected in full_listing_payload.items():
        assert body[field] == expected, f"field `{field}` did not round-trip"


@pytest.mark.asyncio
async def test_create_rejects_missing_business_name(client: AsyncClient) -> None:
    """`business_name` is required; payload without it returns 422."""
    response = await client.post("/api/listings", json={"industry": "HVAC"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_negative_asking_price(client: AsyncClient) -> None:
    """`asking_price` must be non-negative."""
    response = await client.post(
        "/api/listings",
        json={"business_name": "Acme", "asking_price": -1},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_invalid_status(client: AsyncClient) -> None:
    """`status` must be one of the documented Literal values."""
    response = await client.post(
        "/api/listings",
        json={"business_name": "Acme", "status": "bogus"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_listing_by_id(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    """`GET /api/listings/{id}` returns the previously created listing."""
    created = (await client.post("/api/listings", json=listing_payload)).json()
    response = await client.get(f"/api/listings/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_listing_404(client: AsyncClient) -> None:
    """`GET /api/listings/{id}` returns 404 for an unknown id."""
    response = await client.get(f"/api/listings/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_filters_by_status(client: AsyncClient) -> None:
    """`GET /api/listings?status_filter=...` only returns matching rows."""
    await client.post("/api/listings", json={"business_name": "A", "status": "new"})
    await client.post("/api/listings", json={"business_name": "B", "status": "passed"})
    await client.post("/api/listings", json={"business_name": "C", "status": "passed"})

    response = await client.get("/api/listings", params={"status_filter": "passed"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {row["business_name"] for row in body} == {"B", "C"}


@pytest.mark.asyncio
async def test_patch_partial_update(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    """PATCH only modifies provided fields; other fields are preserved."""
    created = (await client.post("/api/listings", json=listing_payload)).json()

    response = await client.patch(
        f"/api/listings/{created['id']}",
        json={"status": "reviewing", "notes": "Looking promising."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reviewing"
    assert body["notes"] == "Looking promising."
    assert body["business_name"] == "Acme HVAC"
    assert body["source"] == "manual"


@pytest.mark.asyncio
async def test_patch_404(client: AsyncClient) -> None:
    """PATCH against a missing id returns 404."""
    response = await client.patch(f"/api/listings/{uuid4()}", json={"status": "passed"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_rejects_unknown_fields(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    """`ListingUpdate` forbids extra fields — typos at the API surface should fail loudly."""
    created = (await client.post("/api/listings", json=listing_payload)).json()

    response = await client.patch(
        f"/api/listings/{created['id']}",
        json={"buisness_name": "typo"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_listing(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    """DELETE returns 204 and the listing is gone afterward."""
    created = (await client.post("/api/listings", json=listing_payload)).json()

    response = await client.delete(f"/api/listings/{created['id']}")
    assert response.status_code == 204

    get_response = await client.get(f"/api/listings/{created['id']}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_404(client: AsyncClient) -> None:
    """DELETE against a missing id returns 404."""
    response = await client.delete(f"/api/listings/{uuid4()}")
    assert response.status_code == 404
