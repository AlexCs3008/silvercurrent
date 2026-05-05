"""Smoke test for the `/api/health` liveness endpoint."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from silvercurrent.main import app


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    """`GET /api/health` returns 200 and a payload tagged `status: ok`."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "silvercurrent-backend"
