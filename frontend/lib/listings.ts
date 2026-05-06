/**
 * Listing types and helpers shared across the listings UI.
 *
 * Mirrors `silvercurrent.schemas.listings` on the backend. Keep field names in
 * sync — divergence shows up as runtime parse errors against the API.
 */

import type { DecisionJournalEntry } from "@/lib/decisions";

export const LISTING_STATUSES = [
  "new",
  "reviewing",
  "passed",
  "tracking",
  "loi",
  "closed",
] as const;

export type ListingStatus = (typeof LISTING_STATUSES)[number];

export const FIT_BANDS = [
  "strong",
  "partial",
  "weak",
  "mismatch",
  "unknown",
] as const;

export type FitBand = (typeof FIT_BANDS)[number];

export type Listing = {
  id: string;
  created_at: string;
  updated_at: string;

  source: string;
  source_url: string | null;

  business_name: string;
  industry: string | null;
  naics_code: string | null;
  location: string | null;

  asking_price: number | null;
  sde: number | null;
  cash_flow: number | null;
  revenue: number | null;

  narrative: string | null;
  reason_for_selling: string | null;
  raw_text: string | null;

  broker_name: string | null;
  broker_contact: string | null;

  status: ListingStatus;
  notes: string | null;
  tags: string[];

  // Computed by the backend on every read from `docs/criteria.md`. Null when
  // criteria are unreadable. Bands are not numeric scores — see ADR 0008.
  fit_band: FitBand | null;
  fit_summary: string | null;

  // Most-recent decision-journal entry for this listing (Phase B). Null when
  // no journal entry has been written.
  latest_decision: DecisionJournalEntry | null;
};

/** PATCH `/api/listings/{id}` response shape — wraps the listing with a `requires_decision` flag. */
export type ListingUpdateResponse = {
  listing: Listing;
  requires_decision: boolean;
  decision_previous_status: string | null;
  decision_new_status: string | null;
};

/** LLM-extracted subset of a listing — what `POST /api/listings/extract` returns. */
export type ExtractedListing = {
  business_name: string;
  industry: string | null;
  naics_code: string | null;
  location: string | null;
  asking_price: number | null;
  sde: number | null;
  cash_flow: number | null;
  revenue: number | null;
  narrative: string | null;
  reason_for_selling: string | null;
  broker_name: string | null;
  broker_contact: string | null;
  tags: string[];
  status: ListingStatus;
};

export type ExtractionUsage = {
  input_tokens: number;
  output_tokens: number;
  model: string;
};

export type ExtractionResult = {
  extracted: ExtractedListing;
  raw_text: string;
  source_url: string | null;
  usage: ExtractionUsage;
};

/** Body for POST `/api/listings`. Mirrors `ListingCreate` server-side. */
export type ListingCreate = {
  source?: string;
  source_url?: string | null;
  business_name: string;
  industry?: string | null;
  naics_code?: string | null;
  location?: string | null;
  asking_price?: number | null;
  sde?: number | null;
  cash_flow?: number | null;
  revenue?: number | null;
  narrative?: string | null;
  reason_for_selling?: string | null;
  raw_text?: string | null;
  broker_name?: string | null;
  broker_contact?: string | null;
  status?: ListingStatus;
  notes?: string | null;
  tags?: string[];
};

/** PATCH body — every field optional. */
export type ListingUpdate = Partial<ListingCreate>;

const USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

/** Render whole-dollar amounts as `$1,234,000`; `null` becomes `"—"`. */
export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return USD.format(value);
}

const DATE = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

/** Format an ISO timestamp as e.g. `May 4, 2026`. */
export function formatDate(iso: string): string {
  return DATE.format(new Date(iso));
}

/** Map a status to a Tailwind color class for the badge. */
export const STATUS_COLOR: Record<ListingStatus, string> = {
  new: "bg-blue-500/15 text-blue-700 dark:text-blue-400",
  reviewing: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  passed: "bg-zinc-500/15 text-zinc-700 dark:text-zinc-400",
  tracking: "bg-purple-500/15 text-purple-700 dark:text-purple-400",
  loi: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  closed: "bg-emerald-700/20 text-emerald-800 dark:text-emerald-300",
};

/**
 * Map a fit band to a Tailwind color class. No red — the band describes
 * fit-to-criteria, not deal quality (charter §6: surface, never decide).
 */
export const FIT_BAND_COLOR: Record<FitBand, string> = {
  strong: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  partial: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  weak: "bg-amber-500/10 text-amber-800/80 dark:text-amber-500/80",
  mismatch: "bg-zinc-500/20 text-zinc-700 dark:text-zinc-300",
  unknown: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
};

export const FIT_BAND_LABEL: Record<FitBand, string> = {
  strong: "strong fit",
  partial: "partial fit",
  weak: "weak fit",
  mismatch: "mismatch",
  unknown: "unknown",
};

/** Sort options exposed in the inventory toolbar. */
export const LISTING_SORT_OPTIONS = [
  "newest",
  "best_fit",
  "asking_asc",
  "asking_desc",
] as const;

export type ListingSort = (typeof LISTING_SORT_OPTIONS)[number];

/** Order used for the "Best fit" sort: strong first, unknown last. */
const FIT_BAND_ORDER: Record<FitBand, number> = {
  strong: 0,
  partial: 1,
  weak: 2,
  unknown: 3,
  mismatch: 4,
};

/**
 * Sort a listing list in-place-ish (returns a new array). `newest` is the
 * default (matches the API's existing order).
 */
export function sortListings(listings: Listing[], sort: ListingSort): Listing[] {
  const out = [...listings];
  switch (sort) {
    case "newest":
      return out.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
    case "best_fit":
      return out.sort((a, b) => {
        const aRank = a.fit_band ? FIT_BAND_ORDER[a.fit_band] : 5;
        const bRank = b.fit_band ? FIT_BAND_ORDER[b.fit_band] : 5;
        if (aRank !== bRank) return aRank - bRank;
        return (
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
      });
    case "asking_asc":
      return out.sort((a, b) => {
        const av = a.asking_price ?? Number.POSITIVE_INFINITY;
        const bv = b.asking_price ?? Number.POSITIVE_INFINITY;
        return av - bv;
      });
    case "asking_desc":
      return out.sort((a, b) => {
        const av = a.asking_price ?? Number.NEGATIVE_INFINITY;
        const bv = b.asking_price ?? Number.NEGATIVE_INFINITY;
        return bv - av;
      });
  }
}

export function isListingSort(value: string | undefined): value is ListingSort {
  return (
    value !== undefined &&
    (LISTING_SORT_OPTIONS as readonly string[]).includes(value)
  );
}
