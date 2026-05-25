import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FitBadge } from "@/components/fit-badge";
import { HealthPill } from "@/components/health-pill";
import { StatusBadge } from "@/components/status-badge";
import { apiGet } from "@/lib/api";
import {
  FIT_BANDS,
  LISTING_STATUSES,
  formatDate,
  formatMoney,
  type FitBand,
  type Listing,
  type ListingStatus,
} from "@/lib/listings";

export const dynamic = "force-dynamic";

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
  decision_reasons: DecisionReason[];
};

type ResourceLink = {
  title: string;
  href: string;
  description: string;
  /** Short label shown next to the title — e.g. "general", "online", "FL". */
  tag?: string;
};

const LISTING_SOURCES: ResourceLink[] = [
  {
    title: "BizBuySell",
    href: "https://www.bizbuysell.com/",
    description:
      "Biggest US small-business aggregator. Strong financial disclosure on most listings — asking, SDE, cash flow, narrative all on one page. Filter by state, industry, SDE band.",
    tag: "general",
  },
  {
    title: "BusinessesForSale.com",
    href: "https://us.businessesforsale.com/",
    description:
      "Second-largest aggregator. Similar shape to BizBuySell, sometimes lists deals the others don't. Worth checking as a second pass.",
    tag: "general",
  },
  {
    title: "BizQuest",
    href: "https://www.bizquest.com/",
    description:
      "Older aggregator. Smaller inventory but occasionally has unique listings from regional brokers who don't post elsewhere.",
    tag: "general",
  },
  {
    title: "Sunbelt Business Network",
    href: "https://www.sunbeltnetwork.com/",
    description:
      "Largest US business-broker network with strong Florida coverage. Browse by office; many of the listings hit your geography target.",
    tag: "FL",
  },
  {
    title: "Quiet Light Brokerage",
    href: "https://quietlight.com/",
    description:
      "Online businesses, vetted before listing. Asking range typically $1M+. Higher disclosure quality than aggregators; CIMs available on request.",
    tag: "online",
  },
  {
    title: "Empire Flippers",
    href: "https://empireflippers.com/",
    description:
      "Online businesses, vetted, mid-market. Public listings show traffic and earnings. Earnest-money required to unlock URL — filters tire-kickers.",
    tag: "online",
  },
  {
    title: "DealStream",
    href: "https://www.dealstream.com/",
    description:
      "Lower middle market, broker-listed. Some deals overlap with BizBuySell; some don't. Free account required to see contact info on most listings.",
    tag: "mid-market",
  },
];

const TOOLS_AND_REFERENCES: ResourceLink[] = [
  {
    title: "NAICS code lookup",
    href: "https://www.naics.com/search/",
    description:
      "Find the industry classification code for a target. NAICS codes drive SBA size standards and are how the Operator's KB indexes industry-specific guidance.",
  },
  {
    title: "Sunbiz — Florida business entity search",
    href: "https://search.sunbiz.org/Inquiry/CorporationSearch/ByName",
    description:
      "Florida Department of State's official business registry. Confirm a target is actually registered, see officers, filing history, and registered agent.",
    tag: "FL",
  },
  {
    title: "SBA Lender Match",
    href: "https://www.sba.gov/funding-programs/loans/lender-match",
    description:
      "SBA's official tool to find a 7(a) lender. Fill out a short form, get matched with banks that fund acquisitions in your size band and industry.",
  },
  {
    title: "IRS Business Expense Resources",
    href: "https://www.irs.gov/forms-pubs/guide-to-business-expense-resources",
    description:
      "Successor hub to the discontinued Pub 535. Use as the authoritative reference when scrutinizing addbacks: ordinary-and-necessary, capitalization, owner compensation.",
  },
  {
    title: "SBA SOP 50 10 — Lender and CDC Loan Programs",
    href: "https://www.sba.gov/document/sop-50-10-lender-development-company-loan-programs",
    description:
      "The official SBA 7(a) and 504 rulebook. Eligibility, use of proceeds, fees, change-of-ownership rules. Already indexed in the Operator's knowledge base.",
  },
  {
    title: "Fed SMB Credit Survey",
    href: "https://www.fedsmallbusiness.org/",
    description:
      "Annual Federal Reserve report on small-business credit access, lender behavior, and financial health. Useful for market context when evaluating financing risk.",
  },
];

export default async function HomePage() {
  const [calibration, listings] = await Promise.all([
    apiGet<Calibration>("/api/calibration").catch(() => null),
    apiGet<Listing[]>("/api/listings").catch(() => [] as Listing[]),
  ]);

  const recentListings = [...listings]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
    .slice(0, 4);

  const recentDecisions = calibration?.decision_reasons.slice(0, 4) ?? [];

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Silvercurrent</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Personal cockpit for evaluating small-business acquisitions.
          </p>
        </div>
        <HealthPill />
      </div>

      <Cockpit
        calibration={calibration}
        recentListings={recentListings}
        recentDecisions={recentDecisions}
      />

      <Section
        title="Where to find listings"
        subtitle="Broker aggregators and vetted marketplaces. URL fetch is blocked on most aggregators (anti-bot defenses) — use copy/paste or PDF upload to ingest."
        items={LISTING_SOURCES}
      />

      <Section
        title="Tools & references"
        subtitle="External utilities and canonical references that complement the agents."
        items={TOOLS_AND_REFERENCES}
      />
    </div>
  );
}

function Cockpit({
  calibration,
  recentListings,
  recentDecisions,
}: {
  calibration: Calibration | null;
  recentListings: Listing[];
  recentDecisions: DecisionReason[];
}) {
  const total = calibration?.n_total ?? recentListings.length;
  const statusMix = calibration?.status_mix ?? {};
  const fitMix = calibration?.fit_band_mix ?? {};

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Inventory</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {total === 0
              ? "No listings yet."
              : `${total} listing${total === 1 ? "" : "s"} in the cockpit.`}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/listings/new"
            className="rounded-md bg-foreground px-3 py-1.5 text-xs font-medium text-background transition-opacity hover:opacity-90"
          >
            Add listing
          </Link>
          <Link
            href="/listings"
            className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
          >
            View inventory
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">By status</CardTitle>
            <CardDescription className="text-xs">
              Click a status to filter the inventory.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {LISTING_STATUSES.map((s) => (
                <StatusChip
                  key={s}
                  status={s}
                  count={statusMix[s] ?? 0}
                />
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">By fit</CardTitle>
            <CardDescription className="text-xs">
              Fit-to-criteria from <span className="font-mono">criteria.md</span>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {FIT_BANDS.map((band) => (
                <FitChip key={band} band={band} count={fitMix[band] ?? 0} />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {(recentListings.length > 0 || recentDecisions.length > 0) && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Recently added</CardTitle>
            </CardHeader>
            <CardContent>
              {recentListings.length === 0 ? (
                <p className="text-xs italic text-muted-foreground">
                  Nothing yet.
                </p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {recentListings.map((l) => (
                    <li key={l.id}>
                      <Link
                        href={`/listings/${l.id}`}
                        className="flex items-start justify-between gap-3 rounded-md px-2 py-1.5 -mx-2 transition-colors hover:bg-muted"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">
                            {l.business_name || (
                              <span className="italic text-muted-foreground">
                                unnamed
                              </span>
                            )}
                          </p>
                          <p className="truncate text-[11px] text-muted-foreground">
                            {l.industry ?? "industry —"}
                            {" · "}
                            {formatMoney(l.asking_price)}
                            {" · "}
                            {formatDate(l.created_at)}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-1">
                          <StatusBadge status={l.status} />
                          {l.fit_band && (
                            <FitBadge
                              band={l.fit_band}
                              summary={l.fit_summary}
                            />
                          )}
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Recent decisions</CardTitle>
            </CardHeader>
            <CardContent>
              {recentDecisions.length === 0 ? (
                <p className="text-xs italic text-muted-foreground">
                  No decision-journal entries yet. They appear when you change a
                  listing's status with a written reason.
                </p>
              ) : (
                <ul className="flex flex-col gap-2 text-sm">
                  {recentDecisions.map((d, i) => (
                    <li
                      key={`${d.listing_id}-${i}`}
                      className="border-l-2 border-border pl-3"
                    >
                      <Link
                        href={`/listings/${d.listing_id}`}
                        className="block hover:underline"
                      >
                        <p className="font-mono text-[11px] text-muted-foreground">
                          {d.status} ·{" "}
                          {new Date(d.decided_at).toLocaleDateString()}
                        </p>
                        <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed">
                          {d.snippet}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  );
}

function StatusChip({
  status,
  count,
}: {
  status: ListingStatus;
  count: number;
}) {
  const dim = count === 0;
  return (
    <Link
      href={`/listings?status=${status}`}
      className={
        "inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] uppercase tracking-wide transition-colors " +
        (dim
          ? "bg-muted/40 text-muted-foreground/60 hover:bg-muted"
          : "bg-muted text-foreground hover:bg-muted/70")
      }
    >
      <span>{status}</span>
      <span className="font-mono text-foreground/80">{count}</span>
    </Link>
  );
}

function FitChip({ band, count }: { band: FitBand; count: number }) {
  const dim = count === 0;
  // Fit-filter not implemented in the listings page yet — render as static
  // pills. If/when a fit filter ships, wrap in Link and key off ?fit=.
  return (
    <span
      className={
        "inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] lowercase tracking-wide " +
        (dim ? "bg-muted/40 text-muted-foreground/60" : "bg-muted text-foreground")
      }
    >
      <span>{band}</span>
      <span className="font-mono text-foreground/80">{count}</span>
    </span>
  );
}

function Section({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle: string;
  items: ResourceLink[];
}) {
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{subtitle}</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <ResourceCard key={item.href} item={item} />
        ))}
      </div>
    </section>
  );
}

function ResourceCard({ item }: { item: ResourceLink }) {
  return (
    <a
      href={item.href}
      target="_blank"
      rel="noopener noreferrer"
      className="block transition-colors hover:bg-card/60"
    >
      <Card className="h-full">
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-sm">{item.title}</CardTitle>
            {item.tag && (
              <span className="shrink-0 rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                {item.tag}
              </span>
            )}
          </div>
          <CardDescription className="text-xs">
            {new URL(item.href).hostname.replace(/^www\./, "")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {item.description}
          </p>
        </CardContent>
      </Card>
    </a>
  );
}
