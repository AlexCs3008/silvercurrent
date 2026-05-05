# Tasks — currently in flight

*Active phase: **Phase 1b — URL paste + LLM extraction***
*Last updated: 2026-05-05 — solo session*

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

## Phase 1b — URL paste + LLM extraction (no PDF yet)

**Goal**: paste a URL or raw text → Anthropic extracts structured fields (Sonnet 4.6, tool-use forced) → user reviews + edits → save via existing POST. Two-step UX (extract → review → save) so the human always reviews before commit. First phase that spends API tokens.

**Done when**: the user can paste a real BizBuySell listing's text on `/listings/new`, click Extract, see the form auto-populate with sensible fields, edit anything wrong, save, and view the listing on the inventory page. Token usage is shown after extraction.

### [backend] — Extraction module + endpoint

- [x] Add `aiosqlite`-compatible `raw_text` Text column to `Listing`. Migration `f0aff42eb570_phase_1b_add_raw_text_column.py` applied.
- [x] Add `extraction_model: str = "claude-sonnet-4-6"` to `Settings`. Settings now reads `.env` from both `backend/` and the repo root (root wins).
- [x] Add `raw_text` to `ListingCreate`, `ListingUpdate`, `ListingRead` Pydantic schemas.
- [x] `silvercurrent/ingestion/listings.py` — `extract_listing(source_text, source_url?, client?, model?)`. Anthropic SDK tool-use with **forced `tool_choice`** for schema-validated output. `<listing_source>` delimiters per ADR 0002. System prompt explicitly frames content as data, never instructions. Configurable client for testing. Returns `ExtractionResult{extracted, raw_text, source_url, usage}`.
- [x] `fetch_url(url)` — httpx GET with reasonable User-Agent, 15s timeout, 2MB body cap, follows redirects.
- [x] `POST /api/listings/extract` endpoint — body `{source_url?, source_text?}` (one required, validator enforces). Fetches URL when given; passes raw HTML to Sonnet. URL-fetch failure → 400 with "try pasting text instead" hint. `ExtractionError` → 502.
- [x] 11 extraction tests: mocked AsyncAnthropic, parse tool_use, prompt-injection wrapping verified structurally, forced tool_choice asserted, URL passthrough, missing tool_use → ExtractionError, Pydantic rejects missing required fields. Endpoint tests: text mode, empty body 422, URL fetch failure 400, ExtractionError 502.
- [x] Gates: pytest (26 pass total), ruff check + format, mypy --strict (24 source files) — all green.

### [frontend] — Auto-fill panel

- [x] `lib/listings.ts`: add `raw_text` to `Listing`; new types `ExtractedListing`, `ExtractionUsage`, `ExtractionResult`.
- [x] `ListingForm` extended with optional `enableExtraction` prop. When true, renders an Auto-fill panel above the form with two tabs (Paste text / Paste URL), Extract button, token usage display after success, error state. On extraction success, populates ALL form fields from `ExtractedListing`, sets `source` to URL hostname or `"paste"`, sets `source_url` and `raw_text`.
- [x] `app/listings/new/page.tsx` — passes `enableExtraction`. Edit page does not.
- [x] Gates: pnpm lint, pnpm build — green.

### Closeout

- [ ] **Live LLM smoke test** (requires user — costs ~$0.03–$0.10): paste a real BizBuySell listing text, click Extract, verify auto-fill is sensible, save it, view detail. Confirm token-usage display shows.
- [ ] Session note `docs/sessions/2026-05-05-phase-1b-llm-extraction.md`.
- [ ] Move Phase 1b to `tasks/DONE.md` after smoke pass.

---

## What comes after Phase 1b

- **Phase 1c — PDF upload + extraction.** Upload broker teaser/CIM PDFs, parse text via `pypdf` or `pymupdf`, run same extraction pipeline. Probably needs page-by-page chunking for long CIMs.
- **Phase 2 — Operator agent + global chat.** Knowledge corpus + router + operator + chat panel.
