"""契約と請求書の public の9表と税率の API の試験（ADR-1061 便2-2a。design.md §8 A14・A15・A31）。

非 PG: 権限（403）と入力の形（422）。
PG（CI の使い捨て DB。pg fixture。書き込みはアプリの役割 salesanchor_app）: 9表の RLS（A31）・名簿を消したときの
SET NULL（A14）・税率の追加と削除の決まり（A15 の後半）・印が張られないときに処理が止まること（A31 の処理の動き）。
テストデータはすべて架空。
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import psycopg2
import pytest
from sqlalchemy.engine import make_url

from app.database import get_db
from tests.test_super_admin_viewers import _account, _api, _call, _make_user, _prepare
from tests.test_super_admin_viewers import override_user as override_user  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

needs_ci_pg = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") != "true" or not os.getenv("RLS_TEST_DATABASE_URL"),
    reason="Disposable CI PostgreSQL service and app role required",
)

NEW_MIGRATION = "20261112_140000_create_viewer_contract_public_tables.sql"
BASE = "/api/v1/super-admin/tax-rates"

ROUTES = [
    ("GET", BASE, None),
    ("POST", BASE, {"rate_percent": "10.00", "effective_from": "2019-10-01"}),
    ("DELETE", f"{BASE}/1", None),
]


# ── 非 PG ─────────────────────────────────────────────────────


async def test_non_super_admin_gets_403_on_all_routes(override_user):  # noqa: F811
    override_user(_make_user(is_super_admin=False))
    for method, path, body in ROUTES:
        resp = await _call(method, path, body)
        assert resp.status_code == 403, (method, path)


@pytest.mark.parametrize(
    "body",
    [
        {"rate_percent": "100.01", "effective_from": "2030-01-01"},
        {"rate_percent": "-1", "effective_from": "2030-01-01"},
        {"rate_percent": "10.001", "effective_from": "2030-01-01"},
        {"rate_percent": "10.00", "effective_from": "2030-01-01", "extra": 1},
        {"rate_percent": "10.00"},
        {"effective_from": "2030-01-01"},
    ],
)
async def test_create_body_validation_422(override_user, body):  # noqa: F811
    from app.main import app

    async def _no_db():
        yield None

    override_user(_make_user(is_super_admin=True))
    app.dependency_overrides[get_db] = _no_db
    resp = await _call("POST", BASE, body)
    assert resp.status_code == 422


# ── PG 共通 ───────────────────────────────────────────────────


def _today_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


def _app_conn_and_url(conn):
    """アプリの役割 salesanchor_app で同じ使い捨て DB へつなぐ（同期の接続と、API 用の非同期の URL）。"""
    app_url = make_url(os.environ["RLS_TEST_DATABASE_URL"]).set(database=conn.info.dbname)
    app_conn = psycopg2.connect(
        dbname=app_url.database, host=app_url.host, port=app_url.port,
        user=app_url.username, password=app_url.password,
    )
    return app_conn, app_url.set(drivername="postgresql+asyncpg")


def _setup(conn, async_url):
    cur = _prepare(conn, async_url, seed_templates=False)
    cur.execute((MIGRATIONS / NEW_MIGRATION).read_text())
    return cur


def _seed(cur):
    """管理者（RLS を通らない）で各表に1行ずつ入れる。"""
    cur.execute("INSERT INTO public.prefectures (code, name_ja, name_en, sort_order) VALUES ('13', '東京都', 'Tokyo', 13)")
    cur.execute("INSERT INTO public.sa_products (code, name, seller_tenant_id) VALUES ('p-1', 'test product', 999) RETURNING id")
    product_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO public.sa_plans (product_id, code, name, billing_type, unit_price_jpy) "
        "VALUES (%s, 'plan-1', 'test plan', 'one_time', 200000) RETURNING id",
        (product_id,),
    )
    plan_id = cur.fetchone()[0]
    cur.execute("INSERT INTO public.sa_plan_features (plan_id, feature_key) VALUES (%s, 'inventory_view')", (plan_id,))
    vid = _account(cur, "a31@example.com", "contracting", expires_in_days=3)
    cur.execute(
        "INSERT INTO public.sa_contracts (plan_id, viewer_account_id, status) VALUES (%s, %s, 'active') RETURNING id",
        (plan_id, vid),
    )
    contract_id = cur.fetchone()[0]
    cur.execute("INSERT INTO public.tax_rates (rate_percent, effective_from) VALUES (10.00, '2019-10-01')")
    cur.execute(
        "INSERT INTO public.viewer_invoices (invoice_number, contract_id, viewer_account_id, status, issued_at, due_date, "
        "subtotal_jpy, discount_total_jpy, taxable_jpy, tax_rate_percent, tax_amount_jpy, total_jpy, "
        "bill_to_snapshot, issuer_snapshot) "
        "VALUES ('INV-TEST-1', %s, %s, 'issued', now(), CURRENT_DATE + 3, 200000, 0, 200000, 10.00, 20000, 220000, "
        "'{}'::jsonb, '{}'::jsonb) RETURNING id",
        (contract_id, vid),
    )
    invoice_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO public.viewer_invoice_lines (invoice_id, line_type, description, amount_jpy, sort_order) "
        "VALUES (%s, 'item', 'line-1', 200000, 1)",
        (invoice_id,),
    )
    cur.execute("INSERT INTO public.viewer_invoice_number_seq (year, last_number) VALUES (2026, 1)")
    return vid


# 表ごとに: (表, 目印の列, 種の行の値, 2行目の値, 2行目を入れる文, UPDATE の SET)
TABLE_CASES = [
    ("prefectures", "code", "13", "14",
     "INSERT INTO public.prefectures (code, name_ja, name_en, sort_order) VALUES ('14', '神奈川県', 'Kanagawa', 14)",
     "sort_order = sort_order"),
    ("sa_products", "code", "p-1", "p-2",
     "INSERT INTO public.sa_products (code, name, seller_tenant_id) VALUES ('p-2', 'test product 2', 999)",
     "name = name"),
    ("sa_plans", "code", "plan-1", "plan-2",
     "INSERT INTO public.sa_plans (product_id, code, name, billing_type, unit_price_jpy) "
     "SELECT id, 'plan-2', 'test plan 2', 'one_time', 1000 FROM public.sa_products WHERE code = 'p-1'",
     "name = name"),
    ("sa_plan_features", "feature_key", "inventory_view", "sheet_distribution",
     "INSERT INTO public.sa_plan_features (plan_id, feature_key) "
     "SELECT id, 'sheet_distribution' FROM public.sa_plans WHERE code = 'plan-1'",
     "feature_key = feature_key"),
    ("sa_contracts", "status", "active", "cancelled",
     "INSERT INTO public.sa_contracts (plan_id, status) SELECT id, 'cancelled' FROM public.sa_plans WHERE code = 'plan-1'",
     "status = status"),
    ("tax_rates", "effective_from", "2019-10-01", "2030-01-01",
     "INSERT INTO public.tax_rates (rate_percent, effective_from) VALUES (8.00, '2030-01-01')",
     "rate_percent = rate_percent"),
    ("viewer_invoices", "invoice_number", "INV-TEST-1", "INV-TEST-2",
     "INSERT INTO public.viewer_invoices (invoice_number, status, issued_at, due_date, subtotal_jpy, "
     "discount_total_jpy, taxable_jpy, tax_rate_percent, tax_amount_jpy, total_jpy, bill_to_snapshot, issuer_snapshot) "
     "VALUES ('INV-TEST-2', 'voided', now(), CURRENT_DATE + 3, 1000, 0, 1000, 10.00, 100, 1100, '{}'::jsonb, '{}'::jsonb)",
     "mail_error = mail_error"),
    ("viewer_invoice_lines", "description", "line-1", "line-2",
     "INSERT INTO public.viewer_invoice_lines (invoice_id, line_type, description, amount_jpy, sort_order) "
     "SELECT id, 'item', 'line-2', 1000, 2 FROM public.viewer_invoices WHERE invoice_number = 'INV-TEST-1'",
     "sort_order = sort_order"),
    ("viewer_invoice_number_seq", "year", 2026, 2027,
     "INSERT INTO public.viewer_invoice_number_seq (year, last_number) VALUES (2027, 0)",
     "last_number = last_number"),
]


@needs_ci_pg
def test_public_tables_rls_and_viewer_delete_sets_null(pg):  # noqa: F811
    """A31（DB の動き。9表それぞれ）と A14（名簿を消すと請求書と契約の viewer_account_id が NULL）。"""
    conn, _, async_url = pg
    cur = _setup(conn, async_url)
    vid = _seed(cur)
    app_conn, _ = _app_conn_and_url(conn)
    try:
        acur = app_conn.cursor()
        acur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        assert acur.fetchone() == (False, False)
        app_conn.rollback()

        assert len(TABLE_CASES) == 9
        for table, key, seed_value, second_value, insert_sql, set_sql in TABLE_CASES:
            # 印なし: INSERT は RLS の誤り（42501）、UPDATE と DELETE は0行、読むのはできる
            with pytest.raises(psycopg2.Error) as exc_info:
                acur.execute(insert_sql)
            assert exc_info.value.pgcode == "42501", table
            app_conn.rollback()
            acur.execute(f"UPDATE public.{table} SET {set_sql} WHERE {key} = %s", (seed_value,))
            assert acur.rowcount == 0, table
            acur.execute(f"DELETE FROM public.{table} WHERE {key} = %s", (seed_value,))
            assert acur.rowcount == 0, table
            acur.execute(f"SELECT count(*) FROM public.{table} WHERE {key} = %s", (seed_value,))
            assert acur.fetchone()[0] == 1, table
            app_conn.rollback()

            # 印あり: 足す・直す・消すが通る
            acur.execute("SELECT set_config('app.is_operator', 'true', true)")
            acur.execute(insert_sql)
            assert acur.rowcount == 1, table
            acur.execute(f"UPDATE public.{table} SET {set_sql} WHERE {key} = %s", (seed_value,))
            assert acur.rowcount == 1, table
            acur.execute(f"DELETE FROM public.{table} WHERE {key} = %s", (second_value,))
            assert acur.rowcount == 1, table
            app_conn.commit()

        # A14: アプリの役割（印なし）で名簿の行を消す
        acur.execute("DELETE FROM public.viewer_accounts WHERE id = %s", (vid,))
        assert acur.rowcount == 1
        app_conn.commit()
    finally:
        app_conn.close()

    cur.execute("SELECT viewer_account_id, contract_id FROM public.viewer_invoices WHERE invoice_number = 'INV-TEST-1'")
    viewer_id, contract_id = cur.fetchone()
    assert viewer_id is None
    assert contract_id is not None
    cur.execute("SELECT viewer_account_id FROM public.sa_contracts WHERE id = %s", (contract_id,))
    assert cur.fetchone()[0] is None


def _api_or_error(url, method, path, body=None):
    """ASGITransport はアプリの例外をそのまま投げる。投げたときは 500 と誤りの文を返す。"""
    try:
        return _api(url, method, path, body).status_code, ""
    except Exception as exc:  # noqa: BLE001  試験の中で誤りの種類と文を確かめる
        return 500, f"{type(exc).__name__}: {exc}"


@needs_ci_pg
def test_tax_rate_api_rules_and_operator_flag(pg, monkeypatch):  # noqa: F811
    """A15 の後半（422・409 の2種・404）と A31 の処理の動き（印が張られないと止まり、行は変わらない）。"""
    conn, _, async_url = pg
    cur = _setup(conn, async_url)
    app_conn, app_async_url = _app_conn_and_url(conn)
    app_conn.close()
    today = _today_jst()
    tomorrow = today + timedelta(days=1)

    # 表が空のときだけ過去の日付が通る
    resp = _api(app_async_url, "POST", BASE, {"rate_percent": "10.00", "effective_from": "2019-10-01"})
    assert resp.status_code == 201, resp.text
    first = resp.json()
    assert Decimal(str(first["rate_percent"])) == Decimal("10.00")
    assert first["effective_from"] == "2019-10-01"
    cur.execute("SELECT created_by_user_id FROM public.tax_rates WHERE id = %s", (first["id"],))
    assert cur.fetchone()[0] == 999

    # 表が空でないとき: 今日以前・最新行以前は 422
    for value in (today.isoformat(), "2019-10-01", "2020-01-01"):
        resp = _api(app_async_url, "POST", BASE, {"rate_percent": "10.00", "effective_from": value})
        assert resp.status_code == 422, value
        assert resp.json()["detail"] == "tax_rate.effective_from_invalid"

    # 明日は通る。同じ日はもう一度は通らない（最新行以前）
    resp = _api(app_async_url, "POST", BASE, {"rate_percent": "8.00", "effective_from": tomorrow.isoformat()})
    assert resp.status_code == 201, resp.text
    future_id = resp.json()["id"]
    resp = _api(app_async_url, "POST", BASE, {"rate_percent": "8.00", "effective_from": tomorrow.isoformat()})
    assert resp.status_code == 422

    # 同時に2つ来たとき（前の確かめを素通りした）: 一意の制約で 409。行は増えない
    async def _no_latest(db):
        return None

    import app.routers.super_admin_tax_rates as tax_router

    real_latest = tax_router._latest_effective_from
    monkeypatch.setattr(tax_router, "_latest_effective_from", _no_latest)
    resp = _api(app_async_url, "POST", BASE, {"rate_percent": "8.00", "effective_from": tomorrow.isoformat()})
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == "tax_rate.effective_from_taken"
    monkeypatch.setattr(tax_router, "_latest_effective_from", real_latest)
    cur.execute("SELECT count(*) FROM public.tax_rates")
    assert cur.fetchone()[0] == 2

    # 一覧: 新しい順・今日は日本時間
    resp = _api(app_async_url, "GET", BASE)
    assert resp.status_code == 200
    data = resp.json()
    assert [r["effective_from"] for r in data["rates"]] == [tomorrow.isoformat(), "2019-10-01"]
    assert data["today"] == today.isoformat()

    # 削除: 始まった行は 409、無い id は 404、明日の行は 204
    resp = _api(app_async_url, "DELETE", f"{BASE}/{first['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "tax_rate.not_deletable"
    resp = _api(app_async_url, "DELETE", f"{BASE}/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "tax_rate.not_found"
    resp = _api(app_async_url, "DELETE", f"{BASE}/{future_id}")
    assert resp.status_code == 204
    cur.execute("SELECT count(*) FROM public.tax_rates")
    assert cur.fetchone()[0] == 1

    # A31 処理の動き: 印を張る関数を空にすると、削除は0行で止まり、追加は RLS で止まる。行は変わらない
    cur.execute(
        "INSERT INTO public.tax_rates (rate_percent, effective_from) VALUES (10.00, %s) RETURNING id",
        (tomorrow + timedelta(days=1),),
    )
    later_id = cur.fetchone()[0]

    async def _no_flag(db):
        return None

    monkeypatch.setattr("app.routers.super_admin_tax_rates.set_operator_context", _no_flag)
    status_code, message = _api_or_error(app_async_url, "DELETE", f"{BASE}/{later_id}")
    assert status_code == 500
    assert message == "" or "affected 0 rows" in message, message
    cur.execute("SELECT count(*) FROM public.tax_rates WHERE id = %s", (later_id,))
    assert cur.fetchone()[0] == 1

    status_code, message = _api_or_error(
        app_async_url, "POST", BASE,
        {"rate_percent": "10.00", "effective_from": (tomorrow + timedelta(days=2)).isoformat()},
    )
    assert status_code == 500
    assert message == "" or "row-level security" in message, message
    cur.execute("SELECT count(*) FROM public.tax_rates")
    assert cur.fetchone()[0] == 2
