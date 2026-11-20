"""請求書を作る流れ（invoice-create-portfolio 便C・SQLite）。

額の計算は stub_invoice_totals で public の表の代わりに差し替える。
対象: POST /invoices・POST /invoices/preview・POST /invoices/from-quote/{id}・POST /invoices/{id}/issue・PATCH。
design.md §3-4・§8 の K4・K6・K7・K9・K13・K15・K16・K18・K23。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.services import invoice_totals
from app.services.invoice_totals import DutyComponent, DutyRule, FxRow, TaxRow, today_jst
from tests.test_invoices import _create_company_contact

ITEMS = [
    {"product_name": "商品A", "quantity": 2, "unit_price": "1000.00"},
]
PREVIEW_ITEMS = [{"quantity": 2, "unit_price": "1000.00"}]


def D(value) -> Decimal:
    return Decimal(str(value))


def _body(company_id: int, contact_id: int, **kw) -> dict:
    body = {"company_id": company_id, "contact_id": contact_id, "items": ITEMS}
    body.update(kw)
    return body


def _fedex_rule(rate: str = "10") -> DutyRule:
    comp = DutyComponent(
        sort_order=1, label="Tariff", base="subtotal", rate_pct=Decimal(rate),
        min_amount=None, max_amount=None, amount_currency=None,
    )
    return DutyRule(
        id=1, carrier="fedex", label="US duty", source_url="https://example.com/duty",
        effective_from=date(2026, 1, 1), effective_to=None, components=(comp,),
    )


def _generic_rule(rate: str = "10") -> DutyRule:
    comp = DutyComponent(
        sort_order=1, label="Tariff", base="subtotal", rate_pct=Decimal(rate),
        min_amount=None, max_amount=None, amount_currency=None,
    )
    return DutyRule(
        id=2, carrier=None, label="US duty (any)", source_url="https://example.com/duty",
        effective_from=date(2026, 1, 1), effective_to=None, components=(comp,),
    )


async def _quote(client, company_id: int, contact_id: int, shipping_fee: str | None = None, currency: str | None = None) -> int:
    body = {
        "company_id": company_id,
        "contact_id": contact_id,
        "items": [{"product_name": "商品X", "quantity": 2, "unit_price": "1000.00"}],
    }
    if shipping_fee is not None:
        body["shipping_fee"] = shipping_fee
    if currency is not None:
        body["currency"] = currency
    res = await client.post("/api/v1/quotes", json=body)
    assert res.status_code == 201, res.text
    quote_id = res.json()["id"]
    await client.post(f"/api/v1/quotes/{quote_id}/send")
    await client.post(f"/api/v1/quotes/{quote_id}/approve")
    return quote_id


async def test_f1_missing_shipping_is_422(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F1会社")
    res = await client.post("/api/v1/invoices", json=_body(company_id, contact_id))
    assert res.status_code == 422, res.text
    assert res.json()["detail"] == "shipping_required"


async def test_f2_no_charge_shipping(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F2会社")
    res = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, shipping={"mode": "none"}))
    assert res.status_code == 201, res.text
    data = res.json()
    assert D(data["shipping_fee"]) == 0
    assert data["shipping_snapshot"]["no_charge"] is True
    assert data["shipping_carrier"] is None


async def test_f3_calculated_shipping_is_converted(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F3会社")
    res = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, currency="USD",
        shipping={"mode": "calculate", "carrier": "FedEx", "service_type": "FEDEX_INTERNATIONAL_PRIORITY", "fee": "12000", "currency": "JPY"},
    ))
    assert res.status_code == 201, res.text
    data = res.json()
    assert D(data["shipping_fee"]) == Decimal("80.00")
    assert data["shipping_carrier"] == "FedEx"
    assert data["shipping_service"] == "FEDEX_INTERNATIONAL_PRIORITY"


@pytest.mark.parametrize("field", [
    "tax_amount", "shipping_fee", "exchange_rate_jpy", "exchange_rate_usd", "amount_jpy", "amount_usd", "payment_method",
])
async def test_f4_amount_fields_are_not_accepted(client, stub_invoice_totals, field):
    company_id, contact_id = await _create_company_contact(client, f"F4会社{field}")
    body = _body(company_id, contact_id, shipping={"mode": "none"})
    body[field] = "1" if field != "payment_method" else "銀行振込"
    res = await client.post("/api/v1/invoices", json=body)
    assert res.status_code == 422, res.text


async def test_f5_shipping_shape_is_checked(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F5会社")
    no_carrier = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping={"mode": "calculate", "fee": "100", "currency": "JPY"}))
    assert no_carrier.status_code == 422
    no_fee = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping={"mode": "calculate", "carrier": "FedEx", "currency": "JPY"}))
    assert no_fee.status_code == 422
    none_with_fee = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping={"mode": "none", "fee": "100"}))
    assert none_with_fee.status_code == 422


async def test_f6_preview_and_create_agree(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F6会社", country="JP")
    shipping = {"mode": "calculate", "carrier": "FedEx", "service_type": "FEDEX_IP", "fee": "1500", "currency": "JPY"}
    items = [
        {"product_name": "商品A", "quantity": 2, "unit_price": "1000.00"},
        {"product_name": "商品B", "quantity": 1, "unit_price": "333.00"},
    ]
    prev = await client.post("/api/v1/invoices/preview", json={
        "company_id": company_id, "currency": "JPY", "shipping": shipping,
        "items": [{"quantity": i["quantity"], "unit_price": i["unit_price"]} for i in items],
    })
    assert prev.status_code == 200, prev.text
    p = prev.json()
    created = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id, "currency": "JPY", "shipping": shipping, "items": items,
    })
    assert created.status_code == 201, created.text
    c = created.json()
    for key in ("subtotal", "shipping_fee", "tax_amount", "total_amount"):
        assert D(p[key]) == D(c[key]), key
    assert p["uncomputed"] == []
    assert D(p["total_amount"]) > 0


async def test_f7_missing_tax_rate_blocks(client, stub_invoice_totals):
    stub_invoice_totals.set(tax=None)
    company_id, contact_id = await _create_company_contact(client, "F7会社", country="JP")
    prev = await client.post("/api/v1/invoices/preview", json={
        "company_id": company_id, "currency": "JPY", "items": PREVIEW_ITEMS, "shipping": {"mode": "none"},
    })
    assert prev.status_code == 200, prev.text
    assert prev.json()["uncomputed"] == ["tax_rate"]
    res = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, shipping={"mode": "none"}))
    assert res.status_code == 409, res.text
    assert res.json()["detail"] == "tax_rate"


async def test_f8_missing_exchange_rate_blocks(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F8会社")
    prev = await client.post("/api/v1/invoices/preview", json={
        "company_id": company_id, "currency": "EUR", "items": PREVIEW_ITEMS, "shipping": {"mode": "none"},
    })
    assert prev.status_code == 200, prev.text
    assert "fx_rate" in prev.json()["uncomputed"]
    res = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, currency="EUR", shipping={"mode": "none"}))
    assert res.status_code == 409, res.text
    assert res.json()["detail"] == "fx_rate"


async def test_f9_ddp_needs_a_matching_carrier(client, stub_invoice_totals):
    stub_invoice_totals.set(incoterms="DDP", duty_rules=(_fedex_rule(),))
    company_id, contact_id = await _create_company_contact(client, "F9会社")
    no_ship = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, shipping={"mode": "none"}))
    assert no_ship.status_code == 409, no_ship.text
    assert no_ship.json()["detail"] == "duty_needs_carrier"
    dhl = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping={"mode": "calculate", "carrier": "dhl", "fee": "0", "currency": "JPY"}))
    assert dhl.status_code == 409, dhl.text
    assert dhl.json()["detail"] == "duty_needs_carrier"
    ok = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping={"mode": "calculate", "carrier": " FedEx ", "fee": "0", "currency": "JPY"}))
    assert ok.status_code == 201, ok.text
    assert D(ok.json()["duty_amount"]) == Decimal("200")


async def test_f10_duty_follows_the_rate(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F10会社")
    shipping = {"mode": "none"}
    stub_invoice_totals.set(incoterms="DDP", duty_rules=(_generic_rule("10"),))
    prev = await client.post("/api/v1/invoices/preview", json={
        "company_id": company_id, "currency": "JPY", "items": PREVIEW_ITEMS, "shipping": shipping,
    })
    assert D(prev.json()["duty_amount"]) == Decimal("200")
    first = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, shipping=shipping))
    assert first.status_code == 201, first.text
    assert D(first.json()["duty_amount"]) == Decimal("200")
    stub_invoice_totals.set(duty_rules=(_generic_rule("20"),))
    prev2 = await client.post("/api/v1/invoices/preview", json={
        "company_id": company_id, "currency": "JPY", "items": PREVIEW_ITEMS, "shipping": shipping,
    })
    assert D(prev2.json()["duty_amount"]) == Decimal("400")
    second = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, shipping=shipping))
    assert D(second.json()["duty_amount"]) == Decimal("400")


async def test_f11_from_quote_recomputes_shipping(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F11会社", country="JP")
    free_quote = await _quote(client, company_id, contact_id)
    free = await client.post(f"/api/v1/invoices/from-quote/{free_quote}")
    assert free.status_code == 201, free.text
    assert free.json()["shipping_snapshot"]["source"] == "none"
    paid_quote = await _quote(client, company_id, contact_id, shipping_fee="500.00")
    paid = await client.post(f"/api/v1/invoices/from-quote/{paid_quote}")
    assert paid.status_code == 201, paid.text
    snap = paid.json()["shipping_snapshot"]
    assert snap["source"] == "quote"
    assert snap["original_fee"] in ("500.00", "500")
    direct = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id, "currency": "JPY",
        "shipping": {"mode": "calculate", "carrier": "FedEx", "fee": "500", "currency": "JPY"},
        "items": [{"product_name": "商品X", "quantity": 2, "unit_price": "1000.00"}],
    })
    assert direct.status_code == 201, direct.text
    for key in ("subtotal", "shipping_fee", "tax_amount", "total_amount"):
        assert D(paid.json()[key]) == D(direct.json()[key]), key


async def test_f12_from_quote_matches_carrier_after_trimming(client, db_session, stub_invoice_totals):
    stub_invoice_totals.set(incoterms="DDP", duty_rules=(_fedex_rule(),))
    company_id, contact_id = await _create_company_contact(client, "F12会社")
    quote_id = await _quote(client, company_id, contact_id, shipping_fee="500.00")
    blocked = await client.post(f"/api/v1/invoices/from-quote/{quote_id}")
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"] == "duty_needs_carrier"
    await db_session.execute(
        text("UPDATE quotes SET shipping_carrier = :c WHERE id = :id"), {"c": "  FEDEX ", "id": quote_id},
    )
    await db_session.commit()
    ok = await client.post(f"/api/v1/invoices/from-quote/{quote_id}")
    assert ok.status_code == 201, ok.text
    assert D(ok.json()["duty_amount"]) == Decimal("200")


async def test_f13_issue_recomputes_with_todays_tax_rate(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F13会社", country="JP")
    created = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, shipping={"mode": "none"}))
    assert created.status_code == 201, created.text
    assert D(created.json()["tax_amount"]) == Decimal("200")
    stub_invoice_totals.set(tax=TaxRow(rate_percent=Decimal("8.00"), effective_from=date(2019, 1, 1)))
    issued = await client.post(f"/api/v1/invoices/{created.json()['id']}/issue")
    assert issued.status_code == 200, issued.text
    data = issued.json()
    assert data["status"] == "issued"
    assert D(data["tax_amount"]) == Decimal("160")
    assert D(data["tax_rate_percent"]) == Decimal("8.00")
    assert data["shipping_carrier"] == created.json()["shipping_carrier"]
    assert stub_invoice_totals.calls[-1]["base_date"] == today_jst()
    detail = await client.get(f"/api/v1/invoices/{created.json()['id']}")
    assert len(detail.json()["items"]) == 1


async def test_f14_issue_refreshes_the_exchange_rate(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F14会社")
    created = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, currency="USD",
        shipping={"mode": "calculate", "carrier": "FedEx", "service_type": "FEDEX_IP", "fee": "15000", "currency": "JPY"},
    ))
    assert created.status_code == 201, created.text
    assert D(created.json()["shipping_fee"]) == Decimal("100.00")
    fetched = datetime(2026, 11, 15, 2, 0, tzinfo=timezone.utc)
    stub_invoice_totals.set(fx={"USD": FxRow(currency="USD", rate_jpy=Decimal("100.0000"), fetched_at=fetched)})
    issued = await client.post(f"/api/v1/invoices/{created.json()['id']}/issue")
    assert issued.status_code == 200, issued.text
    data = issued.json()
    assert D(data["shipping_fee"]) == Decimal("150.00")
    assert D(data["exchange_rate_jpy"]) == Decimal("100")
    assert D(data["total_amount"]) == Decimal("2150.00")
    assert data["shipping_snapshot"]["original_fee"] == "15000"


async def test_f15_issue_stops_when_duty_cannot_be_decided(client, stub_invoice_totals):
    company_id, contact_id = await _create_company_contact(client, "F15会社")
    created = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, shipping={"mode": "none"}))
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]
    stub_invoice_totals.set(incoterms="DDP", duty_rules=(_fedex_rule(),))
    issued = await client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert issued.status_code == 409, issued.text
    assert issued.json()["detail"] == "duty_needs_carrier"
    detail = await client.get(f"/api/v1/invoices/{invoice_id}")
    assert detail.json()["status"] == "draft"


async def test_f16_exchange_rate_comes_only_from_the_table(client, stub_invoice_totals, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("get_fx_rate must not be called")

    monkeypatch.setattr("app.services.fx_rate.get_fx_rate", _boom)
    company_id, contact_id = await _create_company_contact(client, "F16会社")
    created = await client.post("/api/v1/invoices", json=_body(company_id, contact_id, currency="USD", shipping={"mode": "none"}))
    assert created.status_code == 201, created.text
    quote_id = await _quote(client, company_id, contact_id, currency="USD")
    from_quote = await client.post(f"/api/v1/invoices/from-quote/{quote_id}")
    assert from_quote.status_code == 201, from_quote.text
    invoice_id = created.json()["id"]

    bad_rate = await client.patch(f"/api/v1/invoices/{invoice_id}", json={"exchange_rate_jpy": "100"})
    assert bad_rate.status_code == 422
    bad_text = await client.patch(f"/api/v1/invoices/{invoice_id}", json={"payment_method": "銀行振込"})
    assert bad_text.status_code == 422
    null_ref = await client.patch(f"/api/v1/invoices/{invoice_id}", json={"payment_method_ref": None})
    assert null_ref.status_code == 422
    assert null_ref.json()["detail"] == "payment_method"

    issued = await client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert issued.status_code == 200, issued.text
    locked = await client.patch(f"/api/v1/invoices/{invoice_id}", json={"notes": "x"})
    assert locked.status_code == 400
    assert "draft状態の請求書のみ編集できます" in locked.text
    assert invoice_totals.REASON_FX == "fx_rate"


# ── 便E: PayPal の支払い手数料（design-e.md §3・K5〜K7）──────────────────

from tests.conftest import paypal_fee_rows  # noqa: E402

PAYPAL = {"method_type": "paypal", "id": None}
BANK = {"method_type": "bank", "id": 3}
NO_SHIP = {"mode": "none"}


async def _count_invoices(client, company_id: int) -> int:
    res = await client.get(f"/api/v1/invoices?company_id={company_id}&per_page=100")
    assert res.status_code == 200, res.text
    return len(res.json())


async def test_e_preview_paypal_adds_fee(client, stub_invoice_totals, fake_payment_ref):
    stub_invoice_totals.set(payment_fee_rows=paypal_fee_rows())
    company_id, _contact_id = await _create_company_contact(client, "E1会社")
    base = {"company_id": company_id, "currency": "JPY", "items": PREVIEW_ITEMS, "shipping": NO_SHIP}
    bank = (await client.post("/api/v1/invoices/preview", json={**base, "payment_method_type": "bank"})).json()
    paypal = (await client.post("/api/v1/invoices/preview", json={**base, "payment_method_type": "paypal"})).json()
    assert D(bank["payment_fee"]) == 0
    assert D(paypal["payment_fee"]) > 0
    assert D(paypal["total_amount"]) == D(bank["total_amount"]) + D(paypal["payment_fee"])
    assert paypal["uncomputed"] == []


async def test_e_preview_paypal_without_rows_is_uncomputed(client, stub_invoice_totals, fake_payment_ref):
    company_id, _contact_id = await _create_company_contact(client, "E2会社")
    res = await client.post("/api/v1/invoices/preview", json={
        "company_id": company_id, "currency": "JPY", "items": PREVIEW_ITEMS, "shipping": NO_SHIP,
        "payment_method_type": "paypal",
    })
    assert res.status_code == 200, res.text
    assert res.json()["uncomputed"][-1] == "payment_fee"
    assert res.json()["total_amount"] is None


async def test_e_create_paypal_stores_fee_and_blocks_without_rows(client, stub_invoice_totals, fake_payment_ref):
    company_id, contact_id = await _create_company_contact(client, "E3会社")
    before = await _count_invoices(client, company_id)
    blocked = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping=NO_SHIP, payment_method_ref=PAYPAL))
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"] == "payment_fee"
    assert await _count_invoices(client, company_id) == before

    stub_invoice_totals.set(payment_fee_rows=paypal_fee_rows())
    ok = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping=NO_SHIP, payment_method_ref=PAYPAL))
    assert ok.status_code == 201, ok.text
    data = ok.json()
    assert D(data["payment_fee_charged"]) > 0
    assert D(data["total_amount"]) == D(data["subtotal"]) + D(data["payment_fee_charged"])
    assert await _count_invoices(client, company_id) == before + 1


async def test_e_patch_payment_method_recomputes_total(client, stub_invoice_totals, fake_payment_ref):
    stub_invoice_totals.set(payment_fee_rows=paypal_fee_rows())
    company_id, contact_id = await _create_company_contact(client, "E4会社")
    created = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping=NO_SHIP, payment_method_ref=BANK))
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]
    base_total = D(created.json()["total_amount"])
    assert created.json()["payment_fee_charged"] is None

    to_paypal = await client.patch(f"/api/v1/invoices/{invoice_id}", json={"payment_method_ref": PAYPAL})
    assert to_paypal.status_code == 200, to_paypal.text
    fee = D(to_paypal.json()["payment_fee_charged"])
    assert fee > 0
    assert D(to_paypal.json()["total_amount"]) == base_total + fee

    back = await client.patch(f"/api/v1/invoices/{invoice_id}", json={"payment_method_ref": BANK})
    assert back.status_code == 200, back.text
    assert back.json()["payment_fee_charged"] is None
    assert D(back.json()["total_amount"]) == base_total

    stub_invoice_totals.set(payment_fee_rows=None)
    stopped = await client.patch(f"/api/v1/invoices/{invoice_id}", json={"payment_method_ref": PAYPAL})
    assert stopped.status_code == 409, stopped.text
    assert stopped.json()["detail"] == "payment_fee"
    # 詳細の道は振込先の版を読みに行くので、一覧（同じ列）で「前のまま」を確かめる
    listed = (await client.get(f"/api/v1/invoices?company_id={company_id}&per_page=100")).json()
    after = next(i for i in listed if i["id"] == invoice_id)
    assert after["payment_method"] == "bank"
    assert after["payment_fee_charged"] is None
    assert D(after["total_amount"]) == base_total


async def test_e_issue_keeps_payment_fee(client, stub_invoice_totals, fake_payment_ref):
    stub_invoice_totals.set(payment_fee_rows=paypal_fee_rows())
    company_id, contact_id = await _create_company_contact(client, "E5会社")
    created = await client.post("/api/v1/invoices", json=_body(
        company_id, contact_id, shipping=NO_SHIP, payment_method_ref=PAYPAL))
    assert created.status_code == 201, created.text
    issued = await client.post(f"/api/v1/invoices/{created.json()['id']}/issue")
    assert issued.status_code == 200, issued.text
    assert D(issued.json()["payment_fee_charged"]) == D(created.json()["payment_fee_charged"])
    assert D(issued.json()["total_amount"]) == D(created.json()["total_amount"])
