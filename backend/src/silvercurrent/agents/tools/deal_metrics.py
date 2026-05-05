"""`compute_deal_metrics` — deterministic deal-math for the Analyst agent.

Per CLAUDE.md rule 5: numerical claims always come from tool calls. This is the
tool that supplies the asking-multiple, SDE margin, and SBA-financing-scenario
numbers the Analyst quotes in a Deal Sheet. The Analyst itself never makes them
up.

SBA assumptions are explicit constants below — they are scenario inputs, not
forecasts. If the buyer wants a different rate or down payment, those become
parameters in a later iteration; for now we compute one standard scenario.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.tools._envelope import Envelope, fail, ok
from silvercurrent.db.models import Listing

# Standard SBA 7(a) acquisition scenario. Documented in CLAUDE.md domain glossary
# ("SBA 7(a): up to ~$5M, ~10y term, ~25% down typical"). Rate is a placeholder
# anchored to recent SBA Prime + typical spread; tune as the rate environment
# moves.
SBA_DOWN_PAYMENT_FRACTION = 0.25
SBA_TERM_YEARS = 10
SBA_ANNUAL_RATE = 0.105  # 10.5% — illustrative; replace with a settings value when rate sensitivity matters.


def _annual_debt_service(loan_amount: float, annual_rate: float, term_years: int) -> float:
    """Standard amortization: monthly payment × 12.

    PMT = P · (r/12) / (1 − (1 + r/12)^(−12·t))
    """
    if loan_amount <= 0:
        return 0.0
    monthly_rate = annual_rate / 12
    n = term_years * 12
    if monthly_rate == 0:
        return (loan_amount / n) * 12
    monthly_payment = loan_amount * monthly_rate / (1 - (1 + monthly_rate) ** (-n))
    return monthly_payment * 12


async def compute_deal_metrics(
    *,
    listing_id: UUID,
    session: AsyncSession,
) -> Envelope:
    """Compute asking multiples, SDE margin, and an SBA financing scenario for a listing.

    Returns a structured payload the Analyst quotes verbatim. Any field the
    listing didn't disclose appears in `missing_fields` and is omitted from the
    derived metric (rather than substituted with a guess).
    """
    listing = await session.get(Listing, listing_id)
    if listing is None:
        return fail(f"listing {listing_id} not found")

    asking = listing.asking_price
    sde = listing.sde
    revenue = listing.revenue

    missing: list[str] = []
    if asking is None:
        missing.append("asking_price")
    if sde is None:
        missing.append("sde")
    if revenue is None:
        missing.append("revenue")

    multiples: dict[str, float] = {}
    if asking is not None and sde is not None and sde > 0:
        multiples["asking_multiple_sde"] = round(asking / sde, 2)
    if asking is not None and revenue is not None and revenue > 0:
        multiples["asking_multiple_revenue"] = round(asking / revenue, 2)

    sde_margin: float | None = None
    if sde is not None and revenue is not None and revenue > 0:
        sde_margin = round(sde / revenue, 4)

    sba_scenario: dict[str, Any] | None = None
    if asking is not None and asking > 0:
        down = asking * SBA_DOWN_PAYMENT_FRACTION
        loan = asking - down
        annual_ds = _annual_debt_service(loan, SBA_ANNUAL_RATE, SBA_TERM_YEARS)
        scenario: dict[str, Any] = {
            "assumptions": {
                "down_payment_fraction": SBA_DOWN_PAYMENT_FRACTION,
                "annual_rate": SBA_ANNUAL_RATE,
                "term_years": SBA_TERM_YEARS,
            },
            "down_payment": round(down),
            "loan_amount": round(loan),
            "annual_debt_service": round(annual_ds),
        }
        if sde is not None and annual_ds > 0:
            scenario["dscr"] = round(sde / annual_ds, 2)
            scenario["sde_after_debt_service"] = round(sde - annual_ds)
        sba_scenario = scenario

    return ok(
        {
            "listing_id": str(listing.id),
            "inputs": {
                "asking_price": asking,
                "sde": sde,
                "revenue": revenue,
            },
            "multiples": multiples,
            "sde_margin": sde_margin,
            "sba_scenario": sba_scenario,
            "missing_fields": missing,
        }
    )
