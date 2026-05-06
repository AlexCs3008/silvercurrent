"""Tests for the heuristic `criteria.md` parser."""

from __future__ import annotations

from pathlib import Path

from silvercurrent.criteria.parser import parse_criteria

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CRITERIA_PATH = _REPO_ROOT / "docs" / "criteria.md"


def test_parses_real_criteria_md_round_trip() -> None:
    """The shipping `docs/criteria.md` parses with all the documented fields populated."""
    markdown = _CRITERIA_PATH.read_text(encoding="utf-8")
    parsed = parse_criteria(markdown)

    assert parsed.is_v1_placeholder is True

    # Financials
    assert parsed.asking_price_band == (500_000, 3_000_000)
    assert parsed.sde_band == (200_000, 800_000)
    assert parsed.revenue_band == (1_000_000, 8_000_000)
    assert parsed.multiple_ceiling == 3.5

    # Operating profile
    assert parsed.employee_band == (5, 30)
    assert parsed.years_established_min == 7
    assert parsed.recurring_revenue_min_pct == 30.0

    # Risk
    assert parsed.customer_concentration_max_pct == 20.0

    # Geography
    assert any("miami" in t for t in parsed.geography_primary)
    assert any("california" in t for t in parsed.geography_hard_nos)

    # Industry
    assert parsed.industry_targets, "expected target sectors to parse"
    assert parsed.industry_hard_nos, "expected industry hard-nos to parse"

    # Hard knockouts (instant pass)
    assert any("declining revenue" in k.lower() for k in parsed.hard_knockouts_text)
    assert any("× sde" in k.lower() or "x sde" in k.lower() for k in parsed.hard_knockouts_text)


def test_partial_criteria_skips_missing_dimensions() -> None:
    """A criteria file with only some sections leaves other dimensions empty."""
    markdown = """
# Partial criteria

## Financial profile

- **Asking price range**: `$1,000,000` – `$2,000,000`
"""
    parsed = parse_criteria(markdown)
    assert parsed.asking_price_band == (1_000_000, 2_000_000)
    assert parsed.sde_band == (None, None)
    assert parsed.revenue_band == (None, None)
    assert parsed.multiple_ceiling is None
    assert parsed.industry_targets == set()
    assert parsed.is_v1_placeholder is False


def test_handles_unrecognized_lines_silently() -> None:
    """Lines we don't recognize don't raise — they're skipped."""
    markdown = """
## Financial profile

- **Asking price range**: `$500,000` – `$1,500,000`
- **Some thing we never specified**: not a real field

## A future heading we don't know about

- a bullet
"""
    parsed = parse_criteria(markdown)
    assert parsed.asking_price_band == (500_000, 1_500_000)


def test_v1_banner_detected() -> None:
    """Any blockquote-like line mentioning 'V1 placeholder' flips the banner flag."""
    markdown = "> ⚠ V1 placeholder content — engineered defaults.\n\n## Industry\n"
    parsed = parse_criteria(markdown)
    assert parsed.is_v1_placeholder is True
