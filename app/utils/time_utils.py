"""
Date / time utility helpers.

All timestamps are parsed and serialised as ``"YYYY-MM-DD HH:mm:ss"``
(i.e. the Python format string ``"%Y-%m-%d %H:%M:%S"``).
"""

from __future__ import annotations

import calendar
from datetime import datetime
from typing import Optional

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_timestamp(raw: str) -> datetime:
    try:
        return datetime.strptime(raw, TIMESTAMP_FORMAT)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid timestamp {raw!r}. Expected format: YYYY-MM-DD HH:mm:ss"
        ) from exc


def parse_timestamp_lenient(raw: str) -> datetime:
    # Fast path – valid date
    try:
        return datetime.strptime(raw, TIMESTAMP_FORMAT)
    except (ValueError, TypeError):
        pass

    # Slow path – attempt day clamping
    try:
        date_part, time_part = raw.strip().split(" ", 1)
        y_str, m_str, d_str = date_part.split("-")
        year, month, day = int(y_str), int(m_str), int(d_str)
        max_day = calendar.monthrange(year, month)[1]
        day = min(day, max_day)
        clamped = f"{year:04d}-{month:02d}-{day:02d} {time_part}"
        return datetime.strptime(clamped, TIMESTAMP_FORMAT)
    except Exception as exc:
        raise ValueError(
            f"Invalid timestamp {raw!r}. Expected format: YYYY-MM-DD HH:mm:ss"
        ) from exc


def format_timestamp(dt: datetime) -> str:
    return dt.strftime(TIMESTAMP_FORMAT)


def is_valid_timestamp(raw: str) -> bool:
    try:
        parse_timestamp(raw)
        return True
    except ValueError:
        return False


def is_within_range(dt: datetime, start: datetime, end: datetime) -> bool:
    return start <= dt <= end


def parse_optional_timestamp(raw: Optional[str]) -> Optional[datetime]:
    if raw is None:
        return None
    return parse_timestamp(raw)
