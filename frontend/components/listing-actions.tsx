"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiDelete, apiPatch } from "@/lib/api";
import {
  LISTING_STATUSES,
  type Listing,
  type ListingStatus,
} from "@/lib/listings";

type ListingActionsProps = {
  listing: Listing;
};

/** Detail-page action bar: change status, edit, or delete. */
export function ListingActions({ listing }: ListingActionsProps) {
  const router = useRouter();
  const [status, setStatus] = useState<ListingStatus>(listing.status);
  const [busy, setBusy] = useState<"status" | "delete" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleStatusChange(next: ListingStatus) {
    setBusy("status");
    setError(null);
    setStatus(next);
    try {
      await apiPatch<Listing>(`/api/listings/${listing.id}`, { status: next });
      router.refresh();
    } catch (err) {
      setStatus(listing.status); // revert local state
      setError(err instanceof Error ? err.message : "Status change failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete "${listing.business_name}"? This cannot be undone.`)) {
      return;
    }
    setBusy("delete");
    setError(null);
    try {
      await apiDelete(`/api/listings/${listing.id}`);
      router.push("/listings");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Status</span>
        <Select
          value={status}
          onValueChange={(v) => handleStatusChange(v as ListingStatus)}
          disabled={busy !== null}
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LISTING_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Link
        href={`/listings/${listing.id}/edit`}
        className={buttonVariants({ variant: "outline", size: "sm" })}
      >
        Edit
      </Link>
      <Button
        variant="destructive"
        size="sm"
        onClick={handleDelete}
        disabled={busy !== null}
      >
        {busy === "delete" ? "Deleting…" : "Delete"}
      </Button>
      {error && (
        <span className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
