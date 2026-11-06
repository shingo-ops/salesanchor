"""public.tenant_discord_config・public.tenant_discord_ticket_config に RLS（型C）（ADR-1067 段階④ 便④-3）。

使い捨て DB を試験ごとに作り（共有の検証用 DB に表を足さない）、本物の migration を本番と同じ順で当てて、
アプリ接続役（NOBYPASSRLS）で確かめる。読む＝全行、書く＝自社の会社文脈か運営文脈だけ。
会社番号は 974（自社）/ 975（他社）。
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, urlunsplit

import pytest

from tests.rls_bootstrap import _apply_migration, _ensure_public_users

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not ADMIN_PG_URL or not APP_PG_URL,
        reason=(
            "実 PostgreSQL 環境が必要 "
            "(RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。"
        ),
    ),
    pytest.mark.asyncio,
]

_TENANT_A = 974
_TENANT_B = 975
# 2 表を作る・形を変える移行（本番と同じ順）。20260930_130000 は形を変えないので当てない
_BASE_MIGRATIONS = [
    "099_add_discord_guild_config.sql",
    "20260602_120000_add_discord_ticket_config.sql",
    "20260602_150000_add_discord_scale_channels.sql",
    "20260602_160000_add_discord_role_names.sql",
    "20260602_200000_add_discord_config_connected_by_staff.sql",
    "20260626_120000_add_unique_guild_id_to_tenant_discord_config.sql",
    "20261105_100000_tenant_discord_config_purpose.sql",
    "20261106_100000_tenant_discord_config_purpose_pk.sql",
]
_MIGRATION = "20261107_130000_add_discord_config_rls.sql"
_GRANT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
"""
_TABLES = ["tenant_discord_config", "tenant_discord_ticket_config"]

# 表ごとの「他社 (975) 向けの INSERT 文」（主キーの重複で落ちないよう値を選ぶ）
_INSERT_OTHER_BY_TABLE = {
    "tenant_discord_config": (
        "INSERT INTO public.tenant_discord_config (tenant_id, purpose, guild_id) "
        "VALUES (:t, 'own', 'x975')"
    ),
    "tenant_discord_ticket_config": (
        "INSERT INTO public.tenant_discord_ticket_config "
        "(tenant_id, ticket_category_id, ticket_button_channel_id) "
        "VALUES (:t, 'cx', 'bx')"
    ),
}
# 他社の行を書き換える UPDATE（列だけ変える）
_UPDATE_BY_TABLE = {
    "tenant_discord_config": "UPDATE public.tenant_discord_config SET guild_id = 'hacked' WHERE tenant_id = :t",
    "tenant_discord_ticket_config": (
        "UPDATE public.tenant_discord_ticket_config SET ticket_category_id = 'hacked' WHERE tenant_id = :t"
    ),
}
# 元の値を確かめる列と値（975 の行）
_ORIGINAL_BY_TABLE = {
    "tenant_discord_config": ("guild_id", "g975"),
    "tenant_discord_ticket_config": ("ticket_category_id", "c975"),
}

# 書込の入口の upsert（discord_oauth.py / discord_ticket_config.py と同じ形）
_UPSERT_CONFIG = """
INSERT INTO public.tenant_discord_config (tenant_id, purpose, guild_id, connected_by_staff_id)
VALUES (:tid, :purpose, :guild_id, :staff_id)
ON CONFLICT (tenant_id, purpose)
DO UPDATE SET
    guild_id = EXCLUDED.guild_id,
    connected_by_staff_id = EXCLUDED.connected_by_staff_id,
    updated_at = NOW()
"""
_UPSERT_TICKET = """
INSERT INTO public.tenant_discord_ticket_config
    (tenant_id, ticket_category_id, ticket_button_channel_id,
     staff_role_id, welcome_template,
     small_channel_id, large_channel_id,
     small_role_name, large_role_name, updated_at)
VALUES
    (:tid, :category_id, :button_channel_id,
     :staff_role_id, :welcome_template,
     :small_channel_id, :large_channel_id,
     :small_role_name, :large_role_name, NOW())
ON CONFLICT (tenant_id) DO UPDATE SET
    ticket_category_id       = EXCLUDED.ticket_category_id,
    ticket_button_channel_id = EXCLUDED.ticket_button_channel_id,
    staff_role_id            = EXCLUDED.staff_role_id,
    welcome_template         = EXCLUDED.welcome_template,
    small_channel_id         = EXCLUDED.small_channel_id,
    large_channel_id         = EXCLUDED.large_channel_id,
    small_role_name          = EXCLUDED.small_role_name,
    large_role_name          = EXCLUDED.large_role_name,
    updated_at               = NOW()
"""


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り (admin_engine, app_engine) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "dcf_rls_" + uuid.uuid4().hex[:12]
    async with control.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine = create_async_engine(_with_db(ADMIN_PG_URL, name), echo=False)
    # 接続 1 本で使い回す（SET の戻り忘れ・張り直し漏れを実際に検出するため）
    app_engine = create_async_engine(
        _with_db(APP_PG_URL, name), echo=False, pool_size=1, max_overflow=0
    )
    try:
        async with admin_engine.begin() as conn:
            await _ensure_public_users(conn)
            await conn.execute(
                text(
                    "INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) "
                    "VALUES (974, 'tenant_974', 'T974', 'T974', TRUE), "
                    "(975, 'tenant_975', 'T975', 'T975', TRUE)"
                )
            )
        # 2 表を本物の migration で作る（表の定義を試験に書き写さない）
        for mig in _BASE_MIGRATIONS:
            await _apply_migration(admin_engine, mig)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
            for tid in (_TENANT_A, _TENANT_B):
                await conn.execute(
                    text(
                        "INSERT INTO public.tenant_discord_config (tenant_id, purpose, guild_id) "
                        "VALUES (:t, 'customer', :g)"
                    ),
                    {"t": tid, "g": f"g{tid}"},
                )
                await conn.execute(
                    text(
                        "INSERT INTO public.tenant_discord_ticket_config "
                        "(tenant_id, ticket_category_id, ticket_button_channel_id) "
                        "VALUES (:t, :c, :b)"
                    ),
                    {"t": tid, "c": f"c{tid}", "b": f"b{tid}"},
                )
        await _apply_migration(admin_engine, _MIGRATION)
        yield admin_engine, app_engine
    finally:
        await app_engine.dispose()
        await admin_engine.dispose()
        async with control.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await control.dispose()


async def _admin_exec(admin_engine, sql: str, params: dict | None = None):
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        result = await conn.execute(text(sql), params or {})
        return result.all() if result.returns_rows else []


async def _ctx_conn(app_engine, tenant_id: int | None, operator: bool = False):
    """アプリ接続役で文脈を張った接続と trans を返す（tenant_id=None は会社文脈なし）。"""
    from sqlalchemy import text

    conn = await app_engine.connect()
    trans = await conn.begin()
    if tenant_id is not None:
        await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})
    if operator:
        await conn.execute(text("SELECT set_config('app.tenant_id', '', true)"))
        await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
    return conn, trans


def _sqlstate(exc) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


async def _count_by_tenant(conn, table: str) -> dict[int, int]:
    from sqlalchemy import text

    rows = (
        await conn.execute(text(f"SELECT tenant_id, count(*) FROM public.{table} GROUP BY tenant_id"))
    ).all()
    return {r[0]: r[1] for r in rows}


# ① 読取は全行: 文脈なし・他社の文脈・空文字の文脈（22P02 にならない）でも 2 行とも見える
@pytest.mark.parametrize("table", _TABLES)
async def test_select_sees_all_rows_in_any_context(table):
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        expected = {_TENANT_A: 1, _TENANT_B: 1}
        # 文脈なし（新しい接続）
        conn, trans = await _ctx_conn(app_engine, None)
        try:
            assert await _count_by_tenant(conn, table) == expected
        finally:
            await trans.rollback()
            await conn.close()
        # 975 の文脈でも 974 の行が見える
        conn, trans = await _ctx_conn(app_engine, _TENANT_B)
        try:
            assert await _count_by_tenant(conn, table) == expected
        finally:
            await trans.rollback()
            await conn.close()
        # 同じ接続で SET app.tenant_id = '' の後もエラーにならず 2 行
        conn = await app_engine.connect()
        try:
            await conn.execute(text("SET app.tenant_id = ''"))
            assert await _count_by_tenant(conn, table) == expected
            await conn.execute(text("RESET app.tenant_id"))
            await conn.rollback()
        finally:
            await conn.close()


# ② 他社の tenant_id で INSERT すると 42501
@pytest.mark.parametrize("table", _TABLES)
async def test_insert_other_tenant_rejected(table):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(text(_INSERT_OTHER_BY_TABLE[table]), {"t": _TENANT_B})
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ③ 他社の行への UPDATE・DELETE は 0 行（他社の行は元のまま 1 行）
@pytest.mark.parametrize("table", _TABLES)
async def test_update_delete_other_tenant_rows_affect_nothing(table):
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            r = await conn.execute(text(_UPDATE_BY_TABLE[table]), {"t": _TENANT_B})
            assert r.rowcount == 0
            r = await conn.execute(
                text(f"DELETE FROM public.{table} WHERE tenant_id = :t"), {"t": _TENANT_B}
            )
            assert r.rowcount == 0
        finally:
            await trans.rollback()
            await conn.close()
        rows = await _admin_exec(
            admin_engine,
            f"SELECT count(*) FROM public.{table} WHERE tenant_id = :t",
            {"t": _TENANT_B},
        )
        assert rows == [(1,)]
        col, expected = _ORIGINAL_BY_TABLE[table]
        vals = await _admin_exec(
            admin_engine, f"SELECT {col} FROM public.{table} WHERE tenant_id = :t", {"t": _TENANT_B}
        )
        assert vals == [(expected,)]


# ④ 運営の文脈: 他社の行の UPDATE が 1 行
@pytest.mark.parametrize("table", _TABLES)
async def test_operator_context_can_update_other_tenant_row(table):
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, None, operator=True)
        try:
            r = await conn.execute(text(_UPDATE_BY_TABLE[table]), {"t": _TENANT_B})
            assert r.rowcount == 1
        finally:
            await trans.rollback()
            await conn.close()


# ⑤ 同じ移行をもう一度当てても通り、ポリシーは 2 表とも 4 本のまま
async def test_migration_idempotent_four_policies():
    async with _fresh() as (admin_engine, _app):
        await _apply_migration(admin_engine, _MIGRATION)
        for table in _TABLES:
            flags = await _admin_exec(
                admin_engine,
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                f"WHERE oid = to_regclass('public.{table}')",
            )
            assert tuple(flags[0]) == (True, True)
            n = (
                await _admin_exec(
                    admin_engine,
                    "SELECT count(*) FROM pg_policies "
                    "WHERE schemaname = 'public' AND tablename = :tn",
                    {"tn": table},
                )
            )[0][0]
            assert n == 4


# ⑥ 自社の行の tenant_id を他社へ付け替える UPDATE は 42501
@pytest.mark.parametrize("table", _TABLES)
async def test_update_tenant_id_to_other_rejected(table):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(
                    text(f"UPDATE public.{table} SET tenant_id = :b WHERE tenant_id = :a"),
                    {"a": _TENANT_A, "b": _TENANT_B},
                )
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ⑦ 書込の入口と同じ文脈の張り方（SET app.tenant_id / SET app.is_operator）で、自社の行の upsert が通る
async def test_write_entry_context_upsert_ok():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        conn = await app_engine.connect()
        try:
            await conn.execute(text(f"SET app.tenant_id = '{_TENANT_A}'"))
            await conn.execute(text("SET app.is_operator = ''"))
            await conn.execute(
                text(_UPSERT_CONFIG),
                {"tid": _TENANT_A, "purpose": "customer", "guild_id": "g974x", "staff_id": None},
            )
            await conn.execute(
                text(_UPSERT_TICKET),
                {
                    "tid": _TENANT_A,
                    "category_id": "c974x",
                    "button_channel_id": "b974x",
                    "staff_role_id": None,
                    "welcome_template": "w974",
                    "small_channel_id": None,
                    "large_channel_id": None,
                    "small_role_name": "Member",
                    "large_role_name": "Partner",
                },
            )
            await conn.commit()
        finally:
            await conn.execute(text("SET app.tenant_id = ''"))
            await conn.rollback()
            await conn.close()
        cfg = await _admin_exec(
            admin_engine,
            "SELECT guild_id FROM public.tenant_discord_config "
            "WHERE tenant_id = :t AND purpose = 'customer'",
            {"t": _TENANT_A},
        )
        assert cfg == [("g974x",)]
        tkt = await _admin_exec(
            admin_engine,
            "SELECT ticket_category_id FROM public.tenant_discord_ticket_config WHERE tenant_id = :t",
            {"t": _TENANT_A},
        )
        assert tkt == [("c974x",)]
