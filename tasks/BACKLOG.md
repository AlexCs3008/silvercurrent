# Backlog

*Work that's not yet picked up. Move items into `tasks/CURRENT.md` when starting them.*

---

## Phase 1 — Listing data model + manual ingestion

End state: paste a BizBuySell URL or upload a PDF teaser, see the listing appear in the inventory with extracted fields.

- `[ingestion]` URL paste pipeline — fetch + structured-extraction LLM pass into `Listing`
- `[ingestion]` PDF upload pipeline — parse + structured-extraction
- `[backend]` listing CRUD endpoints (`GET /api/listings`, `GET /api/listings/{id}`, `POST /api/listings`, `PATCH` for status/notes)
- `[backend]` migration: flesh out `Listing` model (asking, SDE, revenue, industry, NAICS, location, narrative, broker, status, tags)
- `[frontend]` Add Listing modal (URL or PDF)
- `[frontend]` Inventory page — searchable, filterable table with status filters
- `[frontend]` Listing detail page — sections for snapshot, narrative, notes, status

## Phase 2 — Operator agent + global chat

End state: ask "how do SBA loans work" in the global chat, get a sourced answer.

- `[knowledge]` Initial Operator corpus: Stanford Search Fund Primer, *Buy Then Build*, *HBR Guide*, SBA SOP 50 10, IRS Pub 535
- `[knowledge]` Chroma ingestion script (chunk + embed + persist)
- `[knowledge]` Populate `docs/knowledge/operator-sources.md`
- `[operator]` System prompt finalized (lift from topology, refine)
- `[operator]` Tools: `search_knowledge_base`, `get_user_criteria`, `get_active_listing`
- `[router]` Routing logic + Haiku call + structured output validation
- `[backend]` `POST /api/chat` endpoint — accepts message, scope, returns assistant turn
- `[backend]` `ChatTurn` persistence per scope
- `[frontend]` Global chat panel with streaming UI

## Phase 3 — Analyst agent + Deal Sheet + Run Analysis

End state: clicking Run Analysis on a listing produces a Deal Sheet.

- **User action**: fill in `docs/criteria.md` with real acquisition criteria (must happen before Analyst runs against real listings)
- `[knowledge]` Analyst corpus: industry multiples (BizBuySell Insight, IBBA Pulse), addback taxonomy, risk taxonomy
- `[knowledge]` Populate `docs/knowledge/analyst-sources.md`
- `[analyst]` Tools: `compute_valuation`, `lookup_industry_multiples`, `compute_dscr`, `model_capital_stack`, `project_financials`, `score_against_criteria`, `extract_red_flags`, `flag_question_for_broker`, `get_listing`, `get_user_criteria`
- `[analyst]` Conversational system prompt
- `[analyst]` Batch (Deal Sheet) system prompt + structured output schema
- `[backend]` `POST /api/listings/{id}/analyze` — runs the batch pass, persists Deal Sheet
- `[frontend]` Listing chat panel
- `[frontend]` Deal Sheet rendering (the structured artifact in topology §4)
- `[frontend]` Run Analysis button on listing detail page

## Phase 4 — Email ingestion

End state: forwarding a BizBuySell alert email lands new listings automatically.

- ADR: email provider choice (Postmark / SendGrid Inbound / IMAP daemon — pick one)
- `[ingestion]` Inbound email parser — text + HTML + attachments
- `[ingestion]` Per-source extractors (BizBuySell email format, BizQuest, etc.)
- `[ingestion]` Dedup logic (URL + title + asking — fuzzy match)
- `[infra]` VPS or serverless function for the inbox watcher (if needed)

## Phase 5 — Optimizer stub

End state: Optimizer scaffold exists end-to-end on test inputs; not exercised against real docs until v2.

- `[optimizer]` Tool signatures defined (return placeholder data): `ingest_pnl`, `ingest_vendor_list`, `benchmark_against_industry`, `identify_automation_candidates`, `track_kpi`
- `[optimizer]` System prompt finalized
- `[optimizer]` End-to-end smoke test on synthetic inputs

## Phase 6 — Polish + first eval suite

- `[frontend]` Home page renders `docs/getting-started.md` + `docs/deal-sources.md` as markdown
- `[infra]` Agent eval harness — golden inputs, regression checks for prompt changes
- `[knowledge]` `operator-gaps.md` and `analyst-gaps.md` workflows: agents log gaps when KB misses
- `[frontend]` Banner on agent outputs: *Silvercurrent surfaces information. You make decisions.*
