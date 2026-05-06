"""`model_capital_stack` — parameterized capital-stack scenario for the Analyst.

Buyer asks "what if I put 30% down at 11%, no seller note?" Chat mode calls
this with the buyer's numbers; tool returns equity required, monthly/annual
debt service across SBA + seller-note tranches, DSCR, cash-on-cash, and the
breakeven-SDE-drop percentage. Every number the agent quotes comes from this
envelope (CLAUDE.md hard rule 5).

The standard SBA scenario in `compute_deal_metrics` is unchanged — that's the
default Deal Sheet scenario. This tool is for what-if exploration in chat.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.tools._amortization import annual_debt_service
from silvercurrent.agents.tools._envelope import Envelope, fail, ok
from silvercurrent.db.models import Listing


def _round_money(value: float | None) -> int | None:
    return None if value is None else round(value)


async def model_capital_stack(
    *,
    asking_price: int | None = None,
    sde: int | None = None,
    equity_pct: float = 0.25,
    sba_pct: float = 0.65,
    sba_rate: float = 0.105,
    sba_term_years: int = 10,
    seller_pct: float = 0.10,
    seller_rate: float = 0.07,
    seller_term_years: int = 5,
    listing_id: UUID | None = None,
    session: AsyncSession | None = None,
) -> Envelope:
    """Compute a parameterized capital-stack scenario.

    Inputs are buyer-supplied. If `asking_price` / `sde` aren't passed, we try
    to resolve them from `listing_id` (when the chat is scoped to a listing).
    Percentages are fractions (0.25 = 25%).
    """
    # Resolve from listing if needed.
    if (asking_price is None or sde is None) and listing_id is not None and session is not None:
        listing = await session.get(Listing, listing_id)
        if listing is not None:
            if asking_price is None:
                asking_price = listing.asking_price
            if sde is None:
                sde = listing.sde

    if asking_price is None:
        return fail("asking_price is required (pass directly or scope the chat to a listing)")
    if asking_price <= 0:
        return fail("asking_price must be positive")

    warnings: list[str] = []
    total_pct = equity_pct + sba_pct + seller_pct
    if abs(total_pct - 1.0) > 0.001:
        warnings.append(
            f"equity ({equity_pct:.0%}) + sba ({sba_pct:.0%}) + seller ({seller_pct:.0%}) "
            f"= {total_pct:.0%}, not 100% — computation proceeds with the values given"
        )

    equity_required = asking_price * equity_pct
    sba_loan_amount = asking_price * sba_pct
    seller_note_amount = asking_price * seller_pct

    sba_annual_ds = annual_debt_service(sba_loan_amount, sba_rate, sba_term_years)
    seller_annual_ds = annual_debt_service(seller_note_amount, seller_rate, seller_term_years)
    total_annual_ds = sba_annual_ds + seller_annual_ds

    dscr: float | None = None
    sde_after_ds: float | None = None
    cash_on_cash: float | None = None
    breakeven_sde_drop_pct: float | None = None

    if sde is not None and sde > 0:
        if total_annual_ds > 0:
            dscr = round(sde / total_annual_ds, 2)
        sde_after_ds = sde - total_annual_ds
        if equity_required > 0:
            cash_on_cash = round(sde_after_ds / equity_required, 4)
        breakeven_sde_drop_pct = round(1 - (total_annual_ds / sde), 4) if sde > 0 else None

    payload: dict[str, Any] = {
        "inputs": {
            "asking_price": asking_price,
            "sde": sde,
            "equity_pct": equity_pct,
            "sba_pct": sba_pct,
            "sba_rate": sba_rate,
            "sba_term_years": sba_term_years,
            "seller_pct": seller_pct,
            "seller_rate": seller_rate,
            "seller_term_years": seller_term_years,
        },
        "equity_required": _round_money(equity_required),
        "sba_loan_amount": _round_money(sba_loan_amount),
        "sba_annual_ds": _round_money(sba_annual_ds),
        "sba_monthly_ds": _round_money(sba_annual_ds / 12),
        "seller_note_amount": _round_money(seller_note_amount),
        "seller_annual_ds": _round_money(seller_annual_ds),
        "seller_monthly_ds": _round_money(seller_annual_ds / 12),
        "total_annual_ds": _round_money(total_annual_ds),
        "total_monthly_ds": _round_money(total_annual_ds / 12),
        "dscr": dscr,
        "sde_after_ds": _round_money(sde_after_ds) if sde_after_ds is not None else None,
        "cash_on_cash": cash_on_cash,
        "breakeven_sde_drop_pct": breakeven_sde_drop_pct,
        "warnings": warnings,
    }
    return ok(payload)
