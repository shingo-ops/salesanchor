"""roles.system_key 列（owner / admin の安定識別子）の構造変更の試験。

- 単体（SQLite 不要）: 新テナント用 DDL に列と部分一意索引が含まれ、移行ファイルが登録されている。
- PG（CI で実行）: 新テナントを作ると列と索引があり、移行ファイルを 2 回流しても変わらない。
  ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_rls_bootstrap_ordering.py と同じ形）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.services import tenant as tenant_service
from tests.rls_bootstrap import bootstrap_tenant_schema, tenant_schema_lock

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261005_150000_add_roles_system_key.sql"
_TENANT_ID = 997
_SCHEMA = f"tenant_{_TENANT_ID:03d}"


def test_tenant_ddl_has_system_key_column_and_partial_unique_index():
    """実際の DDL（_TENANT_TABLES_SQL）を読む。DDL の文面は複製せず、roles の定義ブロックを区切りで取り出す。"""
    sql = tenant_service._TENANT_TABLES_SQL
    marker = "{schema}.roles ("
    assert sql.count(marker) == 2  # roles の定義と、部分一意索引の ON {schema}.roles (system_key)
    definition = sql.split(marker)[1]  # 最初の出現 = roles の列定義
    roles_block = definition[: definition.index(");")]
    assert "system_key TEXT" in roles_block
    index_part = sql.split(marker)[2]  # 2 番目の出現 = 部分一意索引
    assert index_part.startswith("system_key) WHERE system_key IS NOT NULL;")
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_system_key ON " + marker.rstrip("(") in sql


def test_migration_file_exists_and_is_registered():
    migration = _REPO_ROOT / "migrations" / _MIGRATION
    assert migration.is_file()
    body = migration.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS system_key TEXT" in body
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_system_key" in body
    runner = (_REPO_ROOT / "scripts" / "run_all_migrations.sh").read_text(encoding="utf-8")
    lines = [line for line in runner.splitlines() if line.startswith("run_sql ")]
    assert lines.count(f"run_sql migrations/{_MIGRATION}") == 1  # 登録されている（末尾である必要はない）


def test_migration_writes_no_values():
    """ADR-155: 構造変更のみ（INSERT / UPDATE / DELETE を含まない）。"""
    body = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    code = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("--")
    ).upper()
    for word in ("INSERT ", "UPDATE ", "DELETE "):
        assert word not in code


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_new_tenant_has_system_key_and_migration_is_idempotent():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
            assert schema_name == _SCHEMA
            migration_sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
            async with admin_engine.begin() as conn:
                await conn.exec_driver_sql(migration_sql)  # 1 回目
                await conn.exec_driver_sql(migration_sql)  # 2 回目（冪等）
            async with admin_engine.connect() as conn:
                column = await conn.execute(
                    text(
                        "SELECT data_type, is_nullable FROM information_schema.columns "
                        "WHERE table_schema = :s AND table_name = 'roles' AND column_name = 'system_key'"
                    ),
                    {"s": _SCHEMA},
                )
                assert column.one() == ("text", "YES")
                index = await conn.execute(
                    text(
                        "SELECT indexdef FROM pg_indexes "
                        "WHERE schemaname = :s AND indexname = 'uq_roles_system_key'"
                    ),
                    {"s": _SCHEMA},
                )
                definition = index.scalar_one()
                assert "UNIQUE" in definition and "WHERE (system_key IS NOT NULL)" in definition
    finally:
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
        await admin_engine.dispose()
