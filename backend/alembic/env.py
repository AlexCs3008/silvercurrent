"""Alembic migration environment for Silvercurrent.

Reads the connection string from the `DATABASE_URL` env var (falling back to
`alembic.ini`'s `sqlalchemy.url`). The async `+psycopg` driver is normalized to
the sync `psycopg` driver here, so migrations run synchronously even when the
runtime app uses an async engine.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make `silvercurrent.db.models` importable when running `alembic` from `backend/`.
from silvercurrent.db.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _resolve_url() -> str:
    """Resolve the DB URL: env var, then Settings default. Normalize async drivers to sync."""
    from silvercurrent.config import get_settings  # noqa: PLC0415 — local import avoids settings load on package import

    url = os.environ.get("DATABASE_URL") or get_settings().database_url
    # Alembic's autogenerate runs synchronously; strip any async driver suffix.
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    elif url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return url


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits SQL to stdout)."""
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    section = config.get_section(config.config_ini_section, {}) or {}
    section["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
