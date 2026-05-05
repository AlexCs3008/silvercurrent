# 0007 — Inbound email provider for the ingestion daemon

*Status: proposed · 2026-05-05 · needs Mr. Alonso's pick before implementation starts*

## Context

Charter §6 lists three ingestion paths: **email forward**, **paste**, **upload**. Phase 1 shipped paste and upload. Phase 4 ships email forward — Mr. Alonso forwards a broker alert (BizBuySell saved-search digest, broker blast, etc.) to a dedicated Silvercurrent inbox; a daemon parses the email, runs the existing `extract_listing()` pipeline on the body, and persists a new `Listing` row with `source="email"`.

The ingestion *content* path is solved: the existing LLM extractor already handles arbitrary text. What's undecided is how email arrives at the backend. Three real options.

## Options

### Option A — Postmark Inbound

- Mr. Alonso configures DNS so a domain he controls (e.g., `inbound.silvercurrent.alonso.dev`) MX-points to Postmark.
- He forwards broker emails to e.g. `listings@inbound.silvercurrent.alonso.dev`.
- Postmark POSTs a JSON payload with parsed headers, body (text + html), and attachments to a public webhook URL (`POST /api/ingest/email`).
- Backend validates Postmark's signature, runs the extractor, persists.

**Pros**:
- Postmark's parsing is best-in-class — body comes pre-decoded, attachments base64'd, MIME complexity hidden.
- Free tier (10k inbound emails/month) is generous for a single user's broker forwards.
- Webhook is push, not poll — listings appear within seconds.

**Cons**:
- Requires a **public webhook URL**. In dev this means a tunnel (cloudflared, ngrok). In prod it means deploying the backend with a real DNS record + cert.
- Requires an MX record on a domain Mr. Alonso owns (or accepting Postmark's forwarding domain).
- Third-party dependency — Postmark account, signing key in `.env`.

### Option B — SendGrid Inbound Parse

- Functionally identical to Postmark: MX record → SendGrid → webhook → backend.
- Free tier exists but smaller; UX of the dashboard is rougher.

**Pros / cons**: same shape as Postmark. Postmark wins on developer experience for a hobbyist; SendGrid wins on existing-account scenarios. Mr. Alonso doesn't have an existing SendGrid account, so this option mostly exists for completeness.

### Option C — IMAP daemon

- Mr. Alonso creates a dedicated Gmail (or other IMAP-capable) inbox, e.g. `silvercurrent.alonso@gmail.com`.
- Generates an **app password** (Gmail requires this when 2FA is on).
- A long-running script (`scripts/email_ingest_daemon.py`) connects via IMAP IDLE, watches for new mail, processes each one through `extract_listing()`, marks as read.
- He forwards broker emails to that address.

**Pros**:
- **No public webhook needed.** Stays purely local-first; matches the project's no-Docker / no-cloud ethos (ADR 0005).
- No third-party signup beyond the existing email provider.
- Easy to test offline — feed a `.eml` file directly into the same parser.

**Cons**:
- **Polling daemon adds a second long-running process** alongside `uvicorn` and `pnpm dev`. Mr. Alonso has to remember to start it (and keep it running).
- Service supervision is unsolved on Windows. Options: Windows Task Scheduler, run on-demand from the Anaconda terminal, eventually NSSM. Each adds friction.
- Gmail-specific friction: app password setup, Google occasionally tightens IMAP access for "less secure apps."
- Slight latency: IMAP IDLE is fast in practice, but there's no SLA.

## Decision (NEEDED)

Pick one of A / B / C. The implementation diverges meaningfully:

- A or B → public webhook, signature validation, no daemon process; implies a deploy story sooner.
- C → no webhook, but a second always-on process and Windows supervision question.

**Author's recommendation if forced to pick: Option C (IMAP).** It matches the local-first / single-user ethos. The daemon process is awkward but Mr. Alonso runs `uvicorn` and `pnpm dev` already; a third terminal is a small marginal cost. Postmark only becomes the right answer when the system runs somewhere other than his laptop, and that day isn't here. The "no public webhook needed" property is genuinely valuable until then.

If Mr. Alonso prefers to bake in the deploy story now (so Phase 5+ has a working public surface), **Option A** is the right call.

**Option B is dominated by A** for this use case; included only because charter §6 said "broker alerts via email" and SendGrid is the obvious second option to mention.

## Consequences

- **If A**: dev needs cloudflared/ngrok, `.env` gains `POSTMARK_INBOUND_SIGNATURE_KEY`, new endpoint `POST /api/ingest/email` with signature middleware, `TODO-MANUAL.txt` gains "set up Postmark + DNS." Eventually motivates a hosted deployment.
- **If C**: new `scripts/email_ingest_daemon.py`, `.env` gains `IMAP_HOST` / `IMAP_USER` / `IMAP_APP_PASSWORD`, `TODO-MANUAL.txt` gains "create dedicated Gmail + generate app password." A start-the-daemon step joins the getting-started doc. No new ports or DNS.
- **Either way**: the LLM extractor and `Listing` schema do not change. Email-specific tweaks (parsing forwards, stripping prior-thread context) are handled in the prompt or in pre-processing, not via new tools.
- **Either way**: the `extract_listing()` pipeline already handles arbitrary text, so 80% of the work is plumbing. The decision matters mainly for ops shape.

## What we explicitly skip in v1

- **No multi-account inbox / shared mailbox.** Single user, single inbox, single MX/IMAP target. Multi-tenancy is forbidden by CLAUDE.md hard rule #1.
- **No bidirectional email** (replying to brokers from the agent). Out of scope; would require a different decision and conflicts with the "agents surface, user decides" rule.
- **No image/PDF attachment routing.** If a broker email has a PDF attachment, v1 extracts only the email body. Attachments go through the existing `/api/listings/extract-pdf` upload path manually. Auto-routing attachments is a later enhancement.
- **No email-specific ADR for prompt changes.** The existing `extract_listing()` prompt is generic enough to handle email body text; we only revisit if real broker-forward formats trip it up.
