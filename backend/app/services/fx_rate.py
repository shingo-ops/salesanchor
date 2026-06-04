"""
為替レートライブ取得サービス（C-7）。

外部API: open.er-api.com (ExchangeRate-API 無料エンドポイント・API キー不要)
- 取得レートを fx_rate_snapshot JSONB として保存
- JPY 指定時はスキップ（None を返す）
- fetch 失敗時は警告ログ + None を返す（non-fatal）

使い方:
    from app.services.fx_rate import get_fx_rate
    snapshot = get_fx_rate("USD")
    # {"currency": "USD", "rate": 150.25, "fetched_at": "2026-06-04T10:00:00Z"}
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# 環境変数 FX_RATE_API_KEY は将来の有料プラン切り替え用（現在は未使用）
FX_API_KEY = os.getenv("FX_RATE_API_KEY", "")
# JPY 基準の無料エンドポイント（APIキー不要）
FX_BASE_URL = "https://open.er-api.com/v6/latest/JPY"


def get_fx_rate(currency: str) -> dict | None:
    """
    JPY 基準で currency の為替レートを取得する。

    Args:
        currency: 通貨コード（例: "USD", "EUR"）

    Returns:
        {"currency": "USD", "rate": 150.25, "fetched_at": "2026-06-04T10:00:00Z"}
        JPY 指定時、または取得失敗時は None を返す。
    """
    if currency.upper() == "JPY":
        return None

    try:
        resp = httpx.get(FX_BASE_URL, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        rate = rates.get(currency.upper())

        if rate is None:
            logger.warning("fx_rate: currency %s not found in response", currency)
            return None

        # open.er-api.com は JPY 基準なので rates["USD"] = 0.006... (1 JPY の USD 換算)
        # 請求書で必要なのは「1 外貨 = N JPY」なので inverse を計算する
        if rate == 0:
            logger.warning("fx_rate: rate is 0 for currency %s, skipping", currency)
            return None

        jpy_per_currency = 1.0 / rate

        return {
            "currency": currency.upper(),
            "rate": round(jpy_per_currency, 4),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:  # noqa: BLE001
        logger.warning("fx_rate fetch failed for %s: %s", currency, e)
        return None
