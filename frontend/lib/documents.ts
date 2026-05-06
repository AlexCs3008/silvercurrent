/**
 * Document-attachment types + API helpers (Phase C).
 *
 * Files uploaded against a listing are content-extracted, chunked, and indexed
 * in SQLite FTS5 server-side. The frontend only sees the metadata row + a
 * link to download the raw file.
 */

import { API_BASE_URL, apiDelete, apiGet, apiPostMultipart } from "@/lib/api";

export type ListingDocument = {
  id: string;
  listing_id: string;
  filename: string;
  content_type: string;
  byte_size: number;
  sha256: string;
  created_at: string;
};

export function fetchDocuments(listingId: string): Promise<ListingDocument[]> {
  return apiGet<ListingDocument[]>(`/api/listings/${listingId}/documents`);
}

export function uploadDocument(
  listingId: string,
  file: File,
): Promise<ListingDocument> {
  const formData = new FormData();
  formData.append("file", file);
  return apiPostMultipart<ListingDocument>(
    `/api/listings/${listingId}/documents`,
    formData,
  );
}

export function deleteDocument(
  listingId: string,
  documentId: string,
): Promise<void> {
  return apiDelete(`/api/listings/${listingId}/documents/${documentId}`);
}

/** Direct URL to the raw file. PDFs render inline, others download. */
export function rawDocumentUrl(listingId: string, documentId: string): string {
  return `${API_BASE_URL}/api/listings/${listingId}/documents/${documentId}/raw`;
}

const KB = 1024;
const MB = KB * 1024;

export function formatBytes(bytes: number): string {
  if (bytes < KB) return `${bytes} B`;
  if (bytes < MB) return `${(bytes / KB).toFixed(1)} KB`;
  return `${(bytes / MB).toFixed(1)} MB`;
}
