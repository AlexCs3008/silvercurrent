# 0008 — Parsing conventions for `docs/criteria.md`

*Status: accepted · 2026-05-06*

## Context

`docs/criteria.md` is user-owned (CLAUDE.md hard rule, project-memory note). It captures Mr. Alonso's acquisition criteria — financial bands, industry targets, geography, hard knockouts — and is edited freely as the search reveals what actually matters. Phase 3 fed the file to the Analyst as raw markdown and let the LLM reason over it; the result was that two Deal Sheets for the same listing could disagree on whether a band was "in" or "out", and that the Hard Knockouts section sometimes hallucinated criteria the buyer hadn't written.

The Phase A expansion (fit-ranking) needs a deterministic answer to "is this listing in band, out of band, or undisclosed for each criterion?" — both for the inventory's fit-band badge and for the Deal Sheet to quote verbatim.

Two paths were considered:

1. **Move criteria to a structured config** (YAML, TOML, or front-matter on `criteria.md`). Trivial to parse, but imposes schema on a file the user wants to edit prose-style. Conflicts with the hard rule that this file is user-owned.
2. **Parse the prose heuristically** under known patterns, and silently skip what the parser doesn't recognize. The user keeps writing the file the way they want; the system surfaces `dimensions_evaluated` so it's transparent which dimensions the band reflects.

We picked option 2.

## Decision

`silvercurrent.criteria.parser.parse_criteria(markdown)` reads `criteria.md` and returns a `ParsedCriteria` dataclass. Recognized patterns, all anchored under their parent `## ` heading:

- `## Financial profile`
  - `- **Asking price range**: <dollar low> – <dollar high>`
  - `- **SDE range**: <dollar low> – <dollar high>`
  - `- **Revenue range**: <dollar low> – <dollar high>`
  - `- **Multiple ceiling**: <number>×`
- `## Operating profile`
  - `- **Employee count**: <int low> – <int high>`
  - `- **Years established (minimum)**: <int>+`
  - `- **Recurring revenue %** (minimum): <int>%`
- `## Growth & risk`
  - `- **Customer concentration ceiling**: <int>%` (matched against text containing "largest customer")
- `## Geography`
  - `- **Primary**: <comma-separated locations>`
  - `- **Secondary**: <comma-separated locations>`
  - `- **Hard nos**: <comma-separated locations>`
- `## Industry`
  - `- **Target sectors**: <comma-separated keyword list>`
  - `- **Open to with reservations**: <comma-separated keyword list>`
  - `- **Hard nos**: <comma-separated keyword list>`
- `## Hard knockouts (...)` — bulleted list, each line preserved verbatim. The scorer pattern-matches recognized knockouts (asking-multiple-cap, declining revenue, customer concentration, etc.) and tags each with `HIT` / `PASS` / `NOT_DISCLOSED` / `MANUAL_REVIEW`. Knockouts that aren't auto-evaluable from listing fields are surfaced as `MANUAL_REVIEW` — the user still sees them in the Deal Sheet, but the band isn't flipped to `mismatch` on a manual-review entry alone.

A leading blockquote line containing `V1 placeholder` flips `is_v1_placeholder = True`. The scorer adds an explanatory note to the FitResult so the buyer knows the band is illustrative until criteria are real.

The bullet matcher tolerates a trailing parenthetical between the bold label and the colon — `**Recurring revenue %** (minimum): 30%` parses the same as `**Recurring revenue %**: 30%`.

If a value is in a form the parser doesn't recognize (e.g., the user writes "$2M to $5M" instead of "$2M – $5M", or omits the section entirely), that dimension is silently skipped. The scorer's FitResult then reports `dimensions_evaluated < dimensions_total`, which surfaces in the inventory's hover summary as e.g. *"matches 4 of 5 evaluable criteria."* This makes parser limitations visible without throwing errors at the user's prose.

## Banding rule

- Any `HIT` knockout → band is `mismatch`.
- Else, of the dimensions actually evaluated (status `in_band` or `out_of_band`):
  - `in_band / evaluated >= 0.8` → `strong`
  - `>= 0.5` → `partial`
  - `< 0.5` → `weak`
- If `dimensions_evaluated == 0` → `unknown`.

Bands are not numeric scores. The frontend renders them as labeled badges, never as 0–100. (Charter §6: surface, never decide. A 0–100 number invites the user to round it into "buy" or "pass" — a band labels a state without implying ranking precision the data doesn't have.)

## Consequences

- The criteria file stays prose. Users can keep refactoring sections without breaking anything; unrecognized lines are skipped, not flagged.
- One source of truth for fit: the `score_against_criteria` Analyst tool computes the band, the Deal Sheet quotes the result, and the inventory badge surfaces the same band. No drift between agent reasoning and inventory display.
- The parser is deliberately conservative — it would rather leave a dimension `not_disclosed` than guess. Surprising fit-bands ("only 3 of 7 dimensions evaluated") become a diagnostic that the user's prose has drifted from the recognized patterns, not a bug.
- Future criteria features (e.g., adding `addback adjustments`) just add a new heading + recognized pattern + a `ParsedCriteria` field. The contract with the user is "we'll learn your patterns over time" rather than "fill out this form."

## What we explicitly skip

- **No YAML twin file.** A schema'd duplicate would force the user to edit two files in sync, and the schema would inevitably constrain how the prose can be written.
- **No LLM-based criteria parser.** The parser must be deterministic so the same listing + criteria yields the same band every time. LLMs add cost and variance for a problem that's structured enough to grep.
- **No persisted fit_band column.** `fit_band` is computed on every list/get of a Listing. Caching would force a backfill on every criteria.md edit; recomputation cost is microseconds. Revisit only if list-listings shows a real budget pinch.
