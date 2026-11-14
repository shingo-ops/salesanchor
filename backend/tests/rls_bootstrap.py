from __future__ import annotations

import re
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from sqlalchemy import text

from app.services.tenant import create_tenant_schema
from tests.seed_data import (
    aggregation_rules_seed_sql,
    country_seed_sql,
    customer_statuses_seed_sql,
    type_master_seed_sql,
)

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
    "20260623_060000_add_products_tcg_type_fk.sql",
    "20260920_020000_supplier_line_name_unique.sql",
    "20260921_060000_create_product_kinds.sql",
    "20260921_070000_rename_tcg_type_master_to_type_master.sql",
    "20261015_130000_add_permissions_rls.sql",
]
# public.tenants を参照するため、tenants を用意した後に流す
_PG_AFTER_TENANTS_MIGRATIONS = (
    "20261106_190000_create_public_channel_masters.sql",
    "20261112_120000_create_public_customer_statuses.sql",
    # ADR-1061 便2-2c1: 発行元の会社情報が public.countries と public.prefectures を外部キーで指す。
    # prefectures を作る 20261112_150000 は public.viewer_accounts（20261016_150000）を指すので、この順で流す
    "20260621_010000_create_countries_master.sql",
    "20261016_150000_add_viewer_accounts.sql",
    "20261112_150000_create_viewer_contract_public_tables.sql",
)
_TENANT_BOOTSTRAP_MIGRATIONS = [
    "20260611_100000_create_channel_masters.sql",
    "20260614_100000_create_sales_form_tables.sql",
]
_PUBLIC_BOOTSTRAP_LOCK_NAMESPACE = 20260623
_PUBLIC_BOOTSTRAP_LOCK_KEY = 1
_TENANT_SCHEMA_LOCK_NAMESPACE = 20260623


@asynccontextmanager
async def public_bootstrap_lock(admin_engine):
    """shared public bootstrap を xdist 下で直列化する。"""
    async with admin_engine.connect() as conn:
        await conn.execute(
            text("SELECT pg_advisory_lock(:namespace, :lock_key)"),
            {
                "namespace": _PUBLIC_BOOTSTRAP_LOCK_NAMESPACE,
                "lock_key": _PUBLIC_BOOTSTRAP_LOCK_KEY,
            },
        )
        try:
            yield
        finally:
            with suppress(Exception):
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:namespace, :lock_key)"),
                    {
                        "namespace": _PUBLIC_BOOTSTRAP_LOCK_NAMESPACE,
                        "lock_key": _PUBLIC_BOOTSTRAP_LOCK_KEY,
                    },
                )


# ADR-1028 便3: 商品 API が読む荷姿の表・その元の「数える単位」の表・products の細分類列（本番 migration 4 本）
PACKAGING_MIGRATIONS = (
    "20260920_130000_create_product_classification.sql",  # products.product_format_id を足す（詳細 API が読む）
    "20260921_140000_product_classification_masters.sql",
    "20260922_060000_product_unit_condition_infra.sql",  # quantity_units.value の NOT NULL を外す（本番と同じ）
    "20261018_100000_create_product_packagings.sql",
)


async def _packagings_ready(admin_engine) -> bool:
    """荷姿の表・単位 PACK/BOX/CASE/CARD の 4 件・products.product_format_id が揃っているか（lock は取らない）。"""
    async with admin_engine.connect() as conn:
        if not await conn.scalar(text("SELECT to_regclass('public.product_packagings') IS NOT NULL")):
            return False
        has_format_id = await conn.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'product_format_id')"
            )
        )
        if not has_format_id:
            return False
        units = await conn.scalar(
            text("SELECT count(*) FROM public.quantity_units WHERE code IN ('PACK','BOX','CASE','CARD')")
        )
        return units == 4


async def ensure_product_packagings(admin_engine) -> None:
    """荷姿の表と products.product_format_id を、試験の DB に一度だけ・確定（commit）させて作る。

    各試験の巻き戻す transaction の中で DDL を流すと、終わるまで products などの表ロックを持ち続け、
    ほかの worker と取る順が逆になって deadlock する。そのため transaction の外の別接続で流して確定させる。

    流れ:
      1. lock を取らずに確かめる。揃っていれば何もしない。
      2. public.products が無ければ、本番形の products を bootstrap_public_products で作る
         （試験用の少列版 products を共有 DB に確定させない。062 の jan_code の index が壊れるため）。
      3. public_bootstrap_lock の中でもう一度確かめ、揃っていなければ products を先に押さえてから migration を流す。
         先頭は 20260920_130000（products.product_format_id）。本番形 products には無く、試験用の少列版にだけ有るため足す。
         lock_timeout を付けて、待ち続けず失敗にする。
    bootstrap_public_products は自分で public_bootstrap_lock を取るので、この関数は lock の外から呼ぶこと。
    """
    if await _packagings_ready(admin_engine):
        return
    async with admin_engine.connect() as conn:
        products_exists = await conn.scalar(text("SELECT to_regclass('public.products') IS NOT NULL"))
    if not products_exists:
        await bootstrap_public_products(admin_engine)
    async with public_bootstrap_lock(admin_engine):
        if await _packagings_ready(admin_engine):
            return
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await conn.execute(text("SET LOCAL lock_timeout = '60s'"))
            # ロックの順を test_tcg_distribution_pg.py（products → product_kinds）に揃える
            await conn.execute(text("LOCK TABLE public.products IN ACCESS EXCLUSIVE MODE"))
            for name in PACKAGING_MIGRATIONS:
                # この transaction の中で流すので BEGIN/COMMIT は除く
                sql = (_MIGRATIONS_DIR / name).read_text("utf-8").replace("BEGIN;", "").replace("COMMIT;", "")
                await raw.driver_connection.execute(sql)
            await conn.execute(
                text(
                    "INSERT INTO public.quantity_units (code, name, display_order) VALUES "
                    "('PACK','パック',10),('BOX','ボックス',20),('CASE','ケース',30),('CARD','カード',40) ON CONFLICT (code) DO NOTHING"
                )
            )


def provision_packagings_sync(cursor) -> None:
    """ADR-1028 便4: 同期の接続（psycopg2）で、荷姿の表と 4 単位を作る。試験ごとに新しい DB なので lock は要らない。"""
    for name in PACKAGING_MIGRATIONS:
        sql = (_MIGRATIONS_DIR / name).read_text("utf-8").replace("BEGIN;", "").replace("COMMIT;", "")
        cursor.execute(sql)
    cursor.execute(
        "INSERT INTO public.quantity_units (code, name, display_order) VALUES "
        "('PACK','パック',10),('BOX','ボックス',20),('CASE','ケース',30),('CARD','カード',40) "
        "ON CONFLICT (code) DO NOTHING"
    )


async def _apply_migration(admin_engine, filename: str) -> None:
    async with admin_engine.begin() as conn:
        await _apply_migration_on_conn(conn, filename)


# 全テナントを回す正本 migration のうち、試験が1つのテナントに絞って流すもの（lead_merge・calendar・roles の試験）。
# 値は「テナントを選ぶ条件」が SQL に現れる回数（ずれたら検知して止める）。
_TENANT_LOOP_SELECTOR_RE = re.compile(r"nspname\s*(?:LIKE\s+'tenant_%'|~\s+'\^tenant_(?:\\d|\[0-9\])\+\$')")
_TENANT_LOOP_MIGRATIONS = {
    "090_add_lead_contact_links.sql": 1,
    "091_add_leads_discord_messaging_columns.sql": 1,
    "095_add_lead_social_links.sql": 1,
    "099_add_discord_guild_config.sql": 1,
    "20260602_120000_add_discord_ticket_config.sql": 1,
    "20260604_090000_create_conversation_logs.sql": 2,
    "20260715_100000_add_conversation_logs_lead_fk.sql": 1,
    "20260902_100000_create_lead_attachments.sql": 1,
    "20260604_180000_analytics_agent_a_tables.sql": 1,
    "20260604_220000_create_translation_glossary.sql": 2,
    "078_create_calendar_events_tenant.sql": 2,
    "20260621_020000_add_schedule_calendar_category_and_owner_settings.sql": 1,
    "20261103_200000_add_google_calendar_import_sync.sql": 1,
    "20261104_161223_add_calendar_events_meet_url.sql": 1,
    "20261112_170000_add_calendar_events_recurrence.sql": 1,
    "20261005_150000_add_roles_system_key.sql": 1,
    "20261106_150000_add_discord_role_link_tables.sql": 1,
    "20261112_160000_create_tenant_issuer_and_payment_tables.sql": 1,
    "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql": 1,
}


def _scope_tenant_migration(sql: str, filename: str, schema_name: str) -> str:
    """テスト用の正本SQLを、要求された一つの数値テナントに限定する。"""
    if filename in _TENANT_LOOP_MIGRATIONS:
        if not re.fullmatch(r"tenant_[0-9]+", schema_name):
            raise ValueError("Invalid test tenant schema")
        if len(_TENANT_LOOP_SELECTOR_RE.findall(sql)) != _TENANT_LOOP_MIGRATIONS[filename]:
            raise ValueError("Canonical tenant selector changed; review required")
        return _TENANT_LOOP_SELECTOR_RE.sub(lambda m: f"{m.group(0)} AND nspname = '{schema_name}'", sql)
    selectors = {
        "20260611_100000_create_channel_masters.sql": "\n        WHERE nspname ~ '^tenant_\\d+$'\n",
        "20260614_100000_create_sales_form_tables.sql": "\n    WHERE nspname LIKE 'tenant_%'\n",
    }
    if not re.fullmatch(r"tenant_[0-9]+", schema_name):
        raise ValueError("Invalid test tenant schema")
    if filename not in selectors:
        raise ValueError("Unknown tenant bootstrap migration")
    selector = selectors[filename]
    if sql.count(selector) != 1:
        raise ValueError("Canonical tenant selector changed; review required")
    scoped = selector.rstrip("\n") + f" AND nspname = '{schema_name}'\n"
    return sql.replace(selector, scoped, 1)


async def _apply_migration_on_conn(conn, filename: str, *, schema_name: str | None = None) -> None:
    sql = (_MIGRATIONS_DIR / filename).read_text("utf-8")
    if schema_name is not None:
        sql = _scope_tenant_migration(sql, filename, schema_name)
    elif filename in _TENANT_BOOTSTRAP_MIGRATIONS:
        raise ValueError("Tenant bootstrap migration requires a target schema")
    # exec_driver_sql はPrepared Statementプロトコルを使うため
    # マルチ命令SQLを含む migration ファイルで失敗する。
    # asyncpgのraw接続でSimple Query プロトコルを使う。
    raw = await conn.get_raw_connection()
    await raw.driver_connection.execute(sql)


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
                id, tenant_id, username, email, full_name,
                role, is_active, is_super_admin, locale, theme
            )
            VALUES (999, 999, 'testuser', 'test@example.com', 'Test User',
                    'admin', TRUE, TRUE, 'ja', 'light')
            ON CONFLICT (id) DO NOTHING
        """)
    )


async def seed_type_master(conn) -> None:
    """public.type_master に 12 種別を入れる（冪等）。20260921_070000（rename）の後で呼ぶ。"""
    await conn.exec_driver_sql(type_master_seed_sql())


async def bootstrap_public_countries(admin_engine) -> None:
    """public.countries: 構造は migration（冪等）、データは試験側の seed（ADR-1007 段2）。"""
    async with public_bootstrap_lock(admin_engine):
        await _apply_migration(admin_engine, "20260621_010000_create_countries_master.sql")
        async with admin_engine.begin() as conn:
            await conn.exec_driver_sql(country_seed_sql())


async def bootstrap_inventory_aggregation_rules(admin_engine) -> None:
    """public.inventory_aggregation_rules: 構造は migration（冪等）、4 行はアプリの既定から入れる。"""
    async with public_bootstrap_lock(admin_engine):
        await _apply_migration(admin_engine, "20260620_010000_create_inventory_aggregation_rules.sql")
        async with admin_engine.begin() as conn:
            await conn.exec_driver_sql(aggregation_rules_seed_sql())


async def _bootstrap_public_shared(conn) -> None:
    """shared public bootstrap を 1 接続内で適用する。"""
    raw = await conn.get_raw_connection()
    for filename in _PG_BOOTSTRAP_MIGRATIONS:
        sql = (_MIGRATIONS_DIR / filename).read_text("utf-8")
        await raw.driver_connection.execute(sql)
    # type_master の行は migration ではなく試験側で入れる（ADR-1007 段2）。rename の後で入れる
    await seed_type_master(conn)

    # ADR-1030: products.tcg_type は取り除いた。ADD を消した migration を流しても列が出来ないことを確かめる
    col_exists = await conn.scalar(
        text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_type'
        """)
    )
    assert col_exists is None, "products.tcg_type が復活しています（ADR-1030）"


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
    async with public_bootstrap_lock(admin_engine):
        for filename in _PG_BOOTSTRAP_MIGRATIONS:
            await _apply_migration(admin_engine, filename)
        async with admin_engine.begin() as conn:
            await seed_type_master(conn)

        async with admin_engine.connect() as conn:
            # ADR-1030: products.tcg_type は取り除いた。列が復活していないことを確かめる
            col_exists = await conn.scalar(
                text("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_type'
                """)
            )
        assert col_exists is None, "products.tcg_type が復活しています（ADR-1030）"


async def bootstrap_tenant_schema(admin_engine, tenant_id: int) -> str:
    """本番 migration 順で tenant schema を冪等に作成する。"""
    async with admin_engine.begin() as conn:
        await conn.execute(
            text("SELECT pg_advisory_lock(:namespace, 0)"),
            {"namespace": _PUBLIC_BOOTSTRAP_LOCK_NAMESPACE},
        )
        try:
            async with public_bootstrap_lock(admin_engine):
                await _bootstrap_public_shared(conn)
                await _ensure_public_users(conn)
                raw_after_tenants = await conn.get_raw_connection()
                for filename in _PG_AFTER_TENANTS_MIGRATIONS:
                    # この transaction の中で流すので BEGIN/COMMIT は除く
                    sql = (_MIGRATIONS_DIR / filename).read_text("utf-8").replace("BEGIN;", "").replace("COMMIT;", "")
                    await raw_after_tenants.driver_connection.execute(sql)
                # 状態の4行（便2 で tenant.py の status が外部キーで指す・ADR-1076）。書けるのは運営だけ
                await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
                await conn.exec_driver_sql(customer_statuses_seed_sql())
                await conn.execute(text("SELECT set_config('app.is_operator', '', true)"))
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
                    await _apply_migration_on_conn(conn, filename, schema_name=schema_name)
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
