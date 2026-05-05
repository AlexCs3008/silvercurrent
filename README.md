# Silvercurrent

A personal cockpit for evaluating small-business acquisitions. Single user, local-first.

## Where to read next

- **What this is and why** → [`docs/charter.md`](docs/charter.md)
- **How to use it** → [`docs/getting-started.md`](docs/getting-started.md)
- **Where deals come from** → [`docs/deal-sources.md`](docs/deal-sources.md)
- **Runtime agent design** → [`docs/agents/agent-topology.md`](docs/agents/agent-topology.md)
- **Architecture decisions** → [`docs/decisions/`](docs/decisions/)
- **In flight now** → [`tasks/CURRENT.md`](tasks/CURRENT.md)

## Quickstart (Phase 0+)

Local-first, no Docker. Two terminals.

```bash
cp .env.example .env        # fill in ANTHROPIC_API_KEY (needed once agents are wired)

# terminal 1 — backend
cd backend
uv sync
uv run alembic upgrade head           # creates silvercurrent.db (SQLite) + tables
uv run uvicorn silvercurrent.main:app --reload --host 0.0.0.0 --port 8000

# terminal 2 — frontend
cd frontend
pnpm install
pnpm dev
# → http://localhost:3000  (frontend, calls /api/health on load)
# → http://localhost:8000  (backend)
```

If/when SQLite stops being enough (concurrent writers, JSONB, full-text), `docker-compose.yml`
boots Postgres + Chroma server-side. See `docs/decisions/0005-local-dev-without-docker.md`.

## Stack

Python 3.12+ / FastAPI / SQLAlchemy / Postgres / Chroma · Next.js 15 / TypeScript / Tailwind / shadcn · Anthropic API (Sonnet 4.6 default, Opus 4.7 for deep dives, Haiku 4.5 for routing).

## Working in this repo

`CLAUDE.md` at the repo root is the entry point for any Claude Code session. Read it before making changes — it covers conventions, hard rules, and how to coordinate work across the runtime agents.
