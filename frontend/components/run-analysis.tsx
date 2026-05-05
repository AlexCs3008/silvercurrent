"use client";

import { useState } from "react";

import { DealSheetView } from "@/components/deal-sheet-view";
import { Button } from "@/components/ui/button";
import { ApiError, apiPost } from "@/lib/api";
import { type AnalyzeResponse, type DealSheet } from "@/lib/analyze";

type RunAnalysisProps = {
  listingId: string;
  initialSheets: DealSheet[];
};

export function RunAnalysis({ listingId, initialSheets }: RunAnalysisProps) {
  const [sheets, setSheets] = useState<DealSheet[]>(initialSheets);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (pending) return;
    setError(null);
    setPending(true);
    try {
      const response = await apiPost<AnalyzeResponse>(
        `/api/analyze/${listingId}`,
        {},
      );
      setSheets((prev) => [response.deal_sheet, ...prev]);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Backend returned ${err.status}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Run Analysis failed.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Deal sheets</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Run the Analyst against this listing to produce a structured Deal
            Sheet — fit against criteria, computed multiples, an SBA financing
            scenario, and open diligence questions.
          </p>
        </div>
        <Button type="button" onClick={run} disabled={pending}>
          {pending ? "Running…" : "Run Analysis"}
        </Button>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <p className="font-medium">Run Analysis failed.</p>
          <p className="mt-1 font-mono text-xs">{error}</p>
        </div>
      )}

      {pending && sheets.length === 0 && (
        <div className="rounded-lg border border-border bg-card/30 p-6 text-center text-sm text-muted-foreground">
          Analyst is running — first pass usually takes 10–25 seconds.
        </div>
      )}

      {sheets.length === 0 && !pending && !error && (
        <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          No analyses yet. Click <span className="font-medium">Run Analysis</span> to produce one.
        </div>
      )}

      {sheets.length > 0 && (
        <div className="flex flex-col gap-3">
          {sheets.map((sheet, i) => (
            <DealSheetView key={sheet.id} sheet={sheet} defaultOpen={i === 0} />
          ))}
        </div>
      )}
    </div>
  );
}
