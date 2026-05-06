# 2026-05-06 — Phase C: document attachments

**Plan source:** `ultraplan-brief.md` (Screen / Diligence / Judgment expansion).
**Status:** shipped.

## What changed

The cockpit can now ingest CIMs, P&Ls, tax returns, and other diligence documents against a specific listing. Files persist on disk, text gets extracted and chunked, chunks are indexed in SQLite FTS5, and the Analyst's chat mode gains `search_listing_documents` to answer document-aware questions with cited passages.

## What I built

- New `silvercurrent.documents` package: `storage` (filesystem persistence under `data/listings/{id}/`), `extract` (PDF + text dispatcher reusing `pymupdf`), `chunk` (paragraph chunker with sliding-window overlap and PDF page hints), `index` (FTS5 insert/delete/search via raw SQL).
- `db/models.py:ListingDocument` + migration `c78366360fdf` creating the table + index + the FTS5 virtual table.
- `api/documents.py`: POST multipart upload (415 on unsupported types, 413 over size cap), GET list, DELETE, GET raw stream (PDF inline / others attachment).
- `agents/tools/listing_documents.py:search_listing_documents` returning ranked chunks wrapped in `<uploaded_document>` (ADR 0002), with the same first-200-char dedup fingerprint as `kb_search`.
- Analyst tool schema + handler registration; both prompts updated. The batch prompt explicitly skips the new tool, the chat prompt directs its use and reaffirms the DATA framing.
- Frontend: `lib/documents.ts`, `components/document-upload.tsx`, `components/document-list.tsx`, Documents card on the listing detail page.
- `conftest.py` (and the analyst-test fixture) create the FTS5 virtual table alongside `Base.metadata.create_all` since SQLAlchemy doesn't model virtual tables.
- ADR `0009-document-attachments-and-fts5.md`.

## Decisions worth remembering

- **FTS5, not Chroma.** Diligence queries are keyword-shaped; embeddings would add cost and a dependency for a workload where lexical match wins. The tool envelope is symmetric with the kb_search shape so we can swap to Chroma later if quality demands.
- **Files on disk, not in the DB.** `data/` is gitignored; PDFs are 1–50 MB. Path-based storage is debuggable and backup-friendly.
- **Wrapping at the tool-result boundary.** The wrapper isn't applied at write-time; `search_listing_documents` adds it just before the model sees the chunks. Same pattern as `format_passages_for_prompt` in `kb_search`.
- **Batch mode skips this tool.** Deal Sheets run at fixed depth from structured fields. Adding a document-search step in batch mode would unbound iteration. Document-aware analysis is a chat-mode capability.
- **Cascade deletes.** Listing deletion cascades the document row via the FK; the API delete handler additionally unlinks the file from disk and deletes FTS rows. Filesystem cleanup on listing-cascade is left for a future cleanup script — orphans are idempotent.
- **No OCR.** Scanned PDFs return a `PDFParseError`. The error message tells the user to paste the relevant text instead.

## Open / deferred

- Filesystem cleanup on `Listing` cascade-delete is not transactional — orphaned files are theoretically possible. Current behavior: API delete handler explicitly unlinks; cascade-from-listing-delete leaves the directory. Acceptable until we accumulate orphans.
- Re-uploading the same file overwrites the on-disk bytes (path is content-addressed by sha256). The DB row gets a fresh `id` though, so the chunks are re-indexed under the new id. Slight inefficiency that's not worth fixing yet.
- Frontend has no progress bar for large uploads. Acceptable — the multipart wrapper just resolves when the request finishes.
