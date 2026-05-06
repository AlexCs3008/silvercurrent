"""Index chunks into the SQLite FTS5 virtual table.

We use raw SQL through the AsyncSession because SQLAlchemy's ORM doesn't
model FTS5 virtual tables. Insertions are batched in a single `executemany`
to keep the indexing cost off the request's hot path.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.documents.chunk import Chunk

_INSERT_SQL = text(
    """
    INSERT INTO listing_document_chunk_fts (
        document_id, listing_id, chunk_index, page_hint, content
    ) VALUES (:document_id, :listing_id, :chunk_index, :page_hint, :content)
    """
)

_DELETE_BY_DOCUMENT_SQL = text("DELETE FROM listing_document_chunk_fts WHERE document_id = :document_id")


async def index_chunks(
    *,
    session: AsyncSession,
    document_id: UUID,
    listing_id: UUID,
    chunks: Sequence[Chunk],
) -> int:
    """Write `chunks` into the FTS5 virtual table. Returns the row count inserted."""
    if not chunks:
        return 0
    rows = [
        {
            "document_id": str(document_id),
            "listing_id": str(listing_id),
            "chunk_index": chunk.chunk_index,
            "page_hint": chunk.page_hint,
            "content": chunk.content,
        }
        for chunk in chunks
    ]
    await session.execute(_INSERT_SQL, rows)
    return len(rows)


async def delete_chunks_for_document(
    *,
    session: AsyncSession,
    document_id: UUID,
) -> None:
    """Remove all FTS5 rows for a document. Idempotent."""
    await session.execute(_DELETE_BY_DOCUMENT_SQL, {"document_id": str(document_id)})


# FTS5's MATCH operator requires special characters (', ", -, etc.) to be
# escaped or quoted. We wrap each token in double quotes after stripping
# embedded quotes — gives us safe phrase-prefix matching for arbitrary user
# input without needing a real query parser.
_DEFAULT_K = 5


def _build_match_query(query: str) -> str:
    """Sanitize a free-text query into a safe FTS5 MATCH expression."""
    cleaned = query.replace('"', " ").replace("\x00", " ")
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return ""
    # Use prefix matches (`token*`) so partial words still hit. FTS5's tokenizer
    # already handles case and stemming via `tokenize='porter unicode61'`.
    return " ".join(f'"{t}"*' for t in tokens)


async def search_chunks(
    *,
    session: AsyncSession,
    listing_id: UUID,
    query: str,
    k: int = _DEFAULT_K,
) -> list[dict[str, object]]:
    """Return top-`k` chunks matching `query` for a specific listing.

    Uses FTS5's `bm25()` ranking. Results carry the chunk's `document_id`,
    `chunk_index`, `page_hint`, and `content` so the Analyst can cite the
    source filename (resolved separately from the `listing_document` row)
    and quote the matching passage.
    """
    if k < 1:
        return []
    match = _build_match_query(query)
    if not match:
        return []

    sql = text(
        """
        SELECT document_id, chunk_index, page_hint, content,
               bm25(listing_document_chunk_fts) AS rank
        FROM listing_document_chunk_fts
        WHERE listing_document_chunk_fts MATCH :match
          AND listing_id = :listing_id
        ORDER BY rank
        LIMIT :limit
        """
    )
    result = await session.execute(
        sql,
        {"match": match, "listing_id": str(listing_id), "limit": k},
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]
