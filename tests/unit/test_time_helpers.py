"""
Тесты утилит времени.

Чистые функции — не нужны ни БД, ни Redis.
"""

from datetime import date, datetime, timezone

from src.utils.time_helpers import (
    get_seconds_until_midnight,
    get_today_date,
    get_today_str,
)


class TestGetSecondsUntilMidnight:

    def test_returns_positive_value(self):
        seconds = get_seconds_until_midnight()
        assert seconds > 0

    def test_returns_less_than_day(self):
        seconds = get_seconds_until_midnight()
        assert seconds <= 86_400  # 24 * 60 * 60

    def test_returns_int(self):
        seconds = get_seconds_until_midnight()
        assert isinstance(seconds, int)


class TestGetTodayStr:

    def test_returns_string(self):
        result = get_today_str()
        assert isinstance(result, str)

    def test_format_is_iso_date(self):
        result = get_today_str()
        # Должно парситься как дата
        parsed = date.fromisoformat(result)
        assert parsed == datetime.now(timezone.utc).replace(tzinfo=None).date()

    def test_matches_today(self):
        result = get_today_str()
        expected = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")
        assert result == expected


class TestGetTodayDate:

    def test_returns_date_object(self):
        result = get_today_date()
        assert isinstance(result, date)

    def test_matches_utc_today(self):
        result = get_today_date()
        assert result == datetime.now(timezone.utc).replace(tzinfo=None).date()
