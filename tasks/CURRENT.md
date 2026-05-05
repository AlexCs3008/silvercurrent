# Tasks — currently in flight

*Active phase: **Phase 1a — Manual listing CRUD***
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

## Phase 1a — Manual listing CRUD (no LLM)

**Goal**: type a listing into a form by hand, see it on the inventory page, change its status, edit it, delete it. No URL fetching or LLM extraction yet — that's Phase 1b.

**Done when**: end-to-end smoke pass — `pnpm dev` + `uvicorn` running, the user can add a listing in the browser and see it appear; status filter works; PATCH and DELETE work.

### [backend] — Listing CRUD API

- [x] Flesh out `Listing` ORM model: `business_name`, `industry`, `naics_code`, `location`, `asking_price`/`sde`/`cash_flow`/`revenue` (whole-dollar ints), `narrative`, `reason_for_selling`, `broker_name`/`broker_contact`, `status`, `notes`, `tags` (JSON), `updated_at`. Drop `raw_html` (Phase 1b adds `raw_text` instead). Switch UUID type from postgresql-specific to dialect-agnostic `Uuid()`.
- [x] Generate alembic migration `3135435dad97_phase_1a_flesh_out_listing_model.py`. Hand-edited to add `server_default` on non-null columns so it survives non-empty tables.
- [x] Enable `render_as_batch=True` for SQLite in `alembic/env.py` so future column changes work via batch operations.
- [x] Apply migration to dev DB.
- [x] Pydantic schemas in `silvercurrent/schemas/listings.py`: `ListingStatus` Literal, `ListingCreate`, `ListingUpdate` (with `extra="forbid"` so typos fail loudly), `ListingRead` (`from_attributes=True`).
- [x] FastAPI router in `silvercurrent/api/listings.py`: `GET /api/listings` (with `status_filter` query), `POST /api/listings`, `GET /api/listings/{id}`, `PATCH /api/listings/{id}`, `DELETE /api/listings/{id}` (hard delete, 204).
- [x] Wire router into `main.py`.
- [x] Test conftest: in-memory SQLite per test + `httpx.AsyncClient` with `get_session` overridden.
- [x] 14 listing tests covering: empty list, minimal create, full round-trip, missing required, validation errors, get-by-id, 404, status filter, PATCH partial, PATCH 404, PATCH unknown field, DELETE, DELETE 404.
- [x] Gates: `uv run pytest` (15 pass), `uv run ruff check .` clean, `uv run mypy src tests` strict-clean.

### [frontend] — Inventory + add + detail + edit

- [x] Extend `lib/api.ts`: `apiPost`, `apiPatch`, `apiDelete`, `cache: "no-store"` on all calls.
- [x] `lib/listings.ts`: `Listing`, `ListingStatus`, `LISTING_STATUSES`, `formatMoney`, `formatDate`, `STATUS_COLOR` map.
- [x] Add shadcn primitives: `label`, `textarea`, `select`, `badge`.
- [x] `components/status-badge.tsx` — colored pill.
- [x] `components/listing-card.tsx` — render real fields (name, industry, location, asking/SDE/revenue, status badge, source, created date), wraps in `<Link>` to detail.
- [x] `components/listing-form.tsx` — shared create/edit form. All 17 user-editable fields. Money fields strip `$,` and parse to int. Tags input is comma-separated. Submits to POST or PATCH based on `initial` prop, redirects to detail on success.
- [x] `components/listing-actions.tsx` — detail-page action bar: status select (PATCH on change), edit link, delete button (with `confirm()` and redirect to inventory).
- [x] `app/listings/page.tsx` — server component, fetches list (with `?status=` filter), renders cards in 1/2/3-column grid, status filter chips, "Add listing" button.
- [x] `app/listings/new/page.tsx` — server shell + `ListingForm` (no `initial`).
- [x] `app/listings/[id]/page.tsx` — server component, fetches one, renders financials/identity/narrative/broker/notes/tags sections; 404 path via `notFound()`. Uses `ListingActions` for inline status change + edit link + delete.
- [x] `app/listings/[id]/edit/page.tsx` — server fetches, renders `ListingForm` with `initial`.
- [x] Switched `<Button asChild>` to `buttonVariants()` className on `<Link>` since this shadcn build uses Base UI (no Slot).
- [x] Gates: `pnpm lint` clean, `pnpm build` green (all routes compile, dynamic where needed).

### Smoke test

- [x] Backend up via `uv run uvicorn ...`. POST a listing → 201 + JSON. GET list → row present. PATCH status → `updated_at` advanced. Filter `?status_filter=passed` → matching rows. DELETE → 204. GET deleted id → 404.

### Closeout

- [ ] Session note in `docs/sessions/2026-05-04-phase-1a-listing-crud.md`.
- [ ] Commit + push.
- [ ] Move Phase 1a to `tasks/DONE.md`.

---

## What comes after Phase 1a

- **Phase 1b — URL paste + LLM extraction.** Add `raw_text` column. Endpoint that fetches a URL (or accepts pasted text), runs a structured-extraction Anthropic call against it (with the prompt-injection-defense delimiters from ADR 0002), populates a draft listing for the user to review/edit before save. PDF upload after that.
- **Phase 2 — Operator agent + global chat.** See `tasks/BACKLOG.md`.
