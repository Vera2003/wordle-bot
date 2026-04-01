"""Time helper functions with no framework or layer-specific dependencies."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


def get_seconds_until_midnight() -> int:
    """Return the number of seconds remaining until the next UTC midnight."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    midnight = datetime.combine(now.date(), time.min) + timedelta(days=1)
    return int((midnight - now).total_seconds())


def get_today_str() -> str:
    """Return today's UTC date formatted as YYYY-MM-DD."""
    return datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")


def get_today_date() -> date:
    """Return today's UTC date."""
    return datetime.now(timezone.utc).replace(tzinfo=None).date()