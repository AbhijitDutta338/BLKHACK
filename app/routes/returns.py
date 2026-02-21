"""
Returns calculation routes.

Endpoints
---------
POST /blackrock/challenge/v1/returns:nps
    Compound-growth projection using NPS rate (7.11 %) + tax benefit.

POST /blackrock/challenge/v1/returns:index
    Compound-growth projection using Index fund rate (14.49 %).
"""

from __future__ import annotations

from typing import Any, Dict, List

from flask import Blueprint, Response, jsonify, request

from app.models.schemas import KRange, PRule, QRule, RawExpense
from app.services.return_service import calculate_returns
from app.utils.financial import to_decimal
from app.utils.time_utils import parse_timestamp

returns_bp = Blueprint("returns", __name__)

BASE = "/blackrock/challenge/v1"


# ── Shared parsing helpers ────────────────────────────────────────────────────

def _parse_expense(raw: Dict[str, Any]) -> RawExpense:
    for key in ("timestamp", "amount"):
        if key not in raw:
            raise ValueError(f"Expense missing field: {key!r}")
    return RawExpense(
        timestamp=raw["timestamp"],
        amount=to_decimal(raw["amount"]),
    )


def _parse_q_rule(raw: Dict[str, Any]) -> QRule:
    for key in ("fixed", "start", "end"):
        if key not in raw:
            raise ValueError(f"Q rule missing field: {key!r}")
    return QRule(
        fixed=to_decimal(raw["fixed"]),
        start=parse_timestamp(raw["start"]),
        end=parse_timestamp(raw["end"]),
    )


def _parse_p_rule(raw: Dict[str, Any]) -> PRule:
    for key in ("extra", "start", "end"):
        if key not in raw:
            raise ValueError(f"P rule missing field: {key!r}")
    return PRule(
        extra=to_decimal(raw["extra"]),
        start=parse_timestamp(raw["start"]),
        end=parse_timestamp(raw["end"]),
    )


def _parse_k_range(raw: Dict[str, Any]) -> KRange:
    for key in ("start", "end"):
        if key not in raw:
            raise ValueError(f"K range missing field: {key!r}")
    return KRange(
        start=parse_timestamp(raw["start"]),
        end=parse_timestamp(raw["end"]),
    )


def _parse_returns_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and validate all common fields from a returns request body.

    Returns a dict with parsed, typed values.
    """
    for key in ("age", "wage", "inflation", "transactions", "k"):
        if key not in body:
            raise ValueError(f"Missing required field: {key!r}")

    age = body["age"]
    if not isinstance(age, int) or isinstance(age, bool):
        raise ValueError(f"'age' must be an integer, got {type(age).__name__}.")

    wage = to_decimal(body["wage"])
    if wage <= 0:
        raise ValueError("'wage' must be a positive number.")

    inflation = to_decimal(body["inflation"])

    q_rules: List[QRule] = [_parse_q_rule(r) for r in body.get("q", [])]
    p_rules: List[PRule] = [_parse_p_rule(r) for r in body.get("p", [])]
    k_ranges: List[KRange] = [_parse_k_range(r) for r in body.get("k", [])]

    if not k_ranges:
        raise ValueError("At least one K range is required.")

    transactions_raw = body["transactions"]
    if not isinstance(transactions_raw, list):
        raise ValueError("'transactions' must be a list.")

    expenses = [_parse_expense(t) for t in transactions_raw]

    return {
        "age": age,
        "wage": wage,
        "inflation": inflation,
        "q_rules": q_rules,
        "p_rules": p_rules,
        "k_ranges": k_ranges,
        "expenses": expenses,
    }


# ── Endpoint: NPS returns ─────────────────────────────────────────────────────

@returns_bp.route(f"{BASE}/returns:nps", methods=["POST"])
def returns_nps() -> tuple[Response, int]:
    """
    Compute NPS compound-growth returns with tax benefit.

    Uses an annual rate of **7.11 %**.
    Tax benefit = ``tax(wage) - tax(wage - deduction)`` per K bucket.

    Expects JSON body::

        {
            "age": integer,
            "wage": number,
            "inflation": number,
            "q": [...],
            "p": [...],
            "k": [...],
            "transactions": [{"timestamp": "...", "amount": number}]
        }
    """
    body: Dict[str, Any] | None = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid or missing JSON body."}), 400

    try:
        params = _parse_returns_body(body)
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 422

    try:
        result = calculate_returns(**params, include_tax_benefit=True)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Calculation error: {exc}"}), 500

    return jsonify(result.to_dict()), 200


# ── Endpoint: Index returns ───────────────────────────────────────────────────

@returns_bp.route(f"{BASE}/returns:index", methods=["POST"])
def returns_index() -> tuple[Response, int]:
    """
    Compute Index fund compound-growth returns (no tax benefit).

    Uses an annual rate of **14.49 %**.

    Expects the same JSON body structure as ``/returns:nps``.
    """
    body: Dict[str, Any] | None = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid or missing JSON body."}), 400

    try:
        params = _parse_returns_body(body)
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 422

    try:
        result = calculate_returns(**params, include_tax_benefit=False)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Calculation error: {exc}"}), 500

    return jsonify(result.to_dict()), 200
