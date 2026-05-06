import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FitBadge } from "@/components/fit-badge";
import { StatusBadge } from "@/components/status-badge";
import { type DealSheet } from "@/lib/analyze";
import { ApiError, apiGet } from "@/lib/api";
import {
  parseDealSheetSections,
  renderBoldOnly,
  type DealSheetSection,
} from "@/lib/deal-sheet";
import { formatMoney, type Listing } from "@/lib/listings";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ ids?: string }>;

type ListingBundle = {
  listing: Listing | null;
  sheet: DealSheet | null;
  error: string | null;
};

async function loadBundle(id: string): Promise<ListingBundle> {
  let listing: Listing | null = null;
  let sheet: DealSheet | null = null;
  let error: string | null = null;
  try {
    listing = await apiGet<Listing>(`/api/listings/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      error = "listing not found";
    } else {
      error =
        err instanceof Error ? err.message : "Failed to load listing.";
    }
    return { listing, sheet, error };
  }
  try {
    const sheets = await apiGet<DealSheet[]>(`/api/analyze/${id}`);
    sheet = sheets[0] ?? null;
  } catch {
    sheet = null;
  }
  return { listing, sheet, error };
}

export default async function ComparePage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { ids } = await searchParams;
  const idList = (ids ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 3);

  if (idList.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Compare</h1>
        <p className="text-sm text-muted-foreground">
          Pin two or three listings from the inventory and click{" "}
          <span className="font-medium">Compare</span> to view their Deal
          Sheets stacked side-by-side.
        </p>
        <Link
          href="/listings"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          ← Back to listings
        </Link>
      </div>
    );
  }

  const bundles = await Promise.all(idList.map(loadBundle));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            href="/listings"
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            ← Back to listings
          </Link>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">
            Compare
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Latest Deal Sheet for each pinned listing, side-by-side. Re-run
            analysis from the listing page to refresh.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {bundles.map((b, i) => (
          <Column key={idList[i]} listingId={idList[i]} bundle={b} />
        ))}
      </div>
    </div>
  );
}

function Column({
  listingId,
  bundle,
}: {
  listingId: string;
  bundle: ListingBundle;
}) {
  if (bundle.error || bundle.listing === null) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Listing {listingId}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-600 dark:text-red-400">
            {bundle.error ?? "could not load listing"}
          </p>
        </CardContent>
      </Card>
    );
  }

  const listing = bundle.listing;
  const sections = bundle.sheet
    ? parseDealSheetSections(bundle.sheet.markdown)
    : [];

  return (
    <Card>
      <CardHeader className="flex flex-col gap-2">
        <Link
          href={`/listings/${listing.id}`}
          className="text-base font-semibold tracking-tight hover:underline"
        >
          {listing.business_name || "unnamed"}
        </Link>
        <p className="text-xs text-muted-foreground">
          {listing.industry ?? "industry —"}
          {listing.location ? ` · ${listing.location}` : ""}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={listing.status} />
          <FitBadge band={listing.fit_band} summary={listing.fit_summary} />
        </div>
        <dl className="mt-2 grid grid-cols-2 gap-y-1 text-xs">
          <dt className="text-muted-foreground">Asking</dt>
          <dd className="text-right font-mono">{formatMoney(listing.asking_price)}</dd>
          <dt className="text-muted-foreground">SDE</dt>
          <dd className="text-right font-mono">{formatMoney(listing.sde)}</dd>
          <dt className="text-muted-foreground">Revenue</dt>
          <dd className="text-right font-mono">{formatMoney(listing.revenue)}</dd>
        </dl>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {bundle.sheet === null ? (
          <p className="text-sm italic text-muted-foreground">
            No Deal Sheet yet. Run analysis on the listing page to populate
            this column.
          </p>
        ) : (
          sections.map((section, i) => (
            <CompareSection key={i} section={section} />
          ))
        )}
      </CardContent>
    </Card>
  );
}

function CompareSection({ section }: { section: DealSheetSection }) {
  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {section.title}
      </h3>
      <div
        className="whitespace-pre-wrap text-sm leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderBoldOnly(section.body.trim()) }}
      />
    </div>
  );
}
