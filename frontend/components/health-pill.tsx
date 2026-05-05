"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type HealthStatus = "loading" | "ok" | "error";
type HealthResponse = Record<string, unknown>;

/**
 * Small backend connectivity indicator. Shows a colored dot + label, with the
 * raw JSON response (or error message) revealable on click. Intentionally tiny
 * — the home page is for resources, this is just a discreet "is the backend
 * up?" check that survived from the Phase 0 scaffold.
 */
export function HealthPill() {
  const [status, setStatus] = useState<HealthStatus>("loading");
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

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

  const dotClass =
    status === "loading"
      ? "bg-muted-foreground"
      : status === "ok"
        ? "bg-emerald-500"
        : "bg-destructive";
  const label =
    status === "loading"
      ? "Backend: checking…"
      : status === "ok"
        ? "Backend: ok"
        : "Backend: error";

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full border border-border bg-card/40 px-3 py-1 text-xs hover:bg-card"
      >
        <span aria-hidden className={`inline-block size-2 rounded-full ${dotClass}`} />
        <span className="font-mono">{label}</span>
      </button>
      {open && status === "ok" && data !== null && (
        <pre className="max-w-md overflow-x-auto rounded-md bg-muted p-3 text-[11px] leading-snug">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
      {open && status === "error" && error !== null && (
        <p className="max-w-md rounded-md bg-destructive/10 p-3 text-[11px] text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
