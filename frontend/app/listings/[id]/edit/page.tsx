import Link from "next/link";
import { notFound } from "next/navigation";

import { ListingForm } from "@/components/listing-form";
import { ApiError, apiGet } from "@/lib/api";
import { type Listing } from "@/lib/listings";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function EditListingPage({ params }: PageProps) {
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
          href={`/listings/${listing.id}`}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          ← Back to listing
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">
          Edit listing
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {listing.business_name}
        </p>
      </div>
      <ListingForm initial={listing} />
    </div>
  );
}
