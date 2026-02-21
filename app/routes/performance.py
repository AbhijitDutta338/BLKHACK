"""
Performance metrics route.

Endpoint
--------
GET /blackrock/challenge/v1/performance

Returns the execution time of the most recently completed request,
current process RSS memory usage, and active thread count.
"""

from __future__ import annotations

from flask import Blueprint, Response, jsonify

from app import get_last_request_time_ms
from app.utils.performance import collect_performance_snapshot

performance_bp = Blueprint("performance", __name__)

BASE = "/blackrock/challenge/v1"


@performance_bp.route(f"{BASE}/performance", methods=["GET"])
def get_performance() -> tuple[Response, int]:
    """
    Return a live performance snapshot.

    Response body::

        {
            "time":    "X.XXXX ms",
            "memory":  "XXX.XX MB",
            "threads": integer
        }

    * **time** – execution time of the most recently completed request.
    * **memory** – current process RSS (from :mod:`psutil`).
    * **threads** – active Python thread count (``threading.active_count()``).
    """
    last_ms = get_last_request_time_ms()
    snapshot = collect_performance_snapshot(last_ms)
    return jsonify(snapshot), 200
