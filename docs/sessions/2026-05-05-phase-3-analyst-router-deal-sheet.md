# Phase 3 — Analyst agent + Router + Deal Sheet

*Session date: 2026-05-05 · Topic: Phase 3 — deal-specific analysis surface, listing-scoped chat, persisted Run Analysis*

## What shipped

End-to-end deal evaluation surface. Open a listing, click **Run Analysis**, get a structured Deal Sheet (Snapshot · Hard knockouts · Numeric fit · Computed metrics · Qualitative signals · Open questions · Recommendation). Persisted append-only, so re-running shows new sheets without overwriting. The chat panel on the listing page is now Router-classified per turn — Analyst for deal-specific questions, Operator for general ETA mechanics, with clarify / out_of_scope routes for the rest.

This is the **first time the system makes a deal-specific recommendation**. The four-runtime-agent topology is now three-quarters live (Operator / Analyst / Router); Optimizer is a v2 concern.

## Three-slice structure

This phase shipped in three commits:

1. **Slice 1 — Analyst agent + Deal Sheet endpoint (backend only).** New tool `compute_deal_metrics` (deterministic asking-multiples, SDE margin, SBA 7(a) financing scenario at 25% down / 10y / ~10.5%). `AnalystAgent.analyze()` runner, `prompts/analyst.md` locked to a seven-section Deal Sheet. `POST /api/analyze/{listing_id}` non-conversational. 9 new tests. Commit `16947c7`.
2. **Slice 2 — Router + listing-scoped chat.** `RouterAgent` (Haiku 4.5, forced tool-use for structured output). `AnalystAgent.chat()` conversational mode + `prompts/analyst-chat.md`. `POST /api/chat` accepts `scope="listing:<uuid>"`, runs Router → dispatches to operator/analyst/clarify/out_of_scope. Frontend `<ChatPanel variant="listing">` mounted on `/listings/[id]`. 13 new tests. Commit `d9b37a2`.
3. **Slice 3 — Run Analysis button + Deal Sheet persistence.** `DealSheet` SQLAlchemy model + alembic migration `87fc5ed94d49`. `POST /api/analyze/{id}` now persists; new `GET /api/analyze/{listing_id}` returns history newest-first. Frontend `<RunAnalysis>` button + `<DealSheetView>` renderer (custom section parser, no react-markdown dep). 4 new tests. Commit `70d65d8`.

## Architectural decisions (no ADR needed — most fall out of slice 1's design)

- **Two Analyst prompts, not one.** `analyst.md` (batch / Deal Sheet) and `analyst-chat.md` (conversational) keep the structural-discipline prompt out of free chat answers. Same three tools, different system instructions.
- **No KB search for the Analyst (slice 1 deliberate choice).** Per CLAUDE.md rule 5, numerical claims must come from tools. Reusing the Operator KB risked the Analyst quoting a typical-multiple range from a passage. Cleaner to forbid speculation entirely until/unless an analyst-specific corpus and benchmark tools are built.
- **Router uses forced tool-use for structured output.** A single `route` tool with `tool_choice={"type": "tool", "name": "route"}` extracts the classification. No JSON parsing of free text.
- **Router never sees chat history.** Listing context (`listing_id` or null) is passed in the framed user message; prior turns are not. Lets the Router re-route mid-conversation if topic shifts (e.g., user pivots from analyst-style to operator-style mechanics).
- **Defensive fallback for analyst-without-listing.** Router prompt forbids it, but if classification slips, the dispatch returns "Analyst needs a specific listing — open one and ask there" rather than crashing on a null listing_id.
- **Append-only Deal Sheet history.** Re-running creates a new row; the user can compare sheets across criteria refinements or new disclosures. `ondelete=CASCADE` on the FK to `listing` so deleting a listing cleans up.
- **Custom Deal Sheet renderer.** Splits on `### ` (the prompt's locked section structure), pre-wraps section bodies, narrow `**bold**` inline transform with HTML escaping. No `react-markdown` dep per CLAUDE.md.
- **`agent_used` + `routing` fields on chat responses.** Frontend shows the routed agent and the Router's rationale in the usage line so classification is debuggable from the UI.

## Mid-phase corpus + retrieval work (committed earlier in the session)

Before Phase 3 proper, the same session expanded the Operator corpus and fixed a retrieval bug that surfaced once we tested on a real question:

- **Corpus expansion (`ebed448`).** Added SBA SOP 50 10 v8 (docx → md via stdlib zipfile/xml — no pandoc, no python-docx dep), IRS Pub 535 2022, Mercer Capital QoE primer, Paul Weiss working-capital adjustments. 6 files / ~2125 chunks. Inventory updated. Stanford / paid books parked in `TODO-MANUAL.txt`.
- **Retrieval dedup in `kb_search` (same commit).** SBA SOP genuinely repeats requirement paragraphs across loan-program subtypes. Top-k was returning 3–4 copies of the same passage; the Operator burned its 5-iteration cap re-searching for variety. Fix: over-fetch 4× from Chroma, drop near-duplicates by 200-char normalized fingerprint, return top-k unique. The first user-facing question after this fix converged in 1–2 iterations with diverse, on-topic citations.
- **Criteria.md V1 fill (`8b8cecc`).** Engineered placeholder values shaped around Mr. Alonso's Miami location and a generic ETA buyer profile. V1-placeholder banner at the top makes the scaffolding obvious. The earlier "user-owned, do not fill" rule was course-corrected — see the updated `project_criteria_md_ownership.md` memory.

## What got tested

- **9 analyst tests** (slice 1): full-disclosure metrics, missing-field handling (returns inputs in `missing_fields`, omits affected derived metrics), listing-not-found, amortization sanity check (hand-verified $900k @ 10.5% / 10y → $145k–$146.5k annual debt service), three-tool happy path, tool-failure surfacing via `is_error`, iteration cap, endpoint success, endpoint 404.
- **13 routing tests** (slice 2): five Router classifications (operator / analyst-with-listing / clarify / out_of_scope / listing-context-passed-in-message), two Analyst.chat unit tests (short answer, history threading), five dispatch tests (route-to-analyst-on-listing-scope, clarify returns Router question, out_of_scope returns Router reply, analyst-without-listing fallback, listing-404).
- **4 persistence tests** (slice 3): POST persists a row that's retrievable via GET, GET returns newest-first, POST 404 / GET 404 for unknown listing.
- **86 backend tests pass total**. ruff + ruff format + mypy --strict + tsc + eslint all clean.
- **Live smoke** (Mr. Alonso, browser, slice 3): pasted a real BizBuySell listing via copy/paste fallback (URL fetch 403'd as expected per CLAUDE.md hard rule #2 "don't scrape aggregators"), ran analysis, Deal Sheet rendered with Snapshot through Recommendation. Confirmed working.

## Deviations / things to know

1. **The Analyst's `analyze()` and `chat()` share a `_run_loop` helper but use different prompts.** Slice 1's `analyze()` was refactored in slice 2 to extract this helper. Same tool-loop, different system instructions.
2. **`AnalystResult.deal_sheet` is the field name for both modes.** Slightly awkward in `chat()` (it's not really a Deal Sheet, it's a conversational reply), but renaming would split the dataclass and isn't worth the churn for one field.
3. **BizBuySell URL fetch returns 403** — the existing User-Agent has the "Silvercurrent" token, easy to fingerprint. We deliberately did not bypass this. CLAUDE.md hard rule #2 forbids scraping aggregator sites; the paste/upload fallbacks are the intended workflow. Surfaced to Mr. Alonso during the smoke test; he used paste mode and it worked.
4. **No frontend tests.** The repo has no frontend test setup (no Jest / Vitest / Playwright). Relied on `tsc --noEmit` and `eslint` plus the live smoke. Adding a frontend test harness is a separate decision.
5. **MAX_ITERATIONS=6 for the Analyst** vs. 5 for the Operator. Three tool calls cover the happy path; two extra iterations leave room for one retry without unbounded looping.
6. **Custom Deal Sheet renderer uses `dangerouslySetInnerHTML`** but only after escaping all input HTML, then applying a single regex for `**bold**` → `<strong>`. The only HTML in the output is `<strong>` from a regex applied to escaped text — no XSS surface. The alternative was to add `react-markdown`, which would have been ~30KB of transitive deps for two transformations.

## What's open

Nothing for Phase 3 itself. The four-agent topology has three of four agents live; Optimizer is deferred to v2 (post-acquisition operations only become relevant if/when Mr. Alonso owns a business).

The implicit follow-up is **using it for real**: load 2–3 listings, run analyses, refine `criteria.md` and prompts based on what the Analyst surfaces. Failure modes from real listings beat speculative tuning. The `prompt-tuner` subagent at `.claude/agents/prompt-tuner.md` is built for that loop.

## Next session

- **Phase 4 — Email ingestion daemon.** Forwarding broker alert emails lands new listings automatically. **Pre-work**: ADR on inbound-email provider (Postmark Inbound, SendGrid Inbound Parse, or IMAP daemon). The right answer depends on whether Mr. Alonso wants a public webhook (Postmark / SendGrid) or a polling process against a dedicated mailbox (IMAP). ADR drafted at `docs/decisions/0007-inbound-email-provider.md` — needs his decision before implementation starts.
- Or **iterate on prompts based on real listings** — no code changes, just listings + analyses + targeted prompt tweaks. Cheaper than Phase 4 and probably higher leverage at this stage.
