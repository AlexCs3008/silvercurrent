# Phase 1a — Manual listing CRUD

*Session date: 2026-05-05 · Topic: Phase 1a — Manual listing CRUD (no LLM)*

## Decision

Phase 1 (Listing data model + manual ingestion) was split into two slices:
- **1a** — manual CRUD with a hand-entry form, no URL fetching, no LLM. Get a working end-to-end loop in front of the user with the smallest moving parts.
- **1b** — URL paste + Anthropic structured-extraction. PDF upload after that.

This session is 1a only. 1b stays in `tasks/BACKLOG.md` until 1a is in DONE.

## Schema

`Listing` model fleshed out with 19 columns:

- **Identity**: `business_name` (required), `industry`, `naics_code` (8-char), `location`.
- **Provenance**: `source` (default `"manual"`), `source_url`.
- **Financials** (whole-dollar `int`, all nullable): `asking_price`, `sde`, `cash_flow`, `revenue`. SMB listings never quote cents and aggregators sometimes show SDE and Cash Flow separately, so both fields exist.
- **Narrative**: `narrative` (Text), `reason_for_selling`.
- **Broker**: `broker_name`, `broker_contact` (free-form Text — split into structured fields later if Phase 3 needs it).
- **Workflow**: `status` (`Literal["new"|"reviewing"|"passed"|"tracking"|"loi"|"closed"]`, default `"new"`), `notes` (Text), `tags` (`JSON` array, default `[]`).
- **Timestamps**: `id` (`Uuid()` dialect-agnostic), `created_at`, `updated_at` (`onupdate=_utcnow`).

`raw_html` from the Phase 0 stub was dropped — Phase 1b will reintroduce a `raw_text` field for URL-fetched source text. `ChatTurn` left untouched (Phase 2 territory).

## Tooling fixes baked in

- **`Uuid()` dialect-agnostic.** The Phase 0 stub used `from sqlalchemy.dialects.postgresql import UUID`, which doesn't compile cleanly against SQLite at query time. Switched to the generic `Uuid()` from `sqlalchemy`. The migration handles the type change with `alter_column existing_type=NUMERIC type_=Uuid` (NUMERIC was the previous on-disk SQLite representation).
- **`render_as_batch=True` for SQLite in `alembic/env.py`.** SQLite ALTER TABLE can only add nullable columns natively; anything else (drop column, change type, change nullability) needs alembic batch operations, which recreate the table. Toggling this in `env.py` once means future migrations Just Work.
- **Hand-edited migration to add `server_default` on non-null columns.** `updated_at` defaults to `current_timestamp()`, `business_name` to `''`, `tags` to `'[]'`. Empty dev DB doesn't need them, but a future seeded one will.
- **`ListingUpdate` uses `extra="forbid"`.** A typo in a PATCH body (e.g. `buisness_name`) returns 422 instead of silently being ignored. Tested.

## Backend deliverables

```
backend/src/silvercurrent/
├── api/
│   ├── __init__.py
│   └── listings.py        # 5 endpoints, hard delete on DELETE
├── schemas/
│   ├── __init__.py
│   └── listings.py        # ListingCreate/Update/Read + ListingStatus Literal
├── db/models.py           # Listing model fleshed out, ChatTurn unchanged
└── main.py                # router included
```

`tests/conftest.py` provides:
- `session`: in-memory `sqlite+aiosqlite:///:memory:` per test, schema applied via `Base.metadata.create_all`.
- `client`: `httpx.AsyncClient` against the FastAPI app with `get_session` overridden to use the test session.
- `listing_payload`, `full_listing_payload`: minimal and complete request bodies.

`tests/test_listings.py` has 14 tests covering happy paths, validation (missing required, negative price, bad status, unknown PATCH field), 404 paths, status filter, partial update.

**Gates green**: `uv run pytest` (15 pass total), `uv run ruff check .` clean, `uv run ruff format --check .` clean, `uv run mypy src tests` strict-clean (21 source files).

## Frontend deliverables

New shadcn primitives added: `label`, `textarea`, `select`, `badge`.

Components:
- `components/status-badge.tsx` — colored pill keyed off `STATUS_COLOR`.
- `components/listing-card.tsx` — wraps the card in `<Link href="/listings/[id]">`, renders name + industry/location + asking/SDE/revenue + status + source + created date.
- `components/listing-form.tsx` — shared create/edit form (`"use client"`). 17 user-editable fields grouped into Identity / Financials / Narrative / Broker / Source & workflow cards. Money fields strip `$,` and parse to int. Tags input is comma-separated and parsed to `string[]`. Submits via `apiPost` or `apiPatch` based on `initial` prop.
- `components/listing-actions.tsx` — detail-page action bar (`"use client"`). Status `<Select>` PATCHes on change with optimistic update + revert on error; "Edit" link; "Delete" button with `confirm()` + redirect to `/listings`.

Pages:
- `app/listings/page.tsx` — server component. `searchParams: Promise<{status?: string}>` (Next 16). Fetches `/api/listings` with optional `?status_filter=`. Renders 1/2/3-column responsive grid. Filter chips link via `?status=`. Empty state and fetch-error state.
- `app/listings/new/page.tsx` — server shell + `<ListingForm />`.
- `app/listings/[id]/page.tsx` — server component. Fetches by id, calls `notFound()` on 404. Renders Financials, Identity, Narrative, Broker, Notes, Tags sections (sections hide when empty). Embeds `<ListingActions />`.
- `app/listings/[id]/edit/page.tsx` — server shell + `<ListingForm initial={listing} />`.

`lib/api.ts` extended with `apiPost`/`apiPatch`/`apiDelete`. All requests now use `cache: "no-store"` to keep dev freshness.

`lib/listings.ts` mirrors the backend Pydantic types and provides `formatMoney` (Intl USD, no fractional digits, `null → "—"`), `formatDate` (Intl `Mon D, YYYY`), and a `STATUS_COLOR` map.

**Gates green**: `pnpm lint` clean, `pnpm build` produces all 7 routes (4 dynamic, 3 static) without TypeScript errors.

## Deviations / things to know

1. **Base UI shadcn build, not Radix.** The shadcn install in this repo uses `@base-ui/react/button`, which doesn't expose Radix's `Slot` / `asChild` pattern. Anywhere I'd normally write `<Button asChild><Link>...</Link></Button>` I instead apply `buttonVariants({ ... })` as a className on the `<Link>`. Two places: the inventory "Add listing" button and the detail "Edit" link.
2. **Migration safety.** Hand-edited the autogenerated migration to add `server_default`s on the new non-null columns. Future autogenerations will need similar review when a NOT NULL column is added.
3. **Status as string + Literal, not DB enum.** Charter §5 lists six statuses; we may add more (e.g. `passed_for_now`, `archived`). String + Pydantic Literal lets us add values without a DB migration. Trade-off: bad statuses can sneak past the DB layer if Pydantic is bypassed, but every write goes through the API.
4. **Tags as comma-separated text input.** Cheapest UI that works. A real tag picker (with autocomplete from existing tags) is a follow-up if the user complains.
5. **No optimistic UI on create/edit.** The form awaits the response and then redirects. Simple and correct. If form latency becomes annoying, optimistic + rollback later.

## Smoke test (live)

- `uv run uvicorn ...` on `:8000`, then:
  - `POST /api/listings` with `{"business_name": "Acme HVAC", "industry": "HVAC services", "asking_price": 1200000, ...}` → 201, JSON returned with generated `id`/`created_at`/`updated_at`.
  - `GET /api/listings` → list with the new row.
  - `PATCH /api/listings/{id}` with `{"status": "passed", "notes": "..."}` → 200, `updated_at` advanced past `created_at`.
  - `GET /api/listings?status_filter=passed` → matching row only.
  - `DELETE /api/listings/{id}` → 204.
  - `GET /api/listings/{id}` after delete → 404.

The full browser path (open `localhost:3000/listings`, click "Add listing", fill form, submit, see it appear, click into it, change status, edit, delete) was not exercised in this session — the user will validate that next.

## What's open

- Manual browser smoke (above).
- Phase 1b: URL paste + Anthropic structured extraction. Backlogged.

## Next session

Either Phase 1b (LLM extraction starts here) or Phase 2 (Operator agent + global chat), depending on whether Mr. Alonso wants to keep building ingestion or pivot to the chat surface first.
