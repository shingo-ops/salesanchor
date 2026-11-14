"""invoice-create-portfolio 便V（design.md §3-8・ADR-1079）: 振込先を版で持つ形と見張りの試験。

- 単体（PostgreSQL 不要）: 新テナント用 DDL に列 2 つ・決まり・索引・見張りの関数 3 つ・見張り 6 つがあり、
  関数の中身が移行ファイルと一字一句同じで、移行ファイルが登録され、値を入れない。
- PG（CI で実行）: 新テナントを作った形（tenant.py）と、見張り・関数・索引・決まり・列を外してから
  移行ファイルを 2 回流した形が同じ。版の決まりが設計どおりに効く。試験の中で入れた行は最後に戻す。
  ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_tenant_issuer_tables_pg.py と同じ形）。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.services import tenant as tenant_service
from tests import rls_bootstrap
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261115_100000_add_payment_method_versioning.sql"
# 試験・移行のどこにも無い 957 を使う（2026-11-15 に origin/main で git grep して 0 件）
_TENANT_ID = 957
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_TABLES = (
    "tenant_invoice_payment_methods",
    "tenant_invoice_payment_bank",
    "tenant_invoice_payment_wise",
)
_FUNCTIONS = {
    "trg_payment_detail_immutable": "pv_detail",
    "trg_payment_method_version_guard": "pv_method",
    "trg_payment_version_no_wipe": "pv_wipe",
}
_TRIGGERS = (
    ("trg_tenant_invoice_payment_methods_version_guard", "tenant_invoice_payment_methods"),
    ("trg_tenant_invoice_payment_bank_immutable", "tenant_invoice_payment_bank"),
    ("trg_tenant_invoice_payment_wise_immutable", "tenant_invoice_payment_wise"),
    ("trg_tenant_invoice_payment_methods_no_wipe", "tenant_invoice_payment_methods"),
    ("trg_tenant_invoice_payment_bank_no_wipe", "tenant_invoice_payment_bank"),
    ("trg_tenant_invoice_payment_wise_no_wipe", "tenant_invoice_payment_wise"),
)


def _migration_text() -> str:
    return (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")


def _body(sql: str, tag: str) -> str:
    """$tag$ と $tag$ の間（関数の中身）を返す。ちょうど 1 か所であること。"""
    found = re.findall(rf"\${tag}\$(.*?)\${tag}\$", sql, flags=re.S)
    assert len(found) == 1, tag
    return found[0]


def _sqlstate(exc) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def test_tenant_ddl_has_versioning():
    sql = tenant_service._TENANT_TABLES_SQL
    marker = "CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_methods ("
    assert sql.count(marker) == 1
    methods = sql.split(marker)[1]
    methods = methods[: methods.index("\n);")]
    assert "    superseded_by_id INTEGER,\n    deleted_at TIMESTAMPTZ,\n" in methods
    assert "CONSTRAINT chk_tenant_invoice_payment_methods_superseded_not_self CHECK (superseded_by_id <> id)," in methods
    assert (
        "CONSTRAINT fk_tenant_invoice_payment_methods_superseded_by FOREIGN KEY (superseded_by_id)"
        " REFERENCES {schema}.tenant_invoice_payment_methods (id)"
    ) in methods
    assert (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_invoice_payment_methods_superseded_by"
        " ON {schema}.tenant_invoice_payment_methods (superseded_by_id) WHERE superseded_by_id IS NOT NULL;"
    ) in sql
    for name, tag in _FUNCTIONS.items():
        assert f"CREATE OR REPLACE FUNCTION {{schema}}.{name}()\nRETURNS TRIGGER AS ${tag}$" in sql
    for trigger, table in _TRIGGERS:
        assert f"tgname = '{trigger}' AND tgrelid = '{{schema}}.{table}'::regclass" in sql
        assert f"CREATE TRIGGER {trigger} " in sql


def test_function_bodies_are_the_same_in_ddl_and_migration():
    """関数の中身の正本は 1 つ。新テナント用 DDL と移行ファイルで一字一句同じ。"""
    ddl = tenant_service._TENANT_TABLES_SQL
    migration = _migration_text()
    for tag in _FUNCTIONS.values():
        assert _body(ddl, tag) == _body(migration, tag), tag


def test_migration_file_exists_and_is_registered():
    body = _migration_text()
    assert "ADD COLUMN IF NOT EXISTS superseded_by_id INTEGER" in body
    assert "ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ" in body
    for name in _FUNCTIONS:
        assert f"CREATE OR REPLACE FUNCTION %I.{name}() RETURNS TRIGGER AS %L LANGUAGE plpgsql" in body
    for trigger, table in _TRIGGERS:
        assert f"CREATE TRIGGER {trigger} " in body
        assert f"ON %I.{table} " in body
    runner = (_REPO_ROOT / "scripts" / "run_all_migrations.sh").read_text(encoding="utf-8")
    lines = [line for line in runner.splitlines() if line.startswith("run_sql ")]
    assert lines.count(f"run_sql migrations/{_MIGRATION}") == 1
    # 振込先の表を作る移行より後に流す（ファイル名の日付は書かない。分類表の照合に数えられないように）
    issuer = [i for i, line in enumerate(lines) if line.endswith("_create_tenant_issuer_and_payment_tables.sql")]
    assert len(issuer) == 1
    assert lines.index(f"run_sql migrations/{_MIGRATION}") > issuer[0]
    assert rls_bootstrap._TENANT_LOOP_MIGRATIONS[_MIGRATION] == 1


def test_migration_writes_no_values():
    """ADR-155: 構造変更のみ（INSERT INTO / UPDATE 表 / DELETE FROM を含まない）。"""
    code = "\n".join(
        line for line in _migration_text().splitlines() if not line.strip().startswith("--")
    ).upper()
    for word in ("INSERT INTO", "UPDATE %I", "UPDATE PUBLIC.", "DELETE FROM"):
        assert word not in code


def test_migration_is_scoped_to_own_tenant():
    sql = _migration_text()
    scoped = rls_bootstrap._scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql


async def _shape(conn) -> dict:
    tables = list(_TABLES)
    columns = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable, column_default"
            " FROM information_schema.columns WHERE table_schema = :s AND table_name = ANY(:t)"
            " ORDER BY table_name, column_name"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    constraints = await conn.execute(
        text(
            "SELECT c.relname, con.conname, pg_get_constraintdef(con.oid)"
            " FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t) ORDER BY c.relname, con.conname"
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
    triggers = await conn.execute(
        text(
            "SELECT c.relname, t.tgname, pg_get_triggerdef(t.oid), t.tgenabled"
            " FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t) AND NOT t.tgisinternal"
            " ORDER BY c.relname, t.tgname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    functions = await conn.execute(
        text(
            "SELECT p.proname, pg_get_functiondef(p.oid) FROM pg_proc p"
            " JOIN pg_namespace n ON n.oid = p.pronamespace"
            " WHERE n.nspname = :s AND p.proname = ANY(:f) ORDER BY p.proname"
        ),
        {"s": _SCHEMA, "f": list(_FUNCTIONS)},
    )
    return {
        "columns": [tuple(row) for row in columns.all()],
        "constraints": [tuple(row) for row in constraints.all()],
        "indexes": [tuple(row) for row in indexes.all()],
        "triggers": [tuple(row) for row in triggers.all()],
        "functions": [tuple(row) for row in functions.all()],
    }


async def _expect_error(conn, sql: str, params: dict, code: str) -> None:
    sp = await conn.begin_nested()
    with pytest.raises(DBAPIError) as exc_info:
        await conn.execute(text(sql), params)
    await sp.rollback()
    assert _sqlstate(exc_info.value) == code, sql


async def _check_rules(conn) -> None:
    """版の決まりが効くことを確かめる。呼び出し側の取引は最後に戻す（行を残さない）。"""
    methods = f"{_SCHEMA}.tenant_invoice_payment_methods"
    new_method = f"INSERT INTO {methods} (region, method_type, display_name) VALUES (:r, :t, :n) RETURNING id"
    bank_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_bank"
        " (payment_method_id, account_holder, bank_name, bank_branch, bank_account_type, bank_account_number)"
        " VALUES (:id, 'シケン', '試験銀行', '本店', '普通', '1234567')"
    )
    wise_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_wise (payment_method_id, account_holder, wise_currency, wise_email)"
        " VALUES (:id, 'Test', 'USD', 'pay@example.com')"
    )

    async def add(region: str, kind: str, name: str) -> int:
        return (await conn.execute(text(new_method), {"r": region, "t": kind, "n": name})).scalar_one()

    v1 = await add("domestic", "bank", "銀行1")
    await conn.execute(text(bank_sql), {"id": v1})  # 今の版に詳細は書き足せる
    w1 = await add("overseas", "wise", "Wise1")
    await conn.execute(text(wise_sql), {"id": w1})

    # 詳細は書き換えも消しもできない
    await _expect_error(conn, f"UPDATE {_SCHEMA}.tenant_invoice_payment_bank SET bank_branch = '支店' WHERE payment_method_id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"DELETE FROM {_SCHEMA}.tenant_invoice_payment_bank WHERE payment_method_id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"UPDATE {_SCHEMA}.tenant_invoice_payment_wise SET wise_email = 'x@example.com' WHERE payment_method_id = :id", {"id": w1}, "P0001")
    await _expect_error(conn, f"DELETE FROM {_SCHEMA}.tenant_invoice_payment_wise WHERE payment_method_id = :id", {"id": w1}, "P0001")
    # 振込先の行は消せない・版の中身は書き換えられない
    await _expect_error(conn, f"DELETE FROM {methods} WHERE id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"UPDATE {methods} SET display_name = '別名' WHERE id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"UPDATE {methods} SET region = 'overseas' WHERE id = :id", {"id": v1}, "P0001")
    for column, value in (("id", "999999"), ("tenant_id", "1"), ("method_type", "'wise'"), ("created_at", "now() - interval '1 day'")):
        await _expect_error(conn, f"UPDATE {methods} SET {column} = {value} WHERE id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = id WHERE id = :id", {"id": v1}, "P0001")  # 自分は指せない
    # 並び順・使う/使わない・更新者・更新時刻は版を変えずに直せる
    await conn.execute(
        text(f"UPDATE {methods} SET sort_order = 5, is_active = FALSE, updated_by_user_id = 1, updated_at = now() WHERE id = :id"),
        {"id": v1},
    )
    flags = await conn.execute(text(f"SELECT sort_order, is_active FROM {methods} WHERE id = :id"), {"id": v1})
    assert tuple(flags.one()) == (5, False)
    # 新しい振込先は今の版として始まる
    await _expect_error(
        conn,
        f"INSERT INTO {methods} (region, method_type, display_name, deleted_at) VALUES ('domestic', 'bank', 'x', now())",
        {},
        "P0001",
    )

    # 直す: 新しい版を足して、前の版から次の版を指す
    v2 = await add("domestic", "bank", "銀行1（直し）")
    # 次の版を指すのと消すのを1回で同時にはできない
    await _expect_error(
        conn, f"UPDATE {methods} SET superseded_by_id = :n, deleted_at = now() WHERE id = :o", {"n": v2, "o": v1}, "P0001"
    )
    await conn.execute(text(f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o"), {"n": v2, "o": v1})
    await _expect_error(conn, bank_sql, {"id": v1}, "P0001")  # 前の版には詳細を足せない
    await conn.execute(text(bank_sql), {"id": v2})
    v3 = await add("domestic", "bank", "銀行1（再直し）")
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": v3, "o": v1}, "P0001")  # 次の版は1回だけ
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": v1, "o": v2}, "P0001")  # 古い版は指せない
    w2 = await add("overseas", "wise", "Wise2")  # v2 より新しい・今の版・区分と種類が違う
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": w2, "o": v2}, "P0001")  # 区分と種類が違う
    a = await add("domestic", "bank", "A")
    b = await add("domestic", "bank", "B")
    c = await add("domestic", "bank", "C")
    d = await add("domestic", "bank", "D")  # b より新しい・後で消す
    await conn.execute(text(f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o"), {"n": c, "o": a})
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": c, "o": b}, "23505")  # 次の版を指せるのは1つだけ
    await _expect_error(conn, f"UPDATE {methods} SET deleted_at = now() WHERE id = :id", {"id": a}, "P0001")  # 前の版は消せない

    # 消す: 今の版に消した時刻を付ける（行は残る）
    await conn.execute(text(f"UPDATE {methods} SET deleted_at = now() WHERE id = :id"), {"id": v2})
    await _expect_error(conn, f"UPDATE {methods} SET deleted_at = now() - interval '1 day' WHERE id = :id", {"id": v2}, "P0001")
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": v3, "o": v2}, "P0001")
    await _expect_error(conn, bank_sql, {"id": v2}, "P0001")  # 消した版には詳細を足せない
    await conn.execute(text(f"UPDATE {methods} SET deleted_at = now() WHERE id = :id"), {"id": d})
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": d, "o": b}, "P0001")  # 消した版は次の版にならない

    kept = await conn.execute(text(f"SELECT count(*) FROM {methods} WHERE id = ANY(:ids)"), {"ids": [v1, v2]})
    assert kept.scalar_one() == 2  # 前の版も消した版も残る
    details = await conn.execute(
        text(f"SELECT count(*) FROM {_SCHEMA}.tenant_invoice_payment_bank WHERE payment_method_id = ANY(:ids)"), {"ids": [v1, v2]}
    )
    assert details.scalar_one() == 2

    # 見張りは呼び出し側の検索先（search_path）に頼らない
    await conn.execute(text("SET LOCAL search_path TO public"))
    v4 = await add("domestic", "bank", "銀行4")
    await conn.execute(text(bank_sql), {"id": v4})  # 今の版には足せる（表が見つからない 42P01 にならない）
    await _expect_error(conn, bank_sql, {"id": v1}, "P0001")  # 前の版には足せない

    # 表を空にできない（振込先の一覧は詳細から参照されるので CASCADE 付きで試す）
    await _expect_error(conn, f"TRUNCATE {methods} CASCADE", {}, "P0001")
    await _expect_error(conn, f"TRUNCATE {_SCHEMA}.tenant_invoice_payment_bank", {}, "P0001")
    await _expect_error(conn, f"TRUNCATE {_SCHEMA}.tenant_invoice_payment_wise", {}, "P0001")


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_new_tenant_shape_equals_migration_and_versioning_holds():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            try:
                schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
                assert schema_name == _SCHEMA
                async with admin_engine.connect() as conn:
                    before = await _shape(conn)  # 新しい会社の作り方（tenant.py）で作った形
                assert len(before["triggers"]) == 6
                assert len(before["functions"]) == 3
                # 便Vで足したものを外してから、全テナントを回す正本をこの試験のテナントだけに絞って 2 回流す
                async with admin_engine.begin() as conn:
                    for trigger, table in _TRIGGERS:
                        await conn.execute(text(f"DROP TRIGGER {trigger} ON {_SCHEMA}.{table}"))
                    for name in _FUNCTIONS:
                        await conn.execute(text(f"DROP FUNCTION {_SCHEMA}.{name}()"))
                    await conn.execute(text(f"DROP INDEX {_SCHEMA}.uq_tenant_invoice_payment_methods_superseded_by"))
                    for constraint in (
                        "fk_tenant_invoice_payment_methods_superseded_by",
                        "chk_tenant_invoice_payment_methods_superseded_not_self",
                    ):
                        await conn.execute(
                            text(f"ALTER TABLE {_SCHEMA}.tenant_invoice_payment_methods DROP CONSTRAINT {constraint}")
                        )
                    for column in ("deleted_at", "superseded_by_id"):
                        await conn.execute(text(f"ALTER TABLE {_SCHEMA}.tenant_invoice_payment_methods DROP COLUMN {column}"))
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
