"""請求書の額の計算（invoice-create-portfolio 便C・純粋な計算。DB なし）。

対象: app.services.invoice_totals の compute_totals と、その周りの小さな関数。
design.md §3-3・§3-4・§8 の K4・K6・K7・K9・K13・K18。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from app.services import invoice_totals
from app.services.invoice_totals import (
    DutyComponent,
    DutyRule,
    FxRow,
    ShippingChoice,
    TaxRow,
    TotalsInputs,
    TotalsItem,
    compute_totals,
    destination_country,
    destination_postal_code,
    first_block,
    normalize_carrier,
    today_jst,
)

_FETCHED = datetime(2026, 11, 15, 1, 0, tzinfo=timezone.utc)


def inputs(**kw) -> TotalsInputs:
    base = {
        "base_date": date(2026, 11, 15),
        "incoterms": "DAP",
        "tax": TaxRow(rate_percent=Decimal("10.00"), effective_from=date(2019, 10, 1)),
        "duty_rules": (),
        "fx": {"USD": FxRow(currency="USD", rate_jpy=Decimal("150.0000"), fetched_at=_FETCHED)},
    }
    base.update(kw)
    return TotalsInputs(**base)


def _items(*pairs: tuple[int, str]) -> list[TotalsItem]:
    return [TotalsItem(quantity=q, unit_price=Decimal(p)) for q, p in pairs]


def _calc(fee: str, cur: str = "JPY", carrier: str = "FedEx") -> ShippingChoice:
    return ShippingChoice(mode="calculate", carrier=carrier, service_type="FEDEX_IP", fee=Decimal(fee), currency=cur)


NONE = ShippingChoice(mode="none")


def _rule(rule_id: int, carrier: str | None, comps: tuple[DutyComponent, ...], label: str = "US duty") -> DutyRule:
    return DutyRule(
        id=rule_id, carrier=carrier, label=label, source_url="https://example.com/duty",
        effective_from=date(2026, 1, 1), effective_to=None, components=comps,
    )


def _comp(order: int, base: str, rate: str, lo: str | None = None, hi: str | None = None, cur: str | None = None) -> DutyComponent:
    return DutyComponent(
        sort_order=order, label=f"c{order}", base=base, rate_pct=Decimal(rate),
        min_amount=Decimal(lo) if lo is not None else None,
        max_amount=Decimal(hi) if hi is not None else None,
        amount_currency=cur,
    )


def test_t1_jp_destination_jpy_tax_and_total():
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="JP", inputs=inputs())
    assert r.subtotal == Decimal("6000")
    assert r.tax_amount == Decimal("600")
    assert r.total_amount == Decimal("6600")
    assert r.tax_rate_percent == Decimal("10.00")
    assert r.uncomputed == []


def test_t2_tax_base_includes_shipping():
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=_calc("1000"), destination="JP", inputs=inputs())
    assert r.shipping_fee == Decimal("1000")
    assert r.tax_amount == Decimal("700")
    assert r.total_amount == Decimal("7700")


def test_t3_tax_is_floored_to_the_minor_unit():
    jpy = compute_totals(currency="JPY", items=_items((1, "999")), shipping=NONE, destination="JP", inputs=inputs())
    assert jpy.tax_amount == Decimal("99")
    usd = compute_totals(currency="USD", items=_items((1, "10.05")), shipping=NONE, destination="JP", inputs=inputs())
    assert usd.tax_amount == Decimal("1.00")


def test_t4_foreign_destination_has_no_tax():
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US", inputs=inputs())
    assert r.tax_amount == Decimal("0")
    assert r.tax_rate_percent is None
    assert r.total_amount == Decimal("6000")


def test_t5_missing_tax_row_blocks_jp_destination():
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="JP", inputs=inputs(tax=None))
    assert r.uncomputed == ["tax_rate"]
    assert r.total_amount is None
    assert first_block(r) == (409, "tax_rate")


def test_t6_missing_shipping_blocks_with_422():
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=None, destination="US", inputs=inputs())
    assert r.uncomputed[0] == "shipping_required"
    assert r.total_amount is None
    assert first_block(r) == (422, "shipping_required")


def test_t7_shipping_is_converted_into_the_invoice_currency():
    r = compute_totals(currency="USD", items=_items((1, "100")), shipping=_calc("15000", "JPY"), destination="US", inputs=inputs())
    assert r.shipping_fee == Decimal("100.00")
    snap = r.shipping_snapshot
    assert snap["original_fee"] == "15000"
    assert snap["original_currency"] == "JPY"
    assert [row["currency"] for row in snap["fx"]] == ["USD"]


def test_t8_currency_without_an_exchange_rate_blocks():
    r = compute_totals(currency="EUR", items=_items((1, "100")), shipping=NONE, destination="US", inputs=inputs())
    assert "fx_rate" in r.uncomputed
    assert r.total_amount is None


def test_t9_dap_and_ddu_do_not_charge_duty():
    rule = _rule(1, None, (_comp(1, "subtotal", "10"),))
    for incoterms in ("DAP", "DDU"):
        r = compute_totals(
            currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US",
            inputs=inputs(incoterms=incoterms, duty_rules=(rule,)),
        )
        assert r.duty_amount is None
        assert r.total_amount == Decimal("6000")


def test_t10_ddp_generic_rule():
    rule = _rule(7, None, (_comp(1, "subtotal", "10"),), label="US customs")
    r = compute_totals(
        currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US",
        inputs=inputs(incoterms="DDP", duty_rules=(rule,)),
    )
    assert r.duty_amount == Decimal("600")
    assert r.duty_label == "US customs"
    assert r.duty_policy_snapshot["rule"]["id"] == 7
    assert r.total_amount == Decimal("6600")


def test_t11_ddp_carrier_match_wins_over_generic():
    rule_a = _rule(1, "fedex", (_comp(1, "subtotal", "5"),), label="fedex rule")
    rule_b = _rule(2, None, (_comp(1, "subtotal", "10"),), label="any rule")
    r = compute_totals(
        currency="JPY", items=_items((2, "3000")), shipping=_calc("0", "JPY", carrier=" FedEx "), destination="US",
        inputs=inputs(incoterms="DDP", duty_rules=(rule_b, rule_a)),
    )
    assert r.duty_amount == Decimal("300")
    assert r.duty_label == "fedex rule"


def test_t12_ddp_carrier_only_rules_need_a_matching_carrier():
    rule = _rule(1, "fedex", (_comp(1, "subtotal", "5"),))
    ddp = inputs(incoterms="DDP", duty_rules=(rule,))
    none_ship = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US", inputs=ddp)
    assert "duty_needs_carrier" in none_ship.uncomputed
    assert first_block(none_ship) == (409, "duty_needs_carrier")
    other = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=_calc("0", "JPY", carrier="DHL"), destination="US", inputs=ddp)
    assert "duty_needs_carrier" in other.uncomputed
    assert other.total_amount is None


def test_t13_component_bases():
    rule = _rule(1, None, (
        _comp(1, "subtotal", "10"),
        _comp(2, "subtotal_shipping", "10"),
        _comp(3, "subtotal_shipping_prior", "10"),
    ))
    r = compute_totals(
        currency="JPY", items=_items((2, "3000")), shipping=_calc("1000"), destination="US",
        inputs=inputs(incoterms="DDP", duty_rules=(rule,)),
    )
    # 6000×10% = 600、(6000+1000)×10% = 700、(6000+1000+600+700)×10% = 830
    assert [Decimal(c["amount"]) for c in r.duty_components] == [Decimal("600"), Decimal("700"), Decimal("830")]
    assert r.duty_amount == Decimal("2130")


def test_t14_component_min_and_max():
    ddp = {"incoterms": "DDP"}
    low = _rule(1, None, (_comp(1, "subtotal", "10", lo="2000", cur="JPY"),))
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US", inputs=inputs(duty_rules=(low,), **ddp))
    assert r.duty_amount == Decimal("2000")
    high = _rule(2, None, (_comp(1, "subtotal", "50", hi="10", cur="USD"),))
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US", inputs=inputs(duty_rules=(high,), **ddp))
    assert r.duty_amount == Decimal("1500")
    missing = _rule(3, None, (_comp(1, "subtotal", "10", lo="10", cur="EUR"),))
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US", inputs=inputs(duty_rules=(missing,), **ddp))
    assert "fx_rate" in r.uncomputed
    assert r.total_amount is None


def test_t15_components_are_floored_one_by_one():
    rule = _rule(1, None, (_comp(1, "subtotal", "10"), _comp(2, "subtotal", "10")))
    r = compute_totals(
        currency="JPY", items=_items((1, "5")), shipping=NONE, destination="US",
        inputs=inputs(incoterms="DDP", duty_rules=(rule,)),
    )
    assert [Decimal(c["amount"]) for c in r.duty_components] == [Decimal("0"), Decimal("0")]
    assert r.duty_amount == Decimal("0")


def test_t16_total_is_subtotal_shipping_tax_and_duty():
    rule = _rule(1, None, (_comp(1, "subtotal", "10"),))
    with_duty = compute_totals(
        currency="JPY", items=_items((2, "3000")), shipping=_calc("1000"), destination="JP",
        inputs=inputs(incoterms="DDP", duty_rules=(rule,)),
    )
    # 6000 + 1000 + 税 700 + 関税 600
    assert with_duty.total_amount == Decimal("8300")
    without = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=_calc("1000"), destination="JP", inputs=inputs())
    assert without.duty_amount is None
    assert without.total_amount == Decimal("7700")


def test_t17_exchange_rate_columns():
    jpy = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US", inputs=inputs())
    assert jpy.exchange_rate_jpy is None
    assert jpy.amount_jpy == jpy.total_amount
    assert jpy.exchange_rate_usd == Decimal("150.0000")
    assert jpy.amount_usd == round(jpy.total_amount / Decimal("150.0000"), 2)
    usd = compute_totals(currency="USD", items=_items((1, "100")), shipping=NONE, destination="US", inputs=inputs())
    assert usd.exchange_rate_jpy == Decimal("150.0000")
    assert usd.amount_usd == usd.total_amount
    assert usd.amount_jpy == round(usd.total_amount * Decimal("150.0000"), 2)
    assert usd.exchange_rate_usd is None
    assert usd.fx_rate_snapshot["rate"] == 150.0
    assert usd.fx_rate_snapshot["fetched_at"].endswith("+00:00")


def test_t18_missing_usd_row_does_not_block_a_jpy_invoice():
    r = compute_totals(currency="JPY", items=_items((2, "3000")), shipping=NONE, destination="US", inputs=inputs(fx={}))
    assert r.amount_usd is None
    assert r.uncomputed == []
    assert r.total_amount == Decimal("6000")


def test_t19_normalize_carrier():
    assert normalize_carrier(" FedEx ") == "fedex"
    assert normalize_carrier("") is None
    assert normalize_carrier(None) is None


def test_t20_destination_country_and_postal_code():
    ship = {"country": "jp", "postal_code": "100-0001"}
    bill = {"country": "US", "postal_code": "10001"}
    assert destination_country(ship, bill) == "JP"
    assert destination_postal_code(ship, bill) == "100-0001"
    assert destination_country(None, bill) == "US"
    assert destination_postal_code(None, bill) == "10001"
    assert destination_country({"country": None, "postal_code": "x"}, bill) == "US"
    assert destination_country(None, None) is None
    assert destination_postal_code(None, None) is None


def test_t21_today_jst_uses_japan_time(monkeypatch):
    class _Fixed(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 14, 15, 30, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(invoice_totals, "datetime", _Fixed)
    assert today_jst() == date(2026, 11, 15)


# ── 便E: PayPal の支払い手数料（design-e.md §3-2・K1〜K3・K5）──────────────────

from tests.conftest import paypal_fee_rows  # noqa: E402


def test_e1_paypal_domestic_jpy():
    r = compute_totals(
        currency="JPY", items=_items((1, "100000")), shipping=NONE, destination="US",
        inputs=inputs(payment_fee_rows=paypal_fee_rows(international=False)), payment_method_type="paypal",
    )
    assert r.payment_fee == Decimal("3640")
    assert r.total_amount == Decimal("103640")
    assert r.payment_fee_snapshot["rate_pct"] == "3.6000"


def test_e2_paypal_international_usd_with_fx():
    r = compute_totals(
        currency="USD", items=_items((1, "1000.00")), shipping=NONE, destination="US",
        inputs=inputs(payment_fee_rows=paypal_fee_rows(with_fx=True)), payment_method_type="paypal",
    )
    assert r.payment_fee == Decimal("81.26")
    assert r.total_amount == Decimal("1081.26")


def test_e3_bank_wise_none_have_no_fee():
    for method in ("bank", "wise", None):
        r = compute_totals(
            currency="JPY", items=_items((1, "100000")), shipping=NONE, destination="US",
            inputs=inputs(payment_fee_rows=paypal_fee_rows(international=False)), payment_method_type=method,
        )
        assert r.payment_fee == Decimal("0")
        assert r.payment_fee_snapshot is None
        assert r.total_amount == Decimal("100000")


def test_e4_paypal_blocks_without_rows():
    good = paypal_fee_rows(with_fx=True)
    with_threshold = invoice_totals.PaymentFeeRows(
        receiving=invoice_totals.PaymentFeeRow(
            id=9, fee_type="receiving_international", rate_pct=Decimal("4.1"), fixed_amount=Decimal("40"),
            threshold=Decimal("1000"),
        ),
        fx=good.fx, required_fx=True,
    )
    cases = [
        ("JPY", None),
        ("JPY", invoice_totals.PaymentFeeRows(receiving=None, fx=None, required_fx=False)),
        ("USD", with_threshold),
        ("USD", invoice_totals.PaymentFeeRows(receiving=good.receiving, fx=None, required_fx=True)),
    ]
    for cur, rows in cases:
        r = compute_totals(
            currency=cur, items=_items((1, "1000")), shipping=NONE, destination="US",
            inputs=inputs(payment_fee_rows=rows), payment_method_type="paypal",
        )
        assert r.uncomputed[-1] == "payment_fee"
        assert r.total_amount is None
        assert first_block(r) == (409, "payment_fee")


def test_e5_reason_order_ends_with_payment_fee():
    assert invoice_totals.REASON_ORDER[-1] == "payment_fee"


def test_e6_to_db_params_payment_fee_columns():
    import json

    from app.services.invoice_totals import to_db_params

    paypal = compute_totals(
        currency="JPY", items=_items((1, "100000")), shipping=NONE, destination="US",
        inputs=inputs(payment_fee_rows=paypal_fee_rows(international=False)), payment_method_type="paypal",
    )
    p = to_db_params(paypal)
    assert p["payment_fee_charged"] == Decimal("3640")
    assert json.loads(p["payment_fee_snapshot"])["method_type"] == "paypal"
    bank = compute_totals(
        currency="JPY", items=_items((1, "100000")), shipping=NONE, destination="US",
        inputs=inputs(), payment_method_type="bank",
    )
    b = to_db_params(bank)
    assert b["payment_fee_charged"] is None
    assert b["payment_fee_snapshot"] is None
