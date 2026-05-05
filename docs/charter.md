# Silvercurrent — Project Charter

*Version 0.2 · Status: confirmed*
*Source of truth for project scope. Changes to this document require a commit message starting with `charter:` and an explicit reason.*

---

## 1. Thesis

The 2020s–2040s baby-boomer retirement wave is putting an estimated 12M+ US small businesses in play, with most owners lacking succession plans. Buying a profitable, owner-operated business at a 2–4× SDE multiple is one of the most accessible paths to meaningful equity ownership for an individual operator.

The bottleneck for a serious solo searcher isn't capital or appetite — it's **information processing throughput**: reviewing hundreds of listings, doing fast and consistent first-pass analysis, knowing what questions to ask brokers, understanding financing options, and (post-close) operating intelligently.

Silvercurrent is a personal cockpit that automates the information processing so the human can focus on judgment, relationships, and decisions.

## 2. Primary user

One person: the project owner. Silvercurrent is **not** a multi-user product, will not be commercialized, and will not be exposed to the public internet without auth.

This single-user assumption is load-bearing — it justifies skipping auth, billing, multi-tenancy, sharing, RBAC, and most compliance overhead. If that assumption ever changes, the charter must be revised before code is.

## 3. Jobs to be done

Silvercurrent supports four user jobs across the acquisition lifecycle:

1. **Source** — continuously ingest deal flow from email alerts, pasted URLs, and PDF teasers/CIMs into a single searchable inventory.
2. **Screen** — run consistent first-pass analysis on candidate listings so obvious passes get killed in seconds and survivors get attention.
3. **Diligence** — once a listing is a serious candidate, support deep analysis: valuation, projections, risk surfacing, question generation for the broker/seller, financing structure exploration.
4. **Operate** — once a business is acquired, ingest its operating documents and surface improvement opportunities (cost cuts, automation candidates, KPI gaps).

Jobs 1–3 are the v1 focus. Job 4 is designed-for but not built in v1 (see §5).

## 4. The agent system (runtime)

Four runtime agents inside the deployed app. **These are product agents, not Claude Code teammates** — they're called from FastAPI handlers via the Anthropic API.

- **Router** — lightweight; classifies the user's message + current dashboard context and routes to the right specialist. Does not answer substantively itself.
- **Operator agent** — knowledge-base-heavy (RAG over an ETA corpus: legal entity choice, SBA 7(a) mechanics, seller financing, search-fund equity, LOI structure, due diligence checklists, closing flow, transition planning). Answers *how to buy*.
- **Analyst agent** — tool-heavy (valuation calculators, comp lookup, projection modeling, risk scoring). Answers *is this deal good*.
- **Optimizer agent** — document-heavy (ingests P&Ls, vendor lists, org charts, customer concentration data). Surfaces cost cuts and automation candidates. Job 4 — designed in v1, fully built in v2.

Detailed agent specs (system prompts, tools, knowledge sources, guardrails) live in `docs/agents/{name}.md`. The full topology is in `docs/agents/topology.md`.

## 5. MVP scope (in for v1)

- **Ingestion** — email forwarding pipeline (primary), URL paste, PDF upload. LLM-based structured extraction into a normalized `Listing` record.
- **Inventory** — searchable, filterable list of all ingested listings with lightweight tags, status (`new` / `reviewing` / `passed` / `tracking` / `LOI` / `closed`), and notes.
- **Conversation** — chat panel scoped either to a specific listing or to the global knowledge base. Router dispatches to Operator or Analyst.
- **First-pass screen** — *user-triggered* Analyst pass on a listing via a "Run Analysis" button, producing a one-screen Deal Sheet. Manual rather than automatic on ingestion to keep API cost predictable and put the user in control of which listings get analyzed.
- **Operator knowledge base** — curated corpus on ETA mechanics, embedded and queryable.
- **Acquisition criteria document** — your stated criteria (industry, geography, SDE band, ownership transition tolerance, etc.) lives in the repo as `docs/criteria.md` and is injected into every Analyst pass.
- **Home / Getting Started screen** — a landing view inside the dashboard rendered from `docs/getting-started.md` and `docs/deal-sources.md`. Three sections: (1) what Silvercurrent is and how to use it, (2) where to find deals — recommended sites and how to set up email alerts that flow into the inbox pipeline, (3) how to add a deal manually (URL paste, PDF upload). Updates are made by editing markdown, not redeploying UI.

## 6. Non-goals (explicitly OUT for v1)

- Multi-user, auth, billing, sharing, public deployment
- Mobile app or responsive polish
- Scraping aggregator sites (email-forward + paste covers the need)
- Optimizer agent's full build (designed but stubbed)
- Auto-bidding, auto-LOI generation, auto-broker-outreach
- Any transactional/financial action — no money moves through Silvercurrent, ever
- **Advice-giving framing** — Silvercurrent surfaces information and structures analysis; the human decides. Agent prompts must enforce this. No "you should buy this business" outputs.

## 7. Success criteria

Silvercurrent is a success when, within 90 days of v1 launch:

1. Email-forwarded listings appear in the inventory automatically, without manual intervention.
2. The user evaluates at least 50 real listings end-to-end through the system.
3. At least one go/no-go decision on a real deal is made with material support from the system — measurable as: the Deal Sheet surfaced something the user would have missed, or the conversation with the Operator agent answered a question that would otherwise have required a call/Google search/book.
4. The system can be demoed to a friend in 5 minutes and they understand what it does.

## 8. Constraints

- **Builder**: solo, with Claude Code + agent_teams as the primary force multiplier.
- **Stack**: Python 3.12+ / FastAPI / SQLite (dev) → Postgres (when needed) / Next.js 15 / Tailwind / shadcn.
- **LLM budget**: personal API spend. Sonnet 4.6 for most agent calls; Opus 4.7 reserved for Analyst deep-dives and Optimizer document passes; Haiku 4.5 for the Router.
- **Hosting**: local-first (`docker compose up`). A single small VPS is acceptable later for the email ingestion daemon if needed.
- **Time**: weekends + evenings; charter and architecture decisions must be cheap to revisit.

## 9. Risks & mitigations

- **Knowledge-base quality is the project.** A bad RAG corpus turns the Operator agent into a confident bullshitter. *Mitigation*: curate the corpus deliberately; use a small, high-quality set (Stanford Search Fund Primer, *Buy Then Build*, *HBR Guide*, IRS Pub 535, SBA SOP 50 10) before adding volume. Track corpus contents in `docs/knowledge/operator-sources.md`.
- **Agent UX is harder than agent code.** Knowing when to interrupt, when to summarize, when to hand off between agents is the actual hard problem. *Mitigation*: Router agent gets explicit, written-down routing rules in `docs/agents/router.md` that we revise as patterns emerge.
- **Scope creep toward "real product."** Tempting to add auth/sharing/polish. *Mitigation*: every PR that touches `docs/charter.md` requires a commit message starting with `charter:` and an explicit reason.
- **Hallucinated financial analysis.** *Mitigation*: Analyst agent's numerical outputs always come from tool calls (Python calculators), never free-text generation. Prompts enforce "if you don't have a tool result, say so."
- **Prompt injection via ingested content.** Listings, broker emails, and CIMs are external content that may contain hostile instructions. *Mitigation*: ingested content is wrapped in delimiters and explicitly framed as data in agent prompts; documented in `docs/decisions/0002-prompt-injection-defense.md`.

## 10. Working-memory layout

Designed so a fresh Claude Code session — or a teammate spawned by agent_teams with no prior context — can orient itself in under 60 seconds and pick up work without re-asking questions.

```
silvercurrent/
├── CLAUDE.md                          # entry point: how to work in this repo
├── docs/
│   ├── charter.md                     # this document — scope source of truth
│   ├── criteria.md                    # personal acquisition criteria
│   ├── deal-sources.md                # curated list of where to find listings
│   ├── getting-started.md             # how-to-use guide rendered on the home screen
│   ├── agents/
│   │   ├── topology.md                # cross-agent design
│   │   ├── router.md                  # runtime agent specs (one per agent)
│   │   ├── operator.md
│   │   ├── analyst.md
│   │   └── optimizer.md
│   ├── decisions/                     # ADRs, one per significant choice
│   │   └── 0001-fastapi-over-django.md
│   ├── knowledge/                     # RAG corpus inventory
│   │   ├── operator-sources.md
│   │   ├── operator-gaps.md
│   │   ├── analyst-sources.md
│   │   └── analyst-gaps.md
│   └── sessions/                      # one file per working session
│       └── 2026-05-04-charter.md
├── tasks/
│   ├── CURRENT.md                     # in-flight tasks + subtasks, agent-tagged
│   ├── BACKLOG.md                     # not yet picked up
│   └── DONE.md                        # completed, append-only
└── ... (code)
```

### Conventions Claude Code follows

- Read `CLAUDE.md` first, every session. CLAUDE.md points to `docs/charter.md` and `tasks/CURRENT.md`.
- Every task in `tasks/CURRENT.md` carries a scope tag: `[router]`, `[operator]`, `[analyst]`, `[optimizer]`, `[ingestion]`, `[frontend]`, `[infra]`, `[knowledge]`. This is the same tag set agent_teams teammates split work along.
- Subtasks live nested under tasks, with checkbox state. The lead in an agent_teams session keeps `CURRENT.md` accurate; teammates read it but only update their own subtasks.
- Significant architecture choices land as numbered ADRs in `docs/decisions/`. ADR titles are descriptive (`0007-email-ingestion-uses-postmark.md`).
- Each working session ends with a session note in `docs/sessions/YYYY-MM-DD-{topic}.md` summarizing what was decided, what was built, what's open. This is the file a future-you (or Claude Code) reads to remember why a thing exists.
- Agent_teams' own internal task tracking (under `.claude/teams/`) is ephemeral — it doesn't replace `tasks/CURRENT.md`, which is the durable record.

---

## Changelog

- **v0.2** (this version) — Added Home / Getting Started screen to MVP scope (§5); added `docs/deal-sources.md` and `docs/getting-started.md` to working-memory layout (§10); changed first-pass screen from automatic-on-ingestion to user-triggered via "Run Analysis" button (§5); added prompt-injection mitigation row to risks (§9).
- **v0.1** — Initial draft.
