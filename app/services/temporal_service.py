"""
Temporal constraints filter service.

Applies three layers of date-range rules to a list of enriched transactions:

Q rules (override):
    If a transaction's timestamp falls in one or more Q ranges, choose the
    range with the **latest start** date and replace ``remanent`` with its
    ``fixed`` value.

P rules (additive):
    For every P range whose interval contains the transaction's timestamp,
    add ``extra`` to ``remanent``.

K ranges (gating):
    The transaction must fall inside **at least one** K range to be valid.
    Transactions outside all K ranges are moved to *invalid*.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Tuple

from app.models.schemas import (
    InvalidTransaction,
    KRange,
    PRule,
    QRule,
    TemporalResult,
    Transaction,
)
from app.utils.financial import ZERO
from app.utils.time_utils import format_timestamp, is_within_range


# ── Internal helpers ─────────────────────────────────────────────────────────

def _best_q_rule(dt, q_rules: List[QRule]) -> Optional[QRule]:
    """
    Return the Q rule with the latest *start* date that contains *dt*.

    Uses a linear scan (collections are typically small; O(n) is fine).
    For large rule sets, replace with a binary search on sorted start dates.
    """
    matching: List[QRule] = [
        r for r in q_rules if is_within_range(dt, r.start, r.end)
    ]
    if not matching:
        return None
    # Deterministic: prefer latest start; break ties by latest end
    return max(matching, key=lambda r: (r.start, r.end))


def _apply_p_rules(remanent: Decimal, dt, p_rules: List[PRule]) -> Decimal:
    """Add *extra* from every matching P rule to *remanent*."""
    total_extra = ZERO
    for rule in p_rules:
        if is_within_range(dt, rule.start, rule.end):
            total_extra += rule.extra
    return remanent + total_extra


def _in_any_k(dt, k_ranges: List[KRange]) -> bool:
    """Return ``True`` when *dt* falls inside at least one K range."""
    return any(is_within_range(dt, k.start, k.end) for k in k_ranges)


# ── Public API ────────────────────────────────────────────────────────────────

def apply_temporal_filter(
    q_rules: List[QRule],
    p_rules: List[PRule],
    k_ranges: List[KRange],
    transactions: List[Transaction],
) -> TemporalResult:
    """
    Apply Q → P → K constraint layers and partition transactions.

    Parameters
    ----------
    q_rules:
        Zero or more Q rules (fixed remanent override per date range).
    p_rules:
        Zero or more P rules (additive extra per date range).
    k_ranges:
        One or more K validity windows.
    transactions:
        Enriched transaction records *before* temporal adjustment.

    Returns
    -------
    TemporalResult
        ``valid`` = transactions that passed all checks (remanent mutated).
        ``invalid`` = transactions outside every K range.
    """
    valid: List[Transaction] = []
    invalid: List[InvalidTransaction] = []

    for txn in transactions:
        dt = txn.date
        remanent = txn.remanent

        # Step 1 – Q override (pick latest-start matching rule)
        best_q = _best_q_rule(dt, q_rules)
        if best_q is not None:
            remanent = best_q.fixed

        # Step 2 – P additive rules
        remanent = _apply_p_rules(remanent, dt, p_rules)

        # Build adjusted transaction
        adjusted = Transaction(
            date=txn.date,
            amount=txn.amount,
            ceiling=txn.ceiling,
            remanent=remanent,
        )

        # Step 3 – K gating
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
