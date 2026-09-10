from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.rls_bootstrap import (
    _MIGRATIONS_DIR,
    _TENANT_BOOTSTRAP_MIGRATIONS,
    _scope_tenant_migration,
    bootstrap_tenant_schema,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_TENANT_ID = 996
_SCHEMA = f"tenant_{_TENANT_ID:03d}"


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
@pytest.mark.parametrize("unrelated_schema", [None, "tenant_9951"])
async def test_rls_bootstrap_schema_and_migration_share_one_transaction(unrelated_schema):
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    unrelated_created = False
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            if unrelated_schema:
                async with admin_engine.begin() as conn:
                    await conn.execute(text(f"CREATE SCHEMA {unrelated_schema}"))
                unrelated_created = True
            schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
            assert schema_name == _SCHEMA

            async with admin_engine.connect() as conn:
                table_rows = await conn.execute(
                    text(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = :schema
                          AND table_name IN (
                              'leads',
                              'lead_sales_form_selections',
                              'tenant_sales_form_options'
                          )
                        ORDER BY table_name
                        """
                    ),
                    {"schema": _SCHEMA},
                )
                assert set(table_rows.scalars().all()) == {
                    "leads",
                    "lead_sales_form_selections",
                    "tenant_sales_form_options",
                }

                fk_count = await conn.scalar(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON kcu.constraint_name = tc.constraint_name
                         AND kcu.constraint_schema = tc.constraint_schema
                        JOIN information_schema.constraint_column_usage ccu
                          ON ccu.constraint_name = tc.constraint_name
                         AND ccu.constraint_schema = tc.constraint_schema
                        WHERE tc.table_schema = :schema
                          AND tc.table_name = 'lead_sales_form_selections'
                          AND tc.constraint_type = 'FOREIGN KEY'
                          AND kcu.column_name = 'lead_id'
                          AND ccu.table_schema = :schema
                          AND ccu.table_name = 'leads'
                          AND ccu.column_name = 'id'
                        """
                    ),
                    {"schema": _SCHEMA},
                )
                assert fk_count == 1
                if unrelated_schema:
                    other_tables = await conn.scalar(
                        text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = :schema"),
                        {"schema": unrelated_schema},
                    )
                    assert other_tables == 0, "Bootstrap modified an unrelated schema"
    finally:
        try:
            if unrelated_created:
                async with admin_engine.begin() as conn:
                    await conn.execute(text(f"DROP SCHEMA {unrelated_schema} CASCADE"))
        finally:
            await admin_engine.dispose()


@pytest.mark.parametrize("filename", _TENANT_BOOTSTRAP_MIGRATIONS)
def test_tenant_migration_scope_preserves_canonical_body(filename):
    sql = (_MIGRATIONS_DIR / filename).read_text("utf-8")
    scoped = _scope_tenant_migration(sql, filename, _SCHEMA)
    addition = f" AND nspname = '{_SCHEMA}'"
    assert scoped.count(addition) == 1
    assert scoped.replace(addition, "", 1) == sql
    for changed in (sql.replace("WHERE nspname", "WHERE other_name"), sql + sql):
        with pytest.raises(ValueError, match="selector changed"):
            _scope_tenant_migration(changed, filename, _SCHEMA)


@pytest.mark.parametrize("schema_name", ["tenant_", "tenant_996'", "public", "tenant_996\n"])
def test_tenant_migration_scope_rejects_invalid_schema(schema_name):
    with pytest.raises(ValueError, match="Invalid test tenant"):
        _scope_tenant_migration("", _TENANT_BOOTSTRAP_MIGRATIONS[0], schema_name)


def test_tenant_migration_scope_rejects_unknown_migration():
    with pytest.raises(ValueError, match="Unknown tenant"):
        _scope_tenant_migration("", "unknown.sql", _SCHEMA)
