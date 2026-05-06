"""Heuristic parser for `docs/criteria.md`.

`criteria.md` is user-owned (CLAUDE.md hard rule). The parser reads known
patterns under known `## ` headings and exposes them as a `ParsedCriteria`
dataclass. Anything it can't match is silently skipped — the scorer then
exposes `dimensions_evaluated` so the user sees what was actually scored.

ADR 0008 documents the parsing conventions in full.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A forgiving dollar matcher: `$1,200,000`, `$500K`, `$3M`, `$3,000,000` all
# resolve to whole-dollar integers. Returns None if the string doesn't look
# like a dollar amount we recognize.
_DOLLAR_RE = re.compile(
    r"""
    \$\s*                               # leading $
    ([\d,]+(?:\.\d+)?)                  # number with optional commas/decimals
    \s*([KkMmBb])?                      # optional magnitude suffix
    """,
    re.VERBOSE,
)

_PERCENT_RE = re.compile(r"([\d.]+)\s*%")
_MULTIPLE_RE = re.compile(r"([\d.]+)\s*[×x]")
_INT_RANGE_RE = re.compile(r"`?(\d+)`?\s*[–-]\s*`?(\d+)`?")
_INT_FLOOR_RE = re.compile(r"`?(\d+)\+?`?")

# Section headings we know how to parse.
_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

# V1 placeholder banner detection — the file currently leads with a blockquote
# tagged "V1 placeholder content"; treat any blockquote line that mentions the
# phrase as the marker.
_V1_BANNER_RE = re.compile(r"V1\s+placeholder", re.IGNORECASE)


def _parse_dollar(text: str) -> int | None:
    """Parse the first dollar amount in `text` to a whole-dollar integer."""
    m = _DOLLAR_RE.search(text)
    if m is None:
        return None
    raw, suffix = m.group(1), (m.group(2) or "").lower()
    try:
        value = float(raw.replace(",", ""))
    except ValueError:
        return None
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    elif suffix == "b":
        value *= 1_000_000_000
    return int(value)


def _parse_dollar_range(text: str) -> tuple[int | None, int | None]:
    """Parse `$500,000 – $3,000,000` (em-dash or hyphen) into a (low, high) tuple."""
    parts = re.split(r"\s*[–-]\s*", text, maxsplit=1)
    if len(parts) != 2:
        single = _parse_dollar(text)
        return (single, single) if single is not None else (None, None)
    low = _parse_dollar(parts[0])
    high = _parse_dollar(parts[1])
    return (low, high)


def _parse_int_range(text: str) -> tuple[int | None, int | None]:
    """Parse `5 – 30` (any dashes/backticks) into an integer (low, high) tuple."""
    m = _INT_RANGE_RE.search(text)
    if m is None:
        return (None, None)
    return (int(m.group(1)), int(m.group(2)))


def _parse_int_floor(text: str) -> int | None:
    """Parse `7+` → 7. The `+` is optional."""
    m = _INT_FLOOR_RE.search(text)
    return int(m.group(1)) if m is not None else None


def _parse_percent(text: str) -> float | None:
    """Parse `30%` → 30.0. Returns the percentage as a float (not 0–1 fraction)."""
    m = _PERCENT_RE.search(text)
    return float(m.group(1)) if m is not None else None


def _parse_multiple(text: str) -> float | None:
    """Parse `3.5×` or `4x` → 3.5 / 4.0."""
    m = _MULTIPLE_RE.search(text)
    return float(m.group(1)) if m is not None else None


def _split_csv_terms(text: str) -> set[str]:
    """Split a comma/semicolon-separated phrase into lower-cased keyword tokens.

    Strips leading hyphens, backticks, and Markdown emphasis. Used for industry
    and geography keyword lists where the user writes free-form prose.
    """
    cleaned = re.sub(r"\*\*?", "", text)
    cleaned = cleaned.replace("`", "").strip(" -—.")
    tokens = re.split(r"\s*[,;]\s*", cleaned)
    return {t.strip().lower() for t in tokens if t.strip()}


@dataclass(frozen=True)
class ParsedCriteria:
    """Structured view of `docs/criteria.md`.

    Every field is optional — the user may simply not have specified that
    dimension yet, or may have written it in a form the parser doesn't
    recognize. The scorer treats unset fields as "no opinion" rather than
    "fail."
    """

    industry_targets: set[str] = field(default_factory=set)
    industry_open_with_reservations: set[str] = field(default_factory=set)
    industry_hard_nos: set[str] = field(default_factory=set)

    geography_primary: set[str] = field(default_factory=set)
    geography_secondary: set[str] = field(default_factory=set)
    geography_hard_nos: set[str] = field(default_factory=set)

    asking_price_band: tuple[int | None, int | None] = (None, None)
    sde_band: tuple[int | None, int | None] = (None, None)
    revenue_band: tuple[int | None, int | None] = (None, None)
    multiple_ceiling: float | None = None

    employee_band: tuple[int | None, int | None] = (None, None)
    years_established_min: int | None = None
    recurring_revenue_min_pct: float | None = None
    customer_concentration_max_pct: float | None = None

    hard_knockouts_text: list[str] = field(default_factory=list)

    is_v1_placeholder: bool = False


def _split_into_sections(markdown: str) -> dict[str, str]:
    """Return a `{lower_case_heading: section_body}` map for `## ` headings."""
    sections: dict[str, str] = {}
    matches = list(_HEADING_RE.finditer(markdown))
    for i, m in enumerate(matches):
        title = m.group(1).strip().lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        sections[title] = markdown[start:end]
    return sections


def _extract_bullet_after(section: str, label: str) -> str | None:
    """Find the first bullet whose key matches `label` (case-insensitive).

    Looks for lines like `- **Asking price range**: ...` and returns the text
    after the colon, with surrounding whitespace stripped. Returns None when
    no such bullet exists.
    """
    # Tolerate a trailing parenthetical between the bold label and the colon —
    # criteria.md occasionally writes `**Recurring revenue %** (minimum): 30%`.
    pattern = re.compile(
        rf"^\s*[-*]\s*\*\*{re.escape(label)}\*\*\s*(?:\([^)]*\))?\s*[:\-]\s*(.*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    m = pattern.search(section)
    return m.group(1).strip() if m is not None else None


def _extract_bullets(section: str) -> list[str]:
    """Return the text content of every top-level `- ` bullet in `section`."""
    return [m.group(1).strip() for m in re.finditer(r"^\s*[-*]\s+(.+?)\s*$", section, re.MULTILINE)]


def parse_criteria(markdown: str) -> ParsedCriteria:
    """Parse `docs/criteria.md` markdown into a `ParsedCriteria`.

    Recognizes the patterns listed in ADR 0008. Everything else is silently
    skipped — the scorer reports `dimensions_evaluated` so the user sees what
    contributed.
    """
    sections = _split_into_sections(markdown)
    is_v1 = bool(_V1_BANNER_RE.search(markdown))

    # --- Industry -------------------------------------------------------------
    industry_section = sections.get("industry", "")
    industry_targets = _split_csv_terms(_extract_bullet_after(industry_section, "Target sectors") or "")
    industry_reservations = _split_csv_terms(_extract_bullet_after(industry_section, "Open to with reservations") or "")
    industry_hard_nos = _split_csv_terms(_extract_bullet_after(industry_section, "Hard nos") or "")

    # --- Geography ------------------------------------------------------------
    geography_section = sections.get("geography", "")
    geography_primary = _split_csv_terms(_extract_bullet_after(geography_section, "Primary") or "")
    geography_secondary = _split_csv_terms(_extract_bullet_after(geography_section, "Secondary") or "")
    geography_hard_nos = _split_csv_terms(_extract_bullet_after(geography_section, "Hard nos") or "")

    # --- Financial profile ----------------------------------------------------
    fin_section = sections.get("financial profile", "")
    asking_band = _parse_dollar_range(_extract_bullet_after(fin_section, "Asking price range") or "")
    sde_band = _parse_dollar_range(_extract_bullet_after(fin_section, "SDE range") or "")
    revenue_band = _parse_dollar_range(_extract_bullet_after(fin_section, "Revenue range") or "")
    multiple_ceiling = _parse_multiple(_extract_bullet_after(fin_section, "Multiple ceiling") or "")

    # --- Operating profile ----------------------------------------------------
    op_section = sections.get("operating profile", "")
    employee_band = _parse_int_range(_extract_bullet_after(op_section, "Employee count") or "")
    years_established_min = _parse_int_floor(_extract_bullet_after(op_section, "Years established (minimum)") or "")
    recurring_revenue_min_pct = _parse_percent(_extract_bullet_after(op_section, "Recurring revenue %") or "")

    # --- Growth & risk --------------------------------------------------------
    risk_section = sections.get("growth & risk", "")
    customer_concentration_max_pct = _parse_percent(
        _extract_bullet_after(risk_section, "Customer concentration ceiling") or ""
    )

    # --- Hard knockouts -------------------------------------------------------
    knockouts_section = sections.get("hard knockouts (instant pass — no run analysis needed)", "")
    if not knockouts_section:
        # Fallback: any heading that starts with "hard knockouts".
        for title, body in sections.items():
            if title.startswith("hard knockouts"):
                knockouts_section = body
                break
    hard_knockouts_text = [b for b in _extract_bullets(knockouts_section) if b]

    return ParsedCriteria(
        industry_targets=industry_targets,
        industry_open_with_reservations=industry_reservations,
        industry_hard_nos=industry_hard_nos,
        geography_primary=geography_primary,
        geography_secondary=geography_secondary,
        geography_hard_nos=geography_hard_nos,
        asking_price_band=asking_band,
        sde_band=sde_band,
        revenue_band=revenue_band,
        multiple_ceiling=multiple_ceiling,
        employee_band=employee_band,
        years_established_min=years_established_min,
        recurring_revenue_min_pct=recurring_revenue_min_pct,
        customer_concentration_max_pct=customer_concentration_max_pct,
        hard_knockouts_text=hard_knockouts_text,
        is_v1_placeholder=is_v1,
    )
