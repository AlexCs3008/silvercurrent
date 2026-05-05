# Operator agent — knowledge base sources

*Inventory of what's indexed in the Operator agent's RAG corpus. Add a row when adding a source; reference an ADR when removing one.*

The Operator agent answers **how-to-buy** questions using vector search over this corpus. Source files live in `corpus/operator/` (gitignored — licensed material). Vectors live in `.chroma/operator/` (gitignored — derived). Re-build with:

```
cd backend
uv run python ../scripts/ingest_operator_corpus.py [--rebuild]
```

See ADR `0006-operator-knowledge-base-design.md` for the chunking, embedding, and retrieval choices.

---

## Sources

| Title | Source | File | Date added | Why included |
|---|---|---|---|---|
| SBA 7(a) Loans for Small Business Acquisitions | hand-curated seed (Phase 2 smoke) | `sba_loans.md` | 2026-05-05 | Validates the ingestion + retrieval pipeline. Replace with SBA SOP 50 10 PDF before serious use. |
| Small-Business Valuation Multiples | hand-curated seed (Phase 2 smoke) | `valuation_basics.md` | 2026-05-05 | Validates the ingestion + retrieval pipeline. Replace with content from *Buy Then Build* + IBBA Pulse Survey before serious use. |

## Recommended next adds

The charter (§9 risk #1) commits us to a small, high-quality starting corpus rather than volume. Priority targets:

- **SBA SOP 50 10** — the official lender rulebook for SBA loans. Free PDF from sba.gov.
- **IRS Publication 535 — Business Expenses** — for addback discussions and tax mechanics. Free PDF from irs.gov.
- **Stanford GSB Search Fund Primer** — the canonical academic intro to ETA. Free PDF from gsb.stanford.edu.
- **Buy Then Build** — Walker Deibel. Hands-on operator perspective.
- **HBR Guide to Buying a Small Business** — Ruback & Yudkoff. Mainstream practitioner reference.
- Curated articles on holdco structures, asset vs. stock purchases, working capital adjustments, reps & warranties, search-fund equity mechanics.

Drop the file into `corpus/operator/`, add a row above, run the ingest script.

## Removed

*None yet. When something gets removed, link to the ADR explaining why.*
