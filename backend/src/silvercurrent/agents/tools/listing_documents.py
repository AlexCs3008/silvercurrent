"""`search_listing_documents` — keyword-search uploaded documents for the active listing.

Wraps each returned chunk in `<uploaded_document source="...">…</uploaded_document>`
per ADR 0002 so the Analyst's prompt can treat the content as DATA, not
instructions. The wrapper lives at the tool-result boundary; raw upload bytes
never reach the model otherwise.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.tools._envelope import Envelope, fail, ok
from silvercurrent.db.models import ListingDocument
from silvercurrent.documents.index import search_chunks

DEFAULT_K = 5
MAX_K = 20


def _format_passages_for_prompt(passages: list[dict[str, Any]]) -> str:
    """Wrap chunks in `<uploaded_document>` tags. ADR 0002."""
    parts: list[str] = []
    for i, p in enumerate(passages):
        source = p.get("source", "unknown")
        page = p.get("page_hint")
        chunk_index = p.get("chunk_index")
        attrs = f'index="{i}" source="{source}"'
        if page is not None:
            attrs += f' page="{page}"'
        if chunk_index is not None:
            attrs += f' chunk_index="{chunk_index}"'
        parts.append(f"<uploaded_document {attrs}>\n{p.get('content', '')}\n</uploaded_document>")
    return "\n\n".join(parts)


async def search_listing_documents(
    *,
    listing_id: UUID,
    query: str,
    session: AsyncSession,
    k: int = DEFAULT_K,
) -> Envelope:
    """Run a keyword search against the listing's uploaded documents.

    Returns ranked chunks with `source` (filename), `page` (when known), and
    `content`. Near-duplicate chunks are dropped via the same first-200-char
    fingerprint trick `kb_search` uses, so overlap-driven duplicates don't
    fill the result.
    """
    if not query.strip():
        return fail("query is empty")
    capped_k = max(1, min(k, MAX_K))

    raw = await search_chunks(
        session=session,
        listing_id=listing_id,
        query=query,
        k=capped_k * 3,  # over-fetch for dedup
    )
    if not raw:
        return ok({"query": query, "k": capped_k, "passages": [], "wrapped": ""})

    # Resolve filenames in one pass.
    document_ids: set[str] = {str(row["document_id"]) for row in raw}
    stmt = select(ListingDocument).where(ListingDocument.id.in_([UUID(d) for d in document_ids]))
    result = await session.execute(stmt)
    filename_by_id: dict[str, str] = {str(d.id): d.filename for d in result.scalars().all()}

    seen_fingerprints: set[str] = set()
    passages: list[dict[str, Any]] = []
    for row in raw:
        content = str(row.get("content") or "")
        fingerprint = " ".join(content.lower().split())[:200]
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)
        passages.append(
            {
                "document_id": row["document_id"],
                "source": filename_by_id.get(str(row["document_id"]), "unknown"),
                "chunk_index": row.get("chunk_index"),
                "page_hint": row.get("page_hint"),
                "content": content,
            }
        )
        if len(passages) >= capped_k:
            break

    return ok(
        {
            "query": query,
            "k": capped_k,
            "passages": passages,
            "wrapped": _format_passages_for_prompt(passages),
        }
    )
