"""請求書の額の計算が使う表の読み方を本物の PostgreSQL で確かめる（invoice-create-portfolio 便C・K3・K22・K23・K24・K25）。

- 税率・為替・関税の行の読み方、新しいテナントの請求書の表、支払方法の候補と版、材料の道・為替の道の形。
- 試験の中で入れた行は最後に戻す。ゲートは CI が設定する RLS_ADMIN_DATABASE_URL（前例 test_duty_rules_pg.py）。
- 実 PostgreSQL は手元で立てない。CI だけで動く（ここでは skip と出てよい）。
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.routers.invoices import (
    _INSERT_INVOICE_SQL,
    _INVOICE_COLUMNS,
    fetch_fx_rate,
    get_invoice_draft_context,
)
from app.schemas.invoice import InvoiceDetailResponse
from app.services import invoice_payment_methods as pay
from app.services import invoice_totals as it
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_public_countries,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

# 試験・移行のどこにも無い 953 を使う（2026-11-16 に origin/main で数えた。D18）
_TENANT_ID = 953
_SCHEMA = f"tenant_{_TENANT_ID:03d}"

# G0: 共有の準備が作らない public の表（本番と同じ migration を順に流す。何度流しても同じ結果）
_PUBLIC_MIGRATIONS = (
    "070_add_spreadsheet_phase.sql",
    "20260604_050000_add_tenant_policy_columns.sql",
    "20260610_071110_add_paypal_config.sql",
    "20260628_170000_add_app_fx_rates.sql",
    "20261003_100000_create_app_fx_rate_history.sql",
)


async def _scalar(db: AsyncSession, sql: str, params: dict | None = None):
    return (await db.execute(text(sql), params or {})).scalar_one()


async def _insert_method(db: AsyncSession, region: str, method_type: str, display_name: str, *, is_active: bool = True) -> int:
    return await _scalar(
        db,
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_methods (region, method_type, display_name, is_active) "
        "VALUES (:r, :t, :n, :a) RETURNING id",
        {"r": region, "t": method_type, "n": display_name, "a": is_active},
    )


async def _insert_bank_detail(db: AsyncSession, method_id: int, number: str) -> None:
    await db.execute(
        text(
            f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_bank "
            "(payment_method_id, account_holder, bank_name, bank_branch, bank_account_type, bank_account_number) "
            "VALUES (:id, 'Holder', 'Test Bank', 'Main', 'Ordinary', :num)"
        ),
        {"id": method_id, "num": number},
    )


async def _insert_wise_detail(db: AsyncSession, method_id: int, currency: str) -> None:
    await db.execute(
        text(
            f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_wise "
            "(payment_method_id, account_holder, wise_currency, wise_email) "
            "VALUES (:id, 'Holder', :cur, 'wise@example.com')"
        ),
        {"id": method_id, "cur": currency},
    )


async def _check_readers(db: AsyncSession) -> None:
    # G1 税率と為替の読み方
    await db.execute(text("INSERT INTO public.tax_rates (rate_percent, effective_from) VALUES (9.00, DATE '2100-01-01')"))
    row = await it.load_tax_row(db, date(2100, 1, 2))
    assert row is not None and row.rate_percent == Decimal("9.00")
    before = await it.load_tax_row(db, date(2099, 12, 31))
    assert before is None or before.effective_from < date(2100, 1, 1)

    await db.execute(
        text(
            "INSERT INTO public.app_fx_rate_history (currency, rate_jpy, fetched_at) VALUES "
            "('ZZT', 100, TIMESTAMPTZ '2026-01-01 00:00:00+00'), ('ZZT', 120, TIMESTAMPTZ '2026-06-01 00:00:00+00')"
        )
    )
    fx = await it.load_latest_fx(db)
    assert fx["ZZT"].rate_jpy == Decimal("120.0000")

    # G2 関税の行の読み方
    rule_id = await _scalar(
        db,
        f"INSERT INTO {_SCHEMA}.tenant_duty_rules (destination_country_code, carrier, label, effective_from, effective_to, source_url) "
        "VALUES ('US', NULL, 'US DDP', DATE '2026-01-01', DATE '2026-12-31', 'https://example.com/duty') RETURNING id",
    )
    await db.execute(
        text(
            f"INSERT INTO {_SCHEMA}.tenant_duty_rule_components (rule_id, sort_order, label, base, rate_pct) VALUES "
            "(:r, 2, 'second', 'subtotal_shipping', 5), (:r, 1, 'first', 'subtotal', 10)"
        ),
        {"r": rule_id},
    )
    await db.execute(
        text(
            f"INSERT INTO {_SCHEMA}.tenant_duty_rules (destination_country_code, carrier, label, effective_from, effective_to, source_url, is_active) "
            "VALUES ('US', NULL, 'US stopped', DATE '2026-01-01', DATE '2026-12-31', 'https://example.com/duty', FALSE)"
        )
    )
    rules = await it.load_duty_rules(db, _TENANT_ID, "US", date(2026, 12, 31))
    assert [r.id for r in rules] == [rule_id]
    assert [c.label for c in rules[0].components] == ["first", "second"]
    assert await it.load_duty_rules(db, _TENANT_ID, "US", date(2027, 1, 1)) == ()


async def _check_new_tenant(db: AsyncSession) -> tuple[int, int, int]:
    """G3 新しいテナントの請求書の表に、計算の値をそのまま入れて読める。"""
    lead_id = await _scalar(db, f"INSERT INTO {_SCHEMA}.leads (customer_name) VALUES ('lead') RETURNING id")
    company_id = await _scalar(
        db,
        f"INSERT INTO {_SCHEMA}.companies (company_code, lead_id, name) VALUES ('C-953', :l, 'Company 953') RETURNING id",
        {"l": lead_id},
    )
    contact_id = await _scalar(
        db,
        f"INSERT INTO {_SCHEMA}.contacts (company_id, contact_code, display_name, primary_email) "
        "VALUES (:c, 'CT-953', 'Contact 953', 'c953@example.com') RETURNING id",
        {"c": company_id},
    )
    await db.execute(
        text(
            f"INSERT INTO {_SCHEMA}.company_addresses (company_id, address_type, country_code, is_default) "
            "VALUES (:c, 'billing', 'JP', TRUE)"
        ),
        {"c": company_id},
    )
    inputs = it.TotalsInputs(
        base_date=date(2026, 11, 15), incoterms="DAP", tax=None, duty_rules=(),
        fx={"USD": it.FxRow(currency="USD", rate_jpy=Decimal("150.0000"), fetched_at=datetime(2026, 11, 15, 1, 0, tzinfo=timezone.utc))},
    )
    totals = it.compute_totals(
        currency="USD",
        items=[it.TotalsItem(quantity=2, unit_price=Decimal("10.00"))],
        shipping=it.ShippingChoice(mode="none"),
        destination="US",
        inputs=inputs,
    )
    assert totals.uncomputed == []
    params = {
        "tid": _TENANT_ID, "inv_num": "IN-953-01", "qid": None,
        "company_id": company_id, "contact_id": contact_id, "currency": "USD",
        "payment": None, "payment_method_id": None, "erp_key": "E953",
        "due_date": None, "notes": None, "created_by": None,
        "ship_to": None, "bill_to": None, "issuer_region": "domestic",
        **it.to_db_params(totals),
    }
    invoice_id = await _scalar(db, _INSERT_INVOICE_SQL.replace("INSERT INTO invoices", f"INSERT INTO {_SCHEMA}.invoices"), params)
    fetched = await db.execute(text(f"SELECT {_INVOICE_COLUMNS} FROM {_SCHEMA}.invoices WHERE id = :id"), {"id": invoice_id})
    stored = fetched.mappings().first()
    assert stored is not None
    detail = InvoiceDetailResponse(**dict(stored), items=[])
    assert detail.total_amount == Decimal("20.00")
    assert detail.shipping_snapshot is not None and detail.shipping_snapshot["no_charge"] is True
    return company_id, contact_id, invoice_id


async def _check_payment_methods(db: AsyncSession) -> int:
    """G4・G5 支払方法の候補と版。新しい版の id を返す。"""
    x = await _insert_method(db, "domestic", "bank", "X bank")
    await _insert_bank_detail(db, x, "1111111")
    wise = await _insert_method(db, "overseas", "wise", "Wise USD")
    await _insert_wise_detail(db, wise, "USD")
    no_detail = await _insert_method(db, "domestic", "bank", "No detail")
    stopped = await _insert_method(db, "domestic", "bank", "Stopped", is_active=False)
    await _insert_bank_detail(db, stopped, "2222222")

    domestic = await pay.list_payment_choices(db, _TENANT_ID, "domestic")
    assert [c["id"] for c in domestic] == [x]
    overseas = await pay.list_payment_choices(db, _TENANT_ID, "overseas")
    assert [(c["id"], c["wise_currency"]) for c in overseas] == [(wise, "USD")]
    assert await pay.list_payment_choices(db, _TENANT_ID, None) == []

    ok = await pay.resolve_payment_ref(db, _TENANT_ID, method_type="wise", method_id=wise, region="overseas", currency="USD")
    assert ok == ("wise", wise)
    with pytest.raises(pay.PaymentMethodInvalid):
        await pay.resolve_payment_ref(db, _TENANT_ID, method_type="wise", method_id=wise, region="overseas", currency="JPY")
    with pytest.raises(pay.PaymentMethodInvalid):
        await pay.resolve_payment_ref(db, _TENANT_ID, method_type="bank", method_id=no_detail, region="domestic", currency="JPY")
    with pytest.raises(pay.PaymentMethodInvalid):
        await pay.resolve_payment_ref(db, _TENANT_ID, method_type="paypal", method_id=None, region="overseas", currency="USD")

    # G5 版: 新しい行 Y と詳細を足し、X を Y に差し替える
    y = await _insert_method(db, "domestic", "bank", "X bank v2")
    await _insert_bank_detail(db, y, "3333333")
    await db.execute(
        text(
            f"UPDATE {_SCHEMA}.tenant_invoice_payment_methods SET superseded_by_id = :y "
            "WHERE id = :x AND superseded_by_id IS NULL AND deleted_at IS NULL"
        ),
        {"x": x, "y": y},
    )
    after = await pay.list_payment_choices(db, _TENANT_ID, "domestic")
    assert [c["id"] for c in after] == [y]
    with pytest.raises(pay.PaymentMethodInvalid):
        await pay.resolve_payment_ref(db, _TENANT_ID, method_type="bank", method_id=x, region="domestic", currency="JPY")
    assert await pay.is_current_choice(db, _TENANT_ID, payment_method_id=x, region="domestic", currency="JPY") is False
    assert await pay.is_current_choice(db, _TENANT_ID, payment_method_id=y, region="domestic", currency="JPY") is True
    old = await pay.load_payment_version(db, _TENANT_ID, x)
    assert old is not None and old["account_number"] == "1111111"
    label = await pay.load_payment_label(db, _TENANT_ID, x)
    assert label == {"method_type": "bank", "display_name": "X bank"}
    return y


async def _check_routes(db: AsyncSession, company_id: int, invoice_id: int, y: int, wise_choice_ids: list[int]) -> None:
    """G6 材料の道・G7 為替の道は、道の関数を直接呼ぶ（試験用の client を使わない）。"""
    await db.execute(text(f"SET search_path TO {_SCHEMA}, public"))
    ctx = await get_invoice_draft_context(
        company_id=company_id, contact_id=None, invoice_id=None, db=db, tenant_id=_TENANT_ID, current_user=None,
    )
    assert ctx.issuer_region == "domestic"
    assert [p.id for p in ctx.payment_methods] == [y]
    zzt = [r for r in ctx.fx_rates if r.currency == "ZZT"]
    assert len(zzt) == 1 and zzt[0].rate == 120.0 and (zzt[0].fetched_at or "").endswith("+00:00")
    assert "ZZT" in ctx.currencies and ctx.currencies[0] == "JPY"

    # invoice-portfolio R1 K3: 住所の6項目と国名を返す（請求先の行だけがある会社なので届け先は None）
    await db.execute(
        text(
            "UPDATE company_addresses SET name = 'Recv 953', email = 'a953@example.com', tax_id = 'TX953', "
            "address_line_1 = 'L1', address_line_2 = 'L2', address_line_3 = 'L3', "
            "city = 'C953', state = 'S953', zip = 'Z953' "
            "WHERE company_id = :c AND address_type = 'billing'"
        ),
        {"c": company_id},
    )
    jp_name = (await db.execute(text("SELECT name FROM public.countries WHERE code = 'JP'"))).scalar_one_or_none()
    k3 = await get_invoice_draft_context(
        company_id=company_id, contact_id=None, invoice_id=None, db=db, tenant_id=_TENANT_ID, current_user=None,
    )
    assert k3.ship_to is None and k3.bill_to is not None
    b = k3.bill_to
    assert (b.recipient_name, b.email, b.tax_id) == ("Recv 953", "a953@example.com", "TX953")
    assert (b.address_line_1, b.address_line_2, b.address_line_3) == ("L1", "L2", "L3")
    assert (b.address, b.city, b.state, b.postal_code) == ("L1 L2", "C953", "S953", "Z953")
    assert b.country == "JP" and b.country_name == jp_name
    assert k3.issuer_region == "domestic"

    stored = await get_invoice_draft_context(
        company_id=None, contact_id=None, invoice_id=invoice_id, db=db, tenant_id=_TENANT_ID, current_user=None,
    )
    assert [p.id for p in stored.payment_methods] == [y]
    assert stored.currency == "USD"

    await db.execute(
        text("UPDATE company_addresses SET country_code = 'US' WHERE company_id = :c AND address_type = 'billing'"),
        {"c": company_id},
    )
    changed = await get_invoice_draft_context(
        company_id=None, contact_id=None, invoice_id=invoice_id, db=db, tenant_id=_TENANT_ID, current_user=None,
    )
    assert [p.id for p in changed.payment_methods] == [y]
    fresh = await get_invoice_draft_context(
        company_id=company_id, contact_id=None, invoice_id=None, db=db, tenant_id=_TENANT_ID, current_user=None,
    )
    assert fresh.issuer_region == "overseas"
    assert [p.id for p in fresh.payment_methods] == wise_choice_ids

    # G7 為替の道: 表の最新行から返す
    zzt_rate = await fetch_fx_rate("ZZT", db=db, tenant_id=_TENANT_ID, current_user=None)
    assert zzt_rate["rate"] == 120.0 and str(zzt_rate["fetched_at"]).endswith("+00:00")
    with pytest.raises(HTTPException) as exc_info:
        await fetch_fx_rate("ZZQ", db=db, tenant_id=_TENANT_ID, current_user=None)
    assert exc_info.value.status_code == 503
    jpy = await fetch_fx_rate("JPY", db=db, tenant_id=_TENANT_ID, current_user=None)
    assert jpy == {"currency": "JPY", "rate": 1.0, "fetched_at": None}


async def _cleanup(admin_engine) -> None:
    """G8 後始末: 入れた public の行とテナントのスキーマを消す。無くても失敗しない。"""
    async with public_bootstrap_lock(admin_engine):
        async with admin_engine.begin() as conn:
            await conn.execute(text("DELETE FROM public.tax_rates WHERE effective_from = DATE '2100-01-01'"))
            await conn.execute(text("DELETE FROM public.app_fx_rate_history WHERE currency = 'ZZT'"))
            await conn.execute(text("DELETE FROM public.tenant_settings WHERE tenant_id = :t"), {"t": _TENANT_ID})
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_invoice_totals_pg_end_to_end(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("get_fx_rate must not be called")

    monkeypatch.setattr("app.services.fx_rate.get_fx_rate", _boom)
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        await bootstrap_public_countries(admin_engine)
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            assert await bootstrap_tenant_schema(admin_engine, _TENANT_ID) == _SCHEMA
            # G0: 表の準備は後始末の try の外に置く（表が無いまま後始末が動いて本当の失敗が隠れるのを防ぐ）
            async with public_bootstrap_lock(admin_engine):
                async with admin_engine.begin() as conn:
                    for name in _PUBLIC_MIGRATIONS:
                        await _apply_migration_on_conn(conn, name)
            try:
                async with AsyncSession(admin_engine, expire_on_commit=False) as db:
                    try:
                        await _check_readers(db)
                        company_id, _contact_id, invoice_id = await _check_new_tenant(db)
                        wise_before = await pay.list_payment_choices(db, _TENANT_ID, "overseas")
                        assert wise_before == []
                        y = await _check_payment_methods(db)
                        wise_ids = [c["id"] for c in await pay.list_payment_choices(db, _TENANT_ID, "overseas")]
                        await _check_routes(db, company_id, invoice_id, y, wise_ids)
                    finally:
                        await db.rollback()
            finally:
                await _cleanup(admin_engine)
    finally:
        await admin_engine.dispose()
