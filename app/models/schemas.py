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


# ── Raw input atoms ──────────────────────────────────────────────────────────

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


# ── Enriched transaction (output of builder) ─────────────────────────────────

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


# ── Parser output ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ParseResult:
    """Output of the transaction builder service."""
    transactions: List[Transaction]
    total_expense: Decimal
    total_ceiling: Decimal
    total_remanent: Decimal

    def to_dict(self) -> dict:
        from app.utils.financial import decimal_to_float
        return {
            "transactions": [t.to_dict() for t in self.transactions],
            "totalExpense": decimal_to_float(self.total_expense),
            "totalCeiling": decimal_to_float(self.total_ceiling),
            "totalRemanent": decimal_to_float(self.total_remanent),
        }


# ── Validation output ─────────────────────────────────────────────────────────

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


# ── Temporal rule definitions ─────────────────────────────────────────────────

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


# ── Temporal filter output ────────────────────────────────────────────────────

@dataclass(frozen=True)
class TemporalResult:
    """Output of the temporal constraints filter service."""
    valid: List[Transaction]
    invalid: List[InvalidTransaction]

    def to_dict(self) -> dict:
        return {
            "valid": [t.to_dict() for t in self.valid],
            "invalid": [t.to_dict() for t in self.invalid],
        }


# ── Returns output ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SavingsByDate:
    """Compounded return figure for one K period."""
    start: datetime
    end: datetime
    amount: Decimal
    profits: Decimal
    tax_benefit: Decimal

    def to_dict(self) -> dict:
        from app.utils.time_utils import format_timestamp
        from app.utils.financial import decimal_to_float
        return {
            "start": format_timestamp(self.start),
            "end": format_timestamp(self.end),
            "amount": decimal_to_float(self.amount),
            "profits": decimal_to_float(self.profits),
            "taxBenefit": decimal_to_float(self.tax_benefit),
        }


@dataclass(frozen=True)
class ReturnsResult:
    """Output of both NPS and Index returns services."""
    transactions_total_amount: Decimal
    transactions_total_ceiling: Decimal
    savings_by_dates: List[SavingsByDate]

    def to_dict(self) -> dict:
        from app.utils.financial import decimal_to_float
        return {
            "transactionsTotalAmount": decimal_to_float(self.transactions_total_amount),
            "transactionsTotalCeiling": decimal_to_float(self.transactions_total_ceiling),
            "savingsByDates": [s.to_dict() for s in self.savings_by_dates],
        }
