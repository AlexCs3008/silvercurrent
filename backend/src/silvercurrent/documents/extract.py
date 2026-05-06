"""Extract plain text from an uploaded document.

PDFs route through `silvercurrent.ingestion.pdfs.extract_text_from_pdf`. Text-
shaped formats (`text/plain`, `text/markdown`, `text/csv`) decode as UTF-8
with a permissive fallback to latin-1. Other content types raise — the API
layer catches and returns 415.
"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf

from silvercurrent.ingestion.pdfs import PDFParseError

PDF_CONTENT_TYPE = "application/pdf"
TEXT_LIKE_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/x-markdown",
    }
)


class UnsupportedContentTypeError(ValueError):
    """Raised when a document's content type isn't extractable to text."""


@dataclass(frozen=True)
class ExtractedDocument:
    """Result of running the extractor against an uploaded document."""

    text: str
    page_breaks: list[int]  # character offsets where each new page begins (PDFs)


def _decode_text(content: bytes) -> str:
    """UTF-8 first; latin-1 as a last-resort fallback so we never raise on bytes."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="replace")


def _extract_pdf_with_pages(content: bytes) -> ExtractedDocument:
    """Same shape as `extract_text_from_pdf` but tracks per-page offsets."""
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")  # type: ignore[no-untyped-call]
    except Exception as e:
        raise PDFParseError(f"could not open PDF: {e}") from e

    parts: list[str] = []
    page_breaks: list[int] = []
    cursor = 0
    try:
        if doc.page_count == 0:
            raise PDFParseError("PDF has no pages.")
        for i in range(doc.page_count):
            page = doc.load_page(i)  # type: ignore[no-untyped-call]
            page_text: str = page.get_text()
            if not page_text.strip():
                continue
            page_breaks.append(cursor)
            parts.append(page_text)
            cursor += len(page_text) + 2  # +2 for the "\n\n" join below
    finally:
        doc.close()  # type: ignore[no-untyped-call]

    text = "\n\n".join(parts).strip()
    if not text:
        raise PDFParseError(
            "PDF appears to be scanned or image-only — extracted text is empty. OCR isn't supported yet."
        )
    return ExtractedDocument(text=text, page_breaks=page_breaks)


def extract_document(*, content: bytes, content_type: str, filename: str) -> ExtractedDocument:
    """Dispatch by content type. Raises `PDFParseError` or `UnsupportedContentTypeError`."""
    ct = content_type.lower().split(";", 1)[0].strip()
    if ct == PDF_CONTENT_TYPE:
        return _extract_pdf_with_pages(content)
    if ct in TEXT_LIKE_CONTENT_TYPES:
        # Reuse the standard PDF extractor's emptiness guard implicitly: if the
        # decoded text is whitespace-only, the chunker will yield nothing and
        # `index_chunks` will simply skip writing rows.
        return ExtractedDocument(text=_decode_text(content), page_breaks=[])
    # Some browsers send "application/octet-stream" for .txt files. Use the
    # filename extension as a fallback hint before giving up.
    lower_filename = filename.lower()
    if lower_filename.endswith((".pdf",)):
        return _extract_pdf_with_pages(content)
    if lower_filename.endswith((".txt", ".md", ".csv", ".markdown")):
        return ExtractedDocument(text=_decode_text(content), page_breaks=[])
    raise UnsupportedContentTypeError(
        f"unsupported content type {content_type!r}; supported: PDF, plain text, markdown, CSV."
    )


__all__ = [
    "PDF_CONTENT_TYPE",
    "TEXT_LIKE_CONTENT_TYPES",
    "ExtractedDocument",
    "PDFParseError",
    "UnsupportedContentTypeError",
    "extract_document",
]
