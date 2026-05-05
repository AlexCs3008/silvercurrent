"""Tests for PDF parsing + the `/api/listings/extract-pdf` endpoint.

The parser tests use small PDFs synthesized inline via pymupdf — no fixture
files committed. The Anthropic client is mocked the same way as in
`test_extraction.py`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pymupdf
import pytest
import pytest_asyncio
from anthropic.types import ToolUseBlock
from httpx import ASGITransport, AsyncClient

from silvercurrent.ingestion.pdfs import (
    SPARSE_TEXT_THRESHOLD,
    PDFParseError,
    extract_text_from_pdf,
)
from silvercurrent.main import app


def _make_pdf(text_per_page: list[str]) -> bytes:
    """Build a minimal in-memory PDF with the given text on each page.

    Uses `insert_textbox` (which wraps) rather than `insert_text` (which
    runs off the page edge silently). pymupdf ships without typing stubs,
    so calls into it are tagged with `no-untyped-call` ignores.
    """
    doc = pymupdf.open()  # type: ignore[no-untyped-call]
    for page_text in text_per_page:
        page = doc.new_page()
        rect = pymupdf.Rect(50, 50, page.rect.width - 50, page.rect.height - 50)  # type: ignore[no-untyped-call]
        page.insert_textbox(rect, page_text, fontsize=11)
    buf: bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return buf


# --- Parser tests --------------------------------------------------------------


def test_extract_text_from_pdf_single_page() -> None:
    """A single-page PDF round-trips its text through the parser."""
    long_text = "Acme HVAC for sale. Asking price $1,200,000. " * 10
    pdf_bytes = _make_pdf([long_text])

    result = extract_text_from_pdf(pdf_bytes)

    assert "Acme HVAC" in result
    assert "$1,200,000" in result


def test_extract_text_from_pdf_multi_page_joined() -> None:
    """Multi-page PDFs concatenate page text with a blank line between pages."""
    pdf_bytes = _make_pdf(
        [
            "Page one " * 30,
            "Page two " * 30,
        ]
    )

    result = extract_text_from_pdf(pdf_bytes)

    assert "Page one" in result
    assert "Page two" in result
    # Pages are joined with a separator so the model can see structure.
    assert "\n\n" in result


def test_extract_text_from_pdf_rejects_invalid_bytes() -> None:
    """Random bytes that aren't a PDF raise `PDFParseError`."""
    with pytest.raises(PDFParseError, match="could not open"):
        extract_text_from_pdf(b"this is definitely not a PDF file")


def test_extract_text_from_pdf_rejects_sparse_text() -> None:
    """A PDF with very little text is rejected as likely scanned/image-only."""
    pdf_bytes = _make_pdf(["short"])  # well under SPARSE_TEXT_THRESHOLD

    with pytest.raises(PDFParseError, match="scanned"):
        extract_text_from_pdf(pdf_bytes)


def test_sparse_threshold_is_what_we_expect() -> None:
    """Guard the constant — if someone bumps it, this test should be updated deliberately."""
    assert SPARSE_TEXT_THRESHOLD == 200


# --- Endpoint tests ------------------------------------------------------------


def _mock_client(tool_input: dict[str, Any]) -> MagicMock:
    """Same mock helper as test_extraction.py — an AsyncAnthropic that returns one tool_use block."""
    tool_block = ToolUseBlock(
        type="tool_use",
        id="toolu_test",
        name="record_listing",
        input=tool_input,
    )
    response = MagicMock()
    response.content = [tool_block]
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=120, output_tokens=60)

    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=response)
    return client


@pytest_asyncio.fixture
async def http_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_happy_path(http_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Upload a valid PDF, mock Anthropic, get back the standard ExtractionResult shape."""
    fake_client = _mock_client(
        {
            "business_name": "PDF Listing Co",
            "asking_price": 750_000,
            "industry": "consulting",
            "tags": ["consulting"],
        }
    )
    import silvercurrent.ingestion.listings as ext_module

    monkeypatch.setattr(ext_module, "AsyncAnthropic", lambda **kwargs: fake_client)

    pdf_bytes = _make_pdf(["PDF Listing Co — established consulting practice for sale. " * 10])

    response = await http_client.post(
        "/api/listings/extract-pdf",
        files={"file": ("listing.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["extracted"]["business_name"] == "PDF Listing Co"
    assert body["extracted"]["asking_price"] == 750_000
    assert body["source_url"] is None
    # raw_text is the parsed PDF content, not the original bytes.
    assert "PDF Listing Co" in body["raw_text"]


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_rejects_empty_file(http_client: AsyncClient) -> None:
    """A 0-byte upload returns 400."""
    response = await http_client.post(
        "/api/listings/extract-pdf",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_rejects_too_large(
    http_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Files over `pdf_max_bytes` return 413."""
    from silvercurrent.config import Settings

    # Make the cap small so we don't have to upload 20 MB in test.
    def small_settings() -> Settings:
        s = Settings()
        s.pdf_max_bytes = 100  # 100 bytes — any real PDF exceeds this
        return s

    import silvercurrent.api.listings as routes_module

    monkeypatch.setattr(routes_module, "get_settings", small_settings)

    pdf_bytes = _make_pdf(["big content " * 50])
    assert len(pdf_bytes) > 100  # sanity

    response = await http_client.post(
        "/api/listings/extract-pdf",
        files={"file": ("big.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 413
    assert "cap" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_unparseable_returns_400(http_client: AsyncClient) -> None:
    """Garbage bytes that can't be opened as a PDF return 400 with the parser message."""
    response = await http_client.post(
        "/api/listings/extract-pdf",
        files={"file": ("garbage.pdf", b"not a pdf at all", "application/pdf")},
    )
    assert response.status_code == 400
    assert "could not open" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_scanned_pdf_returns_400(http_client: AsyncClient) -> None:
    """A PDF with too-sparse text returns 400 with the 'paste text' hint."""
    pdf_bytes = _make_pdf(["short"])  # under sparse threshold

    response = await http_client.post(
        "/api/listings/extract-pdf",
        files={"file": ("scanned.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "scanned" in detail
    assert "paste" in detail
