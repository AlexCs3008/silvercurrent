# Tasks — currently in flight

*Active phase: **none — Screen / Diligence / Judgment expansion (Phases A–F) shipped 2026-05-06.***
*Last updated: 2026-05-06 — back to manual-sourcing mode; live-smoke against real listings is the next call to action.*

---

*Nothing in flight.*

The cockpit now supports per-listing fit-band scoring (Phase A), append-only decision journaling on status transitions (Phase B), document attachments with FTS5 keyword search (Phase C), parameterized capital-stack scenarios (Phase D), side-by-side Deal Sheet comparison (Phase E), and an inventory calibration rollup (Phase F).

**Three reasonable next directions when there's appetite for code work again:**

1. **Live smoke against real listings** — upload a real CIM, ask document-aware diligence questions, walk a listing through the status pipeline and confirm the journal modal fires correctly. Likely surfaces prompt tuning needed on `analyst-chat.md` for the new `search_listing_documents` and `model_capital_stack` tools.

2. **Phase 4 — Email ingestion daemon (still deferred).** ADR `0007-inbound-email-provider.md` is parked at status `deferred`. Reopen when manual sourcing is the bottleneck.

3. **Polish backlog** — see `tasks/BACKLOG.md`.

---

## Backlog (parked, not in flight)

- **Cosmetic cleanup of `sba_sop_50_10_8.md`** — `Lender�s` U+FFFD remap.
- **react-markdown for Deal Sheet rendering** if the custom renderer feels rough.
- **Optimizer agent** — v2 work, post-acquisition.
- **Frontend test harness** — Vitest + RTL.
- **shadcn `Dialog` primitive** — replace the hand-rolled modal in `listing-actions.tsx` once a second modal needs the same shell.
- **Filesystem cleanup on listing-cascade-delete** — currently the API delete handler unlinks files; cascade deletes from a listing leave the directory. One-off cleanup script if orphans accumulate.

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

*Nothing in flight.*

Mr. Alonso is using the system in manual-sourcing mode: scrape listings off the web himself, paste or upload-as-PDF into `/listings/new`, run analysis, refine prompts and `criteria.md` based on what surfaces. No new code required to operate the system at this stage.

**Three reasonable next directions when there's appetite for code work again:**

1. **Iterate on prompts based on real listings** — no code beyond prompt edits. The `prompt-tuner` subagent at `.claude/agents/prompt-tuner.md` is built for narrowly-scoped prompt iteration with eval feedback. Highest-leverage move while still in shake-down mode.

2. **Phase 4 — Email ingestion daemon (deferred).** ADR `0007-inbound-email-provider.md` is parked at status `deferred`. Reopen when manual sourcing becomes the bottleneck. Decision needed: webhook path (Postmark / SendGrid) vs. IMAP daemon.

3. **Polish backlog** — see below. Each is a small, self-contained PR.

---

## Backlog (parked, not in flight)

- **Cosmetic cleanup of `sba_sop_50_10_8.md`.** Smart-quote replacement chars (`Lender�s`) survive the docx → md conversion and show up in retrieved passages. Cosmetic, not affecting retrieval. ~30-min fix to remap U+FFFD → likely apostrophe.
- **react-markdown for Deal Sheet rendering** if the custom renderer feels rough once we've used it on more listings. Charter-compatible (it's a UI dep, not a scope expansion).
- **Optimizer agent** — v2 work; only relevant after Mr. Alonso owns a business.
- **Frontend test harness** — repo currently has none. `tsc --noEmit` and `eslint` plus live smokes carry the load. Vitest + React Testing Library would be the conventional pick.
