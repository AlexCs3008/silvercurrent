// Next.js 16: `params` is a Promise and must be awaited.
// See node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/page.md.
type ListingDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ListingDetailPage({
  params,
}: ListingDetailPageProps) {
  const { id } = await params;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Listing <span className="font-mono text-base">{id}</span>
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Detail view placeholder. Deal Sheet rendering lands in Phase 3.
        </p>
      </div>
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        No data wired up yet.
      </div>
    </div>
  );
}
