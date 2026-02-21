from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from app.models.schemas import (
    FilterResult,
    FilteredTransaction,
    InvalidFilteredTransaction,
    InvalidTransaction,
    KRange,
    PRule,
    QRule,
    TemporalResult,
    Transaction,
)
from app.utils.financial import ZERO, compute_ceiling, compute_remanent, to_decimal
from app.utils.time_utils import format_timestamp, is_within_range, parse_timestamp


#Shared internal helpers
def _best_q_rule(dt, q_rules: List[QRule]) -> Optional[QRule]:
    
    matching: List[QRule] = [
        r for r in q_rules if is_within_range(dt, r.start, r.end)
    ]
    if not matching:
        return None
    return max(matching, key=lambda r: r.start)


def _apply_p_rules(remanent: Decimal, dt, p_rules: List[PRule]) -> Decimal:
    
    for rule in p_rules:
        if is_within_range(dt, rule.start, rule.end):
            remanent += rule.extra
    return remanent


def _in_any_k(dt, k_ranges: List[KRange]) -> bool:

    return any(is_within_range(dt, k.start, k.end) for k in k_ranges)


#Public API: pre-built transactions (used by returns pipeline)
def apply_temporal_filter(
    q_rules: List[QRule],
    p_rules: List[PRule],
    k_ranges: List[KRange],
    transactions: List[Transaction],
) -> TemporalResult:
    
    valid: List[Transaction] = []
    invalid: List[InvalidTransaction] = []

    for txn in transactions:
        dt = txn.date
        remanent = txn.remanent

        best_q = _best_q_rule(dt, q_rules)
        if best_q is not None:
            remanent = best_q.fixed

        remanent = _apply_p_rules(remanent, dt, p_rules)

        adjusted = Transaction(
            date=txn.date,
            amount=txn.amount,
            ceiling=txn.ceiling,
            remanent=remanent,
        )

        if not _in_any_k(dt, k_ranges):
            invalid.append(
                InvalidTransaction(
                    transaction=adjusted,
                    message=(
                        f"Timestamp {format_timestamp(dt)!r} does not fall "
                        "within any K validity range."
                    ),
                )
            )
        else:
            valid.append(adjusted)

    return TemporalResult(valid=valid, invalid=invalid)


#Public API: raw transactions (used by :filter route)
def apply_temporal_filter_raw(
    q_rules: List[QRule],
    p_rules: List[PRule],
    k_ranges: List[KRange],
    raw_transactions: List[Dict[str, Any]],
) -> FilterResult:
    
    valid: List[FilteredTransaction] = []
    invalid: List[InvalidFilteredTransaction] = []
    seen_timestamps: Set[str] = set()

    for raw in raw_transactions:
        date_str: str = raw["date"]
        amount: Decimal = to_decimal(raw["amount"])
        dt = parse_timestamp(date_str)
        norm_date = format_timestamp(dt)  # normalised key for duplicate check

        # Step 1 – Negative amount
        if amount < ZERO:
            invalid.append(
                InvalidFilteredTransaction(
                    date=dt,
                    amount=amount,
                    message="Negative amounts are not allowed",
                )
            )
            continue

        # Step 2 – Duplicate timestamp
        if norm_date in seen_timestamps:
            invalid.append(
                InvalidFilteredTransaction(
                    date=dt,
                    amount=amount,
                    message="Duplicate transaction",
                )
            )
            continue
        seen_timestamps.add(norm_date)

        # Step 3 – Compute ceiling / remanent
        ceiling = compute_ceiling(amount)
        remanent = compute_remanent(ceiling, amount)

        # Step 4 – Q rules
        best_q = _best_q_rule(dt, q_rules)
        if best_q is not None:
            remanent = best_q.fixed

        # Step 5 – P rules
        remanent = _apply_p_rules(remanent, dt, p_rules)

        # Step 6 – Drop zero-remanent (contributes nothing to savings)
        if remanent == ZERO:
            continue

        # Step 7 – K gating
        in_k = _in_any_k(dt, k_ranges)
        if not in_k:
            invalid.append(
                InvalidFilteredTransaction(
                    date=dt,
                    amount=amount,
                    message=(
                        f"Timestamp {norm_date!r} does not fall within "
                        "any K validity range."
                    ),
                )
            )
            continue

        valid.append(
            FilteredTransaction(
                date=dt,
                amount=amount,
                ceiling=ceiling,
                remanent=remanent,
                in_k_period=True,
            )
        )

    return FilterResult(valid=valid, invalid=invalid)
