"""FastAPI application entry point for the Silvercurrent backend."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Silvercurrent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Liveness probe used by the frontend and `docker compose` healthchecks."""
    return {"status": "ok", "service": "silvercurrent-backend"}
