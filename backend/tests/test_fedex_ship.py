"""
FedEx Ship API / Pickup API クライアントのユニットテスト（ADR-128）。

実際の FedEx API は呼び出さず、httpx をモックして動作を検証する。

テスト対象:
  - create_shipment: 正常系 / 認証エラー / API エラー / dimensions あり・なし
  - create_pickup: 正常系 / API エラー
  - ShippingCalcRequest: dimensions フィールド追加確認（スキーマテスト）
  - ShippingCalcResult: surcharges フィールド確認（スキーマテスト）

変更履歴:
  2026-06-11: 初版（ADR-128）
"""

from __future__ import annotations

import base64
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.carrier_adapter import PickupResult, ShipmentResult, SurchargeDetail
from app.services.fedex_rates import FedExAPIError, FedExAuthError, clear_token_cache
from app.services import fedex_ship
from app.services.fedex_ship import create_pickup, create_shipment


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


def _sample_label_bytes() -> bytes:
    """テスト用のダミーPDFバイト列（Base64エンコード済み）。"""
    return b"%PDF-1.4 test label content"


def _b64_label() -> str:
    return base64.b64encode(_sample_label_bytes()).decode()


def _mock_ship_resp(
    tracking_number: str = "123456789012",
    fee: float = 12500.0,
    currency: str = "JPY",
    surcharges: list[dict] | None = None,
):
    """Ship API 正常レスポンスモック。"""
    if surcharges is None:
        surcharges = []
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "output": {
            "transactionShipments": [
                {
                    "masterTrackingNumber": tracking_number,
                    "pieceResponses": [
                        {
                            "packageDocuments": [
                                {"encodedLabel": _b64_label()}
                            ]
                        }
                    ],
                    "shipmentRating": {
                        "shipmentRateDetails": [
                            {
                                "totalNetCharge": fee,
                                "currency": currency,
                                "surCharges": surcharges,
                            }
                        ]
                    },
                }
            ]
        }
    }
    return resp


def _mock_pickup_resp(confirmation_code: str = "PU123456", location: str = "JPNRT"):
    """Pickup API 正常レスポンスモック。"""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "output": {
            "pickupConfirmationCode": confirmation_code,
            "location": location,
        }
    }
    return resp


def _sample_shipper() -> dict:
    return {
        "contact": {"personName": "Taro Yamada", "phoneNumber": "0312345678"},
        "address": {
            "streetLines": ["1-1-1 Shinjuku"],
            "city": "Tokyo",
            "postalCode": "1600022",
            "countryCode": "JP",
            "residential": False,
        },
    }


def _sample_recipient() -> dict:
    return {
        "contact": {"personName": "John Doe", "phoneNumber": "2125551234"},
        "address": {
            "streetLines": ["100 Main St"],
            "city": "New York",
            "stateOrProvinceCode": "NY",
            "postalCode": "10001",
            "countryCode": "US",
            "residential": False,
        },
    }


# ---------------------------------------------------------------------------
# create_shipment テスト
# ---------------------------------------------------------------------------


class TestCreateShipment:
    def test_success_returns_shipment_result(self):
        """正常系: tracking_number・label_bytes・confirmed_fee が返る。"""
        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_ship_resp(tracking_number="TRACK001", fee=15000.0, currency="JPY"),
        ]):
            result = create_shipment(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                shipper=_sample_shipper(),
                recipient=_sample_recipient(),
                service_type="FEDEX_INTERNATIONAL_PRIORITY",
                weight_kg=Decimal("2.0"),
            )

        assert isinstance(result, ShipmentResult)
        assert result.tracking_number == "TRACK001"
        assert result.label_bytes == _sample_label_bytes()
        assert result.confirmed_fee == Decimal("15000.0")
        assert result.confirmed_currency == "JPY"
        assert result.surcharges == []

    def test_auth_error_raises_fedex_auth_error(self):
        """Ship API 401 は FedExAuthError を raise する。"""
        auth_resp = MagicMock()
        auth_resp.status_code = 401

        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            auth_resp,
        ]):
            with pytest.raises(FedExAuthError):
                create_shipment(
                    tenant_id=1,
                    environment="sandbox",
                    client_id="cid",
                    client_secret="csec",
                    account_number="123456789",
                    shipper=_sample_shipper(),
                    recipient=_sample_recipient(),
                    service_type="FEDEX_INTERNATIONAL_PRIORITY",
                    weight_kg=Decimal("1.0"),
                )

    def test_api_error_raises_fedex_api_error(self):
        """Ship API 500 は FedExAPIError を raise する。"""
        error_resp = MagicMock()
        error_resp.status_code = 500
        error_resp.json.return_value = {"errors": [{"code": "SYSTEM.UNEXPECTED.ERROR"}]}

        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            error_resp,
        ]):
            with pytest.raises(FedExAPIError) as exc_info:
                create_shipment(
                    tenant_id=1,
                    environment="sandbox",
                    client_id="cid",
                    client_secret="csec",
                    account_number="123456789",
                    shipper=_sample_shipper(),
                    recipient=_sample_recipient(),
                    service_type="FEDEX_INTERNATIONAL_PRIORITY",
                    weight_kg=Decimal("1.0"),
                )

        assert "500" in str(exc_info.value)

    def test_with_dimensions_includes_dimensions_in_request(self):
        """dimensions_cm 指定時は API リクエストに dimensions が含まれる。"""
        captured_payload: list[dict] = []

        def mock_post(url, json=None, headers=None, timeout=None):
            if json and "labelResponseOptions" in json:
                captured_payload.append(json)
            return _mock_ship_resp()

        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            None,  # token は side_effect の最初で消費される
        ]):
            pass  # リセット

        import httpx

        original_post = httpx.post

        def patched_post(url, **kwargs):
            if "oauth/token" in url:
                return _mock_token_resp()
            if kwargs.get("json") and "labelResponseOptions" in (kwargs.get("json") or {}):
                captured_payload.append(kwargs.get("json", {}))
            return _mock_ship_resp()

        with patch("httpx.post", side_effect=patched_post):
            result = create_shipment(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                shipper=_sample_shipper(),
                recipient=_sample_recipient(),
                service_type="FEDEX_INTERNATIONAL_PRIORITY",
                weight_kg=Decimal("1.5"),
                dimensions_cm={"length": 30.0, "width": 20.0, "height": 10.0},
            )

        assert result.tracking_number is not None
        assert len(captured_payload) == 1
        pkg = captured_payload[0]["requestedShipment"]["requestedPackageLineItems"][0]
        assert "dimensions" in pkg
        assert pkg["dimensions"]["length"] == 30.0
        assert pkg["dimensions"]["width"] == 20.0
        assert pkg["dimensions"]["height"] == 10.0
        assert pkg["dimensions"]["units"] == "CM"

    def test_without_dimensions_excludes_dimensions_from_request(self):
        """dimensions_cm 未指定時は API リクエストに dimensions が含まれない。"""
        captured_payload: list[dict] = []

        def patched_post(url, **kwargs):
            if "oauth/token" in url:
                return _mock_token_resp()
            if kwargs.get("json") and "labelResponseOptions" in (kwargs.get("json") or {}):
                captured_payload.append(kwargs.get("json", {}))
            return _mock_ship_resp()

        with patch("httpx.post", side_effect=patched_post):
            result = create_shipment(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                shipper=_sample_shipper(),
                recipient=_sample_recipient(),
                service_type="FEDEX_INTERNATIONAL_PRIORITY",
                weight_kg=Decimal("1.0"),
                # dimensions_cm 未指定
            )

        assert result.tracking_number is not None
        assert len(captured_payload) == 1
        pkg = captured_payload[0]["requestedShipment"]["requestedPackageLineItems"][0]
        assert "dimensions" not in pkg

    def test_surcharges_are_parsed_correctly(self):
        """surcharges が正しくパースされて返る。"""
        surcharges_data = [
            {"description": "FUEL", "amount": 500.0},
            {"description": "RESIDENTIAL_DELIVERY", "amount": 350.0},
        ]
        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_ship_resp(surcharges=surcharges_data, currency="JPY"),
        ]):
            result = create_shipment(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                shipper=_sample_shipper(),
                recipient=_sample_recipient(),
                service_type="FEDEX_INTERNATIONAL_PRIORITY",
                weight_kg=Decimal("1.0"),
            )

        assert len(result.surcharges) == 2
        assert result.surcharges[0].description == "FUEL"
        assert result.surcharges[0].amount == Decimal("500.0")
        assert result.surcharges[1].description == "RESIDENTIAL_DELIVERY"


# ---------------------------------------------------------------------------
# create_pickup テスト
# ---------------------------------------------------------------------------


class TestCreatePickup:
    def _sample_pickup_address(self) -> dict:
        return {
            "contact": {"personName": "Taro Yamada", "phoneNumber": "0312345678"},
            "address": {
                "streetLines": ["1-1-1 Shinjuku"],
                "city": "Tokyo",
                "postalCode": "1600022",
                "countryCode": "JP",
            },
        }

    def test_success_returns_pickup_result(self):
        """正常系: confirmation_code が返る。"""
        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_pickup_resp(confirmation_code="PU999888", location="JPOSA"),
        ]):
            result = create_pickup(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="123456789",
                pickup_address=self._sample_pickup_address(),
                ready_datetime="2026-06-12T10:00:00+09:00",
                company_close_time="18:00",
            )

        assert isinstance(result, PickupResult)
        assert result.confirmation_code == "PU999888"
        assert result.location_code == "JPOSA"

    def test_api_error_raises_fedex_api_error(self):
        """Pickup API エラーは FedExAPIError を raise する。"""
        error_resp = MagicMock()
        error_resp.status_code = 422
        error_resp.json.return_value = {"errors": [{"code": "PICKUP.CUTOFF.EXCEEDED"}]}

        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            error_resp,
        ]):
            with pytest.raises(FedExAPIError) as exc_info:
                create_pickup(
                    tenant_id=1,
                    environment="sandbox",
                    client_id="cid",
                    client_secret="csec",
                    account_number="123456789",
                    pickup_address=self._sample_pickup_address(),
                    ready_datetime="2026-06-12T10:00:00+09:00",
                    company_close_time="18:00",
                )

        assert "422" in str(exc_info.value)


# ---------------------------------------------------------------------------
# スキーマテスト
# ---------------------------------------------------------------------------


class TestShippingSchemas:
    def test_shipping_calc_request_has_dimension_fields(self):
        """ShippingCalcRequest に ADR-128 で追加された寸法フィールドがある。"""
        from app.schemas.shipping import ShippingCalcRequest

        req = ShippingCalcRequest(
            country_code="US",
            weight_kg=Decimal("1.0"),
            length_cm=Decimal("30.0"),
            width_cm=Decimal("20.0"),
            height_cm=Decimal("10.0"),
            address_type="RESIDENTIAL",
            order_id=42,
        )

        assert req.length_cm == Decimal("30.0")
        assert req.width_cm == Decimal("20.0")
        assert req.height_cm == Decimal("10.0")
        assert req.address_type == "RESIDENTIAL"
        assert req.order_id == 42

    def test_shipping_calc_request_dimensions_optional(self):
        """ShippingCalcRequest の寸法フィールドは省略可能。"""
        from app.schemas.shipping import ShippingCalcRequest

        req = ShippingCalcRequest(
            country_code="US",
            weight_kg=Decimal("1.0"),
        )

        assert req.length_cm is None
        assert req.width_cm is None
        assert req.height_cm is None
        assert req.address_type is None
        assert req.order_id is None

    def test_shipping_calc_result_has_surcharges_field(self):
        """ShippingCalcResult に surcharges フィールドがある。"""
        from app.schemas.shipping import ShippingCalcResult

        result = ShippingCalcResult(
            carrier="fedex",
            zone="FEDEX_INTERNATIONAL_PRIORITY",
            fee=Decimal("12500"),
            currency="JPY",
            source="fedex_live",
        )

        assert hasattr(result, "surcharges")
        assert result.surcharges == []

    def test_shipping_calc_result_surcharges_populated(self):
        """ShippingCalcResult の surcharges に値をセットできる。"""
        from app.schemas.shipping import ShippingCalcResult, SurchargeDetail

        surcharges = [
            SurchargeDetail(description="FUEL", amount=Decimal("500"), currency="JPY"),
        ]
        result = ShippingCalcResult(
            carrier="fedex",
            zone="FEDEX_INTERNATIONAL_PRIORITY",
            fee=Decimal("12500"),
            currency="JPY",
            source="fedex_live",
            surcharges=surcharges,
        )

        assert len(result.surcharges) == 1
        assert result.surcharges[0].description == "FUEL"
        assert result.surcharges[0].amount == Decimal("500")
