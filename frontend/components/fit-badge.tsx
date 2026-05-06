import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  FIT_BAND_COLOR,
  FIT_BAND_LABEL,
  type FitBand,
} from "@/lib/listings";

type FitBadgeProps = {
  band: FitBand | null;
  summary?: string | null;
  className?: string;
};

/**
 * Colored pill for a listing's fit-band against `criteria.md`. Hover/title
 * shows the FitResult summary (e.g. "matches 4 of 5 evaluable criteria").
 *
 * Renders nothing when `band` is null — the criteria file isn't loadable or
 * hasn't been parsed yet.
 */
export function FitBadge({ band, summary, className }: FitBadgeProps) {
  if (band === null) return null;
  return (
    <Badge
      variant="secondary"
      className={cn(
        "lowercase tracking-wide",
        FIT_BAND_COLOR[band],
        className,
      )}
      title={summary ?? FIT_BAND_LABEL[band]}
    >
      {FIT_BAND_LABEL[band]}
    </Badge>
  );
}
