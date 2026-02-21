"""
Returns calculation service.

Implements compound-growth projections for two investment vehicles:

* **NPS** (National Pension System) – 7.11 % p.a.; includes tax-benefit.
* **Index fund**                     – 14.49 % p.a.; tax-benefit = 0.

Pipeline per call
-----------------
1. Inline validation: reject negative amounts and duplicate timestamps.
2. Compute ceiling / remanent for every accepted transaction.
3. Track totalTransactionAmount and totalCeiling across ALL accepted transactions.
4. Apply Q rules (latest-start override).
5. Apply P rules (additive extras).
6. For each K period: sum remanent of transactions whose date falls in K
   (zero-remanent rows contribute 0 – accepted but not invested).
7. Compound-grow each K-bucket sum, deflate by inflation, compute tax benefit.

Assumptions
-----------
* ``annual_wage`` received here is the **annual** wage (caller multiplies monthly × 12).
* ``inflation`` received here is a **decimal** rate (caller divides % by 100).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, NamedTuple, Set

from app.models.schemas import (
    KRange,
    PRule,
    QRule,
    ReturnsResult,
    SavingsByDate,
)
from app.services.temporal_service import _apply_p_rules, _best_q_rule
from app.utils.financial import (
    INDEX_ANNUAL_RATE,
    NPS_ANNUAL_RATE,
    ZERO,
    compound_grow,
    compute_ceiling,
    compute_nps_deduction,
    compute_remanent,
    compute_tax_benefit,
    inflation_adjusted,
    resolve_investment_years,
    to_decimal,
)
from app.utils.time_utils import format_timestamp, is_within_range, parse_timestamp


# ── Internal DTO ──────────────────────────────────────────────────────────────

class _EnrichedTxn(NamedTuple):
    """Internal representation of a single processed transaction."""
    date: object          # datetime
    amount: Decimal
    ceiling: Decimal
    remanent: Decimal     # after Q/P rules


# ── Helpers ───────────────────────────────────────────────────────────────────

def _process_raw_transactions(
    raw_transactions: List[Dict[str, Any]],
    q_rules: List[QRule],
    p_rules: List[PRule],
) -> tuple[List[_EnrichedTxn], Decimal, Decimal]:
    """
    Validate, enrich, and apply temporal rules to raw transactions.

    Returns
    -------
    tuple
        ``(enriched_list, total_amount, total_ceiling)``
        *enriched_list* contains only accepted transactions (negatives and
        duplicates removed) with Q/P rules already applied.
        *total_amount* and *total_ceiling* cover all accepted transactions
        regardless of whether their final remanent is zero.
    """
    enriched: List[_EnrichedTxn] = []
    total_amount = ZERO
    total_ceiling = ZERO
    seen: Set[str] = set()

    for raw in raw_transactions:
        date_str: str = raw["date"]
        amount: Decimal = to_decimal(raw["amount"])
        dt = parse_timestamp(date_str)
        norm = format_timestamp(dt)

        # Reject negatives silently
        if amount < ZERO:
            continue

        # Reject duplicates – first occurrence wins
        if norm in seen:
            continue
        seen.add(norm)

        # Compute ceiling / remanent
        ceiling = compute_ceiling(amount)
        remanent = compute_remanent(ceiling, amount)

        # Track totals BEFORE Q/P adjustment
        total_amount += amount
        total_ceiling += ceiling

        # Apply Q rule (latest-start override)
        best_q = _best_q_rule(dt, q_rules)
        if best_q is not None:
            remanent = best_q.fixed

        # Apply P rules (additive)
        remanent = _apply_p_rules(remanent, dt, p_rules)

        enriched.append(_EnrichedTxn(date=dt, amount=amount, ceiling=ceiling, remanent=remanent))

    return enriched, total_amount, total_ceiling


def _sum_remanent_in_k(txns: List[_EnrichedTxn], k: KRange) -> Decimal:
    """Sum remanent for transactions whose date falls inside K (inclusive)."""
    return sum(
        (t.remanent for t in txns if is_within_range(t.date, k.start, k.end)),
        ZERO,
    )


def _compute_savings(
    k: KRange,
    invested: Decimal,
    rate: Decimal,
    years: int,
    inflation: Decimal,
    annual_wage: Decimal,
    include_tax_benefit: bool,
) -> SavingsByDate:
    """
    Build one :class:`~app.models.schemas.SavingsByDate` entry.

    profit = inflation_adjusted(future_value) − principal
    """
    future_value = compound_grow(invested, rate, years)
    real_value = inflation_adjusted(future_value, inflation, years)
    profit = real_value - invested

    tax_benefit = ZERO
    if include_tax_benefit and invested > ZERO:
        deduction = compute_nps_deduction(invested, annual_wage)
        tax_benefit = compute_tax_benefit(annual_wage, deduction)

    return SavingsByDate(
        start=k.raw_start,
        end=k.raw_end,
        amount=invested,
        profit=profit,
        tax_benefit=tax_benefit,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_returns(
    age: int,
    annual_wage: Decimal,
    inflation: Decimal,
    q_rules: List[QRule],
    p_rules: List[PRule],
    k_ranges: List[KRange],
    raw_transactions: List[Dict[str, Any]],
    include_tax_benefit: bool,
) -> ReturnsResult:
    """
    Full returns projection pipeline.

    Parameters
    ----------
    age:
        Current age of the investor.
    annual_wage:
        **Annual** gross salary (monthly value already multiplied by 12 by caller).
    inflation:
        Annual inflation rate as a **decimal** (e.g. ``Decimal("0.055")`` for 5.5 %).
    q_rules, p_rules, k_ranges:
        Temporal constraint definitions.
    raw_transactions:
        List of ``{"date": str, "amount": number}`` dicts.  Negative amounts
        and duplicate timestamps are silently rejected.
    include_tax_benefit:
        ``True`` → NPS rate (7.11 %) + tax benefit.
        ``False`` → Index rate (14.49 %), tax benefit = 0.

    Returns
    -------
    ReturnsResult
        Aggregate totals and per-K savings projections.
    """
    # Steps 1–5: validate, enrich, Q/P rules
    enriched, total_amount, total_ceiling = _process_raw_transactions(
        raw_transactions, q_rules, p_rules
    )

    rate = NPS_ANNUAL_RATE if include_tax_benefit else INDEX_ANNUAL_RATE
    years = resolve_investment_years(age)

    # Steps 6–7: per-K compound growth
    savings_by_dates: List[SavingsByDate] = []
    for k in k_ranges:
        invested = _sum_remanent_in_k(enriched, k)
        entry = _compute_savings(
            k=k,
            invested=invested,
            rate=rate,
            years=years,
            inflation=inflation,
            annual_wage=annual_wage,
            include_tax_benefit=include_tax_benefit,
        )
        savings_by_dates.append(entry)

    return ReturnsResult(
        total_transaction_amount=total_amount,
        total_ceiling=total_ceiling,
        savings_by_dates=savings_by_dates,
    )
