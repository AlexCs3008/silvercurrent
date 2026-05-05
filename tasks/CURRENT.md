# Tasks — currently in flight

*Active phase: **Phase 1c — PDF upload + extraction***
*Last updated: 2026-05-05 — solo session*

---

## How this file works

This is the durable working-memory record of what's actively being built. Conventions:

- Every task carries a scope tag in brackets: `[infra]`, `[backend]`, `[frontend]`, `[ingestion]`, `[knowledge]`, `[router]`, `[operator]`, `[analyst]`, `[optimizer]`.
- Subtasks are nested checkboxes. Mark them complete as you go.
- When a top-level task is fully done, move the whole entry (with its completed subtasks) to `tasks/DONE.md` (append-only).
- When new work emerges that isn't urgent, drop it into `tasks/BACKLOG.md` instead of cluttering this file.
- If you're working in an agent_teams session, the team lead owns this file. Teammates only update the subtasks under their own scope tag.

---

## Phase 1c — PDF upload + extraction

**Goal**: drop a broker teaser or CIM PDF onto `/listings/new`, get the same auto-filled form as Phase 1b. Reuses the `extract_listing()` pipeline; only the parsing layer is new.

**Done when**: user uploads a real PDF, parser extracts text, Sonnet 4.6 returns a populated form, save works end-to-end.

### [backend] — PDF parser + endpoint

- [x] Add `pymupdf` (1.27.x) and `python-multipart` (0.0.27) deps.
- [x] `silvercurrent/ingestion/pdfs.py` — `extract_text_from_pdf(content: bytes) -> str` and `PDFParseError`. Joins page text with `\n\n` separators. Rejects sparse text (< 200 chars) as likely scanned/image-only with a "paste text instead" hint. No OCR.
- [x] `Settings.pdf_max_bytes = 20_000_000` (20 MB cap).
- [x] `POST /api/listings/extract-pdf` — multipart upload (`file` field via `Annotated[UploadFile, File()]`). 0-byte → 400, over-cap → 413, parse failure → 400, ExtractionError → 502. Reuses `extract_listing()` so the response shape is identical to `/extract`.
- [x] 10 tests: parser unit tests (single page, multi-page, garbage bytes, sparse text), endpoint tests (happy path with mocked Anthropic, empty file 400, over-cap 413, garbage 400, scanned 400). Tests synthesize PDFs in-memory via `pymupdf.open()` + `insert_textbox()` — no fixture files committed.
- [x] Gates: pytest (36 pass total), ruff check + format, mypy --strict (26 source files) — all green.

### [frontend] — PDF upload tab

- [x] `apiPostMultipart<T>(path, formData)` helper in `lib/api.ts`. Lets the browser set `Content-Type` with the boundary.
- [x] `ListingForm` extract panel grows a third tab: **Upload PDF**. File `<Input type="file">` with `accept="application/pdf"`, shows filename + size after selection. On Extract, builds `FormData`, POSTs to `/api/listings/extract-pdf`, populates form same as text/URL modes. PDF source labeled `"pdf"` (not `"paste"`).
- [x] Gates: pnpm lint, pnpm build — green.

### Closeout

- [ ] **Live smoke** with a real broker PDF (~$0.05): drop a PDF, verify auto-fill, save, view detail.
- [ ] Session note `docs/sessions/2026-05-05-phase-1c-pdf.md`.
- [ ] Move Phase 1c to `tasks/DONE.md`.

---

## What comes after Phase 1c

- **Phase 2 — Operator agent + global chat.** Pivot to the conversational surface. Curate Operator KB sources, embed into Chroma, write router + operator prompts/tools, build the global chat panel.
- **Phase 3 — Analyst agent + Deal Sheet + "Run Analysis" button.** First place `docs/criteria.md` is read; user fills it before this phase starts.
- **Phase 4 — Email ingestion.**
