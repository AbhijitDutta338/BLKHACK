from __future__ import annotations

from typing import Any, Dict, List

from flask import Blueprint, Response, jsonify, request

from app.models.schemas import KRange, PRule, QRule
from app.services.return_service import calculate_returns
from app.utils.financial import to_decimal
from app.utils.time_utils import parse_timestamp, parse_timestamp_lenient

returns_bp = Blueprint("returns", __name__)

BASE = "/blackrock/challenge/v1"


#Shared parsing helpers
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
    raw_start: str = raw["start"]
    raw_end: str = raw["end"]
    return KRange(
        start=parse_timestamp_lenient(raw_start),
        end=parse_timestamp_lenient(raw_end),
        raw_start=raw_start,
        raw_end=raw_end,
    )


def _parse_returns_body(body: Dict[str, Any]) -> Dict[str, Any]:

    for key in ("age", "wage", "inflation", "transactions", "k"):
        if key not in body:
            raise ValueError(f"Missing required field: {key!r}")

    age = body["age"]
    if not isinstance(age, int) or isinstance(age, bool):
        raise ValueError(f"'age' must be an integer, got {type(age).__name__}.")

    # wage is monthly → convert to annual
    monthly_wage = to_decimal(body["wage"])
    if monthly_wage <= 0:
        raise ValueError("'wage' must be a positive number.")
    annual_wage = monthly_wage * 12

    # inflation is a percentage (e.g. 5.5) → convert to decimal (0.055)
    inflation = to_decimal(body["inflation"]) / 100

    q_rules: List[QRule] = [_parse_q_rule(r) for r in body.get("q", [])]
    p_rules: List[PRule] = [_parse_p_rule(r) for r in body.get("p", [])]
    k_ranges: List[KRange] = [_parse_k_range(r) for r in body.get("k", [])]

    if not k_ranges:
        raise ValueError("At least one K range is required.")

    transactions_raw = body["transactions"]
    if not isinstance(transactions_raw, list):
        raise ValueError("'transactions' must be a list.")

    # Validate each entry has date + amount
    raw_list: List[Dict[str, Any]] = []
    for i, t in enumerate(transactions_raw):
        if "date" not in t:
            raise ValueError(f"Transaction #{i}: missing 'date' field.")
        if "amount" not in t:
            raise ValueError(f"Transaction #{i}: missing 'amount' field.")
        raw_list.append({"date": str(t["date"]), "amount": t["amount"]})

    return {
        "age": age,
        "annual_wage": annual_wage,
        "inflation": inflation,
        "q_rules": q_rules,
        "p_rules": p_rules,
        "k_ranges": k_ranges,
        "raw_transactions": raw_list,
    }


#Endpoint: NPS returns
@returns_bp.route(f"{BASE}/returns:nps", methods=["POST"])
def returns_nps() -> tuple[Response, int]:
    
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


#Endpoint: Index returns
@returns_bp.route(f"{BASE}/returns:index", methods=["POST"])
def returns_index() -> tuple[Response, int]:
    
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
