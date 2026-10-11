"""入金日（日付のみ）→ paid_at 変換規則のテスト。

対応 AC: docs/handoff/paid-at-payment-date/design.md #1〜#2。
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.payment_dates import (
    PAID_AT_SQL,
    PAYPAL_DATE_RECENT_WINDOW,
    paid_at_from_date,
    parse_paypal_payment_date,
    paypal_paid_at,
)


def test_paid_at_from_date_is_utc_noon():
    out = paid_at_from_date(date(2026, 10, 5))
    assert out == datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    assert out.tzinfo is not None


def test_paid_at_from_date_none_returns_none():
    assert paid_at_from_date(None) is None


def test_paid_at_sql_clamps_to_now():
    assert PAID_AT_SQL == "LEAST(COALESCE(:paid_at, NOW()), NOW())"


def test_parse_paypal_payment_date_valid():
    assert parse_paypal_payment_date("2026-10-05") == date(2026, 10, 5)


@pytest.mark.parametrize(
    "value",
    [None, "", "2026-13-01", "2026-10-05T01:00:00Z", 123],
)
def test_parse_paypal_payment_date_invalid_returns_none(value):
    assert parse_paypal_payment_date(value) is None


_NOW = datetime(2026, 10, 9, 3, 0, tzinfo=timezone.utc)


def test_recent_window_is_36_hours():
    assert PAYPAL_DATE_RECENT_WINDOW == timedelta(hours=36)


def test_paypal_paid_at_none_returns_none():
    assert paypal_paid_at(None, now=_NOW) is None


@pytest.mark.parametrize("d", [date(2026, 10, 9), date(2026, 10, 8)])
def test_paypal_paid_at_recent_returns_none(d):
    assert paypal_paid_at(d, now=_NOW) is None


@pytest.mark.parametrize(
    "d, expected",
    [
        (date(2026, 10, 7), datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)),
        (date(2026, 9, 1), datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)),
    ],
)
def test_paypal_paid_at_old_returns_utc_noon(d, expected):
    assert paypal_paid_at(d, now=_NOW) == expected


def test_paypal_paid_at_default_now_treats_today_as_recent():
    assert paypal_paid_at(datetime.now(timezone.utc).date()) is None
