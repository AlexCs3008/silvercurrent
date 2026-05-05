# Phase 2 — Operator agent + global chat

*Session date: 2026-05-05 · Topic: Phase 2 — RAG over a curated ETA corpus, conversational surface live*

## What shipped

End-to-end conversational surface. `/chat` accepts a question, the Operator agent searches a curated Chroma corpus, the answer cites sources by filename. **First time the system is useful as a chat companion**, not just a listing inventory.

Charter §9 risk #1 — "knowledge-base quality is the project" — is now a live concern. The infrastructure is ready; corpus quality is the next-session bottleneck.

## Three-slice structure

This phase shipped in three commits:

1. **Slice 1 — Knowledge layer + ingestion script.** `silvercurrent/ingestion/corpus.py` (chunker + Chroma ingest), `scripts/ingest_operator_corpus.py` CLI, `docs/knowledge/operator-sources.md` inventory, ADR 0006. 15 tests. Commit `4ad4c6b`.
2. **Slice 2 — Operator agent + chat API.** Three tool implementations (`kb_search`, `criteria`, `active_listing`), `OperatorAgent` bounded tool-loop runner, refined system prompt, `POST /api/chat` + `GET /api/chat`, `ChatTurn` persistence. 11 new tests. Commit `dca5b27`.
3. **Slice 3 — Frontend chat panel.** `/chat` page (server-fetches history), `ChatPanel` client component (optimistic rendering, thinking indicator, token usage). Commit `1f3aa9e`.

## Architectural decisions (ADR 0006 records the durable ones)

- **Chunking**: 1000-char target, 150-char overlap, paragraph-aware splitter, 200-char minimum (drops truncated tails). Hard-splits paragraphs longer than target.
- **Embedding model**: Chroma's default ONNX MiniLM. Local, free, no extra deps. Migration trigger to Voyage AI documented.
- **Storage**: `corpus/operator/` (gitignored — licensed material), `.chroma/operator/` (gitignored — derived). Fixed a `lstrip("./")` bug that ate the leading dot of `.chroma`.
- **Retrieval**: cosine distance, k=5 default, k_max=20. Stable IDs (sha256 of `{source}::{chunk}`) so re-ingestion upserts. `--rebuild` drops the collection first.
- **Prompt-injection defense**: every retrieved chunk wrapped in `<retrieved_passage source="...">` tags before reaching the model. System prompt explicitly frames this content as data. Same pattern as Phase 1b's `<listing_source>`.
- **Tool-loop runner**: bounded at `MAX_ITERATIONS=5`. Token usage accumulates across all round trips. Tool failures surfaced to the model with `is_error: true` so it can recover instead of silently substituting.
- **No Router yet.** Global chat hardwires to Operator. Router lands in Phase 3 when Analyst joins and there's a real choice. Avoids one extra Haiku call per turn for a single-target route.
- **No streaming.** Synchronous tool loop; UI shows "Operator is thinking…". Add streaming when latency stops being acceptable.
- **No tool-call replay in history.** Only user/assistant text turns persisted. The Operator re-searches the KB each turn. Simpler; slightly more tokens.
- **Plain-text rendering on the frontend.** `whitespace-pre-wrap`. No `react-markdown` yet.

## What got tested

- **15 corpus tests** (slice 1): chunker edge cases (empty, short, long, hard-split, overlap continuity, constants frozen), source loading dispatch (md / txt / unsupported), full pipeline against `EphemeralClient` (returns stats, retrieval-finds-relevant-chunk, idempotent upsert, rebuild drops old collection, skips unsupported file types).
- **11 operator/chat tests** (slice 2): direct text response, tool-use round trip with mocked KB, tool-failure surfaced via `is_error`, retrieved-passage wrapping verified structurally, conversation history formatting, iteration cap fallback, endpoint persists both turns, rejects non-global scope, validates required fields, loads existing history, GET on empty scope returns `[]`. AsyncAnthropic mocked end-to-end.
- **62 backend tests pass total**. ruff + mypy --strict clean (34 source files).
- **Slice 1 manual smoke** (no Anthropic tokens): seeded `corpus/operator/sba_loans.md` + `valuation_basics.md`, ran the ingest script, queried the on-disk Chroma collection. Top hits matched semantic intent (SBA queries → SBA chunks, valuation queries → valuation chunks) with reasonable cosine distances.
- **Phase 2 live smoke** (Mr. Alonso, browser): opened `/chat`, asked questions across the seed corpus, Operator searched KB and answered with filename citations. Token-usage display worked.

## Deviations / things to know

1. **Settings reads from both `backend/.env` and the repo-root `.env`.** This was already in place from Phase 1b but came up again — the script needs to find the API key whether the user runs uvicorn from `backend/` or from the repo root.
2. **Anthropic SDK type-ignores.** `tools=` and `messages=` arguments to `messages.create()` get `# type: ignore[arg-type]` because dict literals don't satisfy the SDK's strict TypedDict overloads. Same pattern as Phase 1b extraction. Cost: two ignore lines per agent.
3. **The seed corpus is intentionally narrow.** Two hand-curated markdown files (SBA loans + valuation basics) exist to prove the pipeline. Real coverage starts when Mr. Alonso adds *Buy Then Build*, *HBR Guide*, SBA SOP 50 10 PDF, IRS Pub 535, etc.
4. **Optimistic UI on user turns.** The frontend renders the user's message immediately with a temporary id, then replaces it with the persisted turn from the response. On error, the optimistic turn is rolled back and the draft is restored. Better UX than waiting 5–15 seconds with nothing on screen.
5. **`from datetime import UTC` import inside a test function.** `test_chat_endpoint_loads_existing_history` needed explicit timestamps to disambiguate two seed turns; the local import keeps the rest of the test file clean.
6. **Operator re-searches the KB on every turn.** Tool-call results are NOT persisted; only user/assistant text turns are. This means a follow-up question may trigger a fresh search even if the prior turn already retrieved the right context. Acceptable token cost in exchange for simpler history-replay logic.

## What's open

Nothing for Phase 2 itself. Operator is conversational, KB pipeline works, UI ships.

The implicit follow-up is **knowledge-base curation**: the `corpus-curator` agent in `.claude/agents/` is built for this. When Mr. Alonso wants to seriously use the Operator, the workflow is: drop a PDF/markdown into `corpus/operator/`, edit `docs/knowledge/operator-sources.md`, run `uv run python ../scripts/ingest_operator_corpus.py`. Or invoke `corpus-curator` to do it for him.

## Next session

- **Phase 3 — Analyst agent + Deal Sheet + Run Analysis button.** Adds Router (now there's a real choice between Operator and Analyst). Pre-work: Mr. Alonso fills `docs/criteria.md` with real values — the Analyst reads it on every pass, and confident default placeholders would corrupt early output.
- Or **corpus expansion** — add the canonical sources (*Buy Then Build*, SBA SOP 50 10, etc.) before Phase 3 so the Operator is genuinely useful when the user is mid-deal.
