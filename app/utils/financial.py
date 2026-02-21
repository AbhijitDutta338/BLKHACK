"""
Financial utility functions.

All monetary values use :class:`decimal.Decimal` to guarantee
sub-cent accuracy and avoid IEEE-754 floating-point drift.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Tuple


#Constants
HUNDRED = Decimal("100")
ZERO = Decimal("0")

NPS_ANNUAL_RATE = Decimal("0.0711")
INDEX_ANNUAL_RATE = Decimal("0.1449")
NPS_MAX_ABSOLUTE = Decimal("200000")
NPS_WAGE_FRACTION = Decimal("0.10")

# Tax slab boundaries (INR)
_SLAB_7L = Decimal("700000")
_SLAB_10L = Decimal("1000000")
_SLAB_12L = Decimal("1200000")
_SLAB_15L = Decimal("1500000")


#Ceiling & remanent
def compute_ceiling(amount: Decimal) -> Decimal:
    return (amount / HUNDRED).to_integral_value(rounding=ROUND_CEILING) * HUNDRED


def compute_remanent(ceiling: Decimal, amount: Decimal) -> Decimal:
    return ceiling - amount


#Tax calculations
def calculate_tax(income: Decimal) -> Decimal:
    if income <= ZERO:
        return ZERO

    tax = ZERO

    if income > _SLAB_7L:
        band = min(income, _SLAB_10L) - _SLAB_7L
        tax += band * Decimal("0.10")

    if income > _SLAB_10L:
        band = min(income, _SLAB_12L) - _SLAB_10L
        tax += band * Decimal("0.15")

    if income > _SLAB_12L:
        band = min(income, _SLAB_15L) - _SLAB_12L
        tax += band * Decimal("0.20")

    if income > _SLAB_15L:
        band = income - _SLAB_15L
        tax += band * Decimal("0.30")

    return tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_nps_deduction(invested: Decimal, wage: Decimal) -> Decimal:
    return min(invested, wage * NPS_WAGE_FRACTION, NPS_MAX_ABSOLUTE)


def compute_tax_benefit(wage: Decimal, deduction: Decimal) -> Decimal:
    return calculate_tax(wage) - calculate_tax(wage - deduction)


#Compound interest
def compound_grow(principal: Decimal, rate: Decimal, years: int) -> Decimal:
    
    if years <= 0:
        return principal
    return principal * (Decimal("1") + rate) ** years


def inflation_adjusted(nominal: Decimal, inflation: Decimal, years: int) -> Decimal:
    if years <= 0:
        return nominal
    divisor = (Decimal("1") + inflation) ** years
    return (nominal / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def resolve_investment_years(age: int) -> int:
    years = 60 - age
    return max(years, 5)


#Serialisation helpers
def decimal_to_float(value: Decimal) -> float:
    return float(value)


def to_decimal(value: int | float | str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"Cannot convert {value!r} to Decimal: {exc}") from exc
