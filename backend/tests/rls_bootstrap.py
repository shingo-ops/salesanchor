from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import set_tenant_context
from app.services.tenant import (
    get_rls_enable_sql,
    get_rls_policy_sql,
    get_tenant_tables_sql,
    seed_default_channel_masters,
    seed_system_roles,
)

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


async def _execute_statements_preserving_do_blocks(db: AsyncSession, sql: str) -> None:
    """DO block を壊さずに複数 SQL 文を順番に実行する。"""
    for stmt in _split_sql_preserving_do_blocks(sql):
        stmt = stmt.strip()
        if stmt:
            await db.execute(text(stmt))


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
            await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            await _execute_statements_preserving_do_blocks(
                session,
                get_tenant_tables_sql(schema_name, tenant_id),
            )
            await session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.tenant_sales_form_options (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL,
                    label VARCHAR(100) NOT NULL,
                    value VARCHAR(100) NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (tenant_id, value)
                )
            """))
            await session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.lead_sales_form_selections (
                    id SERIAL PRIMARY KEY,
                    lead_id INTEGER NOT NULL
                        REFERENCES {schema_name}.leads(id) ON DELETE CASCADE,
                    option_id INTEGER NOT NULL
                        REFERENCES {schema_name}.tenant_sales_form_options(id) ON DELETE RESTRICT,
                    other_text TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (lead_id, option_id)
                )
            """))
            await session.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_lead_sales_form_selections_lead_id
                ON {schema_name}.lead_sales_form_selections (lead_id)
            """))
            await session.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_tenant_sales_form_options_tenant_active
                ON {schema_name}.tenant_sales_form_options (tenant_id, is_active)
            """))
            if schema_name == "tenant_004":
                await session.execute(text("""
                    INSERT INTO tenant_004.tenant_sales_form_options
                        (tenant_id, label, value, sort_order)
                    VALUES
                        (4, '実店舗',   'physical_store',  1),
                        (4, 'ECサイト', 'ec_site',          2),
                        (4, 'ライブ配信', 'live_streaming', 3),
                        (4, '卸・代理店', 'wholesale',      4),
                        (4, 'その他',   'other',            5)
                    ON CONFLICT (tenant_id, value) DO NOTHING
                """))
            for statement in (
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS messenger_link VARCHAR(1000)",
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS discord_id VARCHAR(255)",
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS instagram_link VARCHAR(1000)",
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS whatsapp_link VARCHAR(1000)",
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS discord_user_id VARCHAR(50)",
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS discord_dm_channel_id VARCHAR(50)",
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS discord_role_sync_status VARCHAR(20)",
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS discord_role_sync_at TIMESTAMPTZ",
                f"ALTER TABLE {schema_name}.leads ADD COLUMN IF NOT EXISTS discord_guild_channel_id VARCHAR(50)",
                f"CREATE INDEX IF NOT EXISTS idx_leads_discord_user_id ON {schema_name}.leads (tenant_id, discord_user_id) WHERE discord_user_id IS NOT NULL",
                f"CREATE INDEX IF NOT EXISTS idx_leads_discord_guild_channel_id ON {schema_name}.leads (tenant_id, discord_guild_channel_id) WHERE discord_guild_channel_id IS NOT NULL",
            ):
                await session.execute(text(statement))
            for statement in get_rls_enable_sql(schema_name).strip().split(";"):
                statement = statement.strip()
                if statement:
                    await session.execute(text(statement))
            await session.execute(text(get_rls_policy_sql(schema_name)))
            await session.execute(text(f"""
            DO $$
            BEGIN
              GRANT USAGE ON SCHEMA {schema_name} TO salesanchor_app;
              GRANT SELECT, INSERT, UPDATE, DELETE
                ON ALL TABLES IN SCHEMA {schema_name} TO salesanchor_app;
              GRANT USAGE, SELECT
                ON ALL SEQUENCES IN SCHEMA {schema_name} TO salesanchor_app;
              ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA {schema_name}
                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO salesanchor_app;
              ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA {schema_name}
                GRANT USAGE, SELECT ON SEQUENCES TO salesanchor_app;
              RAISE NOTICE 'Granted salesanchor_app on schema: {schema_name}';
            EXCEPTION WHEN others THEN
              RAISE WARNING 'GRANT failed for %: %', '{schema_name}', SQLERRM;
            END $$;
            """))
            await seed_system_roles(session, tenant_id, schema_name)
            await seed_default_channel_masters(session, tenant_id, schema_name)
            try:
                async with session.begin_nested():
                    await session.execute(
                        text(
                            "INSERT INTO public.tenant_settings "
                            "(tenant_id, spreadsheet_phase, "
                            " inventory_agg_filter, agg_price_threshold_jpy, agg_qty_threshold, "
                            " quote_validity_days, default_currency, document_language, "
                            " duty_incoterms, issue_mode) "
                            "VALUES (:tid, 'A', "
                            " 'none', 0, 0, "
                            " 1, 'JPY', 'en', "
                            " 'DAP', 'pdf') "
                            "ON CONFLICT (tenant_id) DO NOTHING"
                        ),
                        {"tid": int(tenant_id)},
                    )
            except Exception:
                pass
    return schema_name


@asynccontextmanager
async def tenant_rls_session(app_session_factory: sessionmaker, tenant_id: int):
    """テスト用に tenant 文脈付きの app session を返す。

    GET 系 RLS テストでは get_current_tenant の override だけでは不十分なので、
    実運用と同じく search_path / app.tenant_id / app.is_operator をセットしてから
    request を実行する。
    """
    async with app_session_factory() as session:
        await set_tenant_context(session, tenant_id)
        yield session
