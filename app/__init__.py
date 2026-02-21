"""
Application factory with performance measurement middleware.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from flask import Flask, Response, g, jsonify, request

# Thread-safe store for last request timing
_last_request_lock = threading.Lock()
_last_request_time_ms: float = 0.0


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # ── Performance middleware ──────────────────────────────────────────────

    @app.before_request
    def _start_timer() -> None:
        g.start_time = time.perf_counter()

    @app.after_request
    def _stop_timer(response: Response) -> Response:
        global _last_request_time_ms
        elapsed = (time.perf_counter() - g.start_time) * 1_000
        with _last_request_lock:
            _last_request_time_ms = elapsed
        response.headers["X-Response-Time-Ms"] = f"{elapsed:.4f}"
        return response

    # ── Error handlers ──────────────────────────────────────────────────────

    @app.errorhandler(400)
    def bad_request(exc: Any) -> tuple[Response, int]:
        return jsonify({"error": "Bad Request", "message": str(exc)}), 400

    @app.errorhandler(404)
    def not_found(exc: Any) -> tuple[Response, int]:
        return jsonify({"error": "Not Found", "message": str(exc)}), 404

    @app.errorhandler(405)
    def method_not_allowed(exc: Any) -> tuple[Response, int]:
        return jsonify({"error": "Method Not Allowed", "message": str(exc)}), 405

    @app.errorhandler(422)
    def unprocessable(exc: Any) -> tuple[Response, int]:
        return jsonify({"error": "Unprocessable Entity", "message": str(exc)}), 422

    @app.errorhandler(500)
    def internal_error(exc: Any) -> tuple[Response, int]:
        return jsonify({"error": "Internal Server Error", "message": str(exc)}), 500

    # ── Register blueprints ─────────────────────────────────────────────────

    from app.routes.transactions import transactions_bp
    from app.routes.returns import returns_bp
    from app.routes.performance import performance_bp

    app.register_blueprint(transactions_bp)
    app.register_blueprint(returns_bp)
    app.register_blueprint(performance_bp)

    return app


def get_last_request_time_ms() -> float:
    """Return the execution time of the most recently completed request (ms)."""
    with _last_request_lock:
        return _last_request_time_ms
