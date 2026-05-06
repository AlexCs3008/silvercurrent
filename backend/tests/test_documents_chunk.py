"""Tests for the paragraph chunker."""

from __future__ import annotations

from silvercurrent.documents.chunk import chunk_text


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_yields_one_chunk() -> None:
    text = "A short paragraph that easily fits in one chunk."
    chunks = chunk_text(text, chunk_size=1200, overlap=200)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert text in chunks[0].content


def test_long_text_splits_into_multiple_chunks_with_overlap() -> None:
    paragraph = ("Lorem ipsum dolor sit amet. " * 30).strip()
    text = "\n\n".join([paragraph] * 5)
    chunks = chunk_text(text, chunk_size=600, overlap=100)
    assert len(chunks) >= 2
    # chunk_index is contiguous from 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # Overlap: every chunk after the first shares a substring with the previous.
    for i in range(1, len(chunks)):
        prev_words = chunks[i - 1].content.split()[-5:]
        assert any(word in chunks[i].content for word in prev_words)


def test_page_hint_resolved_from_breaks() -> None:
    text = "page one paragraph.\n\npage two paragraph.\n\npage three paragraph."
    breaks = [0, len("page one paragraph.\n\n"), len("page one paragraph.\n\npage two paragraph.\n\n")]
    chunks = chunk_text(text, page_breaks=breaks, chunk_size=30, overlap=5)
    pages = {c.page_hint for c in chunks}
    assert pages.issubset({1, 2, 3})
    assert pages != {None}


def test_chunk_count_is_deterministic_for_same_input() -> None:
    text = "\n\n".join(["Paragraph " + str(i) + " content here." for i in range(10)])
    a = chunk_text(text, chunk_size=200, overlap=20)
    b = chunk_text(text, chunk_size=200, overlap=20)
    assert len(a) == len(b)
    assert [c.content for c in a] == [c.content for c in b]
