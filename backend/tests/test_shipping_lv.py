"""
ZPLII フォールバック動作の単体テスト（ADR-129）。

lv_issue_sample_labels の ZPLII 発行ロジック:
  - STOCK_4X6 で試みる
  - FedExAPIError 失敗時のみ PAPER_85X11_TOP_HALF_LABEL にフォールバック
  - フォールバックでも失敗した場合は両エラー文を含む HTTPException

テスト対象:
  - _lv_issue_zpl_with_fallback: ZPL フォールバックヘルパー関数

変更履歴:
  2026-06-17: 初版（REQUEST_CHANGES レビュー対応 — ZPL フォールバック実装）
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.services.carrier_adapter import ShipmentResult
from app.services.fedex_rates import FedExAPIError, FedExAuthError


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _make_result(tracking: str = "TRACK001") -> ShipmentResult:
    """テスト用 ShipmentResult。"""
    return ShipmentResult(
        tracking_number=tracking,
        label_bytes=b"ZPL-DATA",
        confirmed_fee=Decimal("0"),
        confirmed_currency="USD",
        surcharges=[],
    )


def _sample_creds() -> dict:
    return {"client_id": "cid", "client_secret": "csec", "account_number": "123456789"}


# ---------------------------------------------------------------------------
# _lv_issue_zpl_with_fallback テスト
# ---------------------------------------------------------------------------


class TestLvIssueZplWithFallback:
    """ZPLII フォールバックヘルパーのテスト。"""

    async def test_stock4x6_success_returns_primary_stock_type(self):
        """STOCK_4X6 で成功 → (result, "STOCK_4X6") を返す。"""
        from app.routers.shipping import _lv_issue_zpl_with_fallback

        with patch("app.services.fedex_ship.create_shipment", return_value=_make_result("ZT001")):
            result, stock = await _lv_issue_zpl_with_fallback(
                tenant_id=1,
                creds=_sample_creds(),
                service_type="INTERNATIONAL_PRIORITY",
                service_name="FedEx International Priority",
                abbr="IP",
            )

        assert result.tracking_number == "ZT001"
        assert stock == "STOCK_4X6"

    async def test_stock4x6_fedex_api_error_falls_back_to_paper(self):
        """STOCK_4X6 が FedExAPIError → PAPER_85X11_TOP_HALF_LABEL で再試行して成功。"""
        from app.routers.shipping import _lv_issue_zpl_with_fallback

        fallback_result = _make_result("ZT002")

        def _side_effect(**kwargs):
            if kwargs.get("label_stock_type") == "STOCK_4X6":
                raise FedExAPIError("STOCK_4X6 not supported in Sandbox", status_code=422)
            return fallback_result

        with patch("app.services.fedex_ship.create_shipment", side_effect=_side_effect):
            result, stock = await _lv_issue_zpl_with_fallback(
                tenant_id=1,
                creds=_sample_creds(),
                service_type="INTERNATIONAL_PRIORITY",
                service_name="FedEx International Priority",
                abbr="IP",
            )

        assert result.tracking_number == "ZT002"
        assert stock == "PAPER_85X11_TOP_HALF_LABEL"

    async def test_fallback_success_does_not_affect_pdf_png(self):
        """ZPLII フォールバックは PDF/PNG の発行に影響しない（独立した関数のため当然）。

        _lv_issue_zpl_with_fallback は label_image_type="ZPLII" のみ発行する。
        PDF/PNG を発行しないことをコールカウントで確認。
        """
        from app.routers.shipping import _lv_issue_zpl_with_fallback

        call_args_list: list[dict] = []
        fallback_result = _make_result("ZT003")

        def _side_effect(**kwargs):
            call_args_list.append(dict(kwargs))
            if kwargs.get("label_stock_type") == "STOCK_4X6":
                raise FedExAPIError("primary failed", status_code=422)
            return fallback_result

        with patch("app.services.fedex_ship.create_shipment", side_effect=_side_effect):
            result, stock = await _lv_issue_zpl_with_fallback(
                tenant_id=1,
                creds=_sample_creds(),
                service_type="INTERNATIONAL_ECONOMY",
                service_name="FedEx International Economy",
                abbr="IE",
            )

        assert stock == "PAPER_85X11_TOP_HALF_LABEL"
        assert result.tracking_number == "ZT003"
        # create_shipment は ZPLII 用に 2 回だけ呼ばれる（PDF/PNG は 0 回）
        assert len(call_args_list) == 2
        assert all(ca["label_image_type"] == "ZPLII" for ca in call_args_list)
        assert call_args_list[0]["label_stock_type"] == "STOCK_4X6"
        assert call_args_list[1]["label_stock_type"] == "PAPER_85X11_TOP_HALF_LABEL"

    async def test_both_stock_types_fail_raises_http_422_with_both_messages(self):
        """STOCK_4X6 / PAPER_85X11_TOP_HALF_LABEL 両方失敗 → HTTPException のエラー文に両方の stock type が含まれる。"""
        from app.routers.shipping import _lv_issue_zpl_with_fallback

        def _always_fail(**kwargs):
            stock = kwargs.get("label_stock_type", "unknown")
            raise FedExAPIError(f"{stock} error detail", status_code=422)

        with patch("app.services.fedex_ship.create_shipment", side_effect=_always_fail):
            with pytest.raises(HTTPException) as exc_info:
                await _lv_issue_zpl_with_fallback(
                    tenant_id=1,
                    creds=_sample_creds(),
                    service_type="INTERNATIONAL_PRIORITY",
                    service_name="FedEx International Priority",
                    abbr="IP",
                )

        detail = exc_info.value.detail
        assert exc_info.value.status_code == 422
        assert "STOCK_4X6" in detail
        assert "PAPER_85X11_TOP_HALF_LABEL" in detail
        # 両エラーの詳細も含まれること
        assert "STOCK_4X6 error detail" in detail
        assert "PAPER_85X11_TOP_HALF_LABEL error detail" in detail

    async def test_stock4x6_fedex_auth_error_raises_http_401(self):
        """STOCK_4X6 が FedExAuthError → フォールバックせず即 HTTP 401 を返す。"""
        from app.routers.shipping import _lv_issue_zpl_with_fallback

        with patch(
            "app.services.fedex_ship.create_shipment",
            side_effect=FedExAuthError("token expired"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await _lv_issue_zpl_with_fallback(
                    tenant_id=1,
                    creds=_sample_creds(),
                    service_type="INTERNATIONAL_PRIORITY",
                    service_name="FedEx International Priority",
                    abbr="IP",
                )

        assert exc_info.value.status_code == 401

    async def test_fallback_fedex_auth_error_raises_http_401(self):
        """STOCK_4X6 が FedExAPIError、PAPER が FedExAuthError → HTTP 401 を返す。"""
        from app.routers.shipping import _lv_issue_zpl_with_fallback

        def _side_effect(**kwargs):
            if kwargs.get("label_stock_type") == "STOCK_4X6":
                raise FedExAPIError("primary failed", status_code=422)
            raise FedExAuthError("token expired at fallback")

        with patch("app.services.fedex_ship.create_shipment", side_effect=_side_effect):
            with pytest.raises(HTTPException) as exc_info:
                await _lv_issue_zpl_with_fallback(
                    tenant_id=1,
                    creds=_sample_creds(),
                    service_type="INTERNATIONAL_PRIORITY",
                    service_name="FedEx International Priority",
                    abbr="IP",
                )

        assert exc_info.value.status_code == 401
