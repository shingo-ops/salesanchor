"""ADR-1061 便2-2c1: 発行元の会社情報と振込先の表 4 つ・請求書の発行元区分の列の構造と決まりの試験。

- 単体（PostgreSQL 不要）: 新テナント用 DDL に表 4 つと列が含まれ、移行ファイルが登録され、値を入れない。
- PG（CI で実行）: 新テナントを作った形（tenant.py）と、表と列を消して移行ファイルを 2 回流した形が同じ。
  決まり（CHECK・一意・外部キー・消したときの連鎖）が設計どおりに効く。試験の中で入れた行は最後に戻す。
  ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_discord_role_link_ddl.py と同じ形）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.services import tenant as tenant_service
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)
from tests.seed_data import country_seed_sql, prefectures_seed_sql

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261112_160000_create_tenant_issuer_and_payment_tables.sql"
# 試験・移行のどこにも無い 963 を使う（2026-11-12 に origin/main で git grep して 0 件）
_TENANT_ID = 963
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_TABLES = (
    "tenant_issuer_profiles",
    "tenant_invoice_payment_methods",
    "tenant_invoice_payment_bank",
    "tenant_invoice_payment_wise",
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


def test_tenant_ddl_has_issuer_and_payment_tables():
    sql = tenant_service._TENANT_TABLES_SQL
    invoices = _block(sql, "{schema}.invoices (")
    assert (
        "issuer_region VARCHAR(20) CONSTRAINT chk_invoices_issuer_region"
        " CHECK (issuer_region IN ('domestic', 'overseas')),"
    ) in invoices

    profiles = _block(sql, "{schema}.tenant_issuer_profiles (")
    assert "country_code CHAR(2) NOT NULL REFERENCES public.countries(code)," in profiles
    assert "prefecture_code CHAR(2) REFERENCES public.prefectures(code)," in profiles
    assert "CONSTRAINT uq_tenant_issuer_profiles_tenant_region UNIQUE (tenant_id, region)," in profiles
    for name in ("jp_address", "foreign_address", "phone", "registration"):
        assert f"CONSTRAINT chk_tenant_issuer_profiles_{name} CHECK" in profiles

    methods = _block(sql, "{schema}.tenant_invoice_payment_methods (")
    assert "CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type)," in methods

    for kind in ("bank", "wise"):
        detail = _block(sql, f"{{schema}}.tenant_invoice_payment_{kind} (")
        assert f"method_type VARCHAR(10) NOT NULL DEFAULT '{kind}'," in detail
        assert (
            f"CONSTRAINT fk_tenant_invoice_payment_{kind}_method FOREIGN KEY (payment_method_id, tenant_id, method_type)"
            " REFERENCES {schema}.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE"
        ) in detail

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
    assert "ADD COLUMN IF NOT EXISTS issuer_region VARCHAR(20)" in body
    assert "ALTER TABLE public.tenant_google_drive_config ADD COLUMN IF NOT EXISTS overseas_folder_id TEXT;" in body
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


async def _shape(conn) -> dict:
    tables = list(_TABLES)
    columns = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable, column_default, character_maximum_length"
            " FROM information_schema.columns"
            " WHERE table_schema = :s AND (table_name = ANY(:t)"
            " OR (table_name = 'invoices' AND column_name = 'issuer_region'))"
            " ORDER BY table_name, column_name"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    constraints = await conn.execute(
        text(
            "SELECT c.relname, con.conname, pg_get_constraintdef(con.oid)"
            " FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND (c.relname = ANY(:t) OR con.conname = 'chk_invoices_issuer_region')"
            " ORDER BY c.relname, con.conname"
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
        "policies": [tuple(row) for row in policies.all()],
        "rls": [tuple(row) for row in rls.all()],
    }


_JP = {
    "region": "domestic",
    "company_name": "試験商事",
    "country_code": "JP",
    "postal_code": "1000001",
    "prefecture_code": "13",
    "city": "千代田区",
    "address1": "千代田1-1",
    "phone": "0312345678",
    "is_invoice_registered": True,
    "registration_number": "T1234567890123",
}
_US = {
    "region": "overseas",
    "company_name": "Test Trading",
    "country_code": "US",
    "postal_code": "10001",
    "prefecture_code": None,
    "state_region": "NY",
    "city": "New York",
    "address1": "1 Main St",
    "phone": "+12125550100",
    "is_invoice_registered": False,
    "registration_number": None,
}


async def _insert_profile(conn, row: dict) -> None:
    cols = ", ".join(row)
    vals = ", ".join(f":{k}" for k in row)
    await conn.execute(text(f"INSERT INTO {_SCHEMA}.tenant_issuer_profiles ({cols}) VALUES ({vals})"), row)


async def _expect_error(conn, sql: str, params: dict, code: str) -> None:
    sp = await conn.begin_nested()
    with pytest.raises(DBAPIError) as exc_info:
        await conn.execute(text(sql), params)
    await sp.rollback()
    assert _sqlstate(exc_info.value) == code, sql


async def _expect_profile_error(conn, row: dict, code: str) -> None:
    cols = ", ".join(row)
    vals = ", ".join(f":{k}" for k in row)
    await _expect_error(conn, f"INSERT INTO {_SCHEMA}.tenant_issuer_profiles ({cols}) VALUES ({vals})", row, code)


async def _check_rules(conn) -> None:
    """決まりが効くことを確かめる。呼び出し側の取引は最後に戻す（行を残さない）。"""
    # rls_bootstrap.bootstrap_tenant_schema と同じ流し方（取引の中・運営の印は取引の中だけ）
    await conn.exec_driver_sql(country_seed_sql())
    await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
    await conn.exec_driver_sql(prefectures_seed_sql())
    await conn.execute(text("SELECT set_config('app.is_operator', '', true)"))

    await _insert_profile(conn, _JP)  # 国内用の正しい形は入る
    # 海外用の区分はまだ空なので、次の失敗は一意の決まりではなく、それぞれの決まりで起きる
    other = {**_JP, "region": "overseas"}
    await _expect_profile_error(conn, {**other, "phone": "03-1234-5678"}, "23514")  # 日本の電話は数字だけ
    await _expect_profile_error(conn, {**other, "prefecture_code": None}, "23514")  # 日本は都道府県が要る
    await _expect_profile_error(conn, {**other, "postal_code": "100-0001"}, "23514")  # 日本の郵便番号は7桁の数字
    await _expect_profile_error(conn, {**_US, "prefecture_code": "13"}, "23514")  # 海外に都道府県は入らない
    await _expect_profile_error(conn, {**_US, "phone": "12125550100"}, "23514")  # 海外の電話は + から
    await _expect_profile_error(conn, {**other, "is_invoice_registered": False}, "23514")  # 登録なしに番号は入らない
    await _expect_profile_error(conn, {**other, "registration_number": None}, "23514")  # 登録ありは番号が要る
    await _expect_profile_error(conn, {**other, "region": "asia"}, "23514")  # 区分は国内用・海外用だけ
    await _expect_profile_error(conn, {**_US, "country_code": "ZZ"}, "23503")  # 国の一覧に無い国
    await _insert_profile(conn, _US)  # 海外用の正しい形は入る
    await _expect_profile_error(conn, {**_JP}, "23505")  # 同じ区分は1行まで

    method_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_methods (region, method_type, display_name)"
        " VALUES (:region, :method_type, :display_name) RETURNING id"
    )
    bank_id = (await conn.execute(text(method_sql), {"region": "domestic", "method_type": "bank", "display_name": "銀行"})).scalar_one()
    wise_id = (await conn.execute(text(method_sql), {"region": "overseas", "method_type": "wise", "display_name": "Wise"})).scalar_one()
    await _expect_error(conn, method_sql, {"region": "domestic", "method_type": "paypal", "display_name": "x"}, "23514")

    bank_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_bank"
        " (payment_method_id, account_holder, bank_name, bank_branch, bank_account_type, bank_account_number)"
        " VALUES (:id, 'シケン', '試験銀行', '本店', '普通', '1234567')"
    )
    wise_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_wise (payment_method_id, account_holder, wise_currency, wise_email)"
        " VALUES (:id, 'Test', :cur, 'pay@example.com')"
    )
    await conn.execute(text(bank_sql), {"id": bank_id})
    await _expect_error(conn, wise_sql, {"id": bank_id, "cur": "USD"}, "23503")  # 銀行の行に Wise の詳細は付かない
    await _expect_error(conn, bank_sql, {"id": wise_id}, "23503")  # Wise の行に銀行の詳細は付かない
    await _expect_error(conn, wise_sql, {"id": wise_id, "cur": "jpy"}, "23514")  # 通貨は英大文字3字
    await conn.execute(text(wise_sql), {"id": wise_id, "cur": "USD"})

    await conn.execute(text(f"DELETE FROM {_SCHEMA}.tenant_invoice_payment_methods WHERE id = :id"), {"id": bank_id})
    left = await conn.execute(
        text(f"SELECT count(*) FROM {_SCHEMA}.tenant_invoice_payment_bank WHERE payment_method_id = :id"), {"id": bank_id}
    )
    assert left.scalar_one() == 0  # 振込先を消すと詳細も消える


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
                assert len(before["rls"]) == 4
                assert all(row[1] for row in before["rls"])
                assert len(before["policies"]) == 4
                # 表と列を消してから、全テナントを回す正本をこの試験のテナントだけに絞って 2 回流す
                async with admin_engine.begin() as conn:
                    for table in reversed(_TABLES):
                        await conn.execute(text(f"DROP TABLE {_SCHEMA}.{table}"))
                    await conn.execute(text(f"ALTER TABLE {_SCHEMA}.invoices DROP COLUMN issuer_region"))
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 1 回目
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 2 回目（冪等）
                async with admin_engine.connect() as conn:
                    after = await _shape(conn)
                assert before == after

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


def test_migration_is_scoped_to_own_tenant():
    from tests.rls_bootstrap import _scope_tenant_migration

    sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    scoped = _scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql
