from __future__ import annotations

from decimal import Decimal
from typing import List

from app.models.schemas import ParseResult, RawExpense, Transaction
from app.utils.financial import (
    ZERO,
    compute_ceiling,
    compute_remanent,
    to_decimal,
)
from app.utils.time_utils import parse_timestamp


def build_transactions(expenses: List[RawExpense]) -> ParseResult:
    
    transactions: List[Transaction] = []
    total_expense = ZERO
    total_ceiling = ZERO
    total_remanent = ZERO

    for exp in expenses:
        amount = to_decimal(exp.amount)
        ceiling = compute_ceiling(amount)
        remanent = compute_remanent(ceiling, amount)
        dt = parse_timestamp(exp.timestamp)

        t = Transaction(
            date=dt,
            amount=amount,
            ceiling=ceiling,
            remanent=remanent,
        )
        transactions.append(t)
        total_expense += amount
        total_ceiling += ceiling
        total_remanent += remanent

    return ParseResult(
        transactions=transactions,
        total_expense=total_expense,
        total_ceiling=total_ceiling,
        total_remanent=total_remanent,
    )
