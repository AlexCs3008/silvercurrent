# 2026-05-06 — Phase B: decision journal

**Plan source:** `ultraplan-brief.md` (Screen / Diligence / Judgment expansion).
**Status:** shipped.

## What changed

The buyer's reason for moving a listing into `passed`, `tracking`, or `loi` is now captured into an append-only journal. Inventory cards and the listing detail page surface the latest reason; the detail page lists every entry under "Decision history."

## What I built

- `backend/src/silvercurrent/db/models.py` — new `DecisionJournalEntry` (id, listing_id, previous_status, new_status, reason, created_at).
- `backend/alembic/versions/255f02549581_phase_b_decision_journal.py` — table + index on `(listing_id)`.
- `backend/src/silvercurrent/schemas/listings.py` — `DecisionJournalRead`, `DecisionJournalCreate` (validates 1≤reason≤500), `ListingUpdateResponse` (wraps a `ListingRead` with `requires_decision`), and `ListingRead.latest_decision`.
- `backend/src/silvercurrent/api/decisions.py` — POST + GET endpoints. POST 404s for unknown listings; 422 on empty reason. Newest-first.
- `backend/src/silvercurrent/api/listings.py` — `_latest_decision()` helper; `_to_listing_read()` is now async and queries the latest entry; PATCH returns `ListingUpdateResponse` with `requires_decision: true` whenever status changes into the decision-worthy bucket.
- `backend/src/silvercurrent/main.py` — registered `decisions_router`.
- `frontend/lib/decisions.ts` — types + thin API wrappers.
- `frontend/lib/listings.ts` — `latest_decision` field on `Listing`; `ListingUpdateResponse` type.
- `frontend/components/listing-actions.tsx` — wraps the existing status `Select` with a `DecisionReasonModal`; opens when the PATCH response carries `requires_decision`. Skip leaves the entry unwritten and refreshes the page (status still changes).
- `frontend/components/listing-card.tsx` — truncated latest decision under the financials block, hover tooltip shows full reason.
- `frontend/app/listings/[id]/page.tsx` — fetches `/api/listings/{id}/decisions` server-side and renders a "Decision history" card when entries exist.

## Tests

`test_decisions.py` (6 cases): happy-path POST, empty reason → 422, missing listing → 404, GET ordering newest-first, `latest_decision` surfaced on detail, null when no entries. `test_listings.py` extended with `requires_decision` assertions for `passed` (true) and `reviewing` (false) transitions. Existing PATCH test updated to read `body["listing"]["status"]` since the response shape now wraps the listing.

Total backend test count: 115.

## Decisions worth remembering

- **Best-effort capture, not a gate.** Skipping the modal still persists the status change. Forcing the reason would create a UX where users habitually paste "x" to dismiss it; the data we'd collect would be worse than no data.
- **No taxonomy column.** Reasons are free text. Per the plan, theme mining is a v2 feature — adding tags now would force premature taxonomy. The `reason` column is `TEXT` so future LLM passes can extract structure post-hoc.
- **`closed` is not decision-worthy.** It's a bookkeeping outcome that follows from LOI → APA → closing, not a fresh judgment moment. Plan covered this; we left `closed` out of the prompt list.
- **PATCH response shape changed.** `ListingUpdateResponse` wraps the listing with `requires_decision`. The two existing callers (`listing-actions.tsx`, the `test_patch_partial_update` test) were both updated. GET routes still return `ListingRead`.
- **Append-only, no edits/deletes.** A second decision a week later (e.g., `tracking` → `passed`) is a new row. The plan called this out: the reason for `passed` may differ from the reason for `tracking`, and we want both.

## Open / deferred

- No frontend test harness (per session note 2026-05-04). Live smoke covers the UX path.
- The modal is hand-rolled, not a shadcn `Dialog`. Adding the Dialog primitive would be ~5 minutes; deferred until a second modal needs the same shell.
