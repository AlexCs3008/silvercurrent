# 0005 — Local dev without Docker

*Status: accepted · 2026-05-04 (supersedes the dev-time portion of ADR 0001)*

## Context

Phase 0 originally targeted `docker compose up` as the dev bring-up: Postgres + Chroma server + backend + frontend, all containerized. That works, but adds a heavy daily-driver dependency (Docker Desktop) for what is, charter-wise, a single-user app.

Charter §8 actually endorses a lighter path: **"Stack: Python 3.12+ / FastAPI / SQLite (dev) → Postgres (when needed)"**. We overshot by reaching for Postgres on day one.

Mr. Alonso pushed back on the Docker dependency in the Phase 0 closeout. Cheaper to switch now (skeleton only) than after Phase 1 wires real models.

## Decision

For local dev, run everything natively in two terminals — no Docker.

- **DB**: SQLite via `aiosqlite` (async driver). Default URL: `sqlite+aiosqlite:///./silvercurrent.db`. The file lives in `backend/silvercurrent.db` and is gitignored.
- **Vector DB**: Chroma in `PersistentClient` mode — file-backed, in-process, no server. Persist directory: `backend/.chroma/` (gitignored).
- **Backend**: `uv run uvicorn silvercurrent.main:app --reload` on port 8000.
- **Frontend**: `pnpm dev` on port 3000.
- **Migrations**: `uv run alembic upgrade head`. The alembic env normalizes `sqlite+aiosqlite://` → `sqlite://` for sync migration runs.

`docker-compose.yml` stays in the repo as the documented path forward when SQLite stops being sufficient.

## Consequences

**Good**

- Two-terminal workflow on Windows. No Docker Desktop, no daemon to start, no resource overhead, no port forwarding gymnastics.
- Fits the charter's stated dev intent — SQLite was always the planned local DB.
- Faster iteration: hot reload on both sides, no container rebuild loop.
- `docker compose up` is still available as the migration target — switching later is a config change (`DATABASE_URL`) plus a Postgres-compatible alembic run, not a rewrite.
- Chroma `PersistentClient` has the same Python API as the HTTP client for our usage (`get_or_create_collection`, `add`, `query`). Phase 2 RAG code doesn't have to change shape when/if we move to a server.

**Trade-offs**

- Lose Postgres-specific features: JSONB, full-text search, listen/notify, concurrent writers. Mitigation: don't use them yet. Phase 1 listing storage is simple enough for SQLite. Revisit when Phase 2+ actually wants them.
- SQLite has weaker concurrency. For one user on one laptop, it's a non-issue.
- Two terminals to start manually. Mitigation: README has the exact commands; a `scripts/dev.sh` that backgrounds both is a future nicety, not a requirement.
- Two persistence formats (SQLite file + Chroma dir) instead of one Postgres + Chroma server. Both are gitignored under `data/`-equivalent paths.

## Migration trigger

Switch back to Postgres (via `docker compose up postgres` or a managed service) when *any* of:

1. We hit a feature SQLite can't reasonably serve (JSONB query patterns, FTS that pgvector + tsvector handles cleanly, write contention).
2. We ship to a small VPS for the email ingestion daemon (Phase 4) and need durable shared state.
3. The DB grows past a few hundred MB and SQLite's single-file model becomes operationally awkward.

When the trigger fires: change `DATABASE_URL` in `.env`, run `alembic upgrade head` against Postgres, copy any user data with a one-off script. The schema and ORM code don't change.

## Affected files

- `backend/src/silvercurrent/config.py` — default `database_url` flipped to SQLite, `chroma_host`/`chroma_port` replaced with `chroma_persist_dir`.
- `backend/alembic/env.py` — `sqlite+aiosqlite://` → `sqlite://` normalization for sync migrations.
- `backend/pyproject.toml` — `aiosqlite` added to runtime deps.
- `.env.example` — new defaults.
- `README.md` — quickstart rewritten for native dev.
- `.gitignore` — `*.db`, `*.db-journal`, `.chroma/` added.
- `docker-compose.yml` — kept, documented as the Postgres migration path.
