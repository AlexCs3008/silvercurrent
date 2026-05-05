# Tasks — currently in flight

*Active phase: **Phase 0 — Repository scaffold***
*Last updated: 2026-05-04 — agent_teams session in progress (lead = main session, teammates = `[backend]`, `[frontend]`)*

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

## Phase 0 — Repository scaffold

**Goal**: from an empty repo to a working skeleton where `docker compose up` boots Next.js + FastAPI + Postgres + Chroma, all foundational docs are at their target paths, and a "hello world" round-trip works end to end.

**Suggested execution**: spawn an agent_teams team with three teammates — `[infra]`, `[backend]`, `[frontend]`. They're independent enough to parallelize cleanly. The lead reads `docs/charter.md` and `docs/agents/topology.md` first, then dispatches.

**Done when**: `docker compose up` boots cleanly, the Next.js home page loads, it can call a FastAPI `/api/health` endpoint and render the response, and all six foundational docs (charter, topology, CLAUDE.md, getting-started, deal-sources, criteria) plus the four initial ADRs are committed.

### [infra] — repository skeleton + Claude Code config + ADRs

- [x] `git init` and create the directory tree per `CLAUDE.md` working-memory layout (§10 of charter)
- [x] Place the foundational docs at their target paths:
  - [x] `docs/charter.md`
  - [x] `docs/agents/agent-topology.md` (note: filename is `agent-topology.md`, not `topology.md` — minor inconsistency vs. charter §10)
  - [x] `docs/getting-started.md`
  - [x] `docs/deal-sources.md`
  - [x] `docs/criteria.md` (template — user fills in before Phase 3)
  - [x] `CLAUDE.md` at repo root
- [x] Create `.gitignore` covering: Python, Node, env files, local data dirs, Claude Code ephemera
- [x] Create `.env.example` with documented placeholder values
- [x] Create `docker-compose.yml` with services: `postgres`, `chroma`, `backend`, `frontend`
- [x] Place `.claude/settings.json` (already in repo)
- [x] Place `.claude/agents/corpus-curator.md`, `prompt-tuner.md`, `adr-scribe.md` (already in repo)
- [x] Write `docs/decisions/0001-stack-and-tooling.md`
- [x] Write `docs/decisions/0002-prompt-injection-defense.md`
- [x] Write `docs/decisions/0003-uv-over-poetry.md`
- [x] Write `docs/decisions/0004-prompts-as-md-files.md`
- [x] Write `README.md`
- [x] Write `tasks/BACKLOG.md`
- [x] Write `tasks/DONE.md`
- [x] GitHub remote added, initial commit pushed (`chore: bootstrap repo with foundational docs and config`)
- [ ] After teammates finish: `docker compose up` smoke test (postgres + chroma + backend + frontend boot, frontend home page renders `/api/health` response)
- [ ] Write `docs/sessions/2026-05-04-phase-0-scaffold.md` session note
- [ ] Move Phase 0 entry to `tasks/DONE.md` once all subtasks pass

### [backend] — FastAPI skeleton

- [x] `cd backend && uv init` — creates `pyproject.toml`
- [x] Add deps: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `anthropic`, `chromadb`, `pydantic-settings`, `httpx`
- [x] Add dev deps: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-httpx`
- [x] Configure `ruff` and `mypy --strict` in `pyproject.toml`
- [x] Create `src/silvercurrent/__init__.py`
- [x] Create `src/silvercurrent/main.py` with FastAPI app + `/api/health` endpoint
- [x] Create `src/silvercurrent/config.py` with `pydantic-settings`-based `Settings` class
- [x] Create `src/silvercurrent/db/session.py` (SQLAlchemy async engine + session factory)
- [x] Create `src/silvercurrent/db/models.py` with initial `Listing` model (stub fields: `id`, `source`, `source_url`, `raw_html`, `status`, `created_at`) and `ChatTurn` model (stub: `id`, `scope`, `role`, `content`, `created_at`)
- [x] `alembic init` and generate the first migration
- [x] Create `src/silvercurrent/agents/{__init__.py, prompts/, tools/}` directory structure
- [x] Create `src/silvercurrent/agents/tools/_envelope.py` with `ok()` / `fail()` helpers
- [x] Stub `src/silvercurrent/agents/{router,operator,analyst,optimizer}.py` with class signature only (no real logic yet)
- [x] Place stub prompt files at `src/silvercurrent/agents/prompts/{router,operator,analyst,optimizer}.md` (lift system-prompt sketches from `docs/agents/topology.md`)
- [x] First test: `tests/test_health.py` — smoke test that `/api/health` returns 200
- [x] `Dockerfile` for backend

### [frontend] — Next.js skeleton

- [x] `cd frontend && pnpm create next-app .` (or `npx`) with: TypeScript yes, App Router yes, Tailwind yes, src dir no, import alias `@/*`
- [x] `pnpm dlx shadcn@latest init` — install shadcn primitives setup
- [x] Add a few baseline shadcn components: `button`, `card`, `input`, `tabs`
- [x] Create `app/layout.tsx` with basic shell (sidebar nav: Home / Listings / Chat)
- [x] Create `app/page.tsx` — home page placeholder; will eventually render `docs/getting-started.md` + `docs/deal-sources.md`
- [x] Create `app/listings/page.tsx` — inventory placeholder
- [x] Create `app/listings/[id]/page.tsx` — listing detail placeholder
- [x] Create `app/chat/page.tsx` — global chat placeholder
- [x] Create `lib/api.ts` — typed wrapper around `fetch` to backend; reads backend URL from `NEXT_PUBLIC_API_URL`
- [x] Wire `app/page.tsx` to call `/api/health` and display the result (proves end-to-end connectivity)
- [x] First component: `components/listing-card.tsx` (skeleton, no real data yet)
- [x] `Dockerfile` for frontend

---

## What comes after Phase 0 (high-level — details land in `BACKLOG.md`)

- **Phase 1 — Listing data model + manual ingestion.** `[ingestion]` URL paste + PDF upload pipelines, `[backend]` listing CRUD endpoints, `[frontend]` add-listing UI and inventory rendering. End state: you can paste a BizBuySell URL and see the listing appear in your inventory with extracted fields.
- **Phase 2 — Operator agent + global chat.** `[knowledge]` Chroma corpus + ingestion script + initial sources, `[operator]` prompt + tools, `[router]` routing logic, `[frontend]` global chat panel. End state: you can ask "how do SBA loans work" and get a sourced answer.
- **Phase 3 — Analyst agent + Deal Sheet + Run Analysis.** `[analyst]` tools (valuation, financing, projections, risk) + prompt + KB, `[frontend]` listing chat + Deal Sheet rendering + Run Analysis button. End state: clicking Run Analysis on any listing produces a Deal Sheet.
- **Phase 4 — Email ingestion.** ADR for provider choice, then `[ingestion]` inbox watcher, parsing, dedup. End state: forwarding a BizBuySell alert email lands new listings automatically.
- **Phase 5 — Optimizer stub.** Tool signatures, system prompt, stubbed bodies. Shipped but inert until v2.
- **Phase 6 — Polish + first eval suite.** Home page rendering markdown docs, agent eval harness, knowledge gaps tracking.
