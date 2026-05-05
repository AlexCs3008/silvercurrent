# Tasks — currently in flight

*Active phase: **Phase 0 — Repository scaffold***
*Last updated: project kickoff*

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

- [ ] `git init` and create the directory tree per `CLAUDE.md` working-memory layout (§10 of charter)
- [ ] Place the foundational docs at their target paths:
  - [ ] `docs/charter.md`
  - [ ] `docs/agents/topology.md`
  - [ ] `docs/getting-started.md`
  - [ ] `docs/deal-sources.md`
  - [ ] `docs/criteria.md` (template — user fills in)
  - [ ] `CLAUDE.md` at repo root
- [ ] Create `.gitignore` covering: Python (`__pycache__`, `.venv`, `*.pyc`), Node (`node_modules`, `.next`), env files (`.env`, `.env.local`), local data dirs (`data/`, `corpus/`), Claude Code ephemera (`.claude/teams/`)
- [ ] Create `.env.example` with documented placeholder values for: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `CHROMA_HOST`, `INGESTION_EMAIL_ADDRESS`
- [ ] Create `docker-compose.yml` with services: `postgres`, `chroma`, `backend`, `frontend`
- [ ] Place `.claude/settings.json` (drafted in setup session)
- [ ] Place `.claude/agents/corpus-curator.md`, `prompt-tuner.md`, `adr-scribe.md`
- [ ] Write `docs/decisions/0001-stack-and-tooling.md` (FastAPI, Next.js, Postgres, Chroma, uv)
- [ ] Write `docs/decisions/0002-prompt-injection-defense.md` (delimiter wrapping + data-not-instruction framing)
- [ ] Write `docs/decisions/0003-uv-over-poetry.md`
- [ ] Write `docs/decisions/0004-prompts-as-md-files.md`
- [ ] Write `README.md` (brief, redirects humans to `docs/charter.md` and `docs/getting-started.md`)
- [ ] Write `tasks/BACKLOG.md` (Phase 1+ outlines from this file's "what comes after Phase 0" section)
- [ ] Write `tasks/DONE.md` (empty header — append-only file)

### [backend] — FastAPI skeleton

- [ ] `cd backend && uv init` — creates `pyproject.toml`
- [ ] Add deps: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `anthropic`, `chromadb`, `pydantic-settings`, `httpx`
- [ ] Add dev deps: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-httpx`
- [ ] Configure `ruff` and `mypy --strict` in `pyproject.toml`
- [ ] Create `src/silvercurrent/__init__.py`
- [ ] Create `src/silvercurrent/main.py` with FastAPI app + `/api/health` endpoint
- [ ] Create `src/silvercurrent/config.py` with `pydantic-settings`-based `Settings` class
- [ ] Create `src/silvercurrent/db/session.py` (SQLAlchemy async engine + session factory)
- [ ] Create `src/silvercurrent/db/models.py` with initial `Listing` model (stub fields: `id`, `source`, `source_url`, `raw_html`, `status`, `created_at`) and `ChatTurn` model (stub: `id`, `scope`, `role`, `content`, `created_at`)
- [ ] `alembic init` and generate the first migration
- [ ] Create `src/silvercurrent/agents/{__init__.py, prompts/, tools/}` directory structure
- [ ] Create `src/silvercurrent/agents/tools/_envelope.py` with `ok()` / `fail()` helpers
- [ ] Stub `src/silvercurrent/agents/{router,operator,analyst,optimizer}.py` with class signature only (no real logic yet)
- [ ] Place stub prompt files at `src/silvercurrent/agents/prompts/{router,operator,analyst,optimizer}.md` (lift system-prompt sketches from `docs/agents/topology.md`)
- [ ] First test: `tests/test_health.py` — smoke test that `/api/health` returns 200
- [ ] `Dockerfile` for backend

### [frontend] — Next.js skeleton

- [ ] `cd frontend && pnpm create next-app .` (or `npx`) with: TypeScript yes, App Router yes, Tailwind yes, src dir no, import alias `@/*`
- [ ] `pnpm dlx shadcn@latest init` — install shadcn primitives setup
- [ ] Add a few baseline shadcn components: `button`, `card`, `input`, `tabs`
- [ ] Create `app/layout.tsx` with basic shell (sidebar nav: Home / Listings / Chat)
- [ ] Create `app/page.tsx` — home page placeholder; will eventually render `docs/getting-started.md` + `docs/deal-sources.md`
- [ ] Create `app/listings/page.tsx` — inventory placeholder
- [ ] Create `app/listings/[id]/page.tsx` — listing detail placeholder
- [ ] Create `app/chat/page.tsx` — global chat placeholder
- [ ] Create `lib/api.ts` — typed wrapper around `fetch` to backend; reads backend URL from `NEXT_PUBLIC_API_URL`
- [ ] Wire `app/page.tsx` to call `/api/health` and display the result (proves end-to-end connectivity)
- [ ] First component: `components/listing-card.tsx` (skeleton, no real data yet)
- [ ] `Dockerfile` for frontend

---

## What comes after Phase 0 (high-level — details land in `BACKLOG.md`)

- **Phase 1 — Listing data model + manual ingestion.** `[ingestion]` URL paste + PDF upload pipelines, `[backend]` listing CRUD endpoints, `[frontend]` add-listing UI and inventory rendering. End state: you can paste a BizBuySell URL and see the listing appear in your inventory with extracted fields.
- **Phase 2 — Operator agent + global chat.** `[knowledge]` Chroma corpus + ingestion script + initial sources, `[operator]` prompt + tools, `[router]` routing logic, `[frontend]` global chat panel. End state: you can ask "how do SBA loans work" and get a sourced answer.
- **Phase 3 — Analyst agent + Deal Sheet + Run Analysis.** `[analyst]` tools (valuation, financing, projections, risk) + prompt + KB, `[frontend]` listing chat + Deal Sheet rendering + Run Analysis button. End state: clicking Run Analysis on any listing produces a Deal Sheet.
- **Phase 4 — Email ingestion.** ADR for provider choice, then `[ingestion]` inbox watcher, parsing, dedup. End state: forwarding a BizBuySell alert email lands new listings automatically.
- **Phase 5 — Optimizer stub.** Tool signatures, system prompt, stubbed bodies. Shipped but inert until v2.
- **Phase 6 — Polish + first eval suite.** Home page rendering markdown docs, agent eval harness, knowledge gaps tracking.
