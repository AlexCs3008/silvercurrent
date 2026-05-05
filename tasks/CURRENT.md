# Tasks — currently in flight

*Active phase: **none — Phase 2 complete, awaiting next pick***
*Last updated: 2026-05-05 — Phase 2 closed out, moved to `tasks/DONE.md`*

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

*Nothing in flight. Pick the next move.*

**Three reasonable next directions:**

1. **Phase 3 — Analyst agent + Deal Sheet + Run Analysis.** Adds Router (now there's a real choice between Operator and Analyst). **Pre-work**: Mr. Alonso fills `docs/criteria.md` with real values — the Analyst injects this on every pass and confident-default placeholders would corrupt early output. ~2–3 sessions.

2. **Corpus expansion (no code).** Add canonical Operator sources before Phase 3: *Buy Then Build*, *HBR Guide*, SBA SOP 50 10 PDF, IRS Pub 535 PDF, Stanford Search Fund Primer. Drop into `corpus/operator/`, update `docs/knowledge/operator-sources.md`, run the ingest script. The `corpus-curator` agent in `.claude/agents/` is built for this. Makes the Operator genuinely useful before stacking more agents on top.

3. **Phase 4 — Email ingestion daemon.** Forwarding broker alert emails lands new listings automatically. Smaller surface area than Phase 3 but requires picking an inbound-email provider (Postmark, SendGrid Inbound, IMAP daemon) — that's an ADR before code starts.
