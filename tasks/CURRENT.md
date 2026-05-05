# Tasks — currently in flight

*Active phase: **none — Phase 1a complete, awaiting next pick***
*Last updated: 2026-05-05 — Phase 1a closed out, moved to `tasks/DONE.md`*

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

*Nothing in flight. Pick the next phase from `tasks/BACKLOG.md` to start work.*

**Two natural next moves:**

1. **Phase 1b — URL paste + LLM extraction.** Continues the ingestion thread. Adds `raw_text` column, a `POST /api/listings/extract` endpoint that fetches a URL (or accepts pasted HTML/text) and runs a structured-extraction Anthropic call against it (Sonnet 4.6, prompt-injection-defense delimiters per ADR 0002). Frontend gets a "Paste URL" / "Paste text" entry on `/listings/new`. End state: paste a BizBuySell URL and review/edit the auto-filled draft before saving. **First phase that spends API tokens.**

2. **Phase 2 — Operator agent + global chat.** Pivots to the chat surface. `[knowledge]` Chroma corpus + Operator KB sources, `[operator]` prompt + tools, `[router]` routing, `[backend]` `/api/chat` endpoint, `[frontend]` global chat panel. End state: ask "how do SBA loans work?" in the chat and get a sourced answer.
