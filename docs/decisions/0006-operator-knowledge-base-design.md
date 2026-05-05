# 0006 — Operator knowledge base: chunking, embeddings, retrieval

*Status: accepted · 2026-05-05*

## Context

Phase 2 introduces the Operator agent — RAG over a curated ETA corpus (SBA SOP 50 10, IRS Pub 535, *Buy Then Build*, *HBR Guide*, etc.). The retrieval substrate is Chroma's `PersistentClient` (chosen in ADR 0005 to avoid Docker). What's left is how we *use* it: how to chunk source text, which embedding model to use, what metadata to attach, and the retrieval shape.

Charter §9 risk #1 is explicit: "knowledge-base quality is the project." A bad RAG corpus turns the Operator into a confident bullshitter. We bias toward boring defaults that are easy to swap when something is provably better.

## Decision

### Source layout
- Files live in `corpus/operator/` (gitignored — licensed/copyrighted material can't go in the repo).
- Supported types: `.pdf`, `.md`, `.txt`. PDFs go through the existing `pymupdf` parser from Phase 1c; markdown and plain text load directly.
- Inventory tracked in `docs/knowledge/operator-sources.md` — title, source, date added, why included. Adding a source is a one-row edit + drop the file.
- Vectors persisted in `.chroma/operator/` (gitignored — derived, regenerable).

### Chunking
- Target chunk size: **1000 chars** with **150 chars overlap**. Min chunk size 200 chars (smaller tails get dropped).
- Splits on paragraph boundaries (`\n\n`) by default. A single paragraph longer than the target gets hard-split.
- Overlap is the literal tail of the previous chunk, with a sentence-boundary search to avoid mid-word seams.
- Implementation: a small recursive splitter in `silvercurrent/ingestion/corpus.py:chunk_text()`. No LangChain.

### Embedding model
- Chroma's default — ONNX `all-MiniLM-L6-v2` (384-dim, English). Local, free, ships with `chromadb` via `onnxruntime`. No additional deps, no API costs, no key management.
- Quality is good-enough for a curated English corpus measured in tens of thousands of chunks. Not state-of-the-art.
- Migration trigger: if retrieval quality is visibly bad (Operator answers from the wrong source, or misses obvious hits), swap to **Voyage AI** (`voyage-3` family — Anthropic's recommended embedder). That swap is a one-function change in `corpus.py` plus a re-index.

### Retrieval shape
- Cosine distance (`hnsw:space: cosine`).
- `k = 5` by default in the Operator's `search_knowledge_base` tool. Configurable per call.
- Metadata stored per chunk: `source` (filename), `chunk_index`, `total_chunks`. Page numbers added in a follow-up if PDF chunking is reworked.
- IDs are deterministic SHA-256 of `{source}::{chunk_index}` so re-ingestion **upserts** rather than duplicating. `--rebuild` drops the collection first when source files have been removed.

### Prompt-injection defense for retrieved content
- Per ADR 0002, retrieved chunks are passed back to the Operator wrapped in `<retrieved_passage source="...">...</retrieved_passage>` tags. The Operator's system prompt frames this content as **data** — instructions inside a passage are ignored. Retrieved KB content is not trusted any more than user-uploaded listings.

### What we explicitly skip in v1
- **No reranker** (Cohere/Voyage rerank). Default cosine retrieval is fine for a curated corpus this size; add a reranker if precision is ever the bottleneck.
- **No hybrid (BM25 + vector) search.** Same reason.
- **No semantic chunking** (header-aware / spaCy-aware splits). The simple paragraph-boundary splitter is good enough until it isn't.
- **No per-page metadata for PDFs.** All pages of a PDF are concatenated before chunking. If a citation needs to reference a specific page, we'll add `page` metadata in the parser layer.
- **No incremental re-embed.** Re-ingestion is upsert by stable ID, which is cheap; for now we don't track per-file mtime to skip unchanged files. Add only if ingestion times become painful (a 200-page CIM takes seconds).

## Consequences

**Good**

- Pipeline ships in one slice. Drop a file → run script → vectors are queryable. No external services.
- Free at runtime. No embedding API costs to forecast.
- Cleanly swappable: every choice (chunk size, embedding model, distance metric, reranker) is one knob in one module.

**Trade-offs**

- ONNX MiniLM is a 2022-era model. Voyage-3 / Cohere Embed v3 / OpenAI text-embedding-3-large are measurably better on multilingual and long-tail technical content. We're betting that for a small ETA corpus in English, the gap doesn't matter at first. The migration trigger above is the explicit re-evaluation point.
- 1000-char chunks miss table semantics — a financial table that wraps across our chunk boundary is broken. For tables-heavy SBA SOPs and IRS pubs, this could degrade retrieval precision. Mitigation: rely on the paragraph splitter staying on `\n\n` boundaries (which `pymupdf` text extraction tends to preserve), and revisit if specific queries fail.
- All pages of a PDF concatenated means citations point to "source: sba_sop_50_10.pdf" not "page 47." For now the Operator's citation style is filename-only. If the user wants page-level citations, the PDF parser change is small.

## Tested by

- `tests/test_corpus.py` — chunking unit tests (empty, single, multi, overlap, hard-split), source loading (md/txt/pdf-suffix), full-pipeline ingest + retrieve against an `EphemeralClient`, idempotent upsert, rebuild-drops-old-collection.
- Manual smoke (Phase 2 slice 1 closeout): seed corpus of two markdown files, ingest script ran, queries against the on-disk collection returned the right files for "How do SBA loans work?" / "addbacks for SDE" / "What multiple do small businesses sell at?".
