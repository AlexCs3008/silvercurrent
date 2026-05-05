# Tasks — currently in flight

*Active phase: **none — Phase 3 complete, Phase 4 deferred***
*Last updated: 2026-05-05 — Phase 4 (email ingestion) deferred until manual sourcing becomes the bottleneck. ADR 0007 status: deferred.*

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
