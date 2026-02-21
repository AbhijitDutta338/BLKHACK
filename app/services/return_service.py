"""
Returns calculation service.

Implements compound-growth projections for two investment vehicles:

* **NPS** (National Pension System) – 7.11 % p.a.; includes tax-benefit.
* **Index fund**                     – 14.49 % p.a.; tax-benefit = 0.

Pipeline per call
-----------------
1. Enrich raw transactions (ceiling / remanent).
2. Apply temporal constraints (Q → P → K).
3. For each K period:
   a. Sum *remanent* of valid transactions in that period.
   b. Compute future value after compound growth.
   c. Deflate by inflation to get real value.
   d. Report profits = real_value - principal.
   e. NPS only: compute tax deduction benefit.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List

from app.models.schemas import (
    KRange,
    PRule,
    QRule,
    RawExpense,
    ReturnsResult,
    SavingsByDate,
    Transaction,
)
from app.services.temporal_service import apply_temporal_filter
from app.services.transaction_service import build_transactions
from app.utils.financial import (
    INDEX_ANNUAL_RATE,
    NPS_ANNUAL_RATE,
    ZERO,
    compound_grow,
    compute_nps_deduction,
    compute_tax_benefit,
    inflation_adjusted,
    resolve_investment_years,
    to_decimal,
)
from app.utils.time_utils import is_within_range


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sum_remanent_in_k(transactions: List[Transaction], k: KRange) -> Decimal:
    """Sum the *remanent* of all transactions whose date falls in K."""
    return sum(
        (t.remanent for t in transactions if is_within_range(t.date, k.start, k.end)),
        ZERO,
    )


def _compute_savings(
    k: KRange,
    invested: Decimal,
    rate: Decimal,
    years: int,
    inflation: Decimal,
    wage: Decimal,
    include_tax_benefit: bool,
) -> SavingsByDate:
    """
    Compute one :class:`~app.models.schemas.SavingsByDate` entry.

    Parameters
    ----------
    k:
        The K range this bucket belongs to.
    invested:
        Sum of remanent amounts within *k*.
    rate:
        Annual compound rate (7.11 % for NPS, 14.49 % for Index).
    years:
        Investment horizon.
    inflation:
        Annual inflation rate (decimal, e.g. 0.06 for 6 %).
    wage:
        Gross annual salary (used only for NPS tax benefit).
    include_tax_benefit:
        ``True`` for NPS, ``False`` for Index.
    """
    future_value = compound_grow(invested, rate, years)
    real_value = inflation_adjusted(future_value, inflation, years)
    profits = real_value - invested

    tax_benefit = ZERO
    if include_tax_benefit and invested > ZERO:
        deduction = compute_nps_deduction(invested, wage)
        tax_benefit = compute_tax_benefit(wage, deduction)

    return SavingsByDate(
        start=k.start,
        end=k.end,
        amount=invested,
        profits=profits,
        tax_benefit=tax_benefit,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_returns(
    age: int,
    wage: Decimal,
    inflation: Decimal,
    q_rules: List[QRule],
    p_rules: List[PRule],
    k_ranges: List[KRange],
    expenses: List[RawExpense],
    include_tax_benefit: bool,
) -> ReturnsResult:
    """
    Full returns projection pipeline.

    Parameters
    ----------
    age:
        Current age of the investor.
    wage:
        Gross annual salary.
    inflation:
        Annual inflation rate as a decimal (e.g. ``Decimal("0.06")``).
    q_rules, p_rules, k_ranges:
        Temporal constraint definitions.
    expenses:
        Raw expense list (timestamp + amount).
    include_tax_benefit:
        ``True`` → NPS rate + tax benefit; ``False`` → Index rate, benefit = 0.

    Returns
    -------
    ReturnsResult
        Aggregate totals and per-K-range savings projections.
    """
    # Step 1 – enrich
    parse_result = build_transactions(expenses)

    # Step 2 – temporal filter
    temporal_result = apply_temporal_filter(
        q_rules=q_rules,
        p_rules=p_rules,
        k_ranges=k_ranges,
        transactions=parse_result.transactions,
    )
    valid_txns = temporal_result.valid

    # Step 3 – investment parameters
    rate = NPS_ANNUAL_RATE if include_tax_benefit else INDEX_ANNUAL_RATE
    years = resolve_investment_years(age)

    # Step 4 – per-K bucket
    savings_by_dates: List[SavingsByDate] = []
    for k in k_ranges:
        invested = _sum_remanent_in_k(valid_txns, k)
        entry = _compute_savings(
            k=k,
            invested=invested,
            rate=rate,
            years=years,
            inflation=inflation,
            wage=wage,
            include_tax_benefit=include_tax_benefit,
        )
        savings_by_dates.append(entry)

    return ReturnsResult(
        transactions_total_amount=parse_result.total_expense,
        transactions_total_ceiling=parse_result.total_ceiling,
        savings_by_dates=savings_by_dates,
    )
