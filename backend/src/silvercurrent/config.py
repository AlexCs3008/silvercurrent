"""Application configuration loaded from environment variables and `.env`."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the Silvercurrent backend."""

    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./silvercurrent.db"
    chroma_persist_dir: str = "./.chroma"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings() -> Settings:
    """Return a fresh `Settings` instance reading the current environment."""
    return Settings()
