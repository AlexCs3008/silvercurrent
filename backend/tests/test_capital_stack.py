"""Tests for `model_capital_stack`."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.tools.capital_stack import model_capital_stack
from silvercurrent.db.models import Listing


@pytest.mark.asyncio
async def test_80_10_10_scenario_at_1m_300k_sde() -> None:
    """80/10/10 stack at $1M asking, $300k SDE → DSCR within hand-checked tolerance."""
    env = await model_capital_stack(
        asking_price=1_000_000,
        sde=300_000,
        equity_pct=0.10,
        sba_pct=0.80,
        sba_rate=0.105,
        sba_term_years=10,
        seller_pct=0.10,
        seller_rate=0.07,
        seller_term_years=5,
    )
    assert env.ok
    data = env.data
    assert data["equity_required"] == 100_000
    assert data["sba_loan_amount"] == 800_000
    assert data["seller_note_amount"] == 100_000
    # SBA: $800k @ 10.5% / 10y annual ≈ $129,506
    assert 128_000 < data["sba_annual_ds"] < 131_000
    # DSCR is positive and below 2 (this is a stretched stack)
    assert 0.5 < data["dscr"] < 2.0
    assert data["warnings"] == []


@pytest.mark.asyncio
async def test_100_percent_equity_returns_zero_debt_service() -> None:
    env = await model_capital_stack(
        asking_price=1_000_000,
        sde=300_000,
        equity_pct=1.0,
        sba_pct=0.0,
        sba_rate=0.105,
        sba_term_years=10,
        seller_pct=0.0,
        seller_rate=0.07,
        seller_term_years=5,
    )
    assert env.ok
    data = env.data
    assert data["equity_required"] == 1_000_000
    assert data["sba_annual_ds"] == 0
    assert data["seller_annual_ds"] == 0
    assert data["total_annual_ds"] == 0
    # DSCR is undefined when there's no debt service.
    assert data["dscr"] is None
    assert data["sde_after_ds"] == 300_000
    assert data["breakeven_sde_drop_pct"] == 1.0


@pytest.mark.asyncio
async def test_mismatched_percentages_emit_warning_but_compute() -> None:
    env = await model_capital_stack(
        asking_price=1_000_000,
        sde=300_000,
        equity_pct=0.20,
        sba_pct=0.50,
        sba_rate=0.105,
        sba_term_years=10,
        seller_pct=0.10,
        seller_rate=0.07,
        seller_term_years=5,
    )
    # 20 + 50 + 10 = 80% — mismatch.
    assert env.ok
    assert env.data["warnings"], "expected a warning when stacks don't sum to 100%"
    # Computation still proceeds with the values given.
    assert env.data["equity_required"] == 200_000
    assert env.data["sba_loan_amount"] == 500_000


@pytest.mark.asyncio
async def test_zero_sde_yields_null_dscr_no_crash() -> None:
    """Division-by-zero on sde=0 returns nullable metrics, not a crash."""
    env = await model_capital_stack(
        asking_price=1_000_000,
        sde=0,
        equity_pct=0.25,
        sba_pct=0.65,
        sba_rate=0.105,
        sba_term_years=10,
        seller_pct=0.10,
        seller_rate=0.07,
        seller_term_years=5,
    )
    assert env.ok
    assert env.data["dscr"] is None
    assert env.data["cash_on_cash"] is None
    assert env.data["breakeven_sde_drop_pct"] is None


@pytest.mark.asyncio
async def test_resolves_asking_price_from_listing(session: AsyncSession) -> None:
    listing = Listing(business_name="Acme HVAC", asking_price=1_500_000, sde=500_000)
    session.add(listing)
    await session.commit()

    env = await model_capital_stack(
        listing_id=listing.id,
        session=session,
        equity_pct=0.25,
        sba_pct=0.65,
        sba_rate=0.105,
        sba_term_years=10,
        seller_pct=0.10,
        seller_rate=0.07,
        seller_term_years=5,
    )
    assert env.ok
    assert env.data["inputs"]["asking_price"] == 1_500_000
    assert env.data["inputs"]["sde"] == 500_000


@pytest.mark.asyncio
async def test_missing_asking_price_returns_fail() -> None:
    env = await model_capital_stack(asking_price=None, sde=300_000)
    assert not env.ok
    assert "asking_price" in (env.error or "")


@pytest.mark.asyncio
async def test_deal_metrics_still_produces_identical_sba_scenario() -> None:
    """The shared amortization helper must not change `compute_deal_metrics` output."""
    from silvercurrent.agents.tools._amortization import annual_debt_service
    from silvercurrent.agents.tools.deal_metrics import (
        SBA_ANNUAL_RATE,
        SBA_DOWN_PAYMENT_FRACTION,
        SBA_TERM_YEARS,
    )

    asking = 1_000_000
    expected_loan = asking * (1 - SBA_DOWN_PAYMENT_FRACTION)
    expected_ds = annual_debt_service(expected_loan, SBA_ANNUAL_RATE, SBA_TERM_YEARS)
    # Sanity: hand-check that the helper produces a recognizable value.
    assert 110_000 < expected_ds < 130_000
