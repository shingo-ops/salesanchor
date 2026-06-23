from __future__ import annotations

from contextlib import asynccontextmanager, suppress
from pathlib import Path

from sqlalchemy import text

from app.services.tenant import create_tenant_schema

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _REPO_ROOT / "migrations"
_PG_BOOTSTRAP_MIGRATIONS = [
    "002_add_permissions_master.sql",
    "056_add_suppliers_type_and_promote_public.sql",
    "062_create_inventory_movements_and_budget.sql",
    "082_extend_products_box_attributes.sql",
    "085_create_tcg_type_master.sql",
    "086_seed_additional_tcg_types.sql",
    "20260602_000000_add_products_central_columns.sql",
    "20260602_020000_add_products_tcg_type.sql",
    "20260602_030000_add_products_unit.sql",
    "20260602_170000_add_products_master_label_columns.sql",
    "20260603_000000_add_products_product_kind.sql",
    "20260603_040000_add_products_set_type.sql",
    "20260605_000000_add_products_display_order.sql",
    "20260616_000000_fix_tcg_type_dedup.sql",
    "20260623_030000_add_products_tcg_type_fk.sql",
]
_TENANT_BOOTSTRAP_MIGRATIONS = [
    "20260611_100000_create_channel_masters.sql",
    "20260614_100000_create_sales_form_tables.sql",
]
_PUBLIC_BOOTSTRAP_LOCK_NAMESPACE = 20260623
_TENANT_SCHEMA_LOCK_NAMESPACE = 20260623


def _split_sql_preserving_do_blocks(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    in_dollar = False
    dollar_tag = ""
    while i < len(sql):
        if sql[i] == "$":
            j = i + 1
            while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < len(sql) and sql[j] == "$":
                tag = sql[i : j + 1]
                if not in_dollar:
                    in_dollar = True
                    dollar_tag = tag
                    buf.append(tag)
                    i = j + 1
                    continue
                if tag == dollar_tag:
                    in_dollar = False
                    dollar_tag = ""
                    buf.append(tag)
                    i = j + 1
                    continue
        if sql[i] == ";" and not in_dollar:
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(sql[i])
        i += 1
    if buf:
        statements.append("".join(buf))
    return statements


async def _apply_migration(admin_engine, filename: str) -> None:
    sql = (_MIGRATIONS_DIR / filename).read_text("utf-8")
    async with admin_engine.begin() as conn:
        for stmt in _split_sql_preserving_do_blocks(sql):
            stmt = stmt.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)


async def _ensure_public_users(conn) -> None:
    await conn.execute(
        text("""
            CREATE TABLE IF NOT EXISTS public.tenants (
                id INTEGER PRIMARY KEY,
                tenant_code VARCHAR(50) NOT NULL UNIQUE,
                tenant_name VARCHAR(255) NOT NULL DEFAULT '',
                company_name VARCHAR(255) NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                settings JSONB NOT NULL DEFAULT '{}'::jsonb
            )
        """)
    )
    await conn.execute(
        text("""
            INSERT INTO public.tenants (
                id, tenant_code, tenant_name, company_name, is_active
            )
            VALUES (999, 'tenant_999', 'Test Tenant', 'Test Tenant', TRUE)
            ON CONFLICT (id) DO UPDATE SET
                tenant_code = EXCLUDED.tenant_code,
                tenant_name = EXCLUDED.tenant_name,
                company_name = EXCLUDED.company_name,
                is_active = EXCLUDED.is_active
        """)
    )
    await conn.execute(
        text("""
            CREATE TABLE IF NOT EXISTS public.users (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT 999,
                firebase_uid VARCHAR(128) UNIQUE,
                username VARCHAR(255),
                email VARCHAR(255),
                full_name VARCHAR(255),
                role VARCHAR(50) DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_super_admin BOOLEAN NOT NULL DEFAULT FALSE,
                locale VARCHAR(10) NOT NULL DEFAULT 'ja',
                theme VARCHAR(10) NOT NULL DEFAULT 'light'
            )
        """)
    )
    await conn.execute(
        text("""
            INSERT INTO public.users (
                id, tenant_id, firebase_uid, username, email, full_name,
                role, is_active, is_super_admin, locale, theme
            )
            VALUES (999, 999, 'test-user', 'testuser', 'test@example.com', 'Test User',
                    'admin', TRUE, TRUE, 'ja', 'light')
            ON CONFLICT (id) DO NOTHING
        """)
    )


async def _bootstrap_public_shared(conn) -> None:
    """shared public bootstrap を 1 接続内で適用する。"""
    for filename in _PG_BOOTSTRAP_MIGRATIONS:
        sql = (_MIGRATIONS_DIR / filename).read_text("utf-8")
        for stmt in _split_sql_preserving_do_blocks(sql):
            stmt = stmt.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)

    fk_exists = await conn.scalar(
        text("""
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class rel ON rel.oid = c.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = 'public'
              AND rel.relname = 'products'
              AND c.conname = 'fk_products_tcg_type'
        """)
    )
    assert fk_exists == 1, "FK migration が public.products に適用されていません"


@asynccontextmanager
async def tenant_schema_lock(admin_engine, tenant_id: int):
    """同じ tenant schema を使う PG/RLS テストを xdist 下で直列化する。"""
    async with admin_engine.connect() as conn:
        await conn.execute(
            text("SELECT pg_advisory_lock(:namespace, :tenant_id)"),
            {"namespace": _TENANT_SCHEMA_LOCK_NAMESPACE, "tenant_id": int(tenant_id)},
        )
        try:
            yield
        finally:
            with suppress(Exception):
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:namespace, :tenant_id)"),
                    {"namespace": _TENANT_SCHEMA_LOCK_NAMESPACE, "tenant_id": int(tenant_id)},
                )


async def bootstrap_public_products(admin_engine) -> None:
    """public.products とその周辺の前提 migration を冪等に適用する。"""
    for filename in _PG_BOOTSTRAP_MIGRATIONS:
        await _apply_migration(admin_engine, filename)

    async with admin_engine.connect() as conn:
        fk_exists = await conn.scalar(
            text("""
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class rel ON rel.oid = c.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE nsp.nspname = 'public'
                  AND rel.relname = 'products'
                  AND c.conname = 'fk_products_tcg_type'
            """)
    )
    assert fk_exists == 1, "FK migration が public.products に適用されていません"


async def bootstrap_tenant_schema(admin_engine, tenant_id: int) -> str:
    """本番 migration 順で tenant schema を冪等に作成する。"""
    async with admin_engine.begin() as conn:
        await conn.execute(
            text("SELECT pg_advisory_lock(:namespace, 0)"),
            {"namespace": _PUBLIC_BOOTSTRAP_LOCK_NAMESPACE},
        )
        try:
            await _bootstrap_public_shared(conn)
            await _ensure_public_users(conn)
            await conn.execute(
                text("""
                    INSERT INTO public.tenants (
                        id, tenant_code, tenant_name, company_name, is_active
                    )
                    VALUES (
                        :tenant_id,
                        :tenant_code,
                        :tenant_name,
                        :company_name,
                        TRUE
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        tenant_code = EXCLUDED.tenant_code,
                        tenant_name = EXCLUDED.tenant_name,
                        company_name = EXCLUDED.company_name,
                        is_active = EXCLUDED.is_active
                """),
                {
                    "tenant_id": int(tenant_id),
                    "tenant_code": f"tenant_{int(tenant_id):03d}",
                    "tenant_name": f"tenant_{int(tenant_id):03d}",
                    "company_name": f"tenant_{int(tenant_id):03d}",
                },
            )
            schema_name = f"tenant_{int(tenant_id):03d}"
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
            schema_name = await create_tenant_schema(conn, tenant_id, admin_db=conn)
            for filename in _TENANT_BOOTSTRAP_MIGRATIONS:
                await _apply_migration(admin_engine, filename)
        finally:
            with suppress(Exception):
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:namespace, 0)"),
                    {"namespace": _PUBLIC_BOOTSTRAP_LOCK_NAMESPACE},
                )
    return schema_name


@asynccontextmanager
async def tenant_rls_session(session_factory, tenant_id: int):
    """RLS 用に app.tenant_id を設定した session を返す。"""
    async with session_factory() as session:
        async with session.begin():
            schema_name = f"tenant_{int(tenant_id):03d}"
            await session.execute(text(f"SET search_path = {schema_name}, public"))
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(int(tenant_id))},
            )
            await session.execute(text("SELECT set_config('app.is_operator', '', true)"))
            yield session
