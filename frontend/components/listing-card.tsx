import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export type ListingCardData = {
  id: string;
  source: string;
  status: string;
};

type ListingCardProps = {
  listing: ListingCardData;
};

/**
 * Skeleton card for an inventory listing. Real fields land with the data
 * model in Phase 1; this just proves the component layer compiles end-to-end.
 */
export function ListingCard({ listing }: ListingCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-mono text-sm">{listing.id}</CardTitle>
        <CardDescription>
          source: {listing.source} · status: {listing.status}
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        Listing details will render here once the data model is wired up.
      </CardContent>
    </Card>
  );
}
