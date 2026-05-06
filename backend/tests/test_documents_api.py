"""End-to-end tests for the documents API."""

from __future__ import annotations

import io
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_text_document_round_trips(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    created = (await client.post("/api/listings", json=listing_payload)).json()
    body = b"Revenue in 2023 was $2.1M.\n\nCustomer concentration: top 5 = 25%."
    files = {"file": ("notes.txt", io.BytesIO(body), "text/plain")}
    response = await client.post(f"/api/listings/{created['id']}/documents", files=files)
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["filename"] == "notes.txt"
    assert doc["content_type"] == "text/plain"
    assert doc["byte_size"] == len(body)
    assert len(doc["sha256"]) == 64

    listed = await client.get(f"/api/listings/{created['id']}/documents")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == doc["id"]


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_content_type(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    created = (await client.post("/api/listings", json=listing_payload)).json()
    files = {
        "file": ("photo.png", io.BytesIO(b"\x89PNG fake bytes"), "image/png"),
    }
    response = await client.post(f"/api/listings/{created['id']}/documents", files=files)
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    created = (await client.post("/api/listings", json=listing_payload)).json()
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    response = await client.post(f"/api/listings/{created['id']}/documents", files=files)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_404_for_unknown_listing(client: AsyncClient) -> None:
    files = {"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")}
    response = await client.post(f"/api/listings/{uuid4()}/documents", files=files)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_removes_document(
    client: AsyncClient, listing_payload: dict[str, Any], tmp_path_factory: pytest.TempPathFactory
) -> None:
    created = (await client.post("/api/listings", json=listing_payload)).json()
    files = {"file": ("notes.txt", io.BytesIO(b"some text"), "text/plain")}
    upload = (await client.post(f"/api/listings/{created['id']}/documents", files=files)).json()

    response = await client.delete(f"/api/listings/{created['id']}/documents/{upload['id']}")
    assert response.status_code == 204

    listed = (await client.get(f"/api/listings/{created['id']}/documents")).json()
    assert listed == []


@pytest.mark.asyncio
async def test_get_raw_streams_uploaded_file(client: AsyncClient, listing_payload: dict[str, Any]) -> None:
    created = (await client.post("/api/listings", json=listing_payload)).json()
    payload_bytes = b"sentinel content for raw download"
    files = {"file": ("notes.txt", io.BytesIO(payload_bytes), "text/plain")}
    upload = (await client.post(f"/api/listings/{created['id']}/documents", files=files)).json()

    response = await client.get(f"/api/listings/{created['id']}/documents/{upload['id']}/raw")
    assert response.status_code == 200
    assert response.content == payload_bytes
