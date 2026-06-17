"""
FedEx Label Validation サンプルラベル発行エンドポイントのテスト（ADR-129）。

通常フロー（A4通常プリンター / PDF）のみで lv_issue_sample_labels が動作することを確認する。
PNG / ZPL は通常フロー対象外であり、レスポンスに含まれないことも確認する。

テスト対象:
  POST /shipping/label-validation/samples
  → lv_issue_sample_labels()（shipping.py）

変更履歴:
  2026-06-17: 初版（PDF/A4 一本化方針 — ZPLフォールバックテストから置き換え）
"""
from __future__ import annotations

import base64
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.carrier_adapter import ShipmentResult
from app.services.fedex_rates import FedExAPIError, FedExAuthError


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

_DUMMY_CREDS = {
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
    "account_number": "123456789",
    "environment": "sandbox",
}

_DUMMY_LABEL_BYTES = b"%PDF-1.4 dummy label"


def _make_shipment_result(tracking_number: str = "TRACK001") -> ShipmentResult:
    return ShipmentResult(
        tracking_number=tracking_number,
        label_bytes=_DUMMY_LABEL_BYTES,
        confirmed_fee=Decimal("0"),
        confirmed_currency="USD",
        surcharges=[],
    )


# ---------------------------------------------------------------------------
# lv_issue_sample_labels テスト
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLVIssueSampleLabels:
    """POST /shipping/label-validation/samples のテスト。"""

    async def test_success_returns_four_pdf_labels(self, client):
        """正常系: 4サービス分のPDFラベルが返る。"""
        tracking_numbers = ["TRACK_IP", "TRACK_IE", "TRACK_IPE", "TRACK_FICP"]
        call_count = 0

        def mock_create_shipment(*args, **kwargs):
            nonlocal call_count
            tn = tracking_numbers[call_count]
            call_count += 1
            return _make_shipment_result(tn)

        with (
            patch(
                "app.services.carrier_credentials.get_credentials",
                new_callable=AsyncMock,
                return_value=_DUMMY_CREDS,
            ),
            patch(
                "app.services.fedex_ship.create_shipment",
                side_effect=mock_create_shipment,
            ),
        ):
            resp = await client.post("/api/v1/shipping/label-validation/samples")

        assert resp.status_code == 200
        data = resp.json()
        assert "labels" in data
        labels = data["labels"]
        assert len(labels) == 4

        abbrs = {lb["service_abbr"] for lb in labels}
        assert abbrs == {"IP", "IE", "IPE", "FICP"}

        expected_b64 = base64.b64encode(_DUMMY_LABEL_BYTES).decode()
        for label in labels:
            assert label["pdf_base64"] == expected_b64
            assert label["tracking_number"] in tracking_numbers

    async def test_response_contains_no_png_or_zpl_fields(self, client):
        """通常フローのレスポンスに PNG / ZPL フィールドが存在しないこと。"""
        def mock_create_shipment(*args, **kwargs):
            return _make_shipment_result()

        with (
            patch(
                "app.services.carrier_credentials.get_credentials",
                new_callable=AsyncMock,
                return_value=_DUMMY_CREDS,
            ),
            patch(
                "app.services.fedex_ship.create_shipment",
                side_effect=mock_create_shipment,
            ),
        ):
            resp = await client.post("/api/v1/shipping/label-validation/samples")

        assert resp.status_code == 200
        for label in resp.json()["labels"]:
            assert "png_base64" not in label
            assert "zpl_base64" not in label
            assert "zpl_label_stock_type" not in label

    async def test_create_shipment_called_four_times_pdf_only(self, client):
        """create_shipment がサービスごとに1回（PDF）だけ呼ばれる（4サービス計4回）。"""
        call_count = 0

        def mock_create_shipment(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_shipment_result(f"TRACK_{call_count:03d}")

        with (
            patch(
                "app.services.carrier_credentials.get_credentials",
                new_callable=AsyncMock,
                return_value=_DUMMY_CREDS,
            ),
            patch(
                "app.services.fedex_ship.create_shipment",
                side_effect=mock_create_shipment,
            ),
        ):
            resp = await client.post("/api/v1/shipping/label-validation/samples")

        assert resp.status_code == 200
        # 4サービス × 1形式(PDF) = 4回
        assert call_count == 4

    async def test_missing_creds_returns_422(self, client):
        """Sandbox 認証情報が未登録のとき 422 を返す。"""
        with patch(
            "app.services.carrier_credentials.get_credentials",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post("/api/v1/shipping/label-validation/samples")

        assert resp.status_code == 422

    async def test_missing_account_number_returns_422(self, client):
        """account_number が空の場合 422 を返す。"""
        creds_no_acct = {**_DUMMY_CREDS, "account_number": None}
        with patch(
            "app.services.carrier_credentials.get_credentials",
            new_callable=AsyncMock,
            return_value=creds_no_acct,
        ):
            resp = await client.post("/api/v1/shipping/label-validation/samples")

        assert resp.status_code == 422

    async def test_fedex_api_error_returns_422(self, client):
        """FedEx PDF API エラー時は 422 を返す（PDF失敗はそのままエラー）。"""
        with (
            patch(
                "app.services.carrier_credentials.get_credentials",
                new_callable=AsyncMock,
                return_value=_DUMMY_CREDS,
            ),
            patch(
                "app.services.fedex_ship.create_shipment",
                side_effect=FedExAPIError("Sandbox API Error"),
            ),
        ):
            resp = await client.post("/api/v1/shipping/label-validation/samples")

        assert resp.status_code == 422

    async def test_fedex_auth_error_returns_401(self, client):
        """FedEx 認証エラー時は 401 を返す。"""
        with (
            patch(
                "app.services.carrier_credentials.get_credentials",
                new_callable=AsyncMock,
                return_value=_DUMMY_CREDS,
            ),
            patch(
                "app.services.fedex_ship.create_shipment",
                side_effect=FedExAuthError("token expired"),
            ),
        ):
            resp = await client.post("/api/v1/shipping/label-validation/samples")

        assert resp.status_code == 401

    async def test_pdf_uses_default_label_image_type(self, client):
        """create_shipment は label_image_type を PDF デフォルトで呼ばれる（非PNG/非ZPL）。"""
        captured_calls: list[dict] = []

        def mock_create_shipment(*args, **kwargs):
            captured_calls.append(dict(kwargs))
            return _make_shipment_result("TRACK_DUMMY")

        with (
            patch(
                "app.services.carrier_credentials.get_credentials",
                new_callable=AsyncMock,
                return_value=_DUMMY_CREDS,
            ),
            patch(
                "app.services.fedex_ship.create_shipment",
                side_effect=mock_create_shipment,
            ),
        ):
            resp = await client.post("/api/v1/shipping/label-validation/samples")

        assert resp.status_code == 200
        assert len(captured_calls) == 4
        for call_kwargs in captured_calls:
            # label_image_type が指定されていない（デフォルトPDF）か、PDF が指定されている
            assert call_kwargs.get("label_image_type", "PDF") == "PDF"
            # PNG / ZPLII は指定されていない
            assert call_kwargs.get("label_image_type", "PDF") not in ("PNG", "ZPLII")
