"""Criteria parsing and scoring — turn `docs/criteria.md` into deterministic fit-bands.

The module is split in two:

- `parser`: heuristic regex parser that reads `criteria.md` (user-owned prose)
  and returns a `ParsedCriteria` dataclass. Anything it can't recognize is
  silently skipped — no schema is imposed on the user's writing.
- `scorer`: takes a `Listing` and a `ParsedCriteria`, returns a `FitResult`
  with `band`, `numeric_fit`, `hard_knockouts`, and `dimensions_evaluated`.

See ADR 0008 for the full convention. The parser/scorer pair powers the
`score_against_criteria` Analyst tool and the inventory's fit-band badge.
"""

from __future__ import annotations

from silvercurrent.criteria.parser import ParsedCriteria, parse_criteria
from silvercurrent.criteria.scorer import (
    FitResult,
    Knockout,
    NumericDim,
    score_listing,
)

__all__ = [
    "FitResult",
    "Knockout",
    "NumericDim",
    "ParsedCriteria",
    "parse_criteria",
    "score_listing",
]
