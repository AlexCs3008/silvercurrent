import Link from "next/link";
import { notFound } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ListingActions } from "@/components/listing-actions";
import { ApiError, apiGet } from "@/lib/api";
import { formatDate, formatMoney, type Listing } from "@/lib/listings";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ListingDetailPage({ params }: PageProps) {
  const { id } = await params;

  let listing: Listing;
  try {
    listing = await apiGet<Listing>(`/api/listings/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/listings"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          ← Back to listings
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">
          {listing.business_name || (
            <span className="italic text-muted-foreground">unnamed</span>
          )}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {listing.industry ?? "industry —"}
          {listing.location ? ` · ${listing.location}` : ""}
        </p>
      </div>

      <ListingActions listing={listing} />

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Financials</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <Row label="Asking price" value={formatMoney(listing.asking_price)} />
              <Row label="SDE" value={formatMoney(listing.sde)} />
              <Row label="Cash flow" value={formatMoney(listing.cash_flow)} />
              <Row label="Revenue" value={formatMoney(listing.revenue)} />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Identity</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
              <Row label="Industry" value={listing.industry ?? "—"} />
              <Row label="NAICS" value={listing.naics_code ?? "—"} />
              <Row label="Location" value={listing.location ?? "—"} />
              <Row label="Source" value={listing.source} />
              {listing.source_url && (
                <Row
                  label="Source URL"
                  value={
                    <a
                      href={listing.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 underline-offset-2 hover:underline dark:text-blue-400"
                    >
                      {listing.source_url}
                    </a>
                  }
                />
              )}
            </dl>
          </CardContent>
        </Card>
      </div>

      {(listing.narrative || listing.reason_for_selling) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Narrative</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            {listing.reason_for_selling && (
              <p>
                <span className="text-muted-foreground">Reason for selling: </span>
                {listing.reason_for_selling}
              </p>
            )}
            {listing.narrative && (
              <p className="whitespace-pre-wrap leading-relaxed">
                {listing.narrative}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {(listing.broker_name || listing.broker_contact) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Broker</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {listing.broker_name && <p>{listing.broker_name}</p>}
            {listing.broker_contact && (
              <p className="mt-1 text-muted-foreground">{listing.broker_contact}</p>
            )}
          </CardContent>
        </Card>
      )}

      {listing.notes && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {listing.notes}
            </p>
          </CardContent>
        </Card>
      )}

      {listing.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {listing.tags.map((tag) => (
            <Badge key={tag} variant="outline">
              {tag}
            </Badge>
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Added {formatDate(listing.created_at)} · last updated{" "}
        {formatDate(listing.updated_at)}
      </p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-mono md:text-left md:font-sans">{value}</dd>
    </>
  );
}
