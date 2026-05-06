import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ComparePin } from "@/components/compare-pin";
import { FitBadge } from "@/components/fit-badge";
import { StatusBadge } from "@/components/status-badge";
import { formatDate, formatMoney, type Listing } from "@/lib/listings";

type ListingCardProps = {
  listing: Listing;
};

/** A single listing in the inventory grid. Links to the detail page. */
export function ListingCard({ listing }: ListingCardProps) {
  return (
    <Link
      href={`/listings/${listing.id}`}
      className="block rounded-xl outline-none ring-offset-2 transition focus-visible:ring-2 focus-visible:ring-foreground/30 hover:opacity-95"
    >
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <CardTitle className="truncate text-base">
                {listing.business_name || (
                  <span className="italic text-muted-foreground">unnamed</span>
                )}
              </CardTitle>
              <CardDescription className="mt-1 truncate text-xs">
                {listing.industry ?? "industry —"}
                {listing.location ? ` · ${listing.location}` : ""}
              </CardDescription>
            </div>
            <div className="flex flex-col items-end gap-1">
              <div className="flex items-center gap-2">
                <ComparePin listingId={listing.id} variant="compact" />
                <StatusBadge status={listing.status} />
              </div>
              <FitBadge band={listing.fit_band} summary={listing.fit_summary} />
            </div>
          </div>
        </CardHeader>
        <CardContent className="text-sm">
          <dl className="grid grid-cols-2 gap-y-1 text-xs">
            <dt className="text-muted-foreground">Asking</dt>
            <dd className="text-right font-mono">
              {formatMoney(listing.asking_price)}
            </dd>
            <dt className="text-muted-foreground">SDE</dt>
            <dd className="text-right font-mono">{formatMoney(listing.sde)}</dd>
            <dt className="text-muted-foreground">Revenue</dt>
            <dd className="text-right font-mono">
              {formatMoney(listing.revenue)}
            </dd>
          </dl>
          {listing.latest_decision && (
            <p
              className="mt-3 truncate text-[11px] italic text-muted-foreground"
              title={listing.latest_decision.reason}
            >
              {listing.latest_decision.new_status}: {listing.latest_decision.reason}
            </p>
          )}
          <p className="mt-3 text-[11px] text-muted-foreground">
            Added {formatDate(listing.created_at)} · {listing.source}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
