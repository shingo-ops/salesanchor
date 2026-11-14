"""invoice-create-portfolio 便A: 関税の決まりの表 2 つ・請求書の 5 列の構造と決まりの試験。

- 単体（PostgreSQL 不要）: 新テナント用 DDL に表 2 つと請求書の列（移行だけにあった 12 列を含む）と明細の hs_code が含まれ、
  移行ファイルが登録され、値を入れない。請求書に振込先の写しと口座番号の列が無い（K21・ADR-1079）。
- PG（CI で実行）: 新テナントを作った形（tenant.py）と、表と列を消して移行ファイルを 2 回流した形が同じ。
  決まり（CHECK・外部キー・消したときの連鎖）が設計どおりに効き、別の会社の文脈では行が見えない（K17）。
  試験の中で入れた行と役割は最後に戻す。ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（前例 test_tenant_issuer_tables_pg.py と同じ形）。
"""
from __future__ import annotations

import datetime
import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.ops.readonly_query import DENY_COLUMN_RE
from app.services import tenant as tenant_service
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql"
# 試験・移行のどこにも無い 962 を使う（2026-11-13 に origin/main で git grep して試験・移行に 0 件）
_TENANT_ID = 962
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_TABLES = ("tenant_duty_rules", "tenant_duty_rule_components")
_NEW_INVOICE_COLUMNS = (
    "payment_method_id",
    "tax_rate_percent",
    "shipping_carrier",
    "shipping_service",
    "shipping_snapshot",
)
_OLD_INVOICE_COLUMNS = (
    "ship_to_snapshot JSONB,",
    "bill_to_snapshot JSONB,",
    "issue_mode VARCHAR(20),",
    "duty_amount NUMERIC(15, 2),",
    "duty_policy_snapshot JSONB,",
    "fx_rate_snapshot JSONB,",
    "paypal_order_id TEXT,",
    "paypal_approval_url TEXT,",
    "payment_fee NUMERIC(15, 2),",
    "paypal_invoicer_view_url TEXT,",
    "paypal_copy_pdf BYTEA,",
    "paypal_copy_pdf_at TIMESTAMPTZ,",
)


def _block(sql: str, marker: str) -> str:
    """marker の直後から、最初の '\\n);' までを返す（表の列定義）。"""
    marker = "CREATE TABLE IF NOT EXISTS " + marker
    assert sql.count(marker) == 1, marker
    body = sql.split(marker)[1]
    return body[: body.index("\n);")]


def _sqlstate(exc) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def test_tenant_ddl_has_duty_tables_and_invoice_columns():
    sql = tenant_service._TENANT_TABLES_SQL
    invoices = _block(sql, "{schema}.invoices (")
    for line in _OLD_INVOICE_COLUMNS:
        assert f"    {line}" in invoices, line
    for line in (
        "payment_method_id INTEGER,",
        "tax_rate_percent NUMERIC(5, 2),",
        "shipping_carrier VARCHAR(50),",
        "shipping_service VARCHAR(100),",
        "shipping_snapshot JSONB,",
    ):
        assert f"    {line}" in invoices, line
    assert "incoterm" not in invoices
    for items in ("{schema}.quote_items (", "{schema}.invoice_items ("):
        assert "    hs_code VARCHAR(20)," in _block(sql, items), items

    rules = _block(sql, "{schema}.tenant_duty_rules (")
    for name in ("country", "carrier", "label", "source_url", "period"):
        assert f"CONSTRAINT chk_tenant_duty_rules_{name} CHECK" in rules
    assert "incoterm" not in rules
    assert "updated_by_user_id" not in rules
    components = _block(sql, "{schema}.tenant_duty_rule_components (")
    assert "rule_id INTEGER NOT NULL REFERENCES {schema}.tenant_duty_rules(id) ON DELETE CASCADE," in components
    for name in ("label", "base", "rate", "amounts", "currency", "currency_required"):
        assert f"CONSTRAINT chk_tenant_duty_rule_components_{name} CHECK" in components

    for table in _TABLES:
        assert f"ALTER TABLE {{schema}}.{table} ENABLE ROW LEVEL SECURITY;" in tenant_service._RLS_ENABLE_SQL
        assert f"CREATE POLICY {table}_tenant_isolation ON {{schema}}.{table}" in tenant_service._RLS_POLICY_SQL


def test_migration_file_exists_and_is_registered():
    migration = _REPO_ROOT / "migrations" / _MIGRATION
    assert migration.is_file()
    body = migration.read_text(encoding="utf-8")
    for table in _TABLES:
        assert f"CREATE TABLE IF NOT EXISTS %I.{table} (" in body
        assert f"ALTER TABLE %I.{table} ENABLE ROW LEVEL SECURITY" in body
        assert f"CREATE POLICY {table}_tenant_isolation ON %I.{table}" in body
    for column in _NEW_INVOICE_COLUMNS:
        assert f"ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS {column} " in body
    runner = (_REPO_ROOT / "scripts" / "run_all_migrations.sh").read_text(encoding="utf-8")
    lines = [line for line in runner.splitlines() if line.startswith("run_sql ")]
    assert lines.count(f"run_sql migrations/{_MIGRATION}") == 1


def test_migration_writes_no_values():
    """ADR-155: 構造変更のみ（INSERT INTO / UPDATE 表 / DELETE FROM を含まない。ON DELETE CASCADE は外部キーの決まり）。"""
    body = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    code = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("--")
    ).upper()
    for word in ("INSERT INTO", "UPDATE %I", "UPDATE PUBLIC.", "DELETE FROM"):
        assert word not in code


def test_invoices_hold_no_payment_copy():
    """K21（ADR-1079）: 請求書は振込先の版の番号だけを持つ。振込先の写しと口座番号の列は、新しい会社の DDL にも移行にも無い。"""
    invoices = _block(tenant_service._TENANT_TABLES_SQL, "{schema}.invoices (")
    body = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    for name in ("payment_method_snapshot", "payment_account_number", "account_number", "iban"):
        assert name not in invoices, name
        assert name not in body, name


def test_migration_is_scoped_to_own_tenant():
    from tests.rls_bootstrap import _scope_tenant_migration

    sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    scoped = _scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql


async def _shape(conn) -> dict:
    tables = list(_TABLES)
    columns = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable, column_default,"
            " character_maximum_length, numeric_precision, numeric_scale"
            " FROM information_schema.columns"
            " WHERE table_schema = :s AND (table_name = ANY(:t)"
            " OR (table_name = 'invoices' AND column_name = ANY(:c)))"
            " ORDER BY table_name, column_name"
        ),
        {"s": _SCHEMA, "t": tables, "c": list(_NEW_INVOICE_COLUMNS)},
    )
    constraints = await conn.execute(
        text(
            "SELECT c.relname, con.conname, pg_get_constraintdef(con.oid)"
            " FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t)"
            " ORDER BY c.relname, con.conname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    indexes = await conn.execute(
        text(
            "SELECT tablename, indexname, indexdef FROM pg_indexes"
            " WHERE schemaname = :s AND tablename = ANY(:t) ORDER BY tablename, indexname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    policies = await conn.execute(
        text(
            "SELECT tablename, policyname, qual FROM pg_policies"
            " WHERE schemaname = :s AND tablename = ANY(:t) ORDER BY tablename, policyname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    rls = await conn.execute(
        text(
            "SELECT c.relname, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t) ORDER BY c.relname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    return {
        "columns": [tuple(row) for row in columns.all()],
        "constraints": [tuple(row) for row in constraints.all()],
        "indexes": [tuple(row) for row in indexes.all()],
        "policies": [tuple(row) for row in policies.all()],
        "rls": [tuple(row) for row in rls.all()],
    }


_RULE_SQL = (
    f"INSERT INTO {_SCHEMA}.tenant_duty_rules"
    " (destination_country_code, carrier, label, effective_from, effective_to, source_url)"
    " VALUES (:country, :carrier, :label, :from_date, :to_date, :url) RETURNING id"
)
_RULE_OK = {
    "country": "US",
    "carrier": "fedex",
    "label": "Duty",
    "from_date": datetime.date(2026, 1, 1),  # asyncpg は DATE に date 型が要る（文字列は DataError）
    "to_date": None,
    "url": "https://example.com/duty",
}
_COMPONENT_SQL = (
    f"INSERT INTO {_SCHEMA}.tenant_duty_rule_components"
    " (rule_id, label, base, rate_pct, min_amount, max_amount, amount_currency)"
    " VALUES (:rule_id, :label, :base, :rate, :min_amount, :max_amount, :currency)"
)


async def _expect_error(conn, sql: str, params: dict, code: str) -> None:
    sp = await conn.begin_nested()
    with pytest.raises(DBAPIError) as exc_info:
        await conn.execute(text(sql), params)
    await sp.rollback()
    assert _sqlstate(exc_info.value) == code, (sql, params)


async def _count(conn, table: str) -> int:
    return (await conn.execute(text(f"SELECT count(*) FROM {_SCHEMA}.{table}"))).scalar_one()


async def _check_rules(conn) -> None:
    """決まりと会社の分けが効くことを確かめる。呼び出し側の取引は最後に戻す（行と役割を残さない）。"""
    rule_id = (await conn.execute(text(_RULE_SQL), _RULE_OK)).scalar_one()
    # 送料の会社は小文字・前後の空白なし・空でない形だけ（K17・第8版）
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "carrier": "FedEx"}, "23514")
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "carrier": " fedex"}, "23514")
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "carrier": ""}, "23514")
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "country": "us"}, "23514")  # 国は英大文字2字
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "url": ""}, "23514")  # 根拠の URL は空にできない
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "url": "   "}, "23514")
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "label": "  "}, "23514")  # 名前は空にできない
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "to_date": datetime.date(2025, 12, 31)}, "23514")  # 終わりは始まり以降

    ok = {"rule_id": rule_id, "label": "Duty", "base": "subtotal", "rate": 10, "min_amount": None, "max_amount": None, "currency": None}
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "base": "x"}, "23514")  # 基準は3つだけ
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "rate": -1}, "23514")  # 率は0以上
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "min_amount": 10, "max_amount": 5, "currency": "USD"}, "23514")  # 下限は上限以下
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "min_amount": 10}, "23514")  # 下限があれば通貨が要る
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "min_amount": 10, "currency": "usd"}, "23514")  # 通貨は英大文字3字
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "rule_id": rule_id + 100000}, "23503")  # 無い決まりは指せない
    await conn.execute(text(_COMPONENT_SQL), {**ok, "min_amount": 1, "max_amount": 100, "currency": "USD"})

    # K17: 別の会社の文脈では、どちらの表も 0 行に見える（RLS を飛ばせない役割で確かめる）
    probe = f"duty_rls_probe_{uuid.uuid4().hex[:12]}"
    await conn.execute(text(f"CREATE ROLE {probe} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
    await conn.execute(text(f"GRANT USAGE ON SCHEMA {_SCHEMA} TO {probe}"))
    for table in _TABLES:
        await conn.execute(text(f"GRANT SELECT ON {_SCHEMA}.{table} TO {probe}"))
    await conn.execute(text(f"SET LOCAL ROLE {probe}"))
    await conn.execute(text("SELECT set_config('app.tenant_id', '961', true)"))
    assert [await _count(conn, t) for t in _TABLES] == [0, 0]
    await conn.execute(text(f"SELECT set_config('app.tenant_id', '{_TENANT_ID}', true)"))
    assert [await _count(conn, t) for t in _TABLES] == [1, 1]
    await conn.execute(text("RESET ROLE"))

    await conn.execute(text(f"DELETE FROM {_SCHEMA}.tenant_duty_rules WHERE id = :id"), {"id": rule_id})
    assert await _count(conn, "tenant_duty_rule_components") == 0  # 決まりを消すと中身も消える


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_new_tenant_shape_equals_migration_and_rules_hold():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            try:
                schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
                assert schema_name == _SCHEMA
                async with admin_engine.connect() as conn:
                    before = await _shape(conn)  # 新しい会社の作り方（tenant.py）で作った形
                assert len(before["rls"]) == 2
                assert all(row[1] for row in before["rls"])
                assert len(before["policies"]) == 2
                assert len([c for c in before["columns"] if c[0] == "invoices"]) == 5
                # 表と列を消してから、全テナントを回す正本をこの試験のテナントだけに絞って 2 回流す
                async with admin_engine.begin() as conn:
                    for table in reversed(_TABLES):
                        await conn.execute(text(f"DROP TABLE {_SCHEMA}.{table}"))
                    for column in _NEW_INVOICE_COLUMNS:
                        await conn.execute(text(f"ALTER TABLE {_SCHEMA}.invoices DROP COLUMN {column}"))
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 1 回目
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 2 回目（冪等）
                async with admin_engine.connect() as conn:
                    after = await _shape(conn)
                assert before == after
                # K21（ADR-1079）: 実物の請求書の表に、読み取りの鍵の列名の決まりに当たる列が0個
                async with admin_engine.connect() as conn:
                    names = (
                        await conn.execute(
                            text(
                                "SELECT column_name FROM information_schema.columns"
                                " WHERE table_schema = :s AND table_name = 'invoices'"
                            ),
                            {"s": _SCHEMA},
                        )
                    ).scalars().all()
                assert len(names) >= 47  # tenant.py の30列＋移行だけにあった12列＋便Aの5列
                assert [n for n in names if DENY_COLUMN_RE.search(n.lower())] == []

                conn = await admin_engine.connect()
                try:
                    trans = await conn.begin()
                    try:
                        await _check_rules(conn)
                    finally:
                        await trans.rollback()
                finally:
                    await conn.close()
            finally:
                async with public_bootstrap_lock(admin_engine):
                    async with admin_engine.begin() as conn:
                        await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    finally:
        await admin_engine.dispose()
