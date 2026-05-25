import Link from "next/link";

import { Card } from "@/components/ui/card";
import { ComparePin } from "@/components/compare-pin";
import { FitBadge } from "@/components/fit-badge";
import { StatusBadge } from "@/components/status-badge";
import { formatDate, formatMoney, type Listing } from "@/lib/listings";

type ListingCardProps = {
  listing: Listing;
};

/**
 * One listing in the inventory list — full-width row with everything visible,
 * no truncation. Click anywhere except the pin button to open the listing.
 */
export function ListingCard({ listing }: ListingCardProps) {
  return (
    <Link
      href={`/listings/${listing.id}`}
      className="block rounded-xl outline-none ring-offset-2 transition focus-visible:ring-2 focus-visible:ring-foreground/30 hover:bg-muted/30"
    >
      <Card className="px-5 py-4">
        <div className="flex flex-col gap-3">
          {/* Header row: name + meta on the left, badges on the right */}
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold leading-snug">
                {listing.business_name || (
                  <span className="italic text-muted-foreground">unnamed</span>
                )}
              </h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {listing.industry ?? "industry —"}
                {listing.location ? ` · ${listing.location}` : ""}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <FitBadge band={listing.fit_band} summary={listing.fit_summary} />
              <StatusBadge status={listing.status} />
              <ComparePin listingId={listing.id} variant="compact" />
            </div>
          </div>

          {/* Financials strip — 4-up, wraps on narrow screens */}
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 border-t border-border pt-3 sm:grid-cols-4">
            <Stat label="Asking" value={formatMoney(listing.asking_price)} />
            <Stat label="SDE" value={formatMoney(listing.sde)} />
            <Stat label="Cash flow" value={formatMoney(listing.cash_flow)} />
            <Stat label="Revenue" value={formatMoney(listing.revenue)} />
          </dl>

          {/* Latest decision — full text, wraps. Hidden when none. */}
          {listing.latest_decision && (
            <p className="rounded-md border-l-2 border-border bg-muted/30 px-3 py-2 text-xs leading-relaxed text-muted-foreground">
              <span className="font-mono text-foreground/70">
                {listing.latest_decision.new_status}
              </span>{" "}
              · {listing.latest_decision.reason}
            </p>
          )}

          {/* Footer: provenance */}
          <p className="text-[11px] text-muted-foreground">
            Added {formatDate(listing.created_at)} · {listing.source}
            {listing.broker_name ? ` · ${listing.broker_name}` : ""}
          </p>
        </div>
      </Card>
    </Link>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="font-mono text-sm text-foreground">{value}</dd>
    </div>
  );
}
