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
| SBA 7(a) Loans for Small Business Acquisitions | hand-curated seed (Phase 2 smoke) | `sba_loans.md` | 2026-05-05 | Validates the ingestion + retrieval pipeline. Kept alongside the official SOP for now — short, opinionated summary; the SOP is the authoritative reference. |
| Small-Business Valuation Multiples | hand-curated seed (Phase 2 smoke) | `valuation_basics.md` | 2026-05-05 | Validates the ingestion + retrieval pipeline. Replace with content from *Buy Then Build* + IBBA Pulse Survey before serious use. |
| SBA SOP 50 10 8 — Lender and Development Company Loan Programs | [sba.gov](https://www.sba.gov/document/sop-50-10-lender-development-company-loan-programs) — version 8, effective 2025-06-01 (with 2026-03-01 citizenship/residency update notice) | `sba_sop_50_10_8.md` | 2026-05-05 | Authoritative SBA rulebook for 7(a) and 504 loans — eligibility, use of proceeds, fees, lender procedures. Highest-leverage single source for financing questions. Sourced as `.docx`, converted to markdown via stdlib `zipfile + xml.etree` (kept original `_sba_sop_50_10_8.docx` alongside for reproducibility; not ingested — `.docx` suffix is unsupported). Conversion is rough on TOC pagination and a few run-together words; body prose is clean. |
| IRS Publication 535 — Business Expenses (2022) | [irs.gov](https://www.irs.gov/pub/irs-prior/p535--2022.pdf) — 2022 final revision | `irs_pub_535_2022.pdf` | 2026-05-05 | Canonical reference for the addback discussion: what counts as ordinary-and-necessary, capitalization vs. expensing, owner compensation, depreciation/amortization rules. **Discontinued by IRS** — last revised 2022, replaced by the [Guide to Business Expense Resources](https://www.irs.gov/forms-pubs/guide-to-business-expense-resources) hub. Still the most coherent single doc on the topic; flag staleness in retrieval if a tax-rate-sensitive question arises. |
| Mercer Capital — Quality of Earnings Analysis | [mercercapital.com](https://mercercapital.com/content/uploads/Mercer-Capital-Quality-of-Earnings-Analysis.pdf) | `mercer_capital_quality_of_earnings.pdf` | 2026-05-05 | Professional-grade primer on QoE from a respected business-valuation firm. Covers normalized EBITDA, addback scrutiny, working-capital review, customer concentration analysis — the full QoE workflow a buyer commissions during diligence. |
| Paul Weiss / IFLR — Working Capital Adjustments in M&A (2008) | [paulweiss.com](https://www.paulweiss.com/media/hz1d0aq4/iflr_-_feb_08_-_working_capital_article_-_bonvino__schneider.pdf) | `paul_weiss_working_capital_adjustments_2008.pdf` | 2026-05-05 | BigLaw treatment of working-capital adjustment mechanics in purchase agreements: the peg, true-up, dispute resolution, drafting traps. 2008 vintage but the legal mechanics are unchanged. |

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
