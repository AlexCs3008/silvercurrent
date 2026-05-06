"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { type DealSheet } from "@/lib/analyze";
import {
  parseDealSheetSections,
  renderBoldOnly,
  type DealSheetSection,
} from "@/lib/deal-sheet";

type DealSheetViewProps = {
  sheet: DealSheet;
  /** First sheet in a list opens expanded; older ones collapse. */
  defaultOpen?: boolean;
};

/**
 * Renders one persisted Deal Sheet.
 *
 * The Analyst writes Deal Sheets with a fixed seven-section structure
 * (### Snapshot, ### Hard knockouts, ### Numeric fit, ### Computed metrics,
 * ### Qualitative signals, ### Open questions, ### Recommendation). We split
 * on `### ` and render each section in its own block; bodies use
 * `whitespace-pre-wrap` so lists and indentation survive without a markdown
 * dep. Inline `**bold**` is the only lightweight inline transform applied.
 */
export function DealSheetView({ sheet, defaultOpen = false }: DealSheetViewProps) {
  const [open, setOpen] = useState(defaultOpen);
  const sections = parseDealSheetSections(sheet.markdown);
  const created = new Date(sheet.created_at);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <p className="text-sm font-medium">
            {created.toLocaleString()}
          </p>
          <p className="text-[11px] text-muted-foreground">
            <span className="font-mono">{sheet.model}</span> ·{" "}
            {sheet.input_tokens.toLocaleString()} in /{" "}
            {sheet.output_tokens.toLocaleString()} out tokens ·{" "}
            {sheet.iterations} iteration{sheet.iterations === 1 ? "" : "s"}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? "Collapse" : "Expand"}
        </Button>
      </CardHeader>
      {open && (
        <CardContent className="flex flex-col gap-4">
          {sections.length === 0 ? (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
              {sheet.markdown}
            </pre>
          ) : (
            sections.map((section, i) => (
              <Section key={i} title={section.title} body={section.body} />
            ))
          )}
        </CardContent>
      )}
    </Card>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
      <div
        className="whitespace-pre-wrap text-sm leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderBoldOnly(body.trim()) }}
      />
    </div>
  );
}

// Re-export for callers that still imported the inline name (none today, but
// safe). Helpers themselves live in `@/lib/deal-sheet`.
export type { DealSheetSection };
