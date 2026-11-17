"""請求書の送料の一覧の道（invoice-create-portfolio R3・design-v2 §3-5・K6）。

DB は使わない。道の関数を直接呼び、DB・住所の写し・発行元の国・静的な表・FedEx を置き換える
（backend/tests/test_fedex_rates.py の TestShippingCalculateEndpoint と同じやり方）。
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.invoices import get_invoice_draft_shipping_quotes
from app.routers.shipping import FEDEX_NOT_CONNECTED_MESSAGE
from app.schemas.invoice import DraftShippingQuotesRequest
from app.schemas.shipping import ShippingCalcResult

SHIP_TO = {"country": "US", "postal_code": "10001"}
BILL_TO = {"country": "US", "postal_code": "94105"}


def _row(carrier: str, source: str = "static", fee: str = "1000") -> ShippingCalcResult:
    return ShippingCalcResult(carrier=carrier, zone="Z1", fee=Decimal(fee), currency="JPY", source=source)


STATIC_ROWS = [_row("FedEx"), _row("fedex"), _row("DHL"), _row("UPS")]


def _db(company_exists: bool = True) -> AsyncMock:
    res = MagicMock()
    res.first.return_value = (5,) if company_exists else None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=res)
    return db


async def _call(db, *, snapshots=(SHIP_TO, BILL_TO), origin="JP", creds=None, live=None):
    """道を呼ぶ。live は _try_fedex_live の戻り値（None なら呼ばれない想定）。"""
    snap = AsyncMock(side_effect=list(snapshots))
    try_live = AsyncMock(return_value=live)
    get_creds = AsyncMock(return_value=creds)
    with patch("app.routers.invoices._fetch_address_snapshot", snap), \
         patch("app.routers.invoices.get_issuer_country_code", AsyncMock(return_value=origin)), \
         patch("app.routers.invoices.calculate_shipping_fee", AsyncMock(return_value=list(STATIC_ROWS))) as calc, \
         patch("app.services.carrier_credentials.get_credentials", get_creds), \
         patch("app.routers.shipping._try_fedex_live", try_live):
        resp = await get_invoice_draft_shipping_quotes(
            data=DraftShippingQuotesRequest(company_id=5, weight_kg=Decimal("2.5")),
            db=db,
            tenant_id=1,
            current_user=MagicMock(),
        )
    return resp, calc, get_creds, try_live


def _carriers(resp, source: str) -> list[str]:
    return [r.carrier.lower() for r in resp.results if r.source == source]


@pytest.mark.asyncio
async def test_k6_live_ok_fedex_live_only_and_others_static():
    """K6: 連携あり・ライブ成功 → FedEx はライブの行だけ・静的な FedEx は0件・DHL と UPS は静的。"""
    live_row = _row("fedex", source="fedex_live", fee="3200")
    resp, calc, _, try_live = await _call(_db(), creds={"client_id": "x"}, live=([live_row], None, "exact"))
    assert _carriers(resp, "fedex_live") == ["fedex"]
    assert "fedex" not in _carriers(resp, "static")
    assert sorted(_carriers(resp, "static")) == ["dhl", "ups"]
    assert resp.results[0].source == "fedex_live"
    assert resp.live_error is None
    assert resp.rate_precision == "exact"
    assert resp.cheapest is None
    calc.assert_awaited_once()
    assert calc.await_args.args[1] == "US"
    kw = try_live.await_args.kwargs
    assert kw["destination_country_code"] == "US"
    assert kw["origin_country_code"] == "JP"
    assert kw["destination_postal_code"] == "10001"
    assert kw["weight_kg"] == Decimal("2.5")


@pytest.mark.asyncio
async def test_k6_not_connected_no_fedex_rows_and_message():
    """K6: 未連携 → FedEx の行は0件（静的もライブも）・未連携の文・DHL と UPS は静的。"""
    resp, _, _, try_live = await _call(_db(), creds=None)
    assert all(r.carrier.lower() != "fedex" for r in resp.results)
    assert sorted(_carriers(resp, "static")) == ["dhl", "ups"]
    assert resp.live_error == FEDEX_NOT_CONNECTED_MESSAGE
    try_live.assert_not_awaited()


@pytest.mark.asyncio
async def test_k6_live_failure_no_fedex_rows_and_error():
    """K6: ライブ失敗 → FedEx の行は0件・live_error あり・DHL と UPS は静的。"""
    resp, _, _, _ = await _call(_db(), creds={"client_id": "x"}, live=([], "タイムアウト", None))
    assert all(r.carrier.lower() != "fedex" for r in resp.results)
    assert sorted(_carriers(resp, "static")) == ["dhl", "ups"]
    assert resp.live_error == "タイムアウト"


@pytest.mark.asyncio
async def test_no_origin_does_not_call_fedex():
    """発送元の国が無い → 連携の鍵を読まず FedEx を呼ばない・静的な行と文を返す（暗黙に JP を使わない）。"""
    resp, _, get_creds, try_live = await _call(_db(), origin=None, creds={"client_id": "x"})
    assert sorted(_carriers(resp, "static")) == ["dhl", "ups"]
    assert resp.live_error is not None and "発送元" in resp.live_error
    get_creds.assert_not_awaited()
    try_live.assert_not_awaited()


@pytest.mark.asyncio
async def test_destination_from_bill_to_when_no_ship_to():
    """発送先の写しが無い → 請求先の国と郵便番号を使う（draft-context と同じ関数）。"""
    live_row = _row("fedex", source="fedex_live")
    _, calc, _, try_live = await _call(
        _db(), snapshots=(None, BILL_TO), creds={"client_id": "x"}, live=([live_row], None, "exact"),
    )
    assert calc.await_args.args[1] == "US"
    assert try_live.await_args.kwargs["destination_postal_code"] == "94105"


@pytest.mark.asyncio
async def test_no_destination_is_422():
    with pytest.raises(HTTPException) as exc:
        await _call(_db(), snapshots=(None, None))
    assert exc.value.status_code == 422
    assert exc.value.detail == "draft_shipping_destination"


@pytest.mark.asyncio
async def test_unknown_company_is_404():
    with pytest.raises(HTTPException) as exc:
        await _call(_db(company_exists=False))
    assert exc.value.status_code == 404
    assert exc.value.detail == "not_found:company"


@pytest.mark.asyncio
async def test_calc_shipping_not_connected_unchanged():
    """今の /shipping/calculate の未連携の応答が前と同じ（D3）。"""
    from app.routers.shipping import calc_shipping
    from app.schemas.shipping import ShippingCalcRequest

    with patch("app.services.carrier_credentials.get_credentials", AsyncMock(return_value=None)):
        resp = await calc_shipping(
            data=ShippingCalcRequest(country_code="US", weight_kg=Decimal("1.0"), carrier="fedex", origin_country_code="JP"),
            db=AsyncMock(),
            tenant_id=1,
            current_user=MagicMock(),
        )
    assert resp.model_dump() == {
        "results": [],
        "cheapest": None,
        "live_error": "FedEx が未連携です。キャリア連携設定でアカウントを接続してください",
        "rate_precision": None,
    }
