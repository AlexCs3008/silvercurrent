import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { HealthPill } from "@/components/health-pill";

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

export default function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Silvercurrent</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Personal cockpit for evaluating small-business acquisitions. Source
            a listing from one of the broker aggregators below, paste or upload
            it via{" "}
            <span className="font-mono text-foreground">/listings/new</span>,
            then open the listing to run the Analyst and chat about it.
          </p>
        </div>
        <HealthPill />
      </div>

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
