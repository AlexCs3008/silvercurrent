"""FastAPI application entry point for the Silvercurrent backend."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from silvercurrent.api.analyze import router as analyze_router
from silvercurrent.api.calibration import router as calibration_router
from silvercurrent.api.chat import router as chat_router
from silvercurrent.api.decisions import router as decisions_router
from silvercurrent.api.documents import router as documents_router
from silvercurrent.api.listings import router as listings_router

app = FastAPI(title="Silvercurrent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listings_router)
app.include_router(decisions_router)
app.include_router(documents_router)
app.include_router(calibration_router)
app.include_router(chat_router)
app.include_router(analyze_router)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Liveness probe used by the frontend and `docker compose` healthchecks."""
    return {"status": "ok", "service": "silvercurrent-backend"}
