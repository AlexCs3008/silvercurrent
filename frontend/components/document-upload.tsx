"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { uploadDocument } from "@/lib/documents";

type DocumentUploadProps = {
  listingId: string;
};

const ACCEPT = ".pdf,.txt,.md,.markdown,.csv,application/pdf,text/plain,text/markdown,text/csv";

/** Button-pick uploader. POSTs the file as multipart and refreshes the page. */
export function DocumentUpload({ listingId }: DocumentUploadProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      await uploadDocument(listingId, file);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
        >
          {busy ? "Uploading…" : "Upload document"}
        </Button>
        <span className="text-xs text-muted-foreground">
          PDF, text, markdown, or CSV. Indexed for chat-mode diligence search.
        </span>
      </div>
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
