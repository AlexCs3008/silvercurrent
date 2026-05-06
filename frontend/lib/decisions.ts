/**
 * Decision-journal types + API helpers (Phase B).
 *
 * The journal captures the buyer's reason for a status transition into
 * `passed`, `tracking`, or `loi`. Append-only; agents don't read or write it.
 */

import { apiGet, apiPost } from "@/lib/api";

export type DecisionJournalEntry = {
  id: string;
  listing_id: string;
  previous_status: string | null;
  new_status: string;
  reason: string;
  created_at: string;
};

export type DecisionJournalCreate = {
  previous_status: string | null;
  new_status: string;
  reason: string;
};

export function fetchDecisions(
  listingId: string,
): Promise<DecisionJournalEntry[]> {
  return apiGet<DecisionJournalEntry[]>(`/api/listings/${listingId}/decisions`);
}

export function postDecision(
  listingId: string,
  body: DecisionJournalCreate,
): Promise<DecisionJournalEntry> {
  return apiPost<DecisionJournalEntry>(
    `/api/listings/${listingId}/decisions`,
    body,
  );
}
