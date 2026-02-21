"""
Temporal constraints filter service.

Provides two public entry-points:

apply_temporal_filter(q, p, k, transactions)
    Accepts pre-built :class:`~app.models.schemas.Transaction` objects.
    Used internally by the returns pipeline.

apply_temporal_filter_raw(q, p, k, raw)
    Accepts raw ``{"date": str, "amount": number}`` dicts coming directly
    from the POST /transactions:filter endpoint.

    Full processing order
    ---------------------
    1. Validate: reject negative amounts and duplicate timestamps.
    2. Compute ceiling and remanent from amount.
    3. Apply Q rules: replace remanent with ``fixed`` for the matching
       Q period with the **latest start** date.
    4. Apply P rules: add all matching ``extra`` values to remanent.
    5. Discard zero-remanent transactions silently (contribute nothing
       to savings; e.g. a Q override of fixed=0).
    6. K gating: ``inKPeriod = True`` when timestamp is in any K range;
       transactions outside all K ranges go to *invalid*.
"""

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


# ── Shared internal helpers ──────────────────────────────────────────────────

def _best_q_rule(dt, q_rules: List[QRule]) -> Optional[QRule]:
    """
    Return the Q rule with the latest *start* date that contains *dt*.

    If two rules share the same start date, the first one in the list wins
    (preserves input ordering, guarantees determinism).
    """
    matching: List[QRule] = [
        r for r in q_rules if is_within_range(dt, r.start, r.end)
    ]
    if not matching:
        return None
    return max(matching, key=lambda r: r.start)


def _apply_p_rules(remanent: Decimal, dt, p_rules: List[PRule]) -> Decimal:
    """Add *extra* from every P rule whose range contains *dt*."""
    for rule in p_rules:
        if is_within_range(dt, rule.start, rule.end):
            remanent += rule.extra
    return remanent


def _in_any_k(dt, k_ranges: List[KRange]) -> bool:
    """Return ``True`` when *dt* falls inside at least one K range."""
    return any(is_within_range(dt, k.start, k.end) for k in k_ranges)


# ── Public API: pre-built transactions (used by returns pipeline) ─────────────

def apply_temporal_filter(
    q_rules: List[QRule],
    p_rules: List[PRule],
    k_ranges: List[KRange],
    transactions: List[Transaction],
) -> TemporalResult:
    """
    Apply Q → P → K constraint layers to pre-built transactions.

    Used by the returns calculation service which already has enriched
    :class:`~app.models.schemas.Transaction` objects.

    Parameters
    ----------
    q_rules, p_rules, k_ranges:
        Temporal constraint definitions.
    transactions:
        Already-enriched transaction records.

    Returns
    -------
    TemporalResult
        ``valid`` – adjusted transactions inside at least one K range.
        ``invalid`` – transactions outside every K range.
    """
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


# ── Public API: raw transactions (used by :filter route) ─────────────────────

def apply_temporal_filter_raw(
    q_rules: List[QRule],
    p_rules: List[PRule],
    k_ranges: List[KRange],
    raw_transactions: List[Dict[str, Any]],
) -> FilterResult:
    """
    Full filter pipeline for raw ``{"date": str, "amount": number}`` inputs.

    Processing order
    ----------------
    1. Reject negative amounts  → invalid (``"Negative amounts are not allowed"``)
    2. Reject duplicate timestamps → invalid (``"Duplicate transaction"``)
    3. Compute ceiling and remanent.
    4. Apply Q rules (latest-start override).
    5. Apply P rules (additive extras).
    6. Drop zero-remanent transactions silently.
    7. K gating: outside-K transactions → invalid.

    Parameters
    ----------
    q_rules, p_rules, k_ranges:
        Temporal constraint definitions.
    raw_transactions:
        List of dicts with at minimum ``"date"`` (timestamp string) and
        ``"amount"`` (number) keys.

    Returns
    -------
    FilterResult
        ``valid``  – :class:`~app.models.schemas.FilteredTransaction` objects
                    with ``inKPeriod = True``.
        ``invalid`` – :class:`~app.models.schemas.InvalidFilteredTransaction`
                    objects with a human-readable ``message``.
    """
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
