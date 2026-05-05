"""Application configuration loaded from environment variables and `.env`."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for `.env` in the backend dir AND the repo root (one above).
# Repo-root `.env` wins over backend-local one when both exist.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILES: tuple[str, ...] = (
    str(_BACKEND_DIR / ".env"),
    str(_BACKEND_DIR.parent / ".env"),
)


class Settings(BaseSettings):
    """Runtime settings for the Silvercurrent backend."""

    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./silvercurrent.db"
    chroma_persist_dir: str = "./.chroma"
    extraction_model: str = "claude-sonnet-4-6"

    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")


def get_settings() -> Settings:
    """Return a fresh `Settings` instance reading the current environment."""
    return Settings()
