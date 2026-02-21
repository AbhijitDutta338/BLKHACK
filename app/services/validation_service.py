"""
Transaction validator service.

Responsibility: apply all business-rule validations to an enriched
transaction list and partition results into *valid* / *invalid* buckets.

Rules (applied in order):
1. Date format must be valid.
2. ``remanent`` >= 0.
3. ``ceiling`` >= ``amount``.
4. No duplicate timestamps.
5. Annual NPS investable limit:
   ``maxInvestable = min(10 % × wage, 200 000)``
   Once cumulative ``remanent`` exceeds *maxInvestable* the offending
   (and all subsequent) transactions are marked invalid.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Sequence, Set, Tuple

from app.models.schemas import InvalidTransaction, Transaction, ValidationResult
from app.utils.financial import NPS_MAX_ABSOLUTE, NPS_WAGE_FRACTION, ZERO, to_decimal
from app.utils.time_utils import format_timestamp, is_valid_timestamp, parse_timestamp


def validate_transactions(
    wage: Decimal,
    transactions: List[Transaction],
) -> ValidationResult:
    """
    Apply all validation rules and return a :class:`~app.models.schemas.ValidationResult`.

    Parameters
    ----------
    wage:
        Gross annual income (must be positive).
    transactions:
        Enriched transaction records (ceiling + remanent already set).

    Returns
    -------
    ValidationResult
        Partitioned *valid* and *invalid* transaction lists.
    """
    valid: List[Transaction] = []
    invalid: List[InvalidTransaction] = []

    max_investable: Decimal = min(wage * NPS_WAGE_FRACTION, NPS_MAX_ABSOLUTE)
    cumulative_remanent = ZERO
    seen_timestamps: Set[str] = set()
    nps_limit_reached = False

    for txn in transactions:
        date_str = format_timestamp(txn.date)

        # Rule 1 – date format (sanity check; already parsed but guard serialise round-trip)
        if not is_valid_timestamp(date_str):
            invalid.append(
                InvalidTransaction(
                    transaction=txn,
                    message=f"Invalid timestamp format: {date_str!r}.",
                )
            )
            continue

        # Rule 2 – remanent >= 0
        if txn.remanent < ZERO:
            invalid.append(
                InvalidTransaction(
                    transaction=txn,
                    message=f"remanent ({txn.remanent}) must be >= 0.",
                )
            )
            continue

        # Rule 3 – ceiling >= amount
        if txn.ceiling < txn.amount:
            invalid.append(
                InvalidTransaction(
                    transaction=txn,
                    message=(
                        f"ceiling ({txn.ceiling}) must be >= amount ({txn.amount})."
                    ),
                )
            )
            continue

        # Rule 4 – no duplicate timestamps
        if date_str in seen_timestamps:
            invalid.append(
                InvalidTransaction(
                    transaction=txn,
                    message=f"Duplicate timestamp: {date_str!r}.",
                )
            )
            continue

        # Rule 5 – NPS annual limit (once breached all remaining are invalid)
        if nps_limit_reached:
            invalid.append(
                InvalidTransaction(
                    transaction=txn,
                    message=(
                        f"Annual NPS investable limit of {float(max_investable):.2f} "
                        "already exceeded."
                    ),
                )
            )
            continue

        new_cumulative = cumulative_remanent + txn.remanent
        if new_cumulative > max_investable:
            nps_limit_reached = True
            invalid.append(
                InvalidTransaction(
                    transaction=txn,
                    message=(
                        f"Adding remanent {txn.remanent} would exceed annual NPS "
                        f"investable limit of {float(max_investable):.2f} "
                        f"(current cumulative: {float(cumulative_remanent):.2f})."
                    ),
                )
            )
            continue

        # All rules passed
        seen_timestamps.add(date_str)
        cumulative_remanent = new_cumulative
        valid.append(txn)

    return ValidationResult(valid=valid, invalid=invalid)
