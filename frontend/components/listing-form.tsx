"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { apiPatch, apiPost, apiPostMultipart } from "@/lib/api";
import {
  LISTING_STATUSES,
  type ExtractionResult,
  type ExtractionUsage,
  type Listing,
  type ListingCreate,
  type ListingStatus,
  type ListingUpdate,
} from "@/lib/listings";

type ListingFormProps = {
  /** When provided, the form is in edit mode and PATCHes this listing. */
  initial?: Listing;
  /** When true, render the URL/text extract panel above the form. */
  enableExtraction?: boolean;
};

type FormState = {
  source: string;
  source_url: string;
  business_name: string;
  industry: string;
  naics_code: string;
  location: string;
  asking_price: string;
  sde: string;
  cash_flow: string;
  revenue: string;
  narrative: string;
  reason_for_selling: string;
  raw_text: string;
  broker_name: string;
  broker_contact: string;
  status: ListingStatus;
  notes: string;
  tags: string;
};

function fromListing(l: Listing | undefined): FormState {
  return {
    source: l?.source ?? "manual",
    source_url: l?.source_url ?? "",
    business_name: l?.business_name ?? "",
    industry: l?.industry ?? "",
    naics_code: l?.naics_code ?? "",
    location: l?.location ?? "",
    asking_price: l?.asking_price?.toString() ?? "",
    sde: l?.sde?.toString() ?? "",
    cash_flow: l?.cash_flow?.toString() ?? "",
    revenue: l?.revenue?.toString() ?? "",
    narrative: l?.narrative ?? "",
    reason_for_selling: l?.reason_for_selling ?? "",
    raw_text: l?.raw_text ?? "",
    broker_name: l?.broker_name ?? "",
    broker_contact: l?.broker_contact ?? "",
    status: l?.status ?? "new",
    notes: l?.notes ?? "",
    tags: (l?.tags ?? []).join(", "),
  };
}

function deriveSource(url: string | null): string {
  if (!url) return "paste";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "url";
  }
}

function applyExtraction(prev: FormState, result: ExtractionResult): FormState {
  const e = result.extracted;
  return {
    ...prev,
    source: deriveSource(result.source_url),
    source_url: result.source_url ?? prev.source_url,
    business_name: e.business_name,
    industry: e.industry ?? "",
    naics_code: e.naics_code ?? "",
    location: e.location ?? "",
    asking_price: e.asking_price?.toString() ?? "",
    sde: e.sde?.toString() ?? "",
    cash_flow: e.cash_flow?.toString() ?? "",
    revenue: e.revenue?.toString() ?? "",
    narrative: e.narrative ?? "",
    reason_for_selling: e.reason_for_selling ?? "",
    raw_text: result.raw_text,
    broker_name: e.broker_name ?? "",
    broker_contact: e.broker_contact ?? "",
    tags: e.tags.join(", "),
    // status stays whatever the user has set (default "new")
  };
}

function toMoney(s: string): number | null {
  const trimmed = s.trim();
  if (trimmed === "") return null;
  const cleaned = trimmed.replace(/[$,\s]/g, "");
  const n = Number(cleaned);
  return Number.isFinite(n) ? Math.round(n) : null;
}

function toNullableString(s: string): string | null {
  const trimmed = s.trim();
  return trimmed === "" ? null : trimmed;
}

function buildPayload(state: FormState): ListingCreate {
  return {
    source: state.source.trim() || "manual",
    source_url: toNullableString(state.source_url),
    business_name: state.business_name.trim(),
    industry: toNullableString(state.industry),
    naics_code: toNullableString(state.naics_code),
    location: toNullableString(state.location),
    asking_price: toMoney(state.asking_price),
    sde: toMoney(state.sde),
    cash_flow: toMoney(state.cash_flow),
    revenue: toMoney(state.revenue),
    narrative: toNullableString(state.narrative),
    reason_for_selling: toNullableString(state.reason_for_selling),
    raw_text: toNullableString(state.raw_text),
    broker_name: toNullableString(state.broker_name),
    broker_contact: toNullableString(state.broker_contact),
    status: state.status,
    notes: toNullableString(state.notes),
    tags: state.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean),
  };
}

/**
 * Form for creating or editing a listing.
 *
 * - If `initial` is omitted, POSTs to `/api/listings` and redirects to the new
 *   listing's detail page.
 * - If `initial` is provided, PATCHes the listing and redirects back to detail.
 */
export function ListingForm({ initial, enableExtraction }: ListingFormProps) {
  const router = useRouter();
  const [state, setState] = useState<FormState>(() => fromListing(initial));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Extract panel state — only used when enableExtraction is true.
  const [extractMode, setExtractMode] = useState<"text" | "url" | "pdf">("text");
  const [extractText, setExtractText] = useState("");
  const [extractUrl, setExtractUrl] = useState("");
  const [extractFile, setExtractFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [lastUsage, setLastUsage] = useState<ExtractionUsage | null>(null);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setState((s) => ({ ...s, [key]: value }));

  async function handleExtract() {
    setExtractError(null);
    if (extractMode === "text" && !extractText.trim()) {
      setExtractError("Paste the listing text first.");
      return;
    }
    if (extractMode === "url" && !extractUrl.trim()) {
      setExtractError("Enter a URL first.");
      return;
    }
    if (extractMode === "pdf" && !extractFile) {
      setExtractError("Choose a PDF first.");
      return;
    }

    setExtracting(true);
    try {
      let result: ExtractionResult;
      let sourceLabel: string | null = null;
      if (extractMode === "pdf") {
        const fd = new FormData();
        fd.append("file", extractFile as File);
        result = await apiPostMultipart<ExtractionResult>(
          "/api/listings/extract-pdf",
          fd,
        );
        sourceLabel = "pdf";
      } else {
        const body =
          extractMode === "text"
            ? { source_text: extractText }
            : { source_url: extractUrl };
        result = await apiPost<ExtractionResult>(
          "/api/listings/extract",
          body,
        );
      }
      setState((prev) => {
        const next = applyExtraction(prev, result);
        return sourceLabel ? { ...next, source: sourceLabel } : next;
      });
      setLastUsage(result.usage);
    } catch (err) {
      setExtractError(
        err instanceof Error ? err.message : "Extraction failed.",
      );
    } finally {
      setExtracting(false);
    }
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    if (!state.business_name.trim()) {
      setError("Business name is required.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = buildPayload(state);
      if (initial) {
        const updatePayload: ListingUpdate = payload;
        const updated = await apiPatch<Listing>(
          `/api/listings/${initial.id}`,
          updatePayload,
        );
        router.push(`/listings/${updated.id}`);
        router.refresh();
      } else {
        const created = await apiPost<Listing>("/api/listings", payload);
        router.push(`/listings/${created.id}`);
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {enableExtraction && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Auto-fill from URL or pasted text
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Pasted text is the reliable path — many aggregator sites block
              automated URL fetches. Review the populated form before saving.
            </p>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex gap-2 text-xs">
              <button
                type="button"
                onClick={() => setExtractMode("text")}
                className={`rounded-full px-3 py-1 uppercase tracking-wide transition ${
                  extractMode === "text"
                    ? "bg-foreground text-background"
                    : "bg-muted text-muted-foreground hover:bg-muted/70"
                }`}
              >
                Paste text
              </button>
              <button
                type="button"
                onClick={() => setExtractMode("url")}
                className={`rounded-full px-3 py-1 uppercase tracking-wide transition ${
                  extractMode === "url"
                    ? "bg-foreground text-background"
                    : "bg-muted text-muted-foreground hover:bg-muted/70"
                }`}
              >
                Paste URL
              </button>
              <button
                type="button"
                onClick={() => setExtractMode("pdf")}
                className={`rounded-full px-3 py-1 uppercase tracking-wide transition ${
                  extractMode === "pdf"
                    ? "bg-foreground text-background"
                    : "bg-muted text-muted-foreground hover:bg-muted/70"
                }`}
              >
                Upload PDF
              </button>
            </div>

            {extractMode === "text" && (
              <Field
                label="Listing text"
                htmlFor="extract_text"
                hint="The broker's description, copied from the page or email."
              >
                <Textarea
                  id="extract_text"
                  rows={6}
                  value={extractText}
                  onChange={(e) => setExtractText(e.target.value)}
                  placeholder="Paste the listing description here…"
                />
              </Field>
            )}
            {extractMode === "url" && (
              <Field
                label="Listing URL"
                htmlFor="extract_url"
                hint="If the fetch fails, switch to paste-text mode and copy the page text in."
              >
                <Input
                  id="extract_url"
                  type="url"
                  value={extractUrl}
                  onChange={(e) => setExtractUrl(e.target.value)}
                  placeholder="https://…"
                />
              </Field>
            )}
            {extractMode === "pdf" && (
              <Field
                label="PDF file"
                htmlFor="extract_pdf"
                hint="Broker teaser or CIM. Scanned/image-only PDFs aren't supported — paste the text instead."
              >
                <Input
                  id="extract_pdf"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(e) =>
                    setExtractFile(e.target.files?.[0] ?? null)
                  }
                  className="cursor-pointer file:mr-3 file:rounded-md file:border file:border-border file:bg-muted file:px-3 file:py-1 file:text-xs file:font-medium hover:file:bg-muted/70"
                />
                {extractFile && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {extractFile.name} ·{" "}
                    {(extractFile.size / 1024).toLocaleString(undefined, {
                      maximumFractionDigits: 1,
                    })}{" "}
                    KB
                  </p>
                )}
              </Field>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                onClick={handleExtract}
                disabled={extracting}
              >
                {extracting ? "Extracting…" : "Extract"}
              </Button>
              {lastUsage && (
                <span className="text-xs text-muted-foreground">
                  Extracted via{" "}
                  <span className="font-mono">{lastUsage.model}</span> ·{" "}
                  {lastUsage.input_tokens.toLocaleString()} in /{" "}
                  {lastUsage.output_tokens.toLocaleString()} out tokens
                </span>
              )}
              {extractError && (
                <span
                  className="text-sm text-red-600 dark:text-red-400"
                  role="alert"
                >
                  {extractError}
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Identity</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Business name" required htmlFor="business_name">
            <Input
              id="business_name"
              value={state.business_name}
              onChange={(e) => update("business_name", e.target.value)}
              required
              placeholder="Acme HVAC"
            />
          </Field>
          <Field label="Industry" htmlFor="industry">
            <Input
              id="industry"
              value={state.industry}
              onChange={(e) => update("industry", e.target.value)}
              placeholder="HVAC services"
            />
          </Field>
          <Field label="Location" htmlFor="location">
            <Input
              id="location"
              value={state.location}
              onChange={(e) => update("location", e.target.value)}
              placeholder="Miami, FL"
            />
          </Field>
          <Field label="NAICS code" htmlFor="naics_code">
            <Input
              id="naics_code"
              value={state.naics_code}
              onChange={(e) => update("naics_code", e.target.value)}
              placeholder="238220"
              maxLength={8}
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Financials</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field
            label="Asking price (USD)"
            htmlFor="asking_price"
            hint="Whole dollars."
          >
            <Input
              id="asking_price"
              inputMode="numeric"
              value={state.asking_price}
              onChange={(e) => update("asking_price", e.target.value)}
              placeholder="1200000"
            />
          </Field>
          <Field label="SDE (USD/yr)" htmlFor="sde">
            <Input
              id="sde"
              inputMode="numeric"
              value={state.sde}
              onChange={(e) => update("sde", e.target.value)}
              placeholder="350000"
            />
          </Field>
          <Field label="Cash flow (USD/yr)" htmlFor="cash_flow">
            <Input
              id="cash_flow"
              inputMode="numeric"
              value={state.cash_flow}
              onChange={(e) => update("cash_flow", e.target.value)}
              placeholder="380000"
            />
          </Field>
          <Field label="Revenue (USD/yr)" htmlFor="revenue">
            <Input
              id="revenue"
              inputMode="numeric"
              value={state.revenue}
              onChange={(e) => update("revenue", e.target.value)}
              placeholder="2400000"
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Narrative</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Field label="Description / pitch" htmlFor="narrative">
            <Textarea
              id="narrative"
              rows={5}
              value={state.narrative}
              onChange={(e) => update("narrative", e.target.value)}
              placeholder="What the broker is saying about the business…"
            />
          </Field>
          <Field label="Reason for selling" htmlFor="reason_for_selling">
            <Input
              id="reason_for_selling"
              value={state.reason_for_selling}
              onChange={(e) => update("reason_for_selling", e.target.value)}
              placeholder="Owner retiring."
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Broker</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Broker name" htmlFor="broker_name">
            <Input
              id="broker_name"
              value={state.broker_name}
              onChange={(e) => update("broker_name", e.target.value)}
              placeholder="Jane Broker"
            />
          </Field>
          <Field
            label="Broker contact"
            htmlFor="broker_contact"
            hint="Email / phone / firm — free-form."
          >
            <Input
              id="broker_contact"
              value={state.broker_contact}
              onChange={(e) => update("broker_contact", e.target.value)}
              placeholder="jane@example.com"
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Source & workflow</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Source" htmlFor="source" hint="e.g. manual, bizbuysell">
            <Input
              id="source"
              value={state.source}
              onChange={(e) => update("source", e.target.value)}
            />
          </Field>
          <Field label="Source URL" htmlFor="source_url">
            <Input
              id="source_url"
              type="url"
              value={state.source_url}
              onChange={(e) => update("source_url", e.target.value)}
              placeholder="https://…"
            />
          </Field>
          <Field label="Status" htmlFor="status">
            <Select
              value={state.status}
              onValueChange={(v) => update("status", v as ListingStatus)}
            >
              <SelectTrigger id="status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LISTING_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field
            label="Tags"
            htmlFor="tags"
            hint="Comma-separated. e.g. fl, service, established"
          >
            <Input
              id="tags"
              value={state.tags}
              onChange={(e) => update("tags", e.target.value)}
            />
          </Field>
          <Field label="Notes" htmlFor="notes" className="md:col-span-2">
            <Textarea
              id="notes"
              rows={4}
              value={state.notes}
              onChange={(e) => update("notes", e.target.value)}
              placeholder="Your running notes — questions to ask, gut takes…"
            />
          </Field>
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : initial ? "Save changes" : "Create listing"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => router.back()}
          disabled={submitting}
        >
          Cancel
        </Button>
      </div>
      </form>
    </div>
  );
}

type FieldProps = {
  label: string;
  htmlFor: string;
  required?: boolean;
  hint?: string;
  className?: string;
  children: React.ReactNode;
};

function Field({ label, htmlFor, required, hint, className, children }: FieldProps) {
  return (
    <div className={`flex flex-col gap-1.5 ${className ?? ""}`}>
      <Label htmlFor={htmlFor}>
        {label}
        {required && <span className="ml-1 text-red-600">*</span>}
      </Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
