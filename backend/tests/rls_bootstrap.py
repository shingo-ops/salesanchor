from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.tenant import create_tenant_schema

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _REPO_ROOT / "migrations"
_PG_BOOTSTRAP_MIGRATIONS = [
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


@asynccontextmanager
async def tenant_schema_lock(admin_engine, tenant_id: int):
    """tenant_id ごとの bootstrap/利用を直列化する。"""
    async with admin_engine.connect() as conn:
        await conn.execute(text("SELECT pg_advisory_lock(:lock_key)"), {"lock_key": int(tenant_id)})
        try:
            yield
        finally:
            await conn.execute(text("SELECT pg_advisory_unlock(:lock_key)"), {"lock_key": int(tenant_id)})


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
    await bootstrap_public_products(admin_engine)
    schema_name = f"tenant_{int(tenant_id):03d}"

    admin_session_factory = sessionmaker(admin_engine, class_=AsyncSession, expire_on_commit=False)
    async with admin_session_factory() as session:
        async with session.begin():
            await session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.users (
                    id INTEGER PRIMARY KEY,
                    role TEXT NOT NULL DEFAULT 'user'
                )
            """))
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS public.permissions (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) NOT NULL UNIQUE,
                    resource VARCHAR(50) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    description VARCHAR(255) NOT NULL,
                    category VARCHAR(50) NOT NULL
                )
            """))
            await session.execute(text("""
                INSERT INTO public.users (id, role) VALUES (999, 'admin')
                ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role
            """))
            for key in ("dashboard.view", "goals.view", "reports.view", "system.manage"):
                resource, action = key.split(".", 1)
                await session.execute(
                    text("""
                        INSERT INTO public.permissions (key, resource, action, description, category)
                        VALUES (:key, :resource, :action, :description, :category)
                        ON CONFLICT (key) DO NOTHING
                    """),
                    {
                        "key": key,
                        "resource": resource,
                        "action": action,
                        "description": key,
                        "category": resource,
                    },
                )
            schema_name = await create_tenant_schema(session, tenant_id, admin_db=session)
    return schema_name
