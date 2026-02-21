from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


#Raw input atoms
@dataclass(frozen=True)
class RawExpense:

    timestamp: str
    amount: Decimal


@dataclass(frozen=True)
class RawTransaction:
    
    date: str
    amount: Decimal
    ceiling: Decimal
    remanent: Decimal


#Enriched transaction (output of builder) 
@dataclass(frozen=True)
class Transaction:
    
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
    
    transaction: Transaction
    message: str

    def to_dict(self) -> dict:
        d = self.transaction.to_dict()
        d["message"] = self.message
        return d


@dataclass(frozen=True)
class ValidationResult:
    
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
    
    fixed: Decimal
    start: datetime
    end: datetime


@dataclass(frozen=True)
class PRule:
    
    extra: Decimal
    start: datetime
    end: datetime


@dataclass(frozen=True)
class KRange:
    
    start: datetime
    end: datetime
    raw_start: str = ""
    raw_end: str = ""


#Temporal filter output
@dataclass(frozen=True)
class TemporalResult:
    
    valid: List[Transaction]
    invalid: List[InvalidTransaction]

    def to_dict(self) -> dict:
        return {
            "valid": [t.to_dict() for t in self.valid],
            "invalid": [t.to_dict() for t in self.invalid],
        }


@dataclass(frozen=True)
class FilteredTransaction:
    
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
