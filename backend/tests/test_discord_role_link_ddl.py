"""discord-server-management 第2段 2a-1: roles.discord_role_id と、消した番号を覚える表 2 つの構造の試験。

- 単体（PostgreSQL 不要）: 新テナント用 DDL に列・部分一意索引・表 2 つが含まれ、移行ファイルが登録され、値を入れない。
- PG（CI で実行）: 新テナントを作ると列・索引・表があり、移行ファイルを 2 回流しても変わらない。
  ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_roles_system_key_ddl.py と同じ形）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.services import tenant as tenant_service
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261106_150000_add_discord_role_link_tables.sql"
# 995 は test_roles_system_key_ddl.py が使うため、試験・移行のどこにも無い 994 を使う
_TENANT_ID = 994
_SCHEMA = f"tenant_{_TENANT_ID:03d}"


def _block(sql: str, marker: str) -> str:
    """marker の直後から、最初の ');' までを返す（表の列定義）。"""
    assert sql.count(marker) == 1, marker
    body = sql.split(marker)[1]
    return body[: body.index(");")]


def test_tenant_ddl_has_discord_role_id_and_retired_tables():
    sql = tenant_service._TENANT_TABLES_SQL
    roles_block = sql.split("{schema}.roles (")[1]
    roles_block = roles_block[: roles_block.index(");")]
    assert "discord_role_id TEXT," in roles_block
    assert (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id ON {schema}.roles (discord_role_id)"
        " WHERE discord_role_id IS NOT NULL;"
    ) in sql

    retired_roles = _block(sql, "{schema}.discord_retired_roles (")
    assert "discord_role_id TEXT PRIMARY KEY" in retired_roles
    assert "retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()" in retired_roles

    retired_members = _block(sql, "{schema}.discord_retired_members (")
    assert "discord_user_id TEXT PRIMARY KEY" in retired_members
    assert "kick            BOOLEAN NOT NULL" in retired_members
    assert "retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()" in retired_members


def test_migration_file_exists_and_is_registered():
    migration = _REPO_ROOT / "migrations" / _MIGRATION
    assert migration.is_file()
    body = migration.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS discord_role_id TEXT" in body
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id" in body
    assert "CREATE TABLE IF NOT EXISTS %I.discord_retired_roles" in body
    assert "CREATE TABLE IF NOT EXISTS %I.discord_retired_members" in body
    runner = (_REPO_ROOT / "scripts" / "run_all_migrations.sh").read_text(encoding="utf-8")
    lines = [line for line in runner.splitlines() if line.startswith("run_sql ")]
    assert lines.count(f"run_sql migrations/{_MIGRATION}") == 1


def test_migration_writes_no_values():
    """ADR-155: 構造変更のみ（INSERT / UPDATE / DELETE を含まない）。"""
    body = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    code = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("--")
    ).upper()
    for word in ("INSERT ", "UPDATE ", "DELETE "):
        assert word not in code


async def _shape(conn) -> dict:
    columns = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = :s AND ("
            " (table_name = 'roles' AND column_name = 'discord_role_id')"
            " OR table_name IN ('discord_retired_roles', 'discord_retired_members'))"
            " ORDER BY table_name, column_name"
        ),
        {"s": _SCHEMA},
    )
    index = await conn.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = :s AND indexname = 'uq_roles_discord_role_id'"
        ),
        {"s": _SCHEMA},
    )
    return {"columns": [tuple(row) for row in columns.all()], "index": index.scalar_one()}


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_new_tenant_has_link_tables_and_migration_is_idempotent():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            try:
                schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
                assert schema_name == _SCHEMA
                async with admin_engine.connect() as conn:
                    before = await _shape(conn)  # 新しい会社の作り方（tenant.py）で作った形
                # 全テナントを回す正本を、この試験のテナントだけに絞って流す（他ワーカーのテナントに触れない）
                async with admin_engine.begin() as conn:
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 1 回目
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 2 回目（冪等）
                async with admin_engine.connect() as conn:
                    after = await _shape(conn)
                assert before == after
                assert after["columns"] == [
                    ("discord_retired_members", "discord_user_id", "text", "NO"),
                    ("discord_retired_members", "kick", "boolean", "NO"),
                    ("discord_retired_members", "retired_at", "timestamp with time zone", "NO"),
                    ("discord_retired_roles", "discord_role_id", "text", "NO"),
                    ("discord_retired_roles", "retired_at", "timestamp with time zone", "NO"),
                    ("roles", "discord_role_id", "text", "YES"),
                ]
                assert "UNIQUE" in after["index"]
                assert "WHERE (discord_role_id IS NOT NULL)" in after["index"]
            finally:
                async with public_bootstrap_lock(admin_engine):
                    async with admin_engine.begin() as conn:
                        await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    finally:
        await admin_engine.dispose()


def test_link_migration_is_scoped_to_own_tenant():
    from tests.rls_bootstrap import _scope_tenant_migration

    sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    scoped = _scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql
