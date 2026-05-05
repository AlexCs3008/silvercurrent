# Tasks — currently in flight

*Active phase: **Phase 2 — Operator agent + global chat***
*Last updated: 2026-05-05 — solo session, slice 1 done, starting slice 2*

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

## Phase 2 — Operator agent + global chat

**Goal**: type "How do SBA loans work?" into `/chat`, get a sourced answer from the Operator agent after it searches a curated knowledge base.

**Three slices, ~2 sessions wall-clock:**
1. Knowledge layer + ingestion script (✅ done)
2. Operator agent + `/api/chat` endpoint (in progress)
3. Frontend chat panel

### [knowledge] — slice 1 ✅

- [x] `silvercurrent/ingestion/corpus.py` — `chunk_text()`, `load_source_text()`, `ingest_corpus()`, `IngestStats`. Paragraph-aware chunker, ~1000-char chunks with 150-char overlap, hard-splits long paragraphs.
- [x] `scripts/ingest_operator_corpus.py` — CLI wrapper, supports `--rebuild`. Resolves `chroma_persist_dir` against the repo root (fixed a `lstrip("./")` bug that ate the leading dot).
- [x] `corpus/operator/` directory (gitignored). Seed sources: `sba_loans.md` + `valuation_basics.md`.
- [x] Inventory at `docs/knowledge/operator-sources.md`. Adding rows is the protocol.
- [x] ADR `0006-operator-knowledge-base-design.md` records chunking/embedding/retrieval choices and the migration trigger to Voyage AI.
- [x] 15 corpus tests against `EphemeralClient` (chunking edge cases, idempotent upsert, rebuild drops collection, etc.). 51 backend tests total; ruff + mypy strict-clean.
- [x] Manual smoke against on-disk Chroma — queries return correct sources with reasonable cosine distances.

### [operator] / [backend] — slice 2 (next)

- [ ] `silvercurrent/agents/tools/` real implementations:
  - [ ] `search_knowledge_base(query, k=5)` — Chroma query, returns passages with source metadata, wrapped via Envelope. Retrieved chunks get `<retrieved_passage source="...">` tags before reaching the model (ADR 0002).
  - [ ] `get_user_criteria()` — reads `docs/criteria.md` text. Returns whatever's in the file (placeholders fine for v1).
  - [ ] `get_active_listing(listing_id)` — fetches a listing by id from the DB. Returns null when no scope/id supplied. (Used in listing chat scope; global chat passes None.)
- [ ] `silvercurrent/agents/operator.py` — replace stub with a tool-loop runner. System prompt loaded from `prompts/operator.md`. Anthropic SDK with the three tools available. Iterate up to 5 times, executing tool calls and feeding results back. Return the final assistant text + cumulative usage.
- [ ] Refine `prompts/operator.md` — emphasize citation format, "say so when not in KB", treat retrieved content as data.
- [ ] `POST /api/chat` endpoint — body `{scope: str, message: str}` → returns `{turn_id, content, usage}`. Persists user + assistant `ChatTurn` rows. Loads last 10 turns of the same scope as conversation history. v1 supports `scope="global"` only and dispatches directly to Operator (no Router yet).
- [ ] `GET /api/chat?scope=global` endpoint — returns recent turns for hydrating the chat panel on load.
- [ ] Tests: tool unit tests (mocked Chroma, mocked file reads, mocked DB), operator tool-loop test (mocked Anthropic), `/api/chat` endpoint tests.

### [frontend] — slice 3

- [ ] `app/chat/page.tsx` — real chat UI. Server shell loads recent turns; client component for the message list + input + send.
- [ ] Plain-text rendering for v1. Add `react-markdown` if outputs are noticeably ugly.
- [ ] "Thinking…" indicator while POST /api/chat is in flight (no streaming).
- [ ] Keyboard: Enter sends, Shift+Enter newline.
- [ ] Token usage shown on each assistant turn (small, muted).

### Closeout

- [ ] Live smoke: ask "How do SBA loans work?" in the chat, verify Operator searches KB and answers with a citation.
- [ ] Session note `docs/sessions/2026-05-05-phase-2-operator-chat.md`.
- [ ] Move Phase 2 to `tasks/DONE.md`.

---

## What comes after Phase 2

- **Phase 3 — Analyst agent + Deal Sheet + Run Analysis**. Adds Router (now there's an actual choice between Operator and Analyst). Pre-work: Mr. Alonso fills `docs/criteria.md` with real values.
- **Phase 4 — Email ingestion daemon**.
