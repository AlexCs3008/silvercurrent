"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { apiDelete, apiPatch } from "@/lib/api";
import { postDecision } from "@/lib/decisions";
import {
  LISTING_STATUSES,
  type Listing,
  type ListingStatus,
  type ListingUpdateResponse,
} from "@/lib/listings";

type ListingActionsProps = {
  listing: Listing;
};

type DecisionPrompt = {
  previousStatus: string | null;
  newStatus: string;
};

/** Detail-page action bar: change status, edit, or delete. */
export function ListingActions({ listing }: ListingActionsProps) {
  const router = useRouter();
  const [status, setStatus] = useState<ListingStatus>(listing.status);
  const [busy, setBusy] = useState<"status" | "delete" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [decisionPrompt, setDecisionPrompt] = useState<DecisionPrompt | null>(
    null,
  );

  async function handleStatusChange(next: ListingStatus) {
    setBusy("status");
    setError(null);
    setStatus(next);
    try {
      const response = await apiPatch<ListingUpdateResponse>(
        `/api/listings/${listing.id}`,
        { status: next },
      );
      if (response.requires_decision) {
        setDecisionPrompt({
          previousStatus: response.decision_previous_status,
          newStatus: response.decision_new_status ?? next,
        });
      } else {
        router.refresh();
      }
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

      {decisionPrompt && (
        <DecisionReasonModal
          listingId={listing.id}
          previousStatus={decisionPrompt.previousStatus}
          newStatus={decisionPrompt.newStatus}
          onClose={() => {
            // Closing without submitting still leaves the status changed —
            // the journal is best-effort capture, not a gate.
            setDecisionPrompt(null);
            router.refresh();
          }}
        />
      )}
    </div>
  );
}

type DecisionReasonModalProps = {
  listingId: string;
  previousStatus: string | null;
  newStatus: string;
  onClose: () => void;
};

function DecisionReasonModal({
  listingId,
  previousStatus,
  newStatus,
  onClose,
}: DecisionReasonModalProps) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Close on Escape — accessibility minimum.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reason.trim()) {
      setError("Add a one-sentence reason — the journal needs the why.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await postDecision(listingId, {
        previous_status: previousStatus,
        new_status: newStatus,
        reason: reason.trim(),
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save decision.");
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-xl border border-border bg-background p-5 shadow-lg"
      >
        <h2 className="text-base font-semibold tracking-tight">
          Why{" "}
          <span className="lowercase">
            {newStatus === "passed"
              ? "pass"
              : newStatus === "tracking"
                ? "track"
                : newStatus === "loi"
                  ? "submit LOI"
                  : newStatus}
          </span>
          ?
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">
          {previousStatus
            ? `Moving from ${previousStatus} to ${newStatus}.`
            : `Moving to ${newStatus}.`}{" "}
          One sentence is enough — the system uses these to surface patterns
          later.
        </p>
        <Textarea
          autoFocus
          className="mt-3 min-h-24"
          maxLength={500}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Asking is 5× SDE with no path to negotiate down."
          disabled={submitting}
        />
        {error && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">
            {error}
          </p>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={submitting}
          >
            Skip
          </Button>
          <Button type="submit" size="sm" disabled={submitting}>
            {submitting ? "Saving…" : "Save reason"}
          </Button>
        </div>
      </form>
    </div>
  );
}
