"""Paragraph-based chunker with sliding-window overlap.

Diligence queries are keyword-shaped ("what was 2023 revenue", "top 5
customers"), so chunks are small enough to surface a relevant passage but
large enough that a sentence's context stays intact. ADR 0009 picks SQLite
FTS5 over embeddings for this workload — chunks here go straight into the
FTS5 virtual table.

Defaults: ~1200 chars per chunk, ~200-char overlap. Tuned for the broker-
document distribution (CIMs, P&Ls, tax returns) — most paragraphs land between
300 and 900 chars.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_OVERLAP = 200

# Paragraph break: a blank line (with any whitespace).
_PARAGRAPH_RE = re.compile(r"\n\s*\n+")


@dataclass(frozen=True)
class Chunk:
    """One indexable chunk: positional metadata + the text that goes into FTS5."""

    chunk_index: int
    page_hint: int | None
    content: str


def _page_for_offset(offset: int, page_breaks: list[int]) -> int | None:
    """Return the 1-indexed page number whose start ≤ offset, or None when unknown."""
    if not page_breaks:
        return None
    page = 1
    for i, start in enumerate(page_breaks, start=1):
        if start <= offset:
            page = i
        else:
            break
    return page


def chunk_text(
    text: str,
    *,
    page_breaks: list[int] | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Split `text` into overlapping chunks.

    The chunker fills a buffer with paragraphs until adding the next one
    would push the buffer past `chunk_size`. The overlap is the trailing
    `overlap` characters of the previous chunk, which gives FTS5 a chance
    to match phrases that straddle a paragraph boundary.
    """
    if not text or not text.strip():
        return []
    breaks = page_breaks or []
    paragraphs = [p for p in _PARAGRAPH_RE.split(text) if p.strip()]

    chunks: list[Chunk] = []
    buffer = ""
    buffer_offset = 0
    cursor = 0  # offset into the original `text`

    for para in paragraphs:
        # Locate this paragraph in the source text starting from `cursor`. We
        # search rather than track cumulative lengths because `_PARAGRAPH_RE.split`
        # consumes the separator whitespace, and the page_break offsets are in
        # the source coordinate system.
        idx = text.find(para, cursor)
        if idx == -1:
            idx = cursor
        cursor = idx + len(para)

        if buffer and len(buffer) + len(para) + 2 > chunk_size:
            chunks.append(
                Chunk(
                    chunk_index=len(chunks),
                    page_hint=_page_for_offset(buffer_offset, breaks),
                    content=buffer.strip(),
                )
            )
            # Carry overlap from the end of the buffer into the next one.
            tail = buffer[-overlap:] if overlap > 0 else ""
            buffer = (tail + "\n\n" + para).strip() if tail else para
            buffer_offset = max(idx - len(tail), 0)
        else:
            if not buffer:
                buffer_offset = idx
                buffer = para
            else:
                buffer = buffer + "\n\n" + para

    if buffer.strip():
        chunks.append(
            Chunk(
                chunk_index=len(chunks),
                page_hint=_page_for_offset(buffer_offset, breaks),
                content=buffer.strip(),
            )
        )
    return chunks
