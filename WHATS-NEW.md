# What's new — Screen / Diligence / Judgment expansion

*Shipped 2026-05-06. Six features across the charter's middle JTBDs.*

This is the user-facing guide. For design rationale see ADRs `0008` and `0009` and the session notes under `docs/sessions/2026-05-06-*`.

---

## 1. Fit-band on every listing (Phase A)

**What it is.** Every listing now carries a deterministic fit-band against `docs/criteria.md`: `strong`, `partial`, `weak`, `mismatch`, or `unknown`. The band shows up as a labeled pill in the inventory (next to the status pill) and feeds the Deal Sheet's "Hard knockouts" and "Numeric fit" sections.

**How to use it.**
- **Inventory** (`/listings`): the colored pill on each card shows the band; hover for the summary (`"matches 4 of 5 evaluable criteria"`).
- **Sort by Best fit**: click the **Best fit** chip in the toolbar. Strong → partial → weak → unknown → mismatch. Default sort is still Newest.
- **Refine criteria**: edit `docs/criteria.md` freely. The next list/get of any listing recomputes the band — no migration needed. Unrecognized prose is silently skipped, so you can keep writing in your own voice. The summary tells you how many dimensions actually scored vs. were attempted.
- **Run Analysis**: the Deal Sheet's "Hard knockouts" and "Numeric fit" sections now quote the scoring tool verbatim instead of re-reasoning over criteria text. Same listing → same numbers, every time.

**How it works.** A heuristic regex parser reads patterns under known `## ` headings in `criteria.md` (`Asking price range`, `SDE range`, `Multiple ceiling`, etc.) and hands a `ParsedCriteria` to the scorer. The scorer evaluates each numeric dimension as `in_band / out_of_band / not_disclosed`, classifies hard knockouts (auto-evaluable ones like asking-multiple-cap; the rest are surfaced as `MANUAL_REVIEW`), and applies the banding rule: any HIT knockout → `mismatch`, else ≥80% in_band → `strong`, ≥50% → `partial`, else `weak`. ADR 0008 has the full pattern list.

---

## 2. Decision journal (Phase B)

**What it is.** When a listing's status changes to `passed`, `tracking`, or `loi`, the system asks for a one-sentence reason and saves it. Append-only — every transition gets its own row.

**How to use it.**
- Change a listing's status from the detail page. If you pick a decision-worthy bucket (passed / tracking / loi), a modal opens asking *why*.
- Type a sentence. Hit **Save reason**. Or **Skip** — the status change still goes through; the journal is best-effort capture, not a gate.
- The latest reason shows up as muted text under the financials on the inventory card.
- The detail page has a **Decision history** card with every entry, newest-first.

**Why it exists.** The data the system can't derive from listings — *why* you passed, *why* you tracked — accrues from now on. Phase F (calibration) surfaces patterns once you have ≥5 decisions. Theme mining is a v2 feature; for now, free text only.

**How it works.** New `decision_journal_entry` table. PATCH to `/api/listings/{id}` returns `requires_decision: true` whenever the status moves into the decision-worthy bucket; the frontend opens the modal on that flag. Cancel skips writing the row.

---

## 3. Document attachments + diligence search (Phase C)

**What it is.** Upload CIMs, P&Ls, tax returns, etc. against a specific listing. Files persist on disk under `data/listings/{id}/`; text is extracted, chunked, and indexed in SQLite FTS5. The Analyst gains `search_listing_documents` in chat mode — ask about the document, get the cited passage.

**How to use it.**
- On a listing detail page, scroll to the **Documents** card.
- Click **Upload document**, pick a PDF / TXT / MD / CSV. Anything else is rejected at the API.
- The list shows each upload with size, type, and an inline link (PDFs open inline; others download).
- In the listing's chat panel, ask things like:
  - "What was 2023 revenue?"
  - "Top 5 customers by revenue?"
  - "Any mention of pending litigation?"
- The Analyst will quote the matching chunk and cite the filename + page (when available). It only does this in **chat mode** — the Deal Sheet (Run Analysis) is fixed-depth and doesn't search documents.
- Delete removes the file from disk, the index rows, and the metadata row.

**How it works.** Upload → `pymupdf` / text decode → paragraph chunker with sliding-window overlap → FTS5 virtual table with `tokenize='porter unicode61'`. The chat tool runs `MATCH ... ORDER BY bm25()`, dedups near-duplicate chunks, and **wraps each returned chunk in `<uploaded_document source="…">…</uploaded_document>` per ADR 0002** so the prompt frames the content as data, never instructions. ADR 0009 explains why FTS5 over Chroma for this workload.

**Caveats.**
- No OCR. Scanned PDFs return an error; paste the text instead.
- 20 MB cap for PDFs; 10 MB for text-shaped uploads.
- Per-listing scope only. The Operator KB (general ETA mechanics) is unchanged.

---

## 4. Capital-stack what-if scenarios (Phase D)

**What it is.** A new chat-mode tool, `model_capital_stack`, runs a parameterized financing scenario. Ask "what if I put 30% down at 11%, no seller note?" and you'll get DSCR, cash-on-cash, monthly/annual debt service per tranche, and the breakeven SDE-drop percentage — every number from the tool, none from the LLM.

**How to use it.**
- In the listing's chat, ask a what-if. Examples:
  - "What if I put 30% down at 11%, term 7 years, no seller note?"
  - "Run an 80/10/10 stack — SBA at 10.5% / 10y, seller note at 8% / 5y."
- The Analyst pulls `asking_price` and `sde` from the active listing automatically; pass them explicitly only if you want to run a hypothetical.
- The default Deal Sheet (Run Analysis) still ships the standard SBA scenario via `compute_deal_metrics` — that's unchanged. This tool is for chat-mode exploration only.

**How it works.** The shared amortization helper (`agents/tools/_amortization.py`) computes annual debt service from `loan_amount`, `annual_rate`, `term_years`. The new tool combines two tranches (SBA + seller note) plus equity, returns `equity_required`, per-tranche debt service, total DSCR, cash-on-cash, breakeven SDE drop, and warns when the percentages don't sum to 100%.

---

## 5. Side-by-side compare (Phase E)

**What it is.** Pin 2–3 listings from the inventory and view their latest Deal Sheets stacked horizontally for side-by-side review.

**How to use it.**
- On any inventory card, click the **+** pin (top-right). It turns into a filled dot when pinned.
- On the listing detail page, the **Pin for compare** button does the same thing.
- Once you have ≥2 pinned, a **Compare (N)** button appears in the inventory toolbar.
- Click it: `/listings/compare?ids=...` renders three columns, one per pinned listing, each showing the listing snapshot + the latest Deal Sheet sections.
- Cap is 3 pinned at a time; pinning a fourth evicts the oldest.
- Pin state persists in your browser's `localStorage` under `silvercurrent.pinned_listing_ids`.

**Caveats.** A listing without a Deal Sheet shows "No Deal Sheet yet — run analysis on the listing page." The compare page is read-only; it doesn't trigger fresh runs.

---

## 6. Calibration view (Phase F)

**What it is.** An inventory rollup at `/listings/calibration`: status mix, fit-band mix, source mix, top brokers, SDE/asking histograms, time-to-decision percentiles, and the most recent 20 decision reasons. Mirror, not advice.

**How to use it.**
- Click **Calibration** in the inventory toolbar.
- Distributions are rendered as plain horizontal bars (no chart library).
- Time-to-decision percentiles only render once you have ≥5 decision-journal entries; below that they show `—`.
- The page shows a "needs ≥20 reviewed listings" advisory at low N — distributions are noisy at small sample sizes — but renders the data anyway for transparency.

**How it works.** A single `GET /api/calibration` endpoint runs `Counter` aggregates over the listings table, computes histograms with fixed-edge buckets, and joins decision-journal entries for the time-to-first-decision distribution. Re-runs on every load — fine until ~500 listings, then we add a materialized view if it matters.

---

## Quick reference

| Feature | Where to use it | Where to look |
|---|---|---|
| Fit-band | Inventory cards, Deal Sheet | Sort dropdown on `/listings` |
| Decision journal | Status change modal, detail-page history card | Modal opens automatically on passed/tracking/loi transitions |
| Documents | Listing detail → Documents card; chat asks document-specific questions | `/listings/{id}` |
| Capital-stack what-if | Listing chat | Ask a what-if |
| Compare | Inventory pin → Compare button | `/listings/compare` |
| Calibration | Inventory toolbar | `/listings/calibration` |

---

## Pointers

- ADR `docs/decisions/0008-criteria-parsing-conventions.md` — how `criteria.md` parses
- ADR `docs/decisions/0009-document-attachments-and-fts5.md` — why FTS5 over embeddings
- Session notes `docs/sessions/2026-05-06-phase-{a,b,c}-*.md` and `2026-05-06-phases-d-e-f-bundle.md` — what was decided and why
- `tasks/DONE.md` — file-level changelog per phase
- `ultraplan-brief.md` — the full implementation plan this session shipped against
