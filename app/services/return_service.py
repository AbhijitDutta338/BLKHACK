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


#Internal DTO
class _EnrichedTxn(NamedTuple):

    date: object          # datetime
    amount: Decimal
    ceiling: Decimal
    remanent: Decimal     # after Q/P rules


#Helpers
def _process_raw_transactions(
    raw_transactions: List[Dict[str, Any]],
    q_rules: List[QRule],
    p_rules: List[PRule],
) -> tuple[List[_EnrichedTxn], Decimal, Decimal]:

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


#Public API
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
