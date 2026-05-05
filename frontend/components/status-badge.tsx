import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { STATUS_COLOR, type ListingStatus } from "@/lib/listings";

type StatusBadgeProps = {
  status: ListingStatus;
  className?: string;
};

/** Colored pill for a listing's workflow status. */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="secondary"
      className={cn("uppercase tracking-wide", STATUS_COLOR[status], className)}
    >
      {status}
    </Badge>
  );
}
