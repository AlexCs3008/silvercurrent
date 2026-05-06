"""HTTP routes for listing-document upload, list, delete, and raw-stream (Phase C).

The flow is:

1. `POST /api/listings/{id}/documents` (multipart) — accept file, persist to disk,
   extract text, chunk, write FTS5 rows, return `ListingDocumentRead`.
2. `GET /api/listings/{id}/documents` — list documents on a listing, newest-first.
3. `DELETE /api/listings/{id}/documents/{doc_id}` — delete file from disk,
   FTS rows, and the metadata row.
4. `GET /api/listings/{id}/documents/{doc_id}/raw` — stream the file back so the
   user can re-download / preview.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.config import get_settings
from silvercurrent.db.models import Listing, ListingDocument
from silvercurrent.db.session import get_session
from silvercurrent.documents.chunk import chunk_text
from silvercurrent.documents.extract import (
    PDF_CONTENT_TYPE,
    PDFParseError,
    UnsupportedContentTypeError,
    extract_document,
)
from silvercurrent.documents.index import delete_chunks_for_document, index_chunks
from silvercurrent.documents.storage import absolute_path, delete_file, save_uploaded

router = APIRouter(prefix="/api/listings", tags=["documents"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Cap for non-PDF uploads. PDFs already use `settings.pdf_max_bytes`. CIM PDFs
# can be tens of MB; CSV/markdown rarely exceed 10 MB, so a tighter cap there
# protects against accidental huge dumps.
_TEXT_MAX_BYTES = 10_000_000


class ListingDocumentRead(BaseModel):
    """Response shape for a `ListingDocument` row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    listing_id: UUID
    filename: str
    content_type: str
    byte_size: int
    sha256: str
    created_at: datetime


def _safe_filename(raw: str) -> str:
    """Trim the filename, drop directory components, cap the length."""
    base = os.path.basename(raw or "").strip() or "upload"
    return base[:512]


@router.post(
    "/{listing_id}/documents",
    response_model=ListingDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    listing_id: UUID,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
) -> ListingDocument:
    """Accept a file, persist it, extract+chunk+index, return the metadata row."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    content_type = (file.content_type or "application/octet-stream").lower()
    settings = get_settings()
    cap = settings.pdf_max_bytes if content_type == PDF_CONTENT_TYPE else _TEXT_MAX_BYTES
    if len(content) > cap:
        raise HTTPException(
            status_code=413,
            detail=(f"File is {len(content):,} bytes; the cap for this content type is {cap:,}."),
        )

    filename = _safe_filename(file.filename or "upload")

    try:
        extracted = extract_document(content=content, content_type=content_type, filename=filename)
    except UnsupportedContentTypeError as e:
        raise HTTPException(status_code=415, detail=str(e)) from e
    except PDFParseError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    stored = save_uploaded(listing_id=listing_id, filename=filename, content=content)

    document = ListingDocument(
        listing_id=listing_id,
        filename=filename,
        content_type=content_type,
        byte_size=stored.byte_size,
        sha256=stored.sha256,
        storage_path=stored.storage_path,
        extracted_text=extracted.text,
    )
    session.add(document)
    await session.flush()  # populate document.id before indexing

    chunks = chunk_text(extracted.text, page_breaks=extracted.page_breaks)
    await index_chunks(
        session=session,
        document_id=document.id,
        listing_id=listing_id,
        chunks=chunks,
    )
    await session.commit()
    await session.refresh(document)
    return document


@router.get(
    "/{listing_id}/documents",
    response_model=list[ListingDocumentRead],
)
async def list_documents(
    listing_id: UUID,
    session: SessionDep,
) -> list[ListingDocument]:
    """List documents on a listing, newest-first. 404 if the listing is missing."""
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    stmt = (
        select(ListingDocument)
        .where(ListingDocument.listing_id == listing_id)
        .order_by(ListingDocument.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.delete(
    "/{listing_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    listing_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> None:
    """Delete the file from disk, FTS rows, and the metadata row."""
    document = await session.get(ListingDocument, document_id)
    if document is None or document.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="document not found")

    await delete_chunks_for_document(session=session, document_id=document_id)
    await session.delete(document)
    await session.commit()
    delete_file(document.storage_path)


@router.get("/{listing_id}/documents/{document_id}/raw")
async def get_document_raw(
    listing_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> Any:
    """Stream the file back to the user. PDFs render inline; everything else attaches."""
    document = await session.get(ListingDocument, document_id)
    if document is None or document.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="document not found")
    path = absolute_path(document.storage_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="file no longer present on disk")
    disposition = "inline" if document.content_type == PDF_CONTENT_TYPE else "attachment"
    return FileResponse(
        path=str(path),
        media_type=document.content_type,
        filename=document.filename,
        content_disposition_type=disposition,
    )
