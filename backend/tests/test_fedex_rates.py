"""
FedEx Rates API クライアントのユニットテスト（ADR-125）。

実際の FedEx API は呼び出さず、httpx をモックして動作を検証する。

テスト対象:
  - get_or_refresh_token: キャッシュヒット / ミス / 期限切れ
  - get_rates: 正常系 / 認証エラー / API エラー / タイムアウト / サービスフィルタ
  - _fetch_transit_days: SA API 正常系 / 失敗時の空 dict フォールバック
  - /shipping/calculate エンドポイント: FedEx ライブ分岐 / 静的フォールバック /
                                         未連携時の live_error 明示返却 /
                                         rate_precision exact/approximate（仕様追補 2026-06-10）

変更履歴:
  2026-06-09: 初版（ADR-125 Phase B）
  2026-06-10: TARGET_INTERNATIONAL_SERVICE_TYPES フィルタ対応
              rate_precision (exact/approximate) テスト追加
              _try_fedex_live の 3-tuple 戻り値に対応
  2026-06-10: SA API transit days 統合テスト追加（_fetch_transit_days）
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import fedex_rates
from app.services.fedex_rates import (
    FedExAPIError,
    FedExAuthError,
    FedExRateQuote,
    _fetch_transit_days,
    clear_token_cache,
    get_or_refresh_token,
    get_rates,
)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_cache():
    """各テスト前後にトークンキャッシュをクリア。"""
    clear_token_cache()
    yield
    clear_token_cache()


def _mock_token_resp(token: str = "test-token", expires_in: int = 3600):
    """OAuth トークンレスポンスモック。"""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": token, "expires_in": expires_in}
    return resp


def _mock_rates_resp(quotes: list[dict] | None = None):
    """Rates API レスポンスモック。

    デフォルトは FEDEX_INTERNATIONAL_PRIORITY（本番 API の正しい名称）。
    """
    if quotes is None:
        quotes = [
            {
                "serviceType": "FEDEX_INTERNATIONAL_PRIORITY",
                "serviceName": "FedEx International Priority®",
                "ratedShipmentDetails": [
                    {
                        "rateType": "PAYOR_LIST_SHIPMENT",
                        "totalNetCharge": 12500,
                        "currency": "JPY",
                    }
                ],
                "operationalDetail": {"transitTime": "2_DAYS"},
            }
        ]
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"output": {"rateReplyDetails": quotes}}
    return resp


# ---------------------------------------------------------------------------
# get_or_refresh_token テスト
# ---------------------------------------------------------------------------

class TestGetOrRefreshToken:
    def test_cache_miss_fetches_token(self):
        """キャッシュミス時にOAuthトークンを取得してキャッシュする。"""
        with patch("httpx.post", return_value=_mock_token_resp("token-abc")) as mock_post:
            token = get_or_refresh_token(1, "sandbox", "cid", "csec")

        assert token == "token-abc"
        mock_post.assert_called_once()

    def test_cache_hit_returns_cached(self):
        """キャッシュヒット時に httpx.post を呼ばない。"""
        with patch("httpx.post", return_value=_mock_token_resp("token-xyz")):
            get_or_refresh_token(1, "sandbox", "cid", "csec")

        with patch("httpx.post") as mock_post:
            token = get_or_refresh_token(1, "sandbox", "cid", "csec")

        assert token == "token-xyz"
        mock_post.assert_not_called()

    def test_expired_token_refetches(self):
        """期限切れ（5分バッファ込み）のトークンは再取得する。"""
        # 期限切れトークンをキャッシュに直接注入
        fedex_rates._token_cache[(1, "sandbox")] = fedex_rates._CachedToken(
            access_token="old-token",
            expires_at=time.time() + 60,  # 残り1分 < 5分バッファ → 期限切れ扱い
        )

        with patch("httpx.post", return_value=_mock_token_resp("new-token")) as mock_post:
            token = get_or_refresh_token(1, "sandbox", "cid", "csec")

        assert token == "new-token"
        mock_post.assert_called_once()

    def test_auth_error_raises_fedex_auth_error(self):
        """401 は FedExAuthError を raise。"""
        resp = MagicMock()
        resp.status_code = 401

        with patch("httpx.post", return_value=resp):
            with pytest.raises(FedExAuthError):
                get_or_refresh_token(1, "sandbox", "cid", "bad-secret")

    def test_different_tenants_have_separate_caches(self):
        """テナントが異なれば別キャッシュ。"""
        with patch("httpx.post", side_effect=[
            _mock_token_resp("token-t1"),
            _mock_token_resp("token-t2"),
        ]):
            token1 = get_or_refresh_token(1, "sandbox", "cid", "csec")
            token2 = get_or_refresh_token(2, "sandbox", "cid", "csec")

        assert token1 == "token-t1"
        assert token2 == "token-t2"


# ---------------------------------------------------------------------------
# get_rates テスト
# ---------------------------------------------------------------------------

class TestGetRates:
    def test_success_returns_quotes(self):
        """正常系: FedExRateQuote リストを返す。"""
        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_rates_resp(),
        ]):
            quotes = get_rates(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                origin_country_code="JP",
                destination_country_code="US",
                weight_kg=Decimal("1.5"),
            )

        assert len(quotes) == 1
        assert quotes[0].service_type == "FEDEX_INTERNATIONAL_PRIORITY"
        assert quotes[0].total_net_charge == Decimal("12500")
        assert quotes[0].currency == "JPY"
        assert quotes[0].transit_days == 2

    def test_non_target_service_types_filtered_out(self):
        """TARGET_INTERNATIONAL_SERVICE_TYPES 以外のサービスはフィルタされる。"""
        quotes_data = [
            {
                "serviceType": "FEDEX_GROUND",       # 対象外
                "serviceName": "FedEx Ground®",
                "ratedShipmentDetails": [
                    {"rateType": "PAYOR_LIST_SHIPMENT", "totalNetCharge": 5000, "currency": "JPY"}
                ],
            },
            {
                "serviceType": "FEDEX_INTERNATIONAL_PRIORITY",  # 対象内（本番の正しい名称）
                "serviceName": "FedEx International Priority®",
                "ratedShipmentDetails": [
                    {"rateType": "PAYOR_LIST_SHIPMENT", "totalNetCharge": 12500, "currency": "JPY"}
                ],
            },
            {
                "serviceType": "FIRST_OVERNIGHT",    # 対象外
                "serviceName": "FedEx First Overnight®",
                "ratedShipmentDetails": [
                    {"rateType": "PAYOR_LIST_SHIPMENT", "totalNetCharge": 20000, "currency": "JPY"}
                ],
            },
        ]

        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_rates_resp(quotes_data),
        ]):
            quotes = get_rates(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                origin_country_code="JP",
                destination_country_code="US",
                weight_kg=Decimal("1.0"),
            )

        assert len(quotes) == 1, "対象外サービスがフィルタされず残っている"
        assert quotes[0].service_type == "FEDEX_INTERNATIONAL_PRIORITY"

    def test_rates_api_401_clears_cache_and_raises_auth_error(self):
        """Rates API 401 はキャッシュをクリアして FedExAuthError を raise。"""
        # トークンをキャッシュに注入
        fedex_rates._token_cache[(1, "sandbox")] = fedex_rates._CachedToken(
            access_token="stale-token",
            expires_at=time.time() + 3000,
        )

        rates_401_resp = MagicMock()
        rates_401_resp.status_code = 401

        with patch("httpx.post", return_value=rates_401_resp):
            with pytest.raises(FedExAuthError):
                get_rates(
                    tenant_id=1,
                    environment="sandbox",
                    client_id="cid",
                    client_secret="csec",
                    account_number="123456789",
                    origin_country_code="JP",
                    destination_country_code="US",
                    weight_kg=Decimal("1.0"),
                )

        # キャッシュがクリアされていること
        assert (1, "sandbox") not in fedex_rates._token_cache

    def test_rates_api_500_raises_fedex_api_error(self):
        """Rates API 500 は FedExAPIError を raise。"""
        error_resp = MagicMock()
        error_resp.status_code = 500
        error_resp.json.return_value = {"errors": [{"code": "INTERNAL.SERVER.ERROR"}]}

        with patch("httpx.post", side_effect=[_mock_token_resp(), error_resp]):
            with pytest.raises(FedExAPIError) as exc_info:
                get_rates(
                    tenant_id=1,
                    environment="sandbox",
                    client_id="cid",
                    client_secret="csec",
                    account_number="123456789",
                    origin_country_code="JP",
                    destination_country_code="US",
                    weight_kg=Decimal("1.0"),
                )

        assert exc_info.value.status_code == 500

    def test_sorted_by_price_ascending(self):
        """複数サービスタイプは料金昇順で返す。"""
        quotes_data = [
            {
                "serviceType": "INTERNATIONAL_ECONOMY",
                "serviceName": "FedEx International Economy®",
                "ratedShipmentDetails": [
                    {"rateType": "PAYOR_LIST_SHIPMENT", "totalNetCharge": 8000, "currency": "JPY"}
                ],
            },
            {
                "serviceType": "FEDEX_INTERNATIONAL_PRIORITY",
                "serviceName": "FedEx International Priority®",
                "ratedShipmentDetails": [
                    {"rateType": "PAYOR_LIST_SHIPMENT", "totalNetCharge": 12500, "currency": "JPY"}
                ],
            },
        ]

        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_rates_resp(quotes_data),
        ]):
            quotes = get_rates(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                origin_country_code="JP",
                destination_country_code="US",
                weight_kg=Decimal("1.0"),
            )

        assert len(quotes) == 2
        assert quotes[0].total_net_charge < quotes[1].total_net_charge


# ---------------------------------------------------------------------------
# _fetch_transit_days テスト（SA API）
# ---------------------------------------------------------------------------

class TestFetchTransitDays:
    """SA API（/availability/v1/transittimes）配達日数取得テスト。"""

    def _make_sa_resp(self, details: list[dict]):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "output": {
                "transitTimes": [{"transitTimeDetails": details}]
            }
        }
        return resp

    def test_returns_transit_days_from_sa_api(self):
        """SA API 正常系: serviceType → transit_days を返す。"""
        today = date.today()
        delivery = today + timedelta(days=2)
        day_str = delivery.strftime("%b-%d-%Y")  # e.g. "Jun-12-2026"

        sa_resp = self._make_sa_resp([{
            "serviceType": "FEDEX_INTERNATIONAL_PRIORITY",
            "commit": {"dateDetail": {"day": day_str}},
        }])

        with patch("httpx.post", return_value=sa_resp):
            result = _fetch_transit_days(
                base_url="https://apis.fedex.com",
                token="test-token",
                origin_cc="JP",
                origin_zip="1000001",
                dest_cc="US",
                dest_zip="10001",
                weight_kg=Decimal("1.0"),
            )

        assert result.get("FEDEX_INTERNATIONAL_PRIORITY") == 2

    def test_returns_empty_dict_on_http_error(self):
        """SA API エラー時は空 dict を返し例外を伝播しない。"""
        error_resp = MagicMock()
        error_resp.status_code = 400
        error_resp.json.return_value = {"errors": [{"code": "PACKAGE.NULLOREMPTY.REQUIRED"}]}

        with patch("httpx.post", return_value=error_resp):
            result = _fetch_transit_days(
                base_url="https://apis.fedex.com",
                token="test-token",
                origin_cc="JP",
                origin_zip="1000001",
                dest_cc="US",
                dest_zip="10001",
                weight_kg=Decimal("1.0"),
            )

        assert result == {}

    def test_returns_empty_dict_on_network_exception(self):
        """SA API 通信例外でも空 dict を返す（best-effort）。"""
        import httpx as _httpx

        with patch("httpx.post", side_effect=_httpx.TimeoutException("timeout")):
            result = _fetch_transit_days(
                base_url="https://apis.fedex.com",
                token="test-token",
                origin_cc="JP",
                origin_zip="1000001",
                dest_cc="US",
                dest_zip="10001",
                weight_kg=Decimal("1.0"),
            )

        assert result == {}

    def test_transit_map_used_in_get_rates(self):
        """get_rates が SA API の transit_days を FedExRateQuote に反映する。"""
        today = date.today()
        delivery = today + timedelta(days=3)
        day_str = delivery.strftime("%b-%d-%Y")

        sa_resp = self._make_sa_resp([{
            "serviceType": "FEDEX_INTERNATIONAL_PRIORITY",
            "commit": {"dateDetail": {"day": day_str}},
        }])

        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_rates_resp(),  # rates レスポンス（operationalDetail: 2_DAYS）
            sa_resp,             # SA API レスポンス（3日後配達）
        ]):
            quotes = get_rates(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                origin_country_code="JP",
                destination_country_code="US",
                weight_kg=Decimal("1.0"),
            )

        assert len(quotes) == 1
        # SA API の値（3日）が operationalDetail の値（2日）を上書きする
        assert quotes[0].transit_days == 3

    def test_operationaldetail_fallback_when_sa_api_fails(self):
        """SA API 失敗時は operationalDetail.transitTime にフォールバック。"""
        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_rates_resp(),  # operationalDetail: "2_DAYS"
            # SA API call → side_effect exhausted → StopIteration → caught internally
        ]):
            quotes = get_rates(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                origin_country_code="JP",
                destination_country_code="US",
                weight_kg=Decimal("1.0"),
            )

        assert len(quotes) == 1
        assert quotes[0].transit_days == 2  # operationalDetail フォールバック


# ---------------------------------------------------------------------------
# /shipping/calculate エンドポイント テスト（ADR-125 D5 — 暗黙フォールバック禁止）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestShippingCalculateEndpoint:
    """shipping.py calc_shipping の FedEx 分岐テスト。"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_tenant_id(self):
        return 1

    async def test_no_credentials_returns_live_error_not_static(self):
        """FedEx 未連携（credentials なし）は static に落ちず live_error を返す。

        ADR-125 D5 + PO C1判断:
        - results は空（静的早見表 FedEx 行を返さない）
        - live_error に「未連携」メッセージが入る
        - calculate_shipping_fee は呼ばれない（FedEx 専用 early return）
        """
        from app.routers.shipping import calc_shipping
        from app.schemas.shipping import ShippingCalcRequest

        with patch("app.services.carrier_credentials.get_credentials", return_value=None), \
             patch("app.routers.shipping.calculate_shipping_fee", new_callable=AsyncMock) as mock_calc:
            data = ShippingCalcRequest(
                country_code="US",
                weight_kg=Decimal("1.0"),
                carrier="fedex",
                origin_country_code="JP",
            )
            resp = await calc_shipping(
                data=data,
                db=AsyncMock(),
                tenant_id=1,
                current_user=MagicMock(),
            )

        assert resp.results == [], f"未連携時に静的結果が混入: {resp.results}"
        assert resp.live_error is not None, "未連携時に live_error が None"
        assert "未連携" in resp.live_error, f"live_error に「未連携」文言なし: {resp.live_error}"
        mock_calc.assert_not_called()  # calculate_shipping_fee が呼ばれないこと

    async def test_live_error_explicit_on_api_failure(self):
        """FedEx API エラー時に live_error を明示返却し、results は空。

        ADR-125 D5: 暗黙フォールバック禁止。
        """
        from app.routers.shipping import _try_fedex_live

        creds = {
            "client_id": "cid",
            "client_secret": "csec",
            "environment": "sandbox",
            "account_number": "123456789",
        }

        with patch("app.services.fedex_rates.get_rates", side_effect=FedExAPIError("タイムアウト")):
            results, live_error, rate_precision = await _try_fedex_live(
                creds=creds,
                tenant_id=1,
                destination_country_code="US",
                origin_country_code="JP",
                weight_kg=Decimal("1.0"),
            )

        assert results == []
        assert live_error is not None
        assert "タイムアウト" in live_error
        assert rate_precision is None  # API エラー時は精度フラグなし

    async def test_no_account_number_returns_live_error(self):
        """account_number 未設定時に live_error を返す（D5）。"""
        from app.routers.shipping import _try_fedex_live

        creds = {
            "client_id": "cid",
            "client_secret": "csec",
            "environment": "sandbox",
            "account_number": None,  # 未設定
        }

        results, live_error, rate_precision = await _try_fedex_live(
            creds=creds,
            tenant_id=1,
            destination_country_code="US",
            origin_country_code="JP",
            weight_kg=Decimal("1.0"),
        )

        assert results == []
        assert live_error is not None
        assert rate_precision is None  # account_number 未設定時は精度フラグなし

    async def test_rate_precision_exact_when_postal_code_provided(self):
        """郵便番号指定ありで rate_precision='exact' を返す（仕様追補 2026-06-10）。"""
        from app.routers.shipping import _try_fedex_live

        creds = {
            "client_id": "cid",
            "client_secret": "csec",
            "environment": "sandbox",
            "account_number": "740561073",
        }
        mock_quotes = [
            FedExRateQuote(
                service_type="FEDEX_INTERNATIONAL_PRIORITY",
                service_name="FedEx International Priority®",
                total_net_charge=Decimal("12500"),
                currency="JPY",
            )
        ]

        with patch("app.services.fedex_rates.get_rates", return_value=mock_quotes):
            results, live_error, rate_precision = await _try_fedex_live(
                creds=creds,
                tenant_id=1,
                destination_country_code="US",
                origin_country_code="JP",
                weight_kg=Decimal("1.0"),
                destination_postal_code="10001",  # 郵便番号あり
            )

        assert live_error is None
        assert rate_precision == "exact"

    async def test_rate_precision_approximate_when_no_postal_code(self):
        """郵便番号未指定で rate_precision='approximate' を返す（仕様追補 2026-06-10）。"""
        from app.routers.shipping import _try_fedex_live

        creds = {
            "client_id": "cid",
            "client_secret": "csec",
            "environment": "sandbox",
            "account_number": "740561073",
        }
        mock_quotes = [
            FedExRateQuote(
                service_type="FEDEX_INTERNATIONAL_PRIORITY",
                service_name="FedEx International Priority®",
                total_net_charge=Decimal("12500"),
                currency="JPY",
            )
        ]

        with patch("app.services.fedex_rates.get_rates", return_value=mock_quotes):
            results, live_error, rate_precision = await _try_fedex_live(
                creds=creds,
                tenant_id=1,
                destination_country_code="US",
                origin_country_code="JP",
                weight_kg=Decimal("1.0"),
                # destination_postal_code 未指定
            )

        assert live_error is None
        assert rate_precision == "approximate"
