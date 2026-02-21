from __future__ import annotations

from flask import Blueprint, Response, jsonify

from app import get_last_request_time_ms
from app.utils.performance import collect_performance_snapshot

performance_bp = Blueprint("performance", __name__)

BASE = "/blackrock/challenge/v1"


@performance_bp.route(f"{BASE}/performance", methods=["GET"])
def get_performance() -> tuple[Response, int]:

    last_ms = get_last_request_time_ms()
    snapshot = collect_performance_snapshot(last_ms)
    return jsonify(snapshot), 200
