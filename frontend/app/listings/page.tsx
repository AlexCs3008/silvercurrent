export default function ListingsPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Listings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Inventory of ingested deals. Filter, tag, and triage from here.
        </p>
      </div>
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        No listings yet. Ingestion lands in Phase 1.
      </div>
    </div>
  );
}
