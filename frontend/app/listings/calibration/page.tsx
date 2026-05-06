import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiGet } from "@/lib/api";
import { formatMoney } from "@/lib/listings";

export const dynamic = "force-dynamic";

const REVIEWED_THRESHOLD = 20;

type HistogramBucket = {
  bucket_low: number;
  bucket_high: number | null;
  count: number;
};

type DecisionReason = {
  snippet: string;
  listing_id: string;
  decided_at: string;
  status: string;
};

type Calibration = {
  n_total: number;
  n_reviewed: number;
  status_mix: Record<string, number>;
  fit_band_mix: Record<string, number>;
  sde_histogram: HistogramBucket[];
  asking_histogram: HistogramBucket[];
  source_mix: Record<string, number>;
  broker_top: { name: string; count: number }[];
  time_to_decision_days: { p50: number | null; p90: number | null; n: number };
  decision_reasons: DecisionReason[];
};

export default async function CalibrationPage() {
  let data: Calibration | null = null;
  let error: string | null = null;
  try {
    data = await apiGet<Calibration>("/api/calibration");
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load calibration data.";
  }

  if (error || data === null) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Calibration</h1>
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error ?? "Could not load calibration data."}
        </p>
      </div>
    );
  }

  const insufficientData = data.n_reviewed < REVIEWED_THRESHOLD;

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
          Calibration
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Inventory rollup — distributions and decision patterns. Mirror, not
          advice.
        </p>
      </div>

      {insufficientData && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Not enough data yet</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Calibration is most useful once you&apos;ve reviewed at least{" "}
            <span className="font-medium">{REVIEWED_THRESHOLD}</span> listings.
            You&apos;ve reviewed{" "}
            <span className="font-medium">{data.n_reviewed}</span> so far
            ({data.n_total} total in the inventory). The page below is rendered
            for transparency, but distributions are noisy at this size.
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Status mix</CardTitle>
          </CardHeader>
          <CardContent>
            <CountTable counts={data.status_mix} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Fit-band mix</CardTitle>
          </CardHeader>
          <CardContent>
            <CountTable counts={data.fit_band_mix} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Source mix</CardTitle>
          </CardHeader>
          <CardContent>
            <CountTable counts={data.source_mix} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top brokers</CardTitle>
          </CardHeader>
          <CardContent>
            {data.broker_top.length === 0 ? (
              <p className="text-xs italic text-muted-foreground">
                No brokers listed yet.
              </p>
            ) : (
              <ul className="text-sm">
                {data.broker_top.map((b) => (
                  <li
                    key={b.name}
                    className="flex justify-between border-b border-border py-1 last:border-0"
                  >
                    <span>{b.name}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {b.count}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <HistogramCard
          title="SDE distribution"
          buckets={data.sde_histogram}
        />
        <HistogramCard
          title="Asking-price distribution"
          buckets={data.asking_histogram}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Time to decision (days)</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {data.time_to_decision_days.n === 0 ? (
            <p className="italic text-muted-foreground">
              No decisions logged yet.
            </p>
          ) : (
            <dl className="grid grid-cols-3 gap-y-1">
              <dt className="text-muted-foreground">samples</dt>
              <dd className="col-span-2 font-mono">
                {data.time_to_decision_days.n}
              </dd>
              <dt className="text-muted-foreground">p50</dt>
              <dd className="col-span-2 font-mono">
                {formatDays(data.time_to_decision_days.p50)}
              </dd>
              <dt className="text-muted-foreground">p90</dt>
              <dd className="col-span-2 font-mono">
                {formatDays(data.time_to_decision_days.p90)}
              </dd>
            </dl>
          )}
        </CardContent>
      </Card>

      {data.decision_reasons.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent decision reasons</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-2 text-sm">
              {data.decision_reasons.map((entry, i) => (
                <li
                  key={`${entry.listing_id}-${i}`}
                  className="border-l-2 border-border pl-3"
                >
                  <p className="font-mono text-xs text-muted-foreground">
                    {entry.status} ·{" "}
                    {new Date(entry.decided_at).toLocaleDateString()}
                  </p>
                  <p>{entry.snippet}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function CountTable({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return (
      <p className="text-xs italic text-muted-foreground">No data yet.</p>
    );
  }
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <ul className="flex flex-col gap-1 text-sm">
      {entries.map(([label, count]) => (
        <li key={label} className="flex items-center gap-2">
          <span className="w-20 shrink-0 text-xs text-muted-foreground">
            {label}
          </span>
          <span
            className="h-2 rounded-full bg-foreground/30"
            style={{ width: `${(count / max) * 100}%` }}
            aria-hidden="true"
          />
          <span className="ml-auto font-mono text-xs">{count}</span>
        </li>
      ))}
    </ul>
  );
}

function HistogramCard({
  title,
  buckets,
}: {
  title: string;
  buckets: HistogramBucket[];
}) {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-1 text-xs">
          {buckets.map((b, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="w-32 shrink-0 font-mono text-muted-foreground">
                {formatRange(b.bucket_low, b.bucket_high)}
              </span>
              <span
                className="h-2 rounded-full bg-foreground/30"
                style={{ width: `${(b.count / max) * 100}%` }}
                aria-hidden="true"
              />
              <span className="ml-auto font-mono">{b.count}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function formatRange(low: number, high: number | null): string {
  const lo = formatMoney(low);
  if (high === null) return `${lo}+`;
  return `${lo} – ${formatMoney(high)}`;
}

function formatDays(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(1)} d`;
}
