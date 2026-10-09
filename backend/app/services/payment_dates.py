"""入金日（日付のみ）を paid_at（timestamptz）へ変換する規則の SSOT。

PayPal Invoicing v2 の payments.transactions[].payment_date は schema `date_no_time`
（"YYYY-MM-DD"・時刻/時差なし）。DB の paid_at は timestamptz のため、
  - 日付 d は UTC 正午（UTC-11〜+11 のどの画面でも同じ日付で表示される）に変換する
  - asyncpg は timestamptz に str を渡せない（TypeError）ため、必ず datetime で渡す
  - SQL 側で未来になる場合は現在時刻に丸める（PAID_AT_SQL）
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

# invoices / orders の UPDATE で paid_at に使う SQL 断片（:paid_at は paid_at_from_date の結果）
PAID_AT_SQL = "LEAST(COALESCE(:paid_at, NOW()), NOW())"

_NOON_HOUR = 12


def paid_at_from_date(d: date | None) -> datetime | None:
    """日付 → UTC 正午の datetime。None は None（SQL 側で NOW() になる）。"""
    if d is None:
        return None
    return datetime(d.year, d.month, d.day, _NOON_HOUR, 0, tzinfo=timezone.utc)


def parse_paypal_payment_date(value: object) -> date | None:
    """PayPal の payment_date（"YYYY-MM-DD"）を date に変換する。解析できなければ None。"""
    if value is None:
        return None
    if not isinstance(value, str):
        logger.warning("[paypal] payment_date が文字列ではありません: %r", value)
        return None
    if len(value) != 10:
        logger.warning("[paypal] payment_date の形式が不正です: %r", value)
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        logger.warning("[paypal] payment_date を解析できません: %r", value)
        return None
