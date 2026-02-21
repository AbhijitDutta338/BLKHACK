from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from flask import Blueprint, Response, jsonify, request

from app.models.schemas import (
    KRange,
    PRule,
    QRule,
    RawExpense,
    Transaction,
)
from app.services.temporal_service import apply_temporal_filter, apply_temporal_filter_raw
from app.services.transaction_service import build_transactions
from app.services.validation_service import validate_transactions
from app.utils.financial import to_decimal
from app.utils.time_utils import format_timestamp, parse_timestamp

transactions_bp = Blueprint("transactions", __name__)

BASE = "/blackrock/challenge/v1"


#Shared parsing helpers
def _parse_transaction_dict(raw: Dict[str, Any]) -> Transaction:
    required = ("date", "amount", "ceiling", "remanent")
    for key in required:
        if key not in raw:
            raise ValueError(f"Missing required field: {key!r}")
    return Transaction(
        date=parse_timestamp(raw["date"]),
        amount=to_decimal(raw["amount"]),
        ceiling=to_decimal(raw["ceiling"]),
        remanent=to_decimal(raw["remanent"]),
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


#Endpoint: parse 
@transactions_bp.route(f"{BASE}/transactions:parse", methods=["POST"])
def parse_transactions() -> tuple[Response, int]:

    expenses_raw = request.get_json(silent=True)
    if not isinstance(expenses_raw, list):
        return jsonify({"error": "'expenses' must be a list."}), 422

    try:
        expenses = [
            RawExpense(
                timestamp=_require_str(e, "date"),
                amount=to_decimal(_require_field(e, "amount")),
            )
            for e in expenses_raw
        ]
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 422

    try:
        result = build_transactions(expenses)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    return jsonify(result.to_dict()), 200


#Endpoint: validator
@transactions_bp.route(f"{BASE}/transactions:validator", methods=["POST"])
def validator_transactions() -> tuple[Response, int]:
    
    body: Dict[str, Any] | None = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid or missing JSON body."}), 400

    try:
        wage = to_decimal(_require_field(body, "wage"))
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 422

    if wage <= 0:
        return jsonify({"error": "'wage' must be a positive number."}), 422

    transactions_raw = body.get("transactions")
    if not isinstance(transactions_raw, list):
        return jsonify({"error": "'transactions' must be a list."}), 422

    try:
        transactions = [_parse_transaction_dict(t) for t in transactions_raw]
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 422

    result = validate_transactions(wage=wage, transactions=transactions)
    return jsonify(result.to_dict()), 200


#Endpoint: filter (temporal constraints) 
@transactions_bp.route(f"{BASE}/transactions:filter", methods=["POST"])
def filter_transactions() -> tuple[Response, int]:
    body: Dict[str, Any] | None = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid or missing JSON body."}), 400

    try:
        q_rules = [_parse_q_rule(r) for r in body.get("q", [])]
        p_rules = [_parse_p_rule(r) for r in body.get("p", [])]
        k_ranges = [_parse_k_range(r) for r in body.get("k", [])]
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 422

    if not k_ranges:
        return jsonify({"error": "At least one K range is required."}), 422

    transactions_raw = body.get("transactions")
    if not isinstance(transactions_raw, list):
        return jsonify({"error": "'transactions' must be a list."}), 422

    # Validate each entry has the required minimal fields
    try:
        raw_list: List[Dict[str, Any]] = []
        for i, t in enumerate(transactions_raw):
            if "date" not in t:
                raise ValueError(f"Transaction #{i}: missing 'date' field.")
            if "amount" not in t:
                raise ValueError(f"Transaction #{i}: missing 'amount' field.")
            raw_list.append({"date": str(t["date"]), "amount": t["amount"]})
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 422

    result = apply_temporal_filter_raw(q_rules, p_rules, k_ranges, raw_list)
    return jsonify(result.to_dict()), 200


#Internal field-access helpers 
def _require_field(obj: Dict[str, Any], key: str) -> Any:
    if key not in obj:
        raise KeyError(f"Missing required field: {key!r}")
    return obj[key]


def _require_str(obj: Dict[str, Any], key: str) -> str:
    val = _require_field(obj, key)
    if not isinstance(val, str):
        raise ValueError(f"Field {key!r} must be a string, got {type(val).__name__}.")
    return val
