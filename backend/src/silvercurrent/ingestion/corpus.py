"""Corpus ingestion: chunk text from local source files, embed via Chroma, persist.

Used for the Operator agent's knowledge base (Phase 2) and later the Analyst's
(Phase 3). Same shape; different collection.

Source files live in `corpus/<agent>/` (gitignored) — `.pdf`, `.md`, `.txt`.
Persisted vectors live in `Settings.chroma_persist_dir/<collection>/`.

The embedding function is Chroma's default (ONNX `all-MiniLM-L6-v2`) — local,
free, ships with chromadb. ADR `0006-operator-knowledge-base-design.md` records
this choice.
"""

from __future__ import annotations

import contextlib
import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import chromadb

from silvercurrent.ingestion.pdfs import extract_text_from_pdf

# Chunking targets. Tuned by intuition for ETA prose (books, SOPs, IRS pubs):
# small enough that retrieval returns focused passages, large enough to keep
# multi-sentence reasoning together.
TARGET_CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MIN_CHUNK_SIZE = 200  # Below this, drop the chunk — likely a truncated tail.

SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}


@dataclass(frozen=True)
class IngestStats:
    """Summary of an ingestion run, returned by `ingest_corpus`."""

    files_processed: int
    files_skipped: int
    chunks_created: int
    total_chars: int


@dataclass(frozen=True)
class _Chunk:
    """One indexable chunk plus the metadata we'll store alongside it."""

    text: str
    source: str  # filename relative to corpus root
    chunk_index: int
    total_chunks: int


def chunk_text(
    text: str,
    target_size: int = TARGET_CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into ~`target_size`-char chunks with `overlap`-char overlap.

    Splits on paragraph boundaries (`\\n\\n`) when possible. Sentences within a
    paragraph are kept together; very long paragraphs get hard-split at the
    target size as a fallback. Overlap is taken from the *end* of the previous
    chunk so context carries forward.
    """
    if not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        # Hard-split paragraphs that are themselves longer than target_size.
        if len(paragraph) > target_size:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(paragraph), target_size - overlap):
                slice_ = paragraph[i : i + target_size]
                if slice_.strip():
                    chunks.append(slice_)
            continue

        candidate = (current + "\n\n" + paragraph) if current else paragraph
        if len(candidate) <= target_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            tail = chunks[-1][-overlap:] if chunks and overlap > 0 else ""
            # Try to start the overlap at a sentence boundary so we don't open
            # mid-word.
            sep = tail.find(". ")
            if sep != -1:
                tail = tail[sep + 2 :]
            current = (tail + "\n\n" + paragraph) if tail else paragraph

    if current:
        chunks.append(current)

    return [c for c in chunks if len(c) >= MIN_CHUNK_SIZE]


def load_source_text(path: Path) -> str:
    """Load and return plain text from a corpus source file.

    Dispatches on suffix: `.pdf` → pymupdf, `.md` / `.txt` → utf-8 read.
    Raises `ValueError` for unsupported suffixes.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path.read_bytes())
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8")
    raise ValueError(f"unsupported corpus file type: {path.name}")


def _stable_id(source: str, chunk_index: int) -> str:
    """Generate a stable ID for a chunk so re-ingestion overwrites instead of duplicating."""
    digest = hashlib.sha256(f"{source}::{chunk_index}".encode()).hexdigest()
    return digest[:32]


def _iter_chunks_for_file(path: Path, source_name: str) -> Iterable[_Chunk]:
    """Read a file, chunk it, and yield `_Chunk`s ready for indexing."""
    text = load_source_text(path)
    pieces = chunk_text(text)
    total = len(pieces)
    for i, piece in enumerate(pieces):
        yield _Chunk(text=piece, source=source_name, chunk_index=i, total_chunks=total)


def ingest_corpus(
    *,
    corpus_dir: Path,
    persist_dir: Path,
    collection_name: str,
    rebuild: bool = False,
    client: chromadb.api.ClientAPI | None = None,
) -> IngestStats:
    """Ingest every supported file under `corpus_dir` into the named Chroma collection.

    Args:
        corpus_dir: directory containing source files (`.pdf`, `.md`, `.txt`).
        persist_dir: where Chroma stores its on-disk index.
        collection_name: e.g. `"operator"` or `"analyst"`.
        rebuild: if True, drop and recreate the collection before adding (clean re-index).
        client: injectable for tests; defaults to `PersistentClient(persist_dir)`.

    Returns an `IngestStats` summarizing the run.
    """
    persist_dir.mkdir(parents=True, exist_ok=True)
    chroma_client = client or chromadb.PersistentClient(path=str(persist_dir))

    if rebuild:
        # Collection may not exist yet — that's fine.
        with contextlib.suppress(Exception):
            chroma_client.delete_collection(name=collection_name)

    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    files_processed = 0
    files_skipped = 0
    chunks_created = 0
    total_chars = 0

    for path in sorted(corpus_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            files_skipped += 1
            continue

        source_name = path.name
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, str | int]] = []

        for chunk in _iter_chunks_for_file(path, source_name):
            ids.append(_stable_id(source_name, chunk.chunk_index))
            documents.append(chunk.text)
            metadatas.append(
                {
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                }
            )
            chunks_created += 1
            total_chars += len(chunk.text)

        if ids:
            # `upsert` rather than `add` so re-running ingestion against the same files
            # updates rather than 409-errors on duplicate IDs.
            collection.upsert(ids=ids, documents=documents, metadatas=metadatas)  # type: ignore[arg-type]

        files_processed += 1

    return IngestStats(
        files_processed=files_processed,
        files_skipped=files_skipped,
        chunks_created=chunks_created,
        total_chars=total_chars,
    )
