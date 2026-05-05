# 0001 — Stack and tooling

*Status: accepted · 2026-05-04*

## Context

Silvercurrent needs a backend that runs LLM agents with tool calls, persists structured deal data, and serves a frontend dashboard. The constraints from the charter (§8): solo builder, weekend/evening time, local-first via `docker compose`, personal API spend, eventual single-VPS deployment. The choice of stack determines daily ergonomics for the next year.

## Decision

- **Backend**: Python 3.12+ with FastAPI. SQLAlchemy 2.0 (async) over Postgres for relational data. Chroma for the vector DB (Operator + Analyst RAG corpora). Anthropic SDK directly for agent calls (no LangChain).
- **Frontend**: Next.js 15 with App Router, TypeScript strict, Tailwind, shadcn/ui primitives. `pnpm` for package management.
- **Tooling**: `uv` for Python envs and dependencies (see ADR 0003). `ruff` for lint + format, `mypy --strict` for types. `pytest` + `pytest-asyncio` for tests. `alembic` for migrations.
- **Local dev**: `docker compose` with services for postgres, chroma, backend, frontend. Hot reload in both backend and frontend containers.

## Consequences

**Good**

- Python is the natural language for LLM/agent orchestration in 2026. Anthropic SDK is first-class.
- FastAPI is small, async-native, and stays out of the way. No Django ORM/middleware coupling we don't need for a single-user app.
- Next.js + shadcn produces a credible dashboard fast without bespoke design work.
- `uv` + `ruff` + `mypy` is the modern, fast Python toolchain — installs and lints in milliseconds.
- All four runtime agents call the Anthropic API directly. No LangChain abstraction tax.

**Trade-offs**

- No LangChain means we write our own light tool-call loop. Acceptable: the loop is ~50 lines and we control the contract.
- Chroma for RAG is fine in v1 but may need replacement (pgvector, Qdrant) if corpus grows past ~100k chunks. Revisit when it hurts.
- Postgres is overkill for v1 single-user — could start with SQLite. Chosen anyway because (a) JSONB columns are useful for raw listing payloads and (b) Postgres parity with eventual production is worth the modest local footprint.
- Strict mypy will occasionally fight us at agent/tool boundaries where types are dynamic. Worth the friction.

## Alternatives considered

- **Django + DRF**: heavier, opinionated where we don't need opinions (auth, admin), and the async story is younger than FastAPI's.
- **TypeScript end-to-end (tRPC + Prisma + Bun)**: tempting for type-safety, but Anthropic SDK ergonomics + Python's data tooling for ingestion (PDF parsing, scrapy if ever) win for this domain.
- **SQLite for v1**: simpler, but not worth the migration tax later when Postgres-isms (JSONB, full-text, listen/notify) become useful.
