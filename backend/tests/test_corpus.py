"""Tests for the corpus ingestion pipeline (chunking + Chroma persistence)."""

from __future__ import annotations

from pathlib import Path

import chromadb
import pytest

from silvercurrent.ingestion.corpus import (
    CHUNK_OVERLAP,
    MIN_CHUNK_SIZE,
    TARGET_CHUNK_SIZE,
    chunk_text,
    ingest_corpus,
    load_source_text,
)

# --- Chunker ------------------------------------------------------------------


def test_chunk_text_empty_input_returns_empty_list() -> None:
    """Empty / whitespace-only text yields no chunks."""
    assert chunk_text("") == []
    assert chunk_text("   \n\n   ") == []


def test_chunk_text_short_text_below_min_returns_empty() -> None:
    """Text shorter than `MIN_CHUNK_SIZE` produces no chunks (filtered)."""
    assert chunk_text("short") == []


def test_chunk_text_single_chunk_when_under_target() -> None:
    """A doc smaller than `target_size` becomes one chunk."""
    text = "Paragraph one. " * 30  # ~450 chars
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0].startswith("Paragraph one")


def test_chunk_text_splits_long_text_into_multiple_chunks() -> None:
    """Long text yields multiple chunks, each within target size."""
    paragraphs = ["Paragraph " + str(i) + ". " * 50 for i in range(20)]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, target_size=1000, overlap=150)

    assert len(chunks) > 1
    for c in chunks:
        # Allow some slack for overlap stitching but never wildly over target.
        assert len(c) <= 1500


def test_chunk_text_provides_overlap_between_chunks() -> None:
    """Successive chunks share trailing/leading content for context continuity."""
    paragraphs = [f"Paragraph {i}. {('lorem ipsum dolor sit amet ' * 10).strip()}." for i in range(10)]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, target_size=600, overlap=120)
    assert len(chunks) >= 2

    # The tail of chunk N should appear at (or near) the head of chunk N+1.
    tail = chunks[0][-50:]
    # Allow whitespace differences; check that some recognizable substring carries over.
    assert any(word in chunks[1] for word in tail.split() if len(word) > 4)


def test_chunk_text_hard_splits_a_giant_paragraph() -> None:
    """A single paragraph longer than `target_size` is hard-split."""
    giant = "x" * 5000  # one paragraph of 5000 chars
    chunks = chunk_text(giant, target_size=1000, overlap=100)
    assert len(chunks) >= 4  # at least ⌈5000/(1000-100)⌉ chunks
    for c in chunks:
        assert len(c) <= 1000


def test_chunking_constants_unchanged() -> None:
    """Guard against accidental changes to the tuned defaults."""
    assert TARGET_CHUNK_SIZE == 1000
    assert CHUNK_OVERLAP == 150
    assert MIN_CHUNK_SIZE == 200


# --- Source loading ----------------------------------------------------------


def test_load_source_text_md(tmp_path: Path) -> None:
    """Markdown files load as plain UTF-8."""
    p = tmp_path / "note.md"
    p.write_text("# Heading\n\nBody text.", encoding="utf-8")
    assert "Heading" in load_source_text(p)
    assert "Body text" in load_source_text(p)


def test_load_source_text_txt(tmp_path: Path) -> None:
    """Plain text files load as-is."""
    p = tmp_path / "note.txt"
    p.write_text("Hello world.", encoding="utf-8")
    assert load_source_text(p) == "Hello world."


def test_load_source_text_rejects_unsupported_suffix(tmp_path: Path) -> None:
    """Files with unknown suffixes raise `ValueError`."""
    p = tmp_path / "note.docx"
    p.write_text("xx", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_source_text(p)


# --- Full ingestion pipeline -------------------------------------------------


def _write_seed_corpus(corpus_dir: Path) -> None:
    """Drop two text files into `corpus_dir` so we can test the full pipeline."""
    (corpus_dir / "sba_loans.md").write_text(
        "# SBA 7(a) Loans\n\n"
        + (
            "The SBA 7(a) loan program offers loans up to $5 million for small "
            "business acquisitions. Typical terms are 10 years for working capital "
            "and up to 25 years for real estate. Down payment is typically 10 to 25 "
            "percent. The lender of record is a bank; the SBA guarantees a portion "
            "of the loan to encourage lending to small operators.\n\n"
        )
        * 4,
        encoding="utf-8",
    )
    (corpus_dir / "valuation_primer.md").write_text(
        "# Valuation Primer\n\n"
        + (
            "Small businesses typically sell at 2 to 4 times Seller's Discretionary "
            "Earnings (SDE). Service businesses skew toward the lower end of that "
            "range. Software and recurring revenue businesses can fetch higher "
            "multiples — sometimes 5x SDE or more — depending on growth and churn.\n\n"
        )
        * 4,
        encoding="utf-8",
    )


def test_ingest_corpus_indexes_files_and_returns_stats(tmp_path: Path) -> None:
    """Full pipeline against an EphemeralClient — files in, vectors out, stats reported."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    persist_dir = tmp_path / "chroma"
    _write_seed_corpus(corpus_dir)

    client = chromadb.EphemeralClient()

    stats = ingest_corpus(
        corpus_dir=corpus_dir,
        persist_dir=persist_dir,
        collection_name="operator_test",
        client=client,
    )

    assert stats.files_processed == 2
    assert stats.files_skipped == 0
    assert stats.chunks_created >= 2
    assert stats.total_chars > 0


def test_ingest_corpus_retrieval_finds_relevant_chunk(tmp_path: Path) -> None:
    """End-to-end: ingest the seed, query 'How do SBA loans work?', expect the SBA chunk back."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    persist_dir = tmp_path / "chroma"
    _write_seed_corpus(corpus_dir)

    client = chromadb.EphemeralClient()

    ingest_corpus(
        corpus_dir=corpus_dir,
        persist_dir=persist_dir,
        collection_name="operator_test",
        client=client,
    )

    collection = client.get_collection(name="operator_test")
    result = collection.query(query_texts=["How do SBA loans work?"], n_results=2)

    raw_docs = result.get("documents")
    raw_metas = result.get("metadatas")
    docs = raw_docs[0] if raw_docs else []
    metas = raw_metas[0] if raw_metas else []
    assert docs, "expected at least one retrieved document"
    # The top-1 result should be from the SBA file, not the valuation file.
    assert metas[0]["source"] == "sba_loans.md", f"expected sba_loans.md as top hit, got {metas[0]['source']}"
    assert "SBA" in docs[0]


def test_ingest_corpus_skips_unsupported_files(tmp_path: Path) -> None:
    """Non-supported file types increment `files_skipped` and don't crash."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "notes.md").write_text("# Title\n\n" + ("Body. " * 100), encoding="utf-8")
    (corpus_dir / "binary.docx").write_bytes(b"\x00\x01\x02")

    client = chromadb.EphemeralClient()
    stats = ingest_corpus(
        corpus_dir=corpus_dir,
        persist_dir=tmp_path / "chroma",
        collection_name="skip_test",
        client=client,
    )

    assert stats.files_processed == 1
    assert stats.files_skipped == 1


def test_ingest_corpus_upsert_is_idempotent(tmp_path: Path) -> None:
    """Re-running ingestion against the same files doesn't duplicate chunks."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    _write_seed_corpus(corpus_dir)

    client = chromadb.EphemeralClient()
    stats1 = ingest_corpus(
        corpus_dir=corpus_dir,
        persist_dir=tmp_path / "chroma",
        collection_name="upsert_test",
        client=client,
    )
    stats2 = ingest_corpus(
        corpus_dir=corpus_dir,
        persist_dir=tmp_path / "chroma",
        collection_name="upsert_test",
        client=client,
    )

    assert stats1.chunks_created == stats2.chunks_created
    collection = client.get_collection(name="upsert_test")
    assert collection.count() == stats1.chunks_created


def test_ingest_corpus_rebuild_drops_old_collection(tmp_path: Path) -> None:
    """`rebuild=True` clears the collection so removed files don't linger as stale chunks."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    _write_seed_corpus(corpus_dir)

    client = chromadb.EphemeralClient()
    ingest_corpus(
        corpus_dir=corpus_dir,
        persist_dir=tmp_path / "chroma",
        collection_name="rebuild_test",
        client=client,
    )
    initial_count = client.get_collection("rebuild_test").count()

    # Simulate the user removing one source file.
    (corpus_dir / "sba_loans.md").unlink()

    ingest_corpus(
        corpus_dir=corpus_dir,
        persist_dir=tmp_path / "chroma",
        collection_name="rebuild_test",
        client=client,
        rebuild=True,
    )
    after_rebuild = client.get_collection("rebuild_test").count()
    assert after_rebuild < initial_count
