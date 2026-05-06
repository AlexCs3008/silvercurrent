"""Listing-document storage, extraction, chunking, and indexing (Phase C).

Files uploaded against a specific listing live under `data/listings/{listing_id}/`
on disk. SQLite stores metadata + the full extracted text snapshot. Chunked
text is indexed in the `listing_document_chunk_fts` FTS5 virtual table so the
Analyst's `search_listing_documents` tool can return ranked passages with
provenance. ADR 0009.
"""

from __future__ import annotations
