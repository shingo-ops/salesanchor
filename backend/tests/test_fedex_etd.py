"""
FedEx ETD サービスのユニットテスト（ADR-137）。

実際の FedEx API は呼び出さず httpx をモックして動作を検証する。

テスト対象:
  - _guard_persistent_only: poka-yoke ガード（S5）
  - upload_etd_image: Upload Image API 呼び出し・imageIndex 取得
  - upsert_etd_image: DB upsert（同一キーの上書き確認）
  - get_etd_images: DB 読み出し
  - _ETD_ENABLED フラグが False のとき create_shipment に etdDetail が含まれないこと（J3 dormant）

変更履歴:
  2026-06-18: 初版（ADR-137 ETD骨格）
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.fedex_etd import (
    PERSISTENT_IMAGE_TYPES,
    _guard_persistent_only,
    get_etd_images,
    upload_etd_image,
    upsert_etd_image,
)
from app.services.fedex_rates import FedExAPIError, clear_token_cache


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cache():
    clear_token_cache()
    yield
    clear_token_cache()


def _mock_token_resp(token: str = "test-token", expires_in: int = 3600):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": token, "expires_in": expires_in}
    return resp


def _mock_upload_resp(image_index: str = "IDX-001"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"imageIndex": image_index}
    return resp


# ---------------------------------------------------------------------------
# S5: poka-yoke ガード
# ---------------------------------------------------------------------------


class TestGuardPersistentOnly:
    def test_letterhead_passes(self):
        _guard_persistent_only("LETTERHEAD")  # 例外なし

    def test_signature_passes(self):
        _guard_persistent_only("SIGNATURE")  # 例外なし

    def test_commercial_invoice_raises(self):
        with pytest.raises(ValueError, match="使い捨て書類"):
            _guard_persistent_only("COMMERCIAL_INVOICE")

    def test_other_raises(self):
        with pytest.raises(ValueError, match="使い捨て書類"):
            _guard_persistent_only("OTHER")

    def test_persistent_image_types_contains_only_images(self):
        assert PERSISTENT_IMAGE_TYPES == {"LETTERHEAD", "SIGNATURE"}
        assert "COMMERCIAL_INVOICE" not in PERSISTENT_IMAGE_TYPES
        assert "ETD_LABEL" not in PERSISTENT_IMAGE_TYPES


# ---------------------------------------------------------------------------
# S2: upload_etd_image
# ---------------------------------------------------------------------------


class TestUploadEtdImage:
    def test_success_returns_image_index(self):
        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_upload_resp("IDX-LHEAD-001"),
        ]):
            result = upload_etd_image(
                tenant_id=1,
                environment="sandbox",
                image_type="LETTERHEAD",
                image_bytes=b"fake-gif-bytes",
                client_id="cid",
                client_secret="csec",
            )
        assert result == "IDX-LHEAD-001"

    def test_signature_success(self):
        with patch("httpx.post", side_effect=[
            _mock_token_resp(),
            _mock_upload_resp("IDX-SIG-001"),
        ]):
            result = upload_etd_image(
                tenant_id=1,
                environment="sandbox",
                image_type="SIGNATURE",
                image_bytes=b"fake-gif-bytes",
                client_id="cid",
                client_secret="csec",
            )
        assert result == "IDX-SIG-001"

    def test_disposable_type_raises_before_api_call(self):
        """COMMERCIAL_INVOICE 等の使い捨てタイプは API 呼び出し前に例外（poka-yoke）。"""
        with pytest.raises(ValueError, match="使い捨て書類"):
            upload_etd_image(
                tenant_id=1,
                environment="sandbox",
                image_type="COMMERCIAL_INVOICE",  # type: ignore[arg-type]
                image_bytes=b"bytes",
                client_id="cid",
                client_secret="csec",
            )

    def test_api_error_raises_fedex_api_error(self):
        err_resp = MagicMock()
        err_resp.status_code = 400
        err_resp.json.return_value = {"errors": [{"code": "ETD.INVALID.IMAGE"}]}
        with patch("httpx.post", side_effect=[_mock_token_resp(), err_resp]):
            with pytest.raises(FedExAPIError, match="HTTP 400"):
                upload_etd_image(
                    tenant_id=1,
                    environment="sandbox",
                    image_type="LETTERHEAD",
                    image_bytes=b"bad",
                    client_id="cid",
                    client_secret="csec",
                )


# ---------------------------------------------------------------------------
# S2: upsert / get
# ---------------------------------------------------------------------------


class TestUpsertGetEtdImage:
    @pytest.mark.asyncio
    async def test_upsert_calls_db_execute(self):
        db = AsyncMock()
        await upsert_etd_image(
            db=db,
            tenant_id=1,
            image_type="LETTERHEAD",
            environment="sandbox",
            image_index="IDX-001",
        )
        db.execute.assert_awaited_once()
        call_sql = str(db.execute.call_args[0][0])
        assert "INSERT" in call_sql.upper()
        assert "ON CONFLICT" in call_sql.upper()

    @pytest.mark.asyncio
    async def test_upsert_disposable_type_raises(self):
        db = AsyncMock()
        with pytest.raises(ValueError, match="使い捨て書類"):
            await upsert_etd_image(
                db=db,
                tenant_id=1,
                image_type="COMMERCIAL_INVOICE",
                environment="sandbox",
                image_index="DOC-001",
            )
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_etd_images_returns_dict(self):
        db = AsyncMock()
        row_lhead = MagicMock()
        row_lhead.image_type = "LETTERHEAD"
        row_lhead.fedex_image_index = "IDX-L-001"
        row_sig = MagicMock()
        row_sig.image_type = "SIGNATURE"
        row_sig.fedex_image_index = "IDX-S-001"

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([row_lhead, row_sig]))
        db.execute.return_value = mock_result

        result = await get_etd_images(db=db, tenant_id=1, environment="sandbox")

        assert result == {"LETTERHEAD": "IDX-L-001", "SIGNATURE": "IDX-S-001"}

    @pytest.mark.asyncio
    async def test_get_etd_images_empty_when_not_registered(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        db.execute.return_value = mock_result

        result = await get_etd_images(db=db, tenant_id=99, environment="sandbox")

        assert result == {}


# ---------------------------------------------------------------------------
# S4: J3 dormant — _ETD_ENABLED=False のとき create_shipment に etdDetail なし
# ---------------------------------------------------------------------------


class TestEtdDormant:
    def test_etd_disabled_flag_is_false(self):
        """_ETD_ENABLED が False であることを直接確認。本番フロー保護の最重要テスト。"""
        import app.services.fedex_ship as fedex_ship_module

        assert fedex_ship_module._ETD_ENABLED is False, (
            "_ETD_ENABLED=True になっています。CTS確認前に有効化してはいけません（ADR-137 J3）"
        )

    def test_create_shipment_excludes_etd_when_disabled(self):
        """_ETD_ENABLED=False の場合、etd_image_indices を渡しても shippingDocumentSpecification が含まれない。"""
        from decimal import Decimal

        captured: list[dict] = []

        def mock_post(url, json=None, headers=None, timeout=None, files=None, data=None, **_):
            if "oauth" in url:
                return _mock_token_resp()
            captured.append(json or {})
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "output": {
                    "transactionShipments": [{
                        "masterTrackingNumber": "TRK001",
                        "pieceResponses": [{
                            "packageDocuments": [{
                                "encodedLabel": __import__("base64").b64encode(b"PDF").decode(),
                            }]
                        }],
                    }]
                }
            }
            return resp

        with patch("httpx.post", side_effect=mock_post):
            from app.services.fedex_ship import create_shipment

            create_shipment(
                tenant_id=1,
                environment="sandbox",
                client_id="cid",
                client_secret="csec",
                account_number="ACC001",
                shipper={"contact": {}, "address": {}},
                recipient={"contact": {}, "address": {}},
                service_type="FEDEX_INTERNATIONAL_PRIORITY",
                weight_kg=Decimal("1.0"),
                etd_image_indices={"LETTERHEAD": "IDX-001", "SIGNATURE": "IDX-002"},
            )

        assert len(captured) == 1
        req_ship = captured[0].get("requestedShipment", {})
        assert "shippingDocumentSpecification" not in req_ship, (
            "shippingDocumentSpecification が本番経路に出ています。_ETD_ENABLED を確認してください"
        )
