"""入金日（日付のみ）→ paid_at 変換規則のテスト。

対応 AC: docs/handoff/paid-at-payment-date/design.md #1〜#2。
"""

from datetime import date, datetime, timezone

import pytest

from app.services.payment_dates import (
    PAID_AT_SQL,
    paid_at_from_date,
    parse_paypal_payment_date,
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
