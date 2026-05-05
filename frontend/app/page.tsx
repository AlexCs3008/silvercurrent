"use client";

import { useEffect, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiGet } from "@/lib/api";

type HealthStatus = "loading" | "ok" | "error";

// The backend `/api/health` shape isn't fully nailed down yet — record-of-unknown
// keeps us honest and lets us pretty-print whatever lands.
type HealthResponse = Record<string, unknown>;

export default function HomePage() {
  const [status, setStatus] = useState<HealthStatus>("loading");
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<HealthResponse>("/api/health")
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setStatus("ok");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Home</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Backend connectivity smoke test. Real Getting Started content will
          render here later from `docs/getting-started.md`.
        </p>
      </div>

      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Backend health</CardTitle>
          <CardDescription>
            Calls <code className="font-mono text-xs">/api/health</code> on
            mount.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <StatusIndicator status={status} />
          {status === "ok" && data !== null && (
            <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
              {JSON.stringify(data, null, 2)}
            </pre>
          )}
          {status === "error" && error !== null && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatusIndicator({ status }: { status: HealthStatus }) {
  const label =
    status === "loading" ? "loading" : status === "ok" ? "ok" : "error";
  const dotClass =
    status === "loading"
      ? "bg-muted-foreground"
      : status === "ok"
        ? "bg-emerald-500"
        : "bg-destructive";

  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        aria-hidden
        className={`inline-block size-2 rounded-full ${dotClass}`}
      />
      <span className="font-mono">{label}</span>
    </div>
  );
}
