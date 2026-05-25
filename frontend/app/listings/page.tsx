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

type SearchParams = Promise<{ status?: string; sort?: string; q?: string }>;

type Calibration = {
  status_mix: Record<string, number>;
};

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

function matchesQuery(listing: Listing, q: string): boolean {
  const needle = q.toLowerCase();
  return (
    listing.business_name.toLowerCase().includes(needle) ||
    (listing.industry?.toLowerCase().includes(needle) ?? false) ||
    (listing.location?.toLowerCase().includes(needle) ?? false)
  );
}

export default async function ListingsPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { status, sort, q } = await searchParams;
  const statusFilter = isStatus(status) ? status : undefined;
  const activeSort: ListingSort = isListingSort(sort) ? sort : "newest";
  const query = (q ?? "").trim();

  const path = statusFilter
    ? `/api/listings?status_filter=${statusFilter}`
    : "/api/listings";

  const [listingsResult, calibrationResult] = await Promise.allSettled([
    apiGet<Listing[]>(path),
    apiGet<Calibration>("/api/calibration"),
  ]);

  let listings: Listing[] = [];
  let fetchError: string | null = null;
  if (listingsResult.status === "fulfilled") {
    listings = listingsResult.value;
  } else {
    fetchError =
      listingsResult.reason instanceof Error
        ? listingsResult.reason.message
        : "Failed to load listings.";
  }

  const statusCounts: Record<string, number> =
    calibrationResult.status === "fulfilled"
      ? calibrationResult.value.status_mix
      : {};
  const totalAll = Object.values(statusCounts).reduce((a, b) => a + b, 0);

  const filtered = query
    ? listings.filter((l) => matchesQuery(l, query))
    : listings;
  const sorted = sortListings(filtered, activeSort);

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
          <CompareLauncher />
          <Link href="/listings/new" className={buttonVariants()}>
            Add listing
          </Link>
        </div>
      </div>

      <form
        method="GET"
        action="/listings"
        className="flex flex-wrap items-center gap-3"
      >
        {statusFilter && (
          <input type="hidden" name="status" value={statusFilter} />
        )}
        {activeSort !== "newest" && (
          <input type="hidden" name="sort" value={activeSort} />
        )}
        <input
          type="search"
          name="q"
          defaultValue={query}
          placeholder="Search name, industry, location…"
          className="flex h-9 w-64 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        {query && (
          <Link
            href={buildHref(statusFilter, activeSort, "")}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            clear
          </Link>
        )}
      </form>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex flex-wrap items-center gap-2 text-xs">
          <FilterChip
            href={buildHref(undefined, activeSort, query)}
            active={statusFilter === undefined}
            count={totalAll || undefined}
          >
            all
          </FilterChip>
          {LISTING_STATUSES.map((s) => (
            <FilterChip
              key={s}
              href={buildHref(s, activeSort, query)}
              active={statusFilter === s}
              count={statusCounts[s] ?? 0}
            >
              {s}
            </FilterChip>
          ))}
        </nav>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Sort by</span>
          <nav className="flex flex-wrap gap-1">
            {SORT_OPTIONS.map((option) => (
              <Link
                key={option}
                href={buildHref(statusFilter, option, query)}
                className={
                  "rounded-md px-2 py-1 tracking-wide transition " +
                  (option === activeSort
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:bg-muted")
                }
              >
                {SORT_LABELS[option]}
              </Link>
            ))}
          </nav>
        </div>
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
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          <p>
            {query
              ? `No listings match “${query}”.`
              : statusFilter
                ? `No listings with status "${statusFilter}".`
                : "No listings yet."}
          </p>
          {!query && !statusFilter && (
            <Link href="/listings/new" className={buttonVariants({ size: "sm" })}>
              Add your first listing
            </Link>
          )}
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {sorted.map((listing) => (
            <li key={listing.id}>
              <ListingCard listing={listing} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function buildHref(
  statusFilter: ListingStatus | undefined,
  sort: ListingSort,
  query: string,
): string {
  const params = new URLSearchParams();
  if (statusFilter) params.set("status", statusFilter);
  if (sort !== "newest") params.set("sort", sort);
  if (query) params.set("q", query);
  const queryString = params.toString();
  return queryString ? `/listings?${queryString}` : "/listings";
}

function FilterChip({
  href,
  active,
  count,
  children,
}: {
  href: string;
  active: boolean;
  count?: number;
  children: React.ReactNode;
}) {
  const dim = count === 0;
  return (
    <Link
      href={href}
      className={
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 uppercase tracking-wide transition " +
        (active
          ? "bg-foreground text-background"
          : dim
            ? "bg-muted/40 text-muted-foreground/60 hover:bg-muted/70"
            : "bg-muted text-muted-foreground hover:bg-muted/70")
      }
    >
      <span>{children}</span>
      {count !== undefined && (
        <span
          className={
            "font-mono text-[10px] " +
            (active ? "text-background/80" : "text-foreground/70")
          }
        >
          {count}
        </span>
      )}
    </Link>
  );
}
