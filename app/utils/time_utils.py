"""
Date / time utility helpers.

All timestamps are parsed and serialised as ``"YYYY-MM-DD HH:mm:ss"``
(i.e. the Python format string ``"%Y-%m-%d %H:%M:%S"``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_timestamp(raw: str) -> datetime:
    """
    Parse a timestamp string into a :class:`~datetime.datetime`.

    Parameters
    ----------
    raw:
        A string conforming to ``"YYYY-MM-DD HH:mm:ss"``.

    Raises
    ------
    ValueError
        If *raw* does not match the expected format.
    """
    try:
        return datetime.strptime(raw, TIMESTAMP_FORMAT)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid timestamp {raw!r}. Expected format: YYYY-MM-DD HH:mm:ss"
        ) from exc


def format_timestamp(dt: datetime) -> str:
    """Serialise a :class:`~datetime.datetime` to ``"YYYY-MM-DD HH:mm:ss"``."""
    return dt.strftime(TIMESTAMP_FORMAT)


def is_valid_timestamp(raw: str) -> bool:
    """Return ``True`` when *raw* is a well-formed timestamp string."""
    try:
        parse_timestamp(raw)
        return True
    except ValueError:
        return False


def is_within_range(dt: datetime, start: datetime, end: datetime) -> bool:
    """
    Return ``True`` when *dt* falls inside [*start*, *end*] (inclusive).
    """
    return start <= dt <= end


def parse_optional_timestamp(raw: Optional[str]) -> Optional[datetime]:
    """Return ``None`` if *raw* is ``None``; otherwise delegate to :func:`parse_timestamp`."""
    if raw is None:
        return None
    return parse_timestamp(raw)
