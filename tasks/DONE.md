# Done — append-only

*Completed tasks land here. Append, never edit.*

---

## Phase 0 — Repository scaffold

*Completed: 2026-05-04 · Session note: `docs/sessions/2026-05-04-phase-0-scaffold.md`*

**Outcome**: empty repo → working skeleton. Backend (FastAPI + SQLAlchemy 2 async + alembic + agent stubs) and frontend (Next.js 16 + Tailwind + shadcn) boot natively, frontend home page calls `/api/health` and renders the response. SQLite + Chroma persistent client; Docker dropped from the dev path. Six foundational docs and five ADRs (0001–0005) committed. Pushed to `https://github.com/AlexCs3008/silvercurrent`.

### [infra] — repository skeleton + Claude Code config + ADRs

- [x] `git init` and create the directory tree per `CLAUDE.md` working-memory layout (§10 of charter)
- [x] Place the foundational docs at their target paths (charter, agent-topology, getting-started, deal-sources, criteria, CLAUDE.md)
- [x] Create `.gitignore` (Python, Node, env, data, Claude ephemera, sqlite, chroma)
- [x] Create `.env.example` with documented placeholder values
- [x] Create `docker-compose.yml` (kept as Postgres migration path, not used for dev)
- [x] Place `.claude/settings.json` and `.claude/agents/{corpus-curator,prompt-tuner,adr-scribe}.md`
- [x] Write ADRs 0001 (stack & tooling), 0002 (prompt-injection defense), 0003 (uv over poetry), 0004 (prompts as md), 0005 (local dev without Docker)
- [x] Write `README.md`, `tasks/BACKLOG.md`, `tasks/DONE.md`
- [x] GitHub remote + initial commit + Phase 0 commit pushed
- [x] Pivot to no-Docker dev: SQLite + Chroma persistent client (charter §8 endorsed)
- [x] Native smoke test: alembic upgrade against SQLite, uvicorn + pnpm dev, `/api/health` → 200, home page renders
- [x] Session note in `docs/sessions/2026-05-04-phase-0-scaffold.md`

### [backend] — FastAPI skeleton

- [x] `uv init --package` with Python 3.12; deps: fastapi, uvicorn[standard], sqlalchemy, alembic, psycopg[binary], aiosqlite, anthropic, chromadb, pydantic-settings, httpx
- [x] Dev deps: ruff, mypy, pytest, pytest-asyncio, pytest-httpx
- [x] `pyproject.toml`: ruff (line 120, py312), mypy strict, pytest asyncio_mode=auto
- [x] `src/silvercurrent/{__init__,config,main}.py` — FastAPI app + CORS for localhost:3000 + `/api/health`
- [x] `src/silvercurrent/db/{session,models}.py` — SQLAlchemy 2 async, `Listing` + `ChatTurn` stubs
- [x] `agents/{router,operator,analyst,optimizer}.py` empty class stubs; `agents/tools/_envelope.py` with `ok()`/`fail()`
- [x] `agents/prompts/{router,operator,analyst,optimizer}.md` lifted from topology doc with `<!-- placeholders: ... -->` per ADR 0004
- [x] Alembic initialized; first migration `fe4b897522e4_initial_listing_and_chat_turn.py` runs cleanly against SQLite
- [x] `tests/test_health.py` (httpx ASGITransport) passes
- [x] `Dockerfile` for backend (kept for future Postgres path)
- [x] Gates: pytest, ruff check, ruff format check, mypy --strict — all green

### [frontend] — Next.js skeleton

- [x] `pnpm create next-app` (Next.js 16, TypeScript, Tailwind, App Router, no src dir, `@/*` alias)
- [x] shadcn init + primitives: button, card, input, tabs
- [x] `app/layout.tsx` server-component sidebar shell (Home / Listings / Chat)
- [x] `app/page.tsx` (`"use client"`) — calls `/api/health`, renders shadcn `<Card>` with loading/ok/error states + JSON
- [x] Placeholder pages: `app/listings/page.tsx`, `app/listings/[id]/page.tsx` (Promise params per Next 16), `app/chat/page.tsx`
- [x] `lib/api.ts` typed `apiGet<T>` + `ApiError`, reads `NEXT_PUBLIC_API_URL`
- [x] `components/listing-card.tsx` typed shadcn `<Card>` skeleton
- [x] `.env.local.example` documenting `NEXT_PUBLIC_API_URL`
- [x] `Dockerfile` for frontend (kept; native dev is `pnpm dev`)
- [x] Gates: pnpm lint, pnpm build — all green

---

## Phase 1a — Manual listing CRUD (no LLM)

*Completed: 2026-05-05 · Session note: `docs/sessions/2026-05-05-phase-1a-listing-crud.md`*

**Outcome**: end-to-end manual entry loop. User can add a listing in the browser, see it on the inventory page, change its status, edit it, and delete it. SQLite + SQLAlchemy 2 async. 15 backend tests, ruff + mypy --strict clean. Frontend `pnpm lint` + `pnpm build` clean. Validated in browser by Mr. Alonso.

### [backend] — Listing CRUD API

- [x] `Listing` model fleshed out: `business_name` (required), `industry`, `naics_code`, `location`, `asking_price`/`sde`/`cash_flow`/`revenue` (whole-dollar `int`), `narrative`, `reason_for_selling`, `broker_name`/`broker_contact`, `status`, `notes`, `tags` (JSON), `updated_at` (with `onupdate=_utcnow`). `raw_html` dropped (1b adds `raw_text` instead). UUID type switched from `postgresql.UUID` to dialect-agnostic `Uuid()`.
- [x] Migration `3135435dad97_phase_1a_flesh_out_listing_model.py` (alembic batch ops; hand-edited to add `server_default` on non-null cols so future seeded DBs survive).
- [x] `alembic/env.py`: enabled `render_as_batch=True` for SQLite so future column changes work.
- [x] Pydantic schemas in `silvercurrent/schemas/listings.py`: `ListingStatus` Literal, `ListingCreate`, `ListingUpdate` (`extra="forbid"`), `ListingRead` (`from_attributes=True`).
- [x] FastAPI router `silvercurrent/api/listings.py`: `GET /api/listings` (with `status_filter`), `POST`, `GET/{id}`, `PATCH/{id}`, `DELETE/{id}` (hard 204).
- [x] Router included in `main.py`.
- [x] `tests/conftest.py`: in-memory SQLite per test + `httpx.AsyncClient` with `get_session` dependency override.
- [x] `tests/test_listings.py`: 14 tests covering happy paths, validation (missing required, negative price, bad status, unknown PATCH field), 404s, status filter, partial update.
- [x] Gates: pytest (15 pass), ruff check + format, mypy --strict (21 source files) — all green.

### [frontend] — Inventory + add + detail + edit

- [x] `lib/api.ts` extended: `apiPost`, `apiPatch`, `apiDelete` + `cache: "no-store"`.
- [x] `lib/listings.ts`: typed mirror of backend schemas; `formatMoney` (Intl USD, no fractions, `null → "—"`); `formatDate`; `STATUS_COLOR` map.
- [x] shadcn primitives added: `label`, `textarea`, `select`, `badge`.
- [x] `components/status-badge.tsx`, `listing-card.tsx` (real fields, `<Link>` to detail), `listing-form.tsx` (shared create/edit, money parsing, comma-separated tags), `listing-actions.tsx` (status select with PATCH, edit link, delete with `confirm()`).
- [x] Pages: `app/listings/page.tsx` (filter chips, grid, empty + error states), `listings/new/page.tsx`, `listings/[id]/page.tsx` (sectioned detail, `notFound()` on 404), `listings/[id]/edit/page.tsx`.
- [x] Switched `<Button asChild>` → `buttonVariants()` className on `<Link>` since this shadcn build uses Base UI (no Radix Slot).
- [x] Gates: pnpm lint, pnpm build — green.

### Smoke test

- [x] Live curl smoke: POST → 201, GET list, PATCH advances `updated_at`, `?status_filter=passed` filters, DELETE → 204, GET deleted → 404.
- [x] Browser smoke: validated by Mr. Alonso end-to-end (add → detail → status change → edit → delete).

---

## Phase 1b — URL paste + LLM extraction (no PDF yet)

*Completed: 2026-05-05 · Session note: `docs/sessions/2026-05-05-phase-1b-llm-extraction.md`*

**Outcome**: paste a real listing's text or URL on `/listings/new`, click Extract, see the form auto-populate from a Sonnet 4.6 tool-use call, review/edit, save normally. Two-step UX (extract → review → save) keeps human in the loop. First phase that spends API tokens. Validated live by Mr. Alonso, including adversarial injection test (model ignored embedded "IGNORE PREVIOUS INSTRUCTIONS" line).

### [backend] — Extraction module + endpoint

- [x] `Listing.raw_text` Text column. Migration `f0aff42eb570_phase_1b_add_raw_text_column.py`. Added to `ListingCreate` / `ListingUpdate` / `ListingRead`.
- [x] `Settings.extraction_model = "claude-sonnet-4-6"`. `Settings` now reads `.env` from both `backend/` and the repo root.
- [x] `silvercurrent/ingestion/listings.py` — `extract_listing()` with Anthropic SDK tool-use, forced `tool_choice` for schema-validated output. `<listing_source>` delimiters per ADR 0002. System prompt explicitly frames source as data, never instructions. Configurable client for tests. Returns `ExtractionResult{extracted, raw_text, source_url, usage}`.
- [x] `fetch_url()` — httpx GET, real User-Agent, 15s timeout, 2MB cap, follows redirects.
- [x] `POST /api/listings/extract` — body `{source_url?, source_text?}` (one required). Fetch failure → 400 with "paste text instead" hint; `ExtractionError` → 502.
- [x] 11 extraction unit tests + 4 endpoint tests. AsyncAnthropic mocked. Verifies: tool-use parsing, `<listing_source>` wrapping, hostile content stays inside tags, forced `tool_choice`, URL in user message, ExtractionError on missing tool_use, ValidationError on missing business_name, endpoint happy path, empty body 422, URL fetch failure 400, ExtractionError 502.
- [x] Gates: pytest (26 pass), ruff check + format, mypy --strict (24 source files) — all green.

### [frontend] — Auto-fill panel

- [x] `lib/listings.ts`: `raw_text` on `Listing`; new `ExtractedListing`, `ExtractionUsage`, `ExtractionResult` types.
- [x] `ListingForm` extended with optional `enableExtraction` prop. Renders Auto-fill Card above form: tabs (Paste text / Paste URL), Extract button, token-usage display, inline error state. On success, populates 13 LLM-fillable fields + `raw_text` + `source_url`; sets `source` to URL hostname or `"paste"`.
- [x] `app/listings/new/page.tsx` passes `enableExtraction`. Edit page does not.
- [x] Gates: pnpm lint, pnpm build — green.

### Live smoke

- [x] Browser smoke: real listing text → Extract → form auto-fills → review → Create → appears in inventory.
- [x] Adversarial test: embedded "IGNORE PREVIOUS INSTRUCTIONS" was ignored; model recorded the real asking price.
- [x] Token-usage line displays after extraction.

---

## Phase 1c — PDF upload + extraction

*Completed: 2026-05-05 · Session note: `docs/sessions/2026-05-05-phase-1c-pdf.md`*

**Outcome**: drop a broker teaser or CIM PDF on `/listings/new`, form auto-populates from Sonnet 4.6 just like 1b. Reuses the entire 1b extraction pipeline; only the parsing layer is new (`pymupdf`). 36 backend tests pass; live smoke validated by Mr. Alonso.

### [backend] — PDF parser + endpoint

- [x] Add `pymupdf` 1.27.x and `python-multipart` 0.0.27 deps.
- [x] `silvercurrent/ingestion/pdfs.py` — `extract_text_from_pdf()` + `PDFParseError`. Iterates pages via `load_page`, joins with blank lines. Sparse-text guard (`< 200 chars`) rejects scanned/image-only PDFs with a "paste text instead" hint. No OCR.
- [x] `Settings.pdf_max_bytes = 20_000_000` (20 MB).
- [x] `POST /api/listings/extract-pdf` — `Annotated[UploadFile, File()]` (avoids ruff B008). Empty 400, over-cap 413, parse failure 400, ExtractionError 502. Reuses `extract_listing()`; response shape identical to `/extract`.
- [x] 10 tests in `tests/test_pdf_extraction.py`. PDFs synthesized in-memory via `pymupdf.open()` + `insert_textbox()`. No fixture files committed.
- [x] Gates: pytest (36 pass total), ruff check + format clean, mypy --strict clean (26 source files).

### [frontend] — PDF upload tab

- [x] `apiPostMultipart<T>(path, FormData)` helper in `lib/api.ts` (lets browser set `Content-Type` with boundary).
- [x] `ListingForm` extract panel grows a third tab: **Upload PDF**. File picker with filename + size preview, posts FormData to `/extract-pdf`, populates form via the same `applyExtraction()` path. PDF source labeled `"pdf"` (not `"paste"`).
- [x] Gates: pnpm lint, pnpm build — green.

### Live smoke

- [x] Real broker PDF → form auto-fills → save → appears in inventory. Mr. Alonso confirmed.
