import Link from "next/link";
import { notFound } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { ChatPanel } from "@/components/chat-panel";
import { ComparePin } from "@/components/compare-pin";
import { DocumentList } from "@/components/document-list";
import { DocumentUpload } from "@/components/document-upload";
import { FitBadge } from "@/components/fit-badge";
import { ListingActions } from "@/components/listing-actions";
import { RunAnalysis } from "@/components/run-analysis";
import { StatusBadge } from "@/components/status-badge";
import { type DealSheet } from "@/lib/analyze";
import { ApiError, apiGet } from "@/lib/api";
import { type ChatTurn } from "@/lib/chat";
import { type DecisionJournalEntry } from "@/lib/decisions";
import { type ListingDocument } from "@/lib/documents";
import { formatDate, formatMoney, type Listing } from "@/lib/listings";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ListingDetailPage({ params }: PageProps) {
  const { id } = await params;
  const scope = `listing:${id}`;

  let listing: Listing;
  try {
    listing = await apiGet<Listing>(`/api/listings/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  // Fetch listing-scoped chat history, decisions, documents, and prior Deal
  // Sheets in parallel. Failures degrade gracefully — the affected panel just
  // shows an empty/error state.
  const [chatResult, decisionsResult, documentsResult, sheetsResult] =
    await Promise.allSettled([
      apiGet<ChatTurn[]>(`/api/chat?scope=${encodeURIComponent(scope)}`),
      apiGet<DecisionJournalEntry[]>(`/api/listings/${id}/decisions`),
      apiGet<ListingDocument[]>(`/api/listings/${id}/documents`),
      apiGet<DealSheet[]>(`/api/analyze/${id}`),
    ]);

  const initialTurns: ChatTurn[] =
    chatResult.status === "fulfilled" ? chatResult.value : [];
  const chatError: string | null =
    chatResult.status === "rejected" ? describeError(chatResult.reason) : null;

  const decisions: DecisionJournalEntry[] =
    decisionsResult.status === "fulfilled" ? decisionsResult.value : [];
  const documents: ListingDocument[] =
    documentsResult.status === "fulfilled" ? documentsResult.value : [];

  const initialSheets: DealSheet[] =
    sheetsResult.status === "fulfilled" ? sheetsResult.value : [];
  const sheetsError: string | null =
    sheetsResult.status === "rejected"
      ? describeError(sheetsResult.reason)
      : null;

  return (
    <div className="flex flex-col gap-6">
      <Header listing={listing} />

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="documents">
            Documents
            {documents.length > 0 && (
              <span className="ml-1.5 rounded-full bg-muted px-1.5 text-[10px] font-mono text-muted-foreground">
                {documents.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="analysis">
            Analysis
            {initialSheets.length > 0 && (
              <span className="ml-1.5 rounded-full bg-muted px-1.5 text-[10px] font-mono text-muted-foreground">
                {initialSheets.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="chat">
            Chat
            {initialTurns.length > 0 && (
              <span className="ml-1.5 rounded-full bg-muted px-1.5 text-[10px] font-mono text-muted-foreground">
                {Math.floor(initialTurns.length / 2)}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <OverviewTab listing={listing} decisions={decisions} />
        </TabsContent>

        <TabsContent value="documents" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Documents</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <DocumentUpload listingId={id} />
              <DocumentList listingId={id} documents={documents} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="mt-4">
          {sheetsError ? (
            <div
              role="alert"
              className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
            >
              <p className="font-medium">Couldn’t load prior analyses.</p>
              <p className="mt-1 font-mono text-xs">{sheetsError}</p>
            </div>
          ) : (
            <RunAnalysis listingId={id} initialSheets={initialSheets} />
          )}
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          <div className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              The Router classifies each message and dispatches to the Analyst
              (this deal) or the Operator (general ETA mechanics).
            </p>
            {chatError ? (
              <div
                role="alert"
                className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
              >
                <p className="font-medium">Couldn’t load chat history.</p>
                <p className="mt-1 font-mono text-xs">{chatError}</p>
              </div>
            ) : (
              <div className="h-[36rem]">
                <ChatPanel
                  scope={scope}
                  initialTurns={initialTurns}
                  variant="listing"
                />
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Header({ listing }: { listing: Listing }) {
  return (
    <div className="flex flex-col gap-4">
      <Link
        href="/listings"
        className="self-start text-xs text-muted-foreground hover:text-foreground"
      >
        ← Back to listings
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              {listing.business_name || (
                <span className="italic text-muted-foreground">unnamed</span>
              )}
            </h1>
            <StatusBadge status={listing.status} />
            <FitBadge band={listing.fit_band} summary={listing.fit_summary} />
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {listing.industry ?? "industry —"}
            {listing.location ? ` · ${listing.location}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ListingActions listing={listing} />
          <ComparePin listingId={listing.id} variant="full" />
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-lg border border-border bg-card/30 px-4 py-3 text-sm md:grid-cols-4">
        <StatBlock label="Asking" value={formatMoney(listing.asking_price)} />
        <StatBlock label="SDE" value={formatMoney(listing.sde)} />
        <StatBlock label="Cash flow" value={formatMoney(listing.cash_flow)} />
        <StatBlock label="Revenue" value={formatMoney(listing.revenue)} />
      </dl>
    </div>
  );
}

function StatBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="font-mono text-base">{value}</dd>
    </div>
  );
}

function OverviewTab({
  listing,
  decisions,
}: {
  listing: Listing;
  decisions: DecisionJournalEntry[];
}) {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Identity</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
            <Row label="Industry" value={listing.industry ?? "—"} />
            <Row label="NAICS" value={listing.naics_code ?? "—"} />
            <Row label="Location" value={listing.location ?? "—"} />
            <Row label="Source" value={listing.source} />
            {listing.source_url && (
              <Row
                label="Source URL"
                value={
                  <a
                    href={listing.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 underline-offset-2 hover:underline dark:text-blue-400"
                  >
                    {listing.source_url}
                  </a>
                }
              />
            )}
          </dl>
        </CardContent>
      </Card>

      {(listing.narrative || listing.reason_for_selling) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Narrative</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            {listing.reason_for_selling && (
              <p>
                <span className="text-muted-foreground">Reason for selling: </span>
                {listing.reason_for_selling}
              </p>
            )}
            {listing.narrative && (
              <p className="max-w-prose whitespace-pre-wrap leading-relaxed">
                {listing.narrative}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {(listing.broker_name || listing.broker_contact) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Broker</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {listing.broker_name && <p>{listing.broker_name}</p>}
            {listing.broker_contact && (
              <p className="mt-1 text-muted-foreground">{listing.broker_contact}</p>
            )}
          </CardContent>
        </Card>
      )}

      {listing.notes && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="max-w-prose whitespace-pre-wrap text-sm leading-relaxed">
              {listing.notes}
            </p>
          </CardContent>
        </Card>
      )}

      {listing.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {listing.tags.map((tag) => (
            <Badge key={tag} variant="outline">
              {tag}
            </Badge>
          ))}
        </div>
      )}

      {decisions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Decision history</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-2 text-sm">
              {decisions.map((entry) => (
                <li
                  key={entry.id}
                  className="border-l-2 border-border pl-3 leading-relaxed"
                >
                  <p>
                    <span className="font-mono text-xs text-muted-foreground">
                      {entry.previous_status ?? "—"} → {entry.new_status}
                    </span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {formatDate(entry.created_at)}
                    </span>
                  </p>
                  <p className="mt-1">{entry.reason}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground">
        Added {formatDate(listing.created_at)} · last updated{" "}
        {formatDate(listing.updated_at)}
      </p>
    </div>
  );
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) return `Backend returned ${err.status}`;
  if (err instanceof Error) return err.message;
  return "Unknown error";
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-mono md:text-left md:font-sans">{value}</dd>
    </>
  );
}
