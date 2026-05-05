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

```bash
cp .env.example .env       # fill in ANTHROPIC_API_KEY
docker compose up          # boots postgres, chroma, backend, frontend
# → http://localhost:3000  (frontend)
# → http://localhost:8000  (backend, /api/health for smoke test)
```

## Stack

Python 3.12+ / FastAPI / SQLAlchemy / Postgres / Chroma · Next.js 15 / TypeScript / Tailwind / shadcn · Anthropic API (Sonnet 4.6 default, Opus 4.7 for deep dives, Haiku 4.5 for routing).

## Working in this repo

`CLAUDE.md` at the repo root is the entry point for any Claude Code session. Read it before making changes — it covers conventions, hard rules, and how to coordinate work across the runtime agents.
