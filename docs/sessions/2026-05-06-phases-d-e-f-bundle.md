# 2026-05-06 — Phases D, E, F (financing tool, compare view, calibration)

**Plan source:** `ultraplan-brief.md` (Screen / Diligence / Judgment expansion).
**Status:** all three shipped. Phases A–F now complete.

## What changed

- **Phase D** — Analyst chat-mode gains `model_capital_stack(...)` for parameterized financing scenarios (DSCR, cash-on-cash, breakeven SDE drop). Existing default SBA scenario in `compute_deal_metrics` is unchanged; the shared amortization helper lives in `agents/tools/_amortization.py`.
- **Phase E** — Inventory cards and listing detail pages get a pin/unpin control. With ≥2 pinned, a Compare button appears in the inventory toolbar; `/listings/compare?ids=...` renders each listing's latest Deal Sheet in a side-by-side column. Pin state persists in `localStorage` under `silvercurrent.pinned_listing_ids` (cap 3, oldest evicts).
- **Phase F** — `GET /api/calibration` returns the inventory rollup; `/listings/calibration` renders it with histograms, count tables, time-to-decision percentiles (gated on ≥5 samples), and the most-recent 20 decision reasons. The page shows a "needs ≥20 reviewed listings" advisory when `n_reviewed` is below the threshold.

## Decisions worth remembering

- **Shared amortization helper.** `_annual_debt_service` retained as a backwards-compat alias in `deal_metrics.py` so the existing test imports keep working. Future amortization callers should import from `_amortization.annual_debt_service` directly.
- **`useSyncExternalStore` for pin state.** The first cut used `useState` + `useEffect`, which tripped ESLint's `react-hooks/set-state-in-effect`. `useSyncExternalStore` with cached snapshot reference is the right primitive when the source of truth is `localStorage`.
- **Compare page is read-only.** It doesn't trigger fresh analyses or expose pin controls. Plan called this out: the user re-runs analysis from the listing page if they want a refresh.
- **Calibration is a single-roundtrip endpoint.** No extra indices. With <500 listings the cost is negligible; if it grows, a materialized view is the fix.
- **Time-to-decision uses the *first* decision per listing.** A listing pinged twice (e.g., `tracking` then `passed` a week later) only contributes the time-to-`tracking` delta. Plan left this open; first-decision is the meaningful number for "how fast do I make calls."
- **Calibration page renders even at low N.** Plan had asked for an empty state at N<20. We chose to render the page with an advisory banner instead — useful for diagnostic peeking when the data is sparse, and avoids hiding the route during early use.

## Backend test totals

136 passing tests after Phase F. Coverage per phase:

- A: `test_criteria_parser.py` (4), `test_criteria_scorer.py` (8), fit-fields in `test_listings.py` (2), tool wiring in `test_analyst_agent.py` (1).
- B: `test_decisions.py` (6), PATCH-status decision flags in `test_listings.py` (2).
- C: `test_documents_chunk.py` (5), `test_documents_search.py` (5), `test_documents_api.py` (6); FTS5 virtual table created in `conftest.py` and the analyst-test fixture.
- D: `test_capital_stack.py` (7).
- F: `test_calibration.py` (4).

## Open / deferred

- Live smoke against real listings is the next call to action. The plan called this out for every phase that touches a prompt or tool (A, C, D). The agent-prompt edits are conservative and quoted-tool-output-style, so the risk surface is small, but real broker documents are needed to validate `search_listing_documents` retrieval quality and the new chat-mode framings.
- No frontend tests for the new pages (compare, calibration). Repo doesn't have a frontend test harness yet (BACKLOG).
- `compute_deal_metrics` still ships the SBA-default scenario as the Deal Sheet's only financing pass. Adding scenario sweep to the Deal Sheet is a future v2 — for now, what-if exploration lives in chat via `model_capital_stack`.
