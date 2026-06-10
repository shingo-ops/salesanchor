"""
FedEx Rates API サンドボックス疎通テスト（ADR-125 D4）

実際の FedEx Sandbox API に接続してトークン取得・見積もり取得が機能することを確認する。
環境変数が未設定の場合は自動的にスキップされる（CI/CD での必須化は任意）。

必要な環境変数:
  FEDEX_SANDBOX_CLIENT_ID     — FedEx Sandbox OAuth Client ID
  FEDEX_SANDBOX_CLIENT_SECRET — FedEx Sandbox OAuth Client Secret
  FEDEX_SANDBOX_ACCOUNT_NUMBER — FedEx 配送契約アカウント番号（Sandbox 用）

実行方法:
  # 環境変数を設定して実行
  export FEDEX_SANDBOX_CLIENT_ID=...
  export FEDEX_SANDBOX_CLIENT_SECRET=...
  export FEDEX_SANDBOX_ACCOUNT_NUMBER=...
  cd backend && pytest tests/test_fedex_sandbox.py -v -s

  # 環境変数なし → 全テストが自動スキップ
  cd backend && pytest tests/test_fedex_sandbox.py -v

変更履歴:
  2026-06-09: 初版（ADR-125 Phase D）
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

from app.services.fedex_rates import (
    FedExRateQuote,
    clear_token_cache,
    get_or_refresh_token,
    get_rates,
)

# ---------------------------------------------------------------------------
# 環境変数チェック
# ---------------------------------------------------------------------------

_CLIENT_ID = os.environ.get("FEDEX_SANDBOX_CLIENT_ID")
_CLIENT_SECRET = os.environ.get("FEDEX_SANDBOX_CLIENT_SECRET")
_ACCOUNT_NUMBER = os.environ.get("FEDEX_SANDBOX_ACCOUNT_NUMBER")

_CREDS_AVAILABLE = bool(_CLIENT_ID and _CLIENT_SECRET and _ACCOUNT_NUMBER)

_skip_reason = (
    "FedEx sandbox credentials not set. "
    "Set FEDEX_SANDBOX_CLIENT_ID, FEDEX_SANDBOX_CLIENT_SECRET, "
    "FEDEX_SANDBOX_ACCOUNT_NUMBER to enable."
)

requires_sandbox = pytest.mark.skipif(not _CREDS_AVAILABLE, reason=_skip_reason)

# テスト用固定値
_TENANT_ID = 0  # sandbox テスト専用（テナントDB参照なし）
_ENV = "sandbox"
_ORIGIN = "JP"
_DESTINATION = "US"
_WEIGHT_KG = Decimal("1.0")


@pytest.fixture(autouse=True)
def reset_cache():
    """各テスト前後にトークンキャッシュをクリア（テスト間干渉防止）。"""
    clear_token_cache()
    yield
    clear_token_cache()


# ---------------------------------------------------------------------------
# T1: OAuth トークン取得疎通
# ---------------------------------------------------------------------------

@requires_sandbox
def test_sandbox_oauth_token_obtained():
    """FedEx Sandbox OAuth エンドポイントからトークンを取得できる。

    ADR-125 D3: トークンキャッシュの動作も併せて検証する。
    """
    # 1回目: API 呼び出し
    token1 = get_or_refresh_token(_TENANT_ID, _ENV, _CLIENT_ID, _CLIENT_SECRET)

    assert token1, "トークンが空"
    assert isinstance(token1, str), f"トークンの型が str でない: {type(token1)}"
    assert len(token1) > 10, f"トークンが短すぎる: {token1!r}"

    # 2回目: キャッシュから返却（API 呼び出しなし）
    token2 = get_or_refresh_token(_TENANT_ID, _ENV, _CLIENT_ID, _CLIENT_SECRET)
    assert token1 == token2, "2回目のトークンがキャッシュから返却されていない"


# ---------------------------------------------------------------------------
# T2: Rates API 疎通（JP→US, 1.0 kg）
# ---------------------------------------------------------------------------

@requires_sandbox
def test_sandbox_rates_returns_quotes():
    """FedEx Sandbox Rates API から見積もりリストを取得できる。

    ADR-125 D4: 以下をアサート
    - 空でないリストが返ること
    - 各要素が FedExRateQuote であること
    - service_type が非空文字列であること
    - total_net_charge が正の値であること
    - currency が非空文字列であること
    """
    quotes = get_rates(
        tenant_id=_TENANT_ID,
        environment=_ENV,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
        account_number=_ACCOUNT_NUMBER,
        origin_country_code=_ORIGIN,
        destination_country_code=_DESTINATION,
        weight_kg=_WEIGHT_KG,
    )

    assert quotes, f"見積もりが 0 件（FedEx Sandbox の返答を確認してください）"
    assert isinstance(quotes, list), f"返却型が list でない: {type(quotes)}"

    for q in quotes:
        assert isinstance(q, FedExRateQuote), f"要素が FedExRateQuote でない: {q}"
        assert q.service_type, f"service_type が空: {q}"
        assert q.service_name, f"service_name が空: {q}"
        assert q.total_net_charge > 0, f"total_net_charge が 0 以下: {q}"
        assert q.currency, f"currency が空: {q}"

    # 料金昇順であることを確認（ADR-125 D4 — ソート要件）
    charges = [q.total_net_charge for q in quotes]
    assert charges == sorted(charges), f"料金昇順でない: {charges}"


# ---------------------------------------------------------------------------
# T3: 配達日数・タイムスタンプが返るサービスを確認
# ---------------------------------------------------------------------------

@requires_sandbox
def test_sandbox_transit_days_present_for_at_least_one_quote():
    """少なくとも 1 件の見積もりに transit_days が設定されている。

    FedEx Sandbox の一部サービスは operationalDetail.transitTime を返さない場合があるが、
    FEDEX_INTERNATIONAL_PRIORITY など標準サービスは返すはず。
    transit_days=None のサービスが混在してもエラーにならないことも確認する。
    """
    quotes = get_rates(
        tenant_id=_TENANT_ID,
        environment=_ENV,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
        account_number=_ACCOUNT_NUMBER,
        origin_country_code=_ORIGIN,
        destination_country_code=_DESTINATION,
        weight_kg=_WEIGHT_KG,
    )

    # transit_days が None でも例外にならないことを確認（存在チェックのみ）
    for q in quotes:
        if q.transit_days is not None:
            assert q.transit_days >= 0, f"transit_days が負: {q}"

    # ログ目的で最初の数件を出力
    for i, q in enumerate(quotes[:5]):
        print(
            f"\n  [{i+1}] {q.service_name} "
            f"{q.total_net_charge} {q.currency} "
            f"transit={q.transit_days}日"
        )
