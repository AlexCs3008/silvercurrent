"""`search_knowledge_base` — query the operator Chroma collection."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import chromadb

from silvercurrent.agents.tools._envelope import Envelope, fail, ok
from silvercurrent.config import get_settings

# Anchor for resolving the persist dir against the repo root the same way
# the ingestion script does. `__file__` is `.../backend/src/silvercurrent/agents/tools/kb_search.py`,
# so parents[5] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[5]

OPERATOR_COLLECTION = "operator"
DEFAULT_K = 5
MAX_K = 20


def _resolve_persist_dir() -> Path:
    """Return the absolute path to the Chroma persist directory."""
    raw = get_settings().chroma_persist_dir
    relative = raw[2:] if raw.startswith("./") else raw
    return (_REPO_ROOT / relative).resolve()


def _sync_search(query: str, k: int) -> Envelope:
    """Synchronous Chroma query — kept private; the public API is `search_knowledge_base`."""
    persist_dir = _resolve_persist_dir()
    if not persist_dir.exists():
        return fail(
            "Operator knowledge base has not been ingested yet. "
            "Run `uv run python ../scripts/ingest_operator_corpus.py` from `backend/`."
        )

    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        collection = client.get_collection(name=OPERATOR_COLLECTION)
    except Exception as e:
        return fail(f"Operator collection not found in Chroma: {e}")

    if collection.count() == 0:
        return fail("Operator collection is empty. Add files to `corpus/operator/` and run the ingest script.")

    result = collection.query(query_texts=[query], n_results=min(k, MAX_K))
    raw_docs = result.get("documents")
    raw_metas = result.get("metadatas")
    raw_dists = result.get("distances")

    docs: list[str] = list(raw_docs[0]) if raw_docs else []
    metas = list(raw_metas[0]) if raw_metas else []
    dists = list(raw_dists[0]) if raw_dists else []

    passages: list[dict[str, Any]] = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        dist = float(dists[i]) if i < len(dists) else None
        passages.append(
            {
                "text": doc,
                "source": meta.get("source", "unknown"),
                "chunk_index": meta.get("chunk_index"),
                "total_chunks": meta.get("total_chunks"),
                "cosine_distance": dist,
            }
        )

    return ok({"query": query, "k": min(k, MAX_K), "passages": passages})


async def search_knowledge_base(query: str, k: int = DEFAULT_K) -> Envelope:
    """Vector-search the Operator KB. Returns top-`k` passages with source metadata.

    Wrapped in `asyncio.to_thread` so the synchronous Chroma client doesn't block
    the event loop during the FastAPI request.
    """
    if not query.strip():
        return fail("query is empty")
    if k < 1:
        return fail("k must be >= 1")
    return await asyncio.to_thread(_sync_search, query, k)


def format_passages_for_prompt(passages: list[dict[str, Any]]) -> str:
    """Wrap retrieved passages in `<retrieved_passage>` tags per ADR 0002.

    The Operator's system prompt instructs it to treat content inside these tags
    as data, never as instructions. KB content is external and not trusted any
    more than user-uploaded listings.
    """
    parts: list[str] = []
    for i, p in enumerate(passages):
        source = p.get("source", "unknown")
        text = p.get("text", "")
        parts.append(f'<retrieved_passage index="{i}" source="{source}">\n{text}\n</retrieved_passage>')
    return "\n\n".join(parts)
