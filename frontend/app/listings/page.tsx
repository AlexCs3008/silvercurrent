import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { CompareLauncher } from "@/components/compare-pin";
import { ListingCard } from "@/components/listing-card";
import { apiGet } from "@/lib/api";
import {
  LISTING_STATUSES,
  isListingSort,
  sortListings,
  type Listing,
  type ListingSort,
  type ListingStatus,
} from "@/lib/listings";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ status?: string; sort?: string }>;

function isStatus(value: string | undefined): value is ListingStatus {
  return (
    value !== undefined && (LISTING_STATUSES as readonly string[]).includes(value)
  );
}

const SORT_LABELS: Record<ListingSort, string> = {
  newest: "Newest",
  best_fit: "Best fit",
  asking_asc: "Asking ↑",
  asking_desc: "Asking ↓",
};

const SORT_OPTIONS: ListingSort[] = [
  "newest",
  "best_fit",
  "asking_asc",
  "asking_desc",
];

export default async function ListingsPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { status, sort } = await searchParams;
  const statusFilter = isStatus(status) ? status : undefined;
  const activeSort: ListingSort = isListingSort(sort) ? sort : "newest";

  const path = statusFilter
    ? `/api/listings?status_filter=${statusFilter}`
    : "/api/listings";

  let listings: Listing[] = [];
  let fetchError: string | null = null;
  try {
    listings = await apiGet<Listing[]>(path);
  } catch (err) {
    fetchError = err instanceof Error ? err.message : "Failed to load listings.";
  }

  const sorted = sortListings(listings, activeSort);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Listings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Inventory of small-business listings. Filter by status, click a card to
            review or edit.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/listings/calibration"
            className={buttonVariants({ variant: "outline" })}
          >
            Calibration
          </Link>
          <CompareLauncher />
          <Link href="/listings/new" className={buttonVariants()}>
            Add listing
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex flex-wrap gap-2 text-xs">
          <FilterChip
            href={buildHref(undefined, activeSort)}
            active={statusFilter === undefined}
          >
            all
          </FilterChip>
          {LISTING_STATUSES.map((s) => (
            <FilterChip
              key={s}
              href={buildHref(s, activeSort)}
              active={statusFilter === s}
            >
              {s}
            </FilterChip>
          ))}
        </nav>

        <nav className="flex flex-wrap gap-2 text-xs">
          {SORT_OPTIONS.map((option) => (
            <Link
              key={option}
              href={buildHref(statusFilter, option)}
              className={
                "rounded-full px-3 py-1 tracking-wide transition " +
                (option === activeSort
                  ? "bg-foreground text-background"
                  : "bg-muted text-muted-foreground hover:bg-muted/70")
              }
            >
              {SORT_LABELS[option]}
            </Link>
          ))}
        </nav>
      </div>

      {fetchError ? (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <p className="font-medium">Couldn’t reach the backend.</p>
          <p className="mt-1 font-mono text-xs">{fetchError}</p>
          <p className="mt-2 text-xs">
            Make sure the backend is running on{" "}
            <code className="font-mono">localhost:8000</code>.
          </p>
        </div>
      ) : sorted.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          {statusFilter
            ? `No listings with status "${statusFilter}".`
            : "No listings yet. Add one to get started."}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sorted.map((listing) => (
            <ListingCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}
    </div>
  );
}

function buildHref(
  statusFilter: ListingStatus | undefined,
  sort: ListingSort,
): string {
  const params = new URLSearchParams();
  if (statusFilter) params.set("status", statusFilter);
  if (sort !== "newest") params.set("sort", sort);
  const query = params.toString();
  return query ? `/listings?${query}` : "/listings";
}

function FilterChip({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={
        "rounded-full px-3 py-1 uppercase tracking-wide transition " +
        (active
          ? "bg-foreground text-background"
          : "bg-muted text-muted-foreground hover:bg-muted/70")
      }
    >
      {children}
    </Link>
  );
}
