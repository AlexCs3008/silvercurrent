# Tasks — currently in flight

*Active phase: **Phase 4 — Email ingestion daemon (pre-work: ADR 0007)***
*Last updated: 2026-05-05 — Phase 3 closed out, moved to `tasks/DONE.md`. Phase 4 opened with an ADR-needed gate.*

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

## Phase 4 — Email ingestion daemon

**Goal**: forwarding broker alert emails into a Silvercurrent inbox lands new listings automatically (charter §6 — "email forward + paste + upload"). The paste/upload paths already work; this slice automates the highest-volume one.

### [ingestion] — pre-work: pick an inbound-email provider (BLOCKING)

- [ ] Mr. Alonso reads `docs/decisions/0007-inbound-email-provider.md` and picks one of: **Postmark Inbound** (webhook, public URL needed), **SendGrid Inbound Parse** (webhook, public URL needed), or **IMAP daemon** (polling against a dedicated mailbox, no public URL).
- [ ] ADR moves from `proposed` to `accepted` with the picked option and the reason. Implementation tasks below get filled in based on the choice.

*(Implementation tasks below are intentionally placeholder — they get scoped concretely after the ADR lands.)*

### [ingestion] — webhook path (if Postmark or SendGrid)

- [ ] Public webhook URL strategy decided (cloudflared / ngrok in dev, a real DNS record + cert in prod).
- [ ] `POST /api/ingest/email` endpoint: accepts the provider's webhook payload, validates the signature, extracts subject + sender + body + attachments.
- [ ] Reuse the existing `extract_listing()` LLM pipeline on the email body. Email-specific extraction tweaks (e.g., parsing broker forwards) handled in the prompt, not as new tools.
- [ ] Persist the new listing with `source="email"` and `source_url=null` (or the broker's listing URL if present in body).
- [ ] Tests: signature validation, happy path against a real recorded payload, malformed payload handling.

### [ingestion] — IMAP path (if IMAP daemon)

- [ ] `scripts/email_ingest_daemon.py` — long-running script that connects via IMAP IDLE to a dedicated mailbox, processes new mail, marks as read, persists.
- [ ] Mailbox credentials in `.env` (or app password for Gmail).
- [ ] Same `extract_listing()` reuse as above.
- [ ] Service supervision strategy decided (Windows Task Scheduler, systemd-style, or run-on-demand).
- [ ] Tests: parse a recorded `.eml` fixture into the same `extract_listing()` call and verify a Listing row.

### [ingestion] — shared

- [ ] Update `docs/getting-started.md` with the email forwarding setup steps once the path is chosen.
- [ ] Add to `TODO-MANUAL.txt` if Mr. Alonso needs to do anything manually (sign up for the provider, configure DNS, generate an app password, etc.).

---

## Backlog (parked, not in flight)

- **Use it for real before more code.** Add 2–3 listings, run analyses, refine `criteria.md` and prompts based on what the Analyst surfaces. Failure modes from real listings beat speculative tuning. The `prompt-tuner` subagent at `.claude/agents/prompt-tuner.md` is built for that loop.
- **Cosmetic cleanup of `sba_sop_50_10_8.md`.** Smart-quote replacement chars (`Lender�s`) survive the docx → md conversion and show up in retrieved passages. Cosmetic, not affecting retrieval. ~30-min fix to remap U+FFFD → likely apostrophe.
- **react-markdown for Deal Sheet rendering** if the custom renderer feels rough once we've used it on more listings. Charter-compatible (it's a UI dep, not a scope expansion).
- **Optimizer agent** — v2 work; only relevant after Mr. Alonso owns a business.
