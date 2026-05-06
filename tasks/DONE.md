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

---

## Phase 2 — Operator agent + global chat

*Completed: 2026-05-05 · Session note: `docs/sessions/2026-05-05-phase-2-operator-chat.md`*

**Outcome**: ask "How do SBA loans work?" in `/chat`, get a sourced answer from the Operator agent after it searches a curated Chroma corpus. First conversational surface on the system. ADR 0006 records the chunking/embedding/retrieval choices.

### [knowledge] — slice 1: ingestion pipeline

- [x] `silvercurrent/ingestion/corpus.py`: `chunk_text` (paragraph-aware, 1000-char target, 150-char overlap, hard-splits long paragraphs, drops chunks under 200 chars), `load_source_text` (.pdf via pymupdf, .md/.txt direct), `ingest_corpus` (upserts with stable sha256 IDs, `--rebuild` drops the collection).
- [x] `scripts/ingest_operator_corpus.py` CLI. Resolves `chroma_persist_dir` against repo root (fixed an `lstrip("./")` bug that ate the leading dot).
- [x] `corpus/operator/` directory layout. Seed sources: `sba_loans.md`, `valuation_basics.md`.
- [x] `docs/knowledge/operator-sources.md` inventory.
- [x] ADR `0006-operator-knowledge-base-design.md`.
- [x] 15 corpus tests against `EphemeralClient`. Manual on-disk retrieval smoke green.

### [operator] / [backend] — slice 2: agent + chat API

- [x] `agents/tools/kb_search.py`: `search_knowledge_base(query, k=5)` async-wrapped Chroma query, returns Envelope with passages + metadata + cosine distance. Helpful errors when collection is missing/empty.
- [x] `agents/tools/criteria.py`: `get_user_criteria()` reads `docs/criteria.md` (placeholders fine).
- [x] `agents/tools/active_listing.py`: `get_active_listing(listing_id, session)` returns `{listing: null}` in global scope.
- [x] `agents/operator.py`: `OperatorAgent.run()` bounded tool-loop (`MAX_ITERATIONS=5`) on Sonnet 4.6. Wraps retrieved passages in `<retrieved_passage>` tags per ADR 0002. Accumulates token usage. Tool failures surfaced via `is_error: true`.
- [x] Refined `prompts/operator.md`: cite by filename, "say so when not in KB", treat retrieved content as data, no prescriptive recs, defer numerical analysis to Analyst.
- [x] `POST /api/chat` — body `{scope, message}`, persists user + assistant turns in one transaction, returns both plus cumulative usage. Phase 2 supports only `scope="global"` (rejects others with 400).
- [x] `GET /api/chat?scope=...` — oldest-first history.
- [x] 11 operator/chat tests. AsyncAnthropic mocked end-to-end. 62 backend tests pass. ruff + mypy --strict clean (34 source files).

### [frontend] — slice 3: chat panel

- [x] `lib/chat.ts`: `ChatTurn`, `ChatUsage`, `ChatRequest`, `ChatResponse` types mirroring backend.
- [x] `components/chat-panel.tsx` — client component with optimistic user-turn rendering, "Operator is thinking…" indicator, Enter sends / Shift+Enter newline, token-usage line below scroller, error rollback that restores the draft.
- [x] `app/chat/page.tsx` — server-fetches existing turns; backend-down path renders an inline error banner instead of throwing.
- [x] pnpm lint + pnpm build green.

### Live smoke

- [x] Browser smoke (Mr. Alonso): asked questions against the seed corpus, Operator searched KB and answered with filename citations. Token usage displays per exchange.

---

## Phase 3 — Analyst agent + Router + Deal Sheet

*Completed: 2026-05-05 · Session note: `docs/sessions/2026-05-05-phase-3-analyst-router-deal-sheet.md`*

**Outcome**: open a listing, click **Run Analysis**, get a structured Deal Sheet (Snapshot · Hard knockouts · Numeric fit · Computed metrics · Qualitative signals · Open questions · Recommendation). Persisted append-only. Listing-scoped chat is Router-classified per turn — Analyst for deal-specific questions, Operator for general ETA mechanics. Three of four runtime agents now live.

### [analyst] / [backend] — slice 1: agent + Deal Sheet endpoint

- [x] `agents/tools/deal_metrics.py`: `compute_deal_metrics(listing_id)` deterministic — asking-multiples (vs. SDE and revenue), SDE margin, SBA 7(a) financing scenario at 25% down / 10y / ~10.5% rate. Reports `missing_fields` instead of substituting guesses.
- [x] `agents/analyst.py`: `AnalystAgent.analyze()` bounded tool-loop (`MAX_ITERATIONS=6`) on Sonnet 4.6. Three tools (`get_active_listing`, `get_user_criteria`, `compute_deal_metrics`).
- [x] `prompts/analyst.md` rewritten — locked seven-section Deal Sheet structure, three "don't" rules (no invented numbers, no buyer-voice prescriptions, no extrapolating from missing data).
- [x] `POST /api/analyze/{listing_id}` non-conversational endpoint. 404 on unknown listing.
- [x] 9 new tests. 71 tests pass total. ruff + mypy --strict clean.

### [router] / [analyst] — slice 2: classification + listing-scoped chat

- [x] `agents/router.py`: `RouterAgent` Haiku 4.5, forced tool-use (`tool_choice={"type": "tool", "name": "route"}`) for structured output. Returns `agent` ∈ {operator, analyst, clarify, out_of_scope} + rationale + optional clarification_question / out_of_scope_reply.
- [x] `prompts/router.md` rewritten — five routing rules including "no listing → never route to analyst" and "listing in scope + vague evaluative question → analyst."
- [x] `agents/analyst.py`: `AnalystAgent.chat()` conversational mode + `prompts/analyst-chat.md` (short answers, no Deal Sheet structure).
- [x] `POST /api/chat` accepts `scope="global"` or `scope="listing:<uuid>"`. Verifies the listing exists (404). Calls Router, dispatches to operator/analyst/clarify/out_of_scope. Defensive fallback for analyst-without-listing.
- [x] `ChatResponse` schema gains `agent_used` + `routing` (model, rationale, tokens) so the UI can label.
- [x] `<ChatPanel variant="listing">` mounted on `/listings/[id]` with listing-flavored copy. Usage line shows routed agent + Router rationale.
- [x] 13 new tests (5 router unit, 2 analyst-chat, 5 dispatch, 1 listing-404). 84 tests pass total. ruff + mypy --strict + tsc + eslint clean.

### [analyst] / [frontend] — slice 3: Run Analysis button + persistence

- [x] `DealSheet` SQLAlchemy model — id, listing_id (FK with `ondelete=CASCADE`), created_at, markdown, model, input_tokens, output_tokens, iterations.
- [x] Alembic migration `87fc5ed94d49_phase_3_slice_3_deal_sheet.py` adds the table.
- [x] `POST /api/analyze/{listing_id}` now persists the run; response shape becomes `{deal_sheet: DealSheetRead, usage}`.
- [x] `GET /api/analyze/{listing_id}` returns all sheets for a listing, newest first.
- [x] `<RunAnalysis>` client component on `/listings/[id]` with button + history list + error rollback.
- [x] `<DealSheetView>` renderer parses on `### ` headers, pre-wraps section bodies, narrow `**bold**` inline transform with HTML escaping. No `react-markdown` dep.
- [x] Latest sheet expanded by default, older ones collapse.
- [x] 4 new tests. 86 tests pass total. ruff + mypy --strict + tsc + eslint clean.

### [knowledge] — mid-phase corpus + retrieval work (committed `ebed448`)

- [x] Operator corpus: SBA SOP 50 10 v8 (docx → md via stdlib zipfile/xml), IRS Pub 535 2022, Mercer Capital QoE primer, Paul Weiss working-capital adjustments. Inventory updated.
- [x] `kb_search` dedup: over-fetch 4× from Chroma, drop near-duplicates by 200-char normalized fingerprint, return top-k unique. Fixed the SOP-repeats-requirements-across-loan-subtypes failure mode.
- [x] `TODO-MANUAL.txt` parking lot established for manual-only work (form-gated downloads, paid books).

### [knowledge] — V1 criteria fill (committed `8b8cecc`)

- [x] `docs/criteria.md` filled with engineered V1 placeholder values shaped around Miami / generic ETA buyer profile. Loud V1-placeholder banner. Earlier "user-owned, do not fill" memory updated.

### Live smoke

- [x] Browser smoke (Mr. Alonso): pasted real BizBuySell listing via copy/paste fallback (URL fetch 403'd as expected per CLAUDE.md hard rule #2). Ran analysis, Deal Sheet rendered cleanly. Confirmed working.

## Phase A — Fit-ranking + criteria parser

*Completed: 2026-05-06 · Session note: `docs/sessions/2026-05-06-phase-a-fit-ranking.md`*

**Outcome**: deterministic fit-band on every Listing. New `silvercurrent.criteria` package parses `docs/criteria.md` heuristically (ADR 0008) and scores listings into one of `strong | partial | weak | mismatch | unknown`. Fit fields surfaced in `ListingRead` (computed at read-time, not persisted) and rendered as a `FitBadge` in inventory cards. New `score_against_criteria` Analyst tool replaces LLM-reasoning over criteria text in the Deal Sheet's "Hard knockouts" and "Numeric fit" sections — the tool's output is quoted verbatim. Inventory page gains Best-fit / Asking-asc / Asking-desc sort options. 113 backend tests pass; ruff + mypy --strict + tsc + eslint clean.

### [analyst] [backend] [frontend]

- [x] `criteria/parser.py` — heuristic regex parser, returns `ParsedCriteria` dataclass; tolerates trailing parentheticals and unrecognized lines
- [x] `criteria/scorer.py` — `score_listing(listing, criteria) -> FitResult`; deterministic banding rule per ADR 0008
- [x] `agents/tools/criteria_score.py` — `score_against_criteria` Envelope tool
- [x] `agents/analyst.py` — tool registered in `ANALYST_TOOL_SCHEMAS` + `_execute_tool`
- [x] `prompts/analyst.md` — Hard knockouts + Numeric fit sections quote tool output verbatim
- [x] `prompts/analyst-chat.md` — chat tool addendum for "does this fit my criteria" questions
- [x] `schemas/listings.py` + `api/listings.py` — `fit_band` and `fit_summary` computed per-read
- [x] `frontend/lib/listings.ts` — FitBand types, FIT_BAND_COLOR, sortListings helper
- [x] `frontend/components/fit-badge.tsx` + listing-card integration
- [x] `frontend/app/listings/page.tsx` — sort dropdown (Newest / Best fit / Asking asc/desc)
- [x] ADR `0008-criteria-parsing-conventions.md`
- [x] Tests: `test_criteria_parser.py`, `test_criteria_scorer.py`, fit-fields assertions in `test_listings.py`, score_against_criteria wiring in `test_analyst_agent.py`

## Phase B — Decision journal

*Completed: 2026-05-06 · Session note: `docs/sessions/2026-05-06-phase-b-decision-journal.md`*

**Outcome**: append-only `DecisionJournalEntry` model + migration; `POST/GET /api/listings/{id}/decisions`; `ListingRead.latest_decision` surfaces newest entry per listing; PATCH-status returns `ListingUpdateResponse` with `requires_decision` flag for transitions to `passed | tracking | loi`. Frontend modal in `listing-actions.tsx` prompts for a one-sentence reason on triggering transitions; cancel still persists the status change (best-effort capture, not a gate). Listing card shows truncated latest reason; detail page renders a "Decision history" card with all entries newest-first. 115 backend tests pass; ruff/mypy/tsc/eslint clean.

### [backend] [frontend]

- [x] `db/models.py` — `DecisionJournalEntry` model
- [x] Alembic migration `255f02549581_phase_b_decision_journal.py`
- [x] `schemas/listings.py` — `DecisionJournalRead`, `DecisionJournalCreate`, `ListingUpdateResponse`, `ListingRead.latest_decision`
- [x] `api/decisions.py` — POST + GET routes (404 / 422 / 201 covered)
- [x] `api/listings.py` — `_latest_decision()`, awaitable `_to_listing_read()`, PATCH returns `ListingUpdateResponse` with `requires_decision`
- [x] `main.py` — registered `decisions_router`
- [x] `frontend/lib/decisions.ts` — types + `postDecision()` / `fetchDecisions()`
- [x] `frontend/lib/listings.ts` — `latest_decision` and `ListingUpdateResponse` types
- [x] `frontend/components/listing-actions.tsx` — `DecisionReasonModal` triggered by `requires_decision`; Skip persists status without journal entry
- [x] `frontend/components/listing-card.tsx` — truncated latest decision shown under financials
- [x] `frontend/app/listings/[id]/page.tsx` — Decision history card
- [x] Tests: `test_decisions.py` (6 tests) and PATCH-status decision-requirement tests in `test_listings.py`

## Phase C — Document attachments

*Completed: 2026-05-06 · Session note: `docs/sessions/2026-05-06-phase-c-documents.md` · ADR 0009*

**Outcome**: CIMs / P&Ls / tax returns can be uploaded against a listing, persisted under `data/listings/{id}/`, extracted, chunked, and indexed in SQLite FTS5. New `search_listing_documents` Analyst tool returns ranked chunks wrapped in `<uploaded_document>` per ADR 0002. Deal Sheet (batch) mode explicitly skips this tool; chat mode uses it for document-aware diligence questions. Frontend gains a Documents card on the listing detail page with upload + list + delete + raw-download. 125 backend tests pass; ruff/mypy/tsc/eslint clean.

### [ingestion] [backend] [analyst] [frontend]

- [x] `db/models.py` — `ListingDocument` model
- [x] Migration `c78366360fdf_phase_c_documents_and_fts5.py` — table + index + FTS5 virtual table via `op.execute()`
- [x] `documents/__init__.py`, `storage.py`, `extract.py`, `chunk.py`, `index.py`
- [x] `api/documents.py` — POST upload, GET list, DELETE (DB + FTS + disk), GET raw stream (PDF inline / others attachment)
- [x] `agents/tools/listing_documents.py` — `search_listing_documents` with `<uploaded_document>` wrapping per ADR 0002, dedup against near-duplicate chunks
- [x] `agents/analyst.py` — registered tool with schema + handler
- [x] `prompts/analyst.md` — explicit "do not call in batch mode" guidance
- [x] `prompts/analyst-chat.md` — directs chat-mode use, frames returned content as DATA
- [x] `main.py` — registered `documents_router`
- [x] Frontend: `lib/documents.ts`, `components/document-upload.tsx`, `components/document-list.tsx`, Documents card in `app/listings/[id]/page.tsx`
- [x] `tests/conftest.py` + `tests/test_analyst_agent.py` — created FTS5 virtual table alongside `metadata.create_all`
- [x] `tests/test_documents_chunk.py`, `tests/test_documents_search.py`, `tests/test_documents_api.py`
- [x] ADR `0009-document-attachments-and-fts5.md`

## Phase D — Financing scenario tool

*Completed: 2026-05-06 · Session note: bundled into the Phase A–F summary.*

**Outcome**: shared amortization helper extracted to `agents/tools/_amortization.py`; new `model_capital_stack` Analyst chat-mode tool exposes parameterized capital-stack scenarios (DSCR, cash-on-cash, breakeven SDE drop). Existing `compute_deal_metrics` SBA-default scenario unchanged. 132 backend tests pass.

### [analyst]

- [x] `agents/tools/_amortization.py` — shared `annual_debt_service` helper
- [x] `agents/tools/deal_metrics.py` — imports the shared helper; `_annual_debt_service` retained as backwards-compat alias
- [x] `agents/tools/capital_stack.py` — `model_capital_stack` Envelope tool
- [x] `agents/analyst.py` — registered tool schema + handler
- [x] `prompts/analyst-chat.md` — describes inputs as buyer-supplied; "don't invent rates"
- [x] Tests: `test_capital_stack.py` covering 80/10/10, 100% equity, mismatched percentages, sde=0, listing resolution, missing-asking-price failure

## Phase E — Comparison view

*Completed: 2026-05-06 · Bundled session note in the Phase A–F summary.*

**Outcome**: pin 2–3 listings from the inventory; `/listings/compare?ids=...` renders their latest Deal Sheets stacked side-by-side. Pin state persists in `localStorage` under `silvercurrent.pinned_listing_ids` with a cap of 3. Pure UI; no new backend.

### [frontend]

- [x] `lib/deal-sheet.ts` — extracted `parseDealSheetSections()` + `renderBoldOnly()` from `deal-sheet-view.tsx`
- [x] `components/compare-pin.tsx` — `<ComparePin>` toggle (compact + full variants) using `useSyncExternalStore`; `<CompareLauncher>` button that appears in inventory toolbar when ≥2 are pinned
- [x] `components/listing-card.tsx` — compact pin in the card header
- [x] `app/listings/[id]/page.tsx` — full pin button next to ListingActions
- [x] `app/listings/page.tsx` — CompareLauncher in the toolbar
- [x] `app/listings/compare/page.tsx` — server component fetches each pinned listing + its latest Deal Sheet, renders three columns, empty state per listing if no Deal Sheet

## Phase F — Calibration view

*Completed: 2026-05-06 · Bundled session note in the Phase A–F summary.*

**Outcome**: `GET /api/calibration` returns the inventory rollup (status mix, fit-band mix, source mix, broker top, SDE/asking histograms, time-to-decision percentiles, recent decision reasons). Frontend renders it at `/listings/calibration` with a "needs ≥20 reviewed listings" advisory state. 136 backend tests pass; frontend gates clean.

### [backend] [frontend]

- [x] `api/calibration.py` — single-roundtrip rollup with histogram bucketing, percentile floor (≥5 samples), 20-most-recent decision reasons
- [x] `main.py` — registered `calibration_router`
- [x] `tests/test_calibration.py` — empty DB, status/source aggregation, decision-reason surfacing, percentile null-under-threshold
- [x] `app/listings/calibration/page.tsx` — count tables, histogram cards, time-to-decision dl, recent reasons
- [x] Listings toolbar link to Calibration
