import { ListingForm } from "@/components/listing-form";

export default function NewListingPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Add listing</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manual entry. URL paste and PDF upload land in Phase 1b.
        </p>
      </div>
      <ListingForm />
    </div>
  );
}
