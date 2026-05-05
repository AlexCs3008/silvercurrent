"""PDF text extraction for broker teasers and CIM uploads.

Phase 1c reuses the existing `extract_listing()` pipeline; this module only
turns PDF bytes into plain text. No OCR — scanned PDFs return an explicit
error and the user pastes the text instead.

`pymupdf` is AGPL-licensed. That's fine for Silvercurrent: charter §2 commits
to single-user, never-distributed, never-publicly-hosted, so the AGPL's
network-distribution clauses never trigger.
"""

from __future__ import annotations

import pymupdf

# If the entire document yields fewer than this many characters, we treat it
# as effectively empty (most likely scanned/image-only) rather than try to
# extract structured fields from it.
SPARSE_TEXT_THRESHOLD = 200


class PDFParseError(RuntimeError):
    """Raised when a PDF cannot be opened or yields no usable text."""


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF byte stream.

    Raises `PDFParseError` if the PDF can't be opened, has no pages, or
    yields suspiciously sparse text (likely scanned/image-only).
    """
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")  # type: ignore[no-untyped-call]
    except Exception as e:
        raise PDFParseError(f"could not open PDF: {e}") from e

    try:
        if doc.page_count == 0:
            raise PDFParseError("PDF has no pages.")

        page_texts: list[str] = []
        for i in range(doc.page_count):
            page = doc.load_page(i)  # type: ignore[no-untyped-call]
            page_texts.append(page.get_text())
    finally:
        doc.close()  # type: ignore[no-untyped-call]

    text = "\n\n".join(t for t in page_texts if t.strip()).strip()

    if len(text) < SPARSE_TEXT_THRESHOLD:
        raise PDFParseError(
            "PDF appears to be scanned or image-only — extracted text is "
            "too sparse to use. OCR is not supported yet; try copy-pasting "
            "the relevant text into the Paste Text tab instead."
        )

    return text
