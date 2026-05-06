"""Shared amortization helper used by the SBA scenario in `compute_deal_metrics`
and the parameterized `model_capital_stack` tool.

Standard fully-amortizing fixed-rate loan: monthly payment is

    PMT = P · (r/12) / (1 − (1 + r/12)^(−12·t))

annual debt service is `PMT × 12`. Zero-rate loans amortize linearly; zero-
principal loans return zero (the tools call this with `loan_amount = 0`
when the buyer puts 100% down or skips a tranche).
"""

from __future__ import annotations


def annual_debt_service(loan_amount: float, annual_rate: float, term_years: int) -> float:
    """Return the annual debt service for a fully-amortizing fixed-rate loan."""
    if loan_amount <= 0:
        return 0.0
    if term_years <= 0:
        return 0.0
    monthly_rate = annual_rate / 12
    n = term_years * 12
    if monthly_rate == 0:
        return (loan_amount / n) * 12
    monthly_payment = loan_amount * monthly_rate / (1 - (1 + monthly_rate) ** (-n))
    return monthly_payment * 12
