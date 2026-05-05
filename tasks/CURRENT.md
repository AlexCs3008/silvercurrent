# Tasks — currently in flight

*Active phase: **none — Phase 1c complete, awaiting next pick***
*Last updated: 2026-05-05 — Phase 1c closed out, moved to `tasks/DONE.md`*

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

*Nothing in flight. Pick the next phase from `tasks/BACKLOG.md`.*

**Two natural next moves:**

1. **Phase 2 — Operator agent + global chat.** Pivots to the conversational surface. Curate Operator KB sources (Stanford Search Fund Primer, *Buy Then Build*, *HBR Guide*, SBA SOP 50 10, IRS Pub 535), embed into Chroma, write router + operator prompts/tools, build the global chat panel. First time we exercise charter §9 risk #1 ("Knowledge-base quality is the project"). ~2 sessions.

2. **Phase 3 — Analyst agent + Deal Sheet + "Run Analysis" button.** Keeps the listing thread hot. **Pre-work**: Mr. Alonso fills `docs/criteria.md` with real acquisition criteria (industry, geography, SDE band, etc.) — Phase 3 reads this file on every Analyst pass. Then: Analyst tools (valuation, multiples, DSCR, capital-stack, projections, red-flags, criteria scoring) + system prompt + Deal Sheet rendering. ~2–3 sessions.
