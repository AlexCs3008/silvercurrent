import { ListingForm } from "@/components/listing-form";

export default function NewListingPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Add listing</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Auto-fill from a URL or pasted listing text, or fill the form
          manually below.
        </p>
      </div>
      <ListingForm enableExtraction />
    </div>
  );
}
