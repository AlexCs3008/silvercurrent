# Tasks — currently in flight

*Active phase: **none — Phase 1b complete, awaiting next pick***
*Last updated: 2026-05-05 — Phase 1b closed out, moved to `tasks/DONE.md`*

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

1. **Phase 1c — PDF upload + extraction.** Extends 1b. Upload broker teasers/CIMs, parse text via `pypdf` (or `pymupdf` for tougher layouts), reuse the existing extraction pipeline. Long CIMs likely need page chunking. ~1 session.

2. **Phase 2 — Operator agent + global chat.** Pivots to the chat surface. Curate Operator KB sources, embed into Chroma, write router + operator prompts/tools, build the global chat panel. First time we exercise charter §9 risk #1 (KB quality). ~2 sessions.
