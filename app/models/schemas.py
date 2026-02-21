"""
Immutable data models / schemas for the BlackRock challenge API.

These dataclasses serve as typed containers that travel between
the route → service → model layers.  No business logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


#Raw input atoms
@dataclass(frozen=True)
class RawExpense:
    """Single raw expense row as received from the client."""
    timestamp: str
    amount: Decimal


@dataclass(frozen=True)
class RawTransaction:
    """
    An enriched transaction (ceiling + remanent already computed).
    Used as input to validator and temporal filter endpoints.
    """
    date: str
    amount: Decimal
    ceiling: Decimal
    remanent: Decimal


#Enriched transaction (output of builder) 
@dataclass(frozen=True)
class Transaction:
    """Fully enriched transaction with ceiling and remanent."""
    date: datetime
    amount: Decimal
    ceiling: Decimal
    remanent: Decimal

    def to_dict(self) -> dict:
        from app.utils.time_utils import format_timestamp
        from app.utils.financial import decimal_to_float
        return {
            "date": format_timestamp(self.date),
            "amount": decimal_to_float(self.amount),
            "ceiling": decimal_to_float(self.ceiling),
            "remanent": decimal_to_float(self.remanent),
        }


#Parser output 
@dataclass(frozen=True)
class ParseResult:
    """Output of the transaction builder service."""
    transactions: List[Transaction]
    total_expense: Decimal
    total_ceiling: Decimal
    total_remanent: Decimal

    def to_dict(self) -> dict:
        from app.utils.financial import decimal_to_float
        return [t.to_dict() for t in self.transactions]


#Validation output 
@dataclass(frozen=True)
class InvalidTransaction:
    """A transaction that failed one or more validation rules."""
    transaction: Transaction
    message: str

    def to_dict(self) -> dict:
        d = self.transaction.to_dict()
        d["message"] = self.message
        return d


@dataclass(frozen=True)
class ValidationResult:
    """Output of the transaction validator service."""
    valid: List[Transaction]
    invalid: List[InvalidTransaction]

    def to_dict(self) -> dict:
        return {
            "valid": [t.to_dict() for t in self.valid],
            "invalid": [t.to_dict() for t in self.invalid],
        }


#Temporal rule definitions 
@dataclass(frozen=True)
class QRule:
    """Replace *remanent* with *fixed* for transactions in [start, end]."""
    fixed: Decimal
    start: datetime
    end: datetime


@dataclass(frozen=True)
class PRule:
    """Add *extra* to *remanent* for transactions in [start, end]."""
    extra: Decimal
    start: datetime
    end: datetime


@dataclass(frozen=True)
class KRange:
    """Validity window; transaction must fall in at least one K range."""
    start: datetime
    end: datetime
    raw_start: str = ""
    raw_end: str = ""


#Temporal filter output
@dataclass(frozen=True)
class TemporalResult:
    """Output of the temporal constraints filter service (pre-built transactions)."""
    valid: List[Transaction]
    invalid: List[InvalidTransaction]

    def to_dict(self) -> dict:
        return {
            "valid": [t.to_dict() for t in self.valid],
            "invalid": [t.to_dict() for t in self.invalid],
        }


@dataclass(frozen=True)
class FilteredTransaction:
    """
    Valid transaction produced by the raw-input temporal filter.
    Includes ``inKPeriod`` flag and fully computed ceiling/remanent.
    """
    date: datetime
    amount: Decimal
    ceiling: Decimal
    remanent: Decimal
    in_k_period: bool = True

    def to_dict(self) -> dict:
        from app.utils.time_utils import format_timestamp
        from app.utils.financial import decimal_to_float
        return {
            "date": format_timestamp(self.date),
            "amount": decimal_to_float(self.amount),
            "ceiling": decimal_to_float(self.ceiling),
            "remanent": decimal_to_float(self.remanent),
            "inKPeriod": self.in_k_period,
        }


@dataclass(frozen=True)
class InvalidFilteredTransaction:
    """
    A transaction rejected during raw-input temporal filtering.
    Only carries date, amount and a human-readable message.
    """
    date: datetime
    amount: Decimal
    message: str

    def to_dict(self) -> dict:
        from app.utils.time_utils import format_timestamp
        from app.utils.financial import decimal_to_float
        return {
            "date": format_timestamp(self.date),
            "amount": decimal_to_float(self.amount),
            "message": self.message,
        }


@dataclass(frozen=True)
class FilterResult:
    """
    Output of the raw-input temporal filter pipeline.
    """
    valid: List[FilteredTransaction]
    invalid: List[InvalidFilteredTransaction]

    def to_dict(self) -> dict:
        return {
            "valid": [t.to_dict() for t in self.valid],
            "invalid": [t.to_dict() for t in self.invalid],
        }


#Returns output schemas
@dataclass(frozen=True)
class SavingsByDate:
    """
    Compounded return figure for one K period.

    ``start`` and ``end`` are stored as the **original input strings** so that
    calendar oddities like ``"2023-11-31"`` are echoed back verbatim.
    """
    start: str
    end: str
    amount: Decimal
    profit: Decimal
    tax_benefit: Decimal

    def to_dict(self) -> dict:
        from app.utils.financial import decimal_to_float
        return {
            "start": self.start,
            "end": self.end,
            "amount": decimal_to_float(self.amount),
            "profit": decimal_to_float(self.profit),
            "taxBenefit": decimal_to_float(self.tax_benefit),
        }


@dataclass(frozen=True)
class ReturnsResult:
    """Output of both NPS and Index returns services."""
    total_transaction_amount: Decimal
    total_ceiling: Decimal
    savings_by_dates: List[SavingsByDate]

    def to_dict(self) -> dict:
        from app.utils.financial import decimal_to_float
        return {
            "totalTransactionAmount": decimal_to_float(self.total_transaction_amount),
            "totalCeiling": decimal_to_float(self.total_ceiling),
            "savingsByDates": [s.to_dict() for s in self.savings_by_dates],
        }
