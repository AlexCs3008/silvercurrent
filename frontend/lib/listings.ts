/**
 * Listing types and helpers shared across the listings UI.
 *
 * Mirrors `silvercurrent.schemas.listings` on the backend. Keep field names in
 * sync — divergence shows up as runtime parse errors against the API.
 */

export const LISTING_STATUSES = [
  "new",
  "reviewing",
  "passed",
  "tracking",
  "loi",
  "closed",
] as const;

export type ListingStatus = (typeof LISTING_STATUSES)[number];

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
