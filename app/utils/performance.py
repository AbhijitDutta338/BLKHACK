"""
System performance snapshot utilities.
"""

from __future__ import annotations

import threading
import time

import psutil


def get_process_memory_mb() -> float:
    """
    Return the RSS (Resident Set Size) of the current process in megabytes.
    Uses :mod:`psutil` for cross-platform accuracy.
    """
    process = psutil.Process()
    rss_bytes: int = process.memory_info().rss
    return rss_bytes / (1024 * 1024)


def get_active_thread_count() -> int:
    """Return the number of currently active Python threads."""
    return threading.active_count()


def collect_performance_snapshot(last_request_ms: float) -> dict:
    """
    Build a performance metrics dictionary.

    Parameters
    ----------
    last_request_ms:
        Execution time of the most recently completed request, in milliseconds.

    Returns
    -------
    dict
        ``{"time": "...", "memory": "...", "threads": int}``
    """
    memory_mb = get_process_memory_mb()
    threads = get_active_thread_count()

    return {
        "time": f"{last_request_ms:.4f} ms",
        "memory": f"{memory_mb:.2f} MB",
        "threads": threads,
    }
