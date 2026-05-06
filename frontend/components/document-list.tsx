"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  deleteDocument,
  formatBytes,
  rawDocumentUrl,
  type ListingDocument,
} from "@/lib/documents";
import { formatDate } from "@/lib/listings";

type DocumentListProps = {
  listingId: string;
  documents: ListingDocument[];
};

/** Read-only listing of uploaded documents with download + delete actions. */
export function DocumentList({ listingId, documents }: DocumentListProps) {
  const router = useRouter();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (documents.length === 0) {
    return (
      <p className="text-xs italic text-muted-foreground">
        No documents uploaded yet. Add a CIM, P&L, or tax return to enable
        document-aware diligence in chat.
      </p>
    );
  }

  async function handleDelete(documentId: string, filename: string) {
    if (!confirm(`Delete "${filename}"? This removes the file and its index entries.`)) {
      return;
    }
    setBusyId(documentId);
    setError(null);
    try {
      await deleteDocument(listingId, documentId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
      <ul className="flex flex-col divide-y divide-border text-sm">
        {documents.map((doc) => (
          <li
            key={doc.id}
            className="flex items-center justify-between gap-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <a
                href={rawDocumentUrl(listingId, doc.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="block truncate font-mono text-xs underline-offset-2 hover:underline"
              >
                {doc.filename}
              </a>
              <p className="text-[11px] text-muted-foreground">
                {formatBytes(doc.byte_size)} · {doc.content_type} · added{" "}
                {formatDate(doc.created_at)}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleDelete(doc.id, doc.filename)}
              disabled={busyId === doc.id}
            >
              {busyId === doc.id ? "Deleting…" : "Delete"}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
