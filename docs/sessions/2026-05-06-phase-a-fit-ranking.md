# 2026-05-06 — Phase A: fit-ranking + criteria parser

**Plan source:** `ultraplan-brief.md` (Screen / Diligence / Judgment expansion).
**Status:** shipped.

## What changed

Deterministic fit-band computation now runs on every `GET /api/listings` and is surfaced as a labeled badge in inventory cards. The Analyst's Deal Sheet "Hard knockouts" and "Numeric fit" sections quote the new `score_against_criteria` tool's output verbatim instead of LLM-reasoning over the raw criteria text. CLAUDE.md hard rule 5 (numerical claims always come from tool calls) now extends to fit-band membership.

## What I built

- `backend/src/silvercurrent/criteria/{__init__,parser,scorer}.py` — parser + scorer pair.
  - `parse_criteria(markdown) -> ParsedCriteria` reads known patterns under known `## ` headings; silently skips lines it doesn't recognize.
  - `score_listing(listing, criteria) -> FitResult` produces `band`, `summary`, `numeric_fit` (per-dimension band check), `hard_knockouts` (HIT / PASS / NOT_DISCLOSED / MANUAL_REVIEW), `dimensions_evaluated`, `notes`.
  - Banding rule: any HIT knockout → `mismatch`; else >=80% in_band → `strong`, >=50% → `partial`, <50% → `weak`; 0 evaluable → `unknown`.
- `backend/src/silvercurrent/agents/tools/criteria_score.py` — the `score_against_criteria` Envelope tool.
- `backend/src/silvercurrent/agents/analyst.py` — registered in `ANALYST_TOOL_SCHEMAS` and `_execute_tool`.
- `backend/src/silvercurrent/agents/prompts/analyst.md` — replaced LLM-reasoned Hard knockouts and Numeric fit with verbatim-quote-the-tool instructions.
- `backend/src/silvercurrent/agents/prompts/analyst-chat.md` — chat tool listing + rule for "how does this fit" questions.
- `backend/src/silvercurrent/schemas/listings.py` — `ListingRead.fit_band: FitBand | None` and `fit_summary: str | None`.
- `backend/src/silvercurrent/api/listings.py` — `_load_criteria()` + `_to_listing_read()` helpers; fit fields computed per request.
- `frontend/lib/listings.ts` — `FitBand` type, `FIT_BAND_COLOR` map, `sortListings()`, `LISTING_SORT_OPTIONS`.
- `frontend/components/fit-badge.tsx` — labeled pill, hover shows summary.
- `frontend/components/listing-card.tsx` — FitBadge below StatusBadge.
- `frontend/app/listings/page.tsx` — sort row (Newest / Best fit / Asking ↑ / Asking ↓), default Newest.
- `docs/decisions/0008-criteria-parsing-conventions.md` — ADR.
- Tests: 4 parser tests, 8 scorer tests, 2 listing-API fit-field tests, 1 analyst tool-loop test. All 101 pre-existing backend tests still pass; total 113.

## Decisions worth remembering

- **No `fit_band` column.** Computed on every read. Caching would force a backfill on every criteria.md edit, and recompute is microseconds. Documented in ADR 0008.
- **Bands, not numeric scores.** A 0–100 score invites "buy / pass" rounding; a label keeps the user in the loop.
- **Parser silently skips unrecognized prose.** Forcing a schema would conflict with the "criteria.md is user-owned" hard rule. The cost is that a user-written band can fail to register; the FitResult exposes `dimensions_evaluated` so this stays visible rather than silent.
- **Hard knockouts mostly land as `MANUAL_REVIEW`.** The current `Listing` model doesn't carry customer-concentration or owner-dependency fields, so most knockouts can't be auto-evaluated. The asking-multiple-cap and any tag-driven knockouts (e.g., a listing tagged `declining-revenue`) do flip the band to `mismatch`. Future enrichment of the Listing schema will increase auto-evaluation coverage.

## Open / deferred

- The frontend sort UX uses chips rather than a `<select>` to match the existing FilterChip aesthetic. If this proves cluttered once we have ≥20 listings, swap to a shadcn `Select`.
- Live smoke against real listings is gated on Mr. Alonso adding a few — covered by Phase B's "decision journal" rollout, since both are visible-to-user changes.
