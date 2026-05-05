# Getting started with Silvercurrent

*Rendered on the home screen. The first thing you (or anyone you show this to) sees.*

---

## What this is

Silvercurrent is your personal cockpit for finding, screening, and analyzing small businesses to acquire. It is **not** a marketplace, broker, or transaction platform. It's a workbench:

1. Listings flow into your inventory automatically (email forwarding) or by hand (URL paste, PDF upload).
2. You browse, filter, tag, and decide what's worth a closer look.
3. When you click **Run Analysis** on a listing, the Analyst agent generates a Deal Sheet — valuation, fit-vs-criteria score, red flags, questions for the broker, financing scenarios.
4. You can chat with the **Operator agent** (general "how to buy" questions) or the **Analyst** (about a specific listing).
5. After you acquire a business, the **Optimizer agent** ingests its operating documents and surfaces improvement opportunities. *(v2 — designed but not yet built.)*

Silvercurrent surfaces information. **You make decisions.**

---

## How to use it in 60 seconds

1. **Set your criteria.** Edit `docs/criteria.md` with your target industry, geography, SDE band, and what kind of business you're looking for. The Analyst agent reads this on every Run Analysis call.
2. **Plug in deal flow.** Set up email alerts on the sites in the *Where to find deals* section below and forward them to your Silvercurrent inbox address.
3. **Browse the inventory.** Open the Listings tab. New listings appear automatically; their default status is `new`.
4. **Screen.** Click into any listing. Read the structured fields and the original snapshot. Click **Run Analysis** if it's worth a deeper look.
5. **Decide.** Mark the listing `passed`, `tracking`, or `LOI` based on the Deal Sheet and your judgment. Use the chat panel for follow-up questions.

---

## How to add a deal

Three paths, all flowing into the same inventory.

### 1. Email forwarding (set this up first — it's the highest-leverage step)

You'll be subscribing to email alerts on the sites listed below anyway. Configure them once to forward to Silvercurrent's inbox address, and listings appear in the inventory without further effort.

The exact forwarding address is set up at install time and printed in your local config. See `docs/decisions/` for the chosen email-ingestion provider once that decision lands.

### 2. URL paste (for ad-hoc finds)

For listings you stumble onto outside your alerts — a broker's site, a LinkedIn post, a tip from a friend:

1. In Silvercurrent, click **Add listing** → **From URL**.
2. Paste the listing URL.
3. The system fetches the page, extracts structured fields, saves a permanent snapshot, and adds it to your inventory.

### 3. PDF upload (for CIMs and teasers)

Once you've expressed interest and signed an NDA, the broker will send a Confidential Information Memorandum — typically 30–80 pages with detailed financials, customer breakdowns, and operating context.

1. Open the corresponding listing (or create one with **Add listing** → **From PDF**).
2. Click **Attach CIM** and drop the PDF.
3. Extraction runs; structured fields update with the deeper detail; the Analyst agent now has the full data set for a thorough Run Analysis pass.

---

## Three things this tool deliberately does NOT do

- **It doesn't buy businesses for you.** You make calls, sign LOIs, write checks. Silvercurrent doesn't move money or send emails to brokers.
- **It doesn't give legal, tax, or financial advice.** For any decision with legal, tax, or financial consequence, talk to the appropriate professional. The Operator agent will explain mechanics; it won't tell you what to do.
- **It doesn't decide for you.** Every output is framed as factors, considerations, scenarios. The "Recommended next action" on a Deal Sheet is about *process* (continue screening / request CIM / pass) — not a verdict on the deal itself.

---

## Where to find deals

See [`docs/deal-sources.md`](./deal-sources.md) for the full curated list — broad aggregators, online-business marketplaces, broker networks, ETA-specific resources, and off-market channels.

For the first month, the recommended starting setup is:

- Set alerts on **BizBuySell**, **BizQuest**, **BusinessesForSale**, and **LoopNet** with your criteria.
- Subscribe to **Searchfunder** and the **Acquiring Minds** podcast.
- Forward all alert emails to your Silvercurrent inbox.

That alone will saturate your screening capacity.
