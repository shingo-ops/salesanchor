"""public.google_webhook_subscriptions に RLS（型C）（ADR-1067 段階④ 便④-4）。

使い捨て DB を試験ごとに作り（共有の検証用 DB に表を足さない）、本物の migration を本番と同じ順で当てて、
アプリ接続役（NOBYPASSRLS）で確かめる。読む＝全行、書く＝自社の会社文脈か運営文脈だけ。
会社番号は 968（自社）/ 969（他社）。
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

_TENANT_A = 968
_TENANT_B = 969
# 表を作る・列を足す移行（本番と同じ順）
_BASE_MIGRATIONS = [
    "076_add_google_calendar_config.sql",
    "077_calendar_sync_mode_and_webhook_subscriptions.sql",
    "20261103_200000_add_google_calendar_import_sync.sql",
]
_MIGRATION = "20261107_150000_add_google_webhook_subscriptions_rls.sql"
_GRANT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
"""
_TABLE = "google_webhook_subscriptions"

# 書込の入口（backend/app/services/google_webhook.py）と同じ文
_UPSERT = """
INSERT INTO google_webhook_subscriptions
    (tenant_id, channel_id, resource_id, calendar_id, expiration, channel_token_hash)
VALUES (968, 'ch968x', 'r968', 'primary', now() + interval '7 days', 'h968')
ON CONFLICT (tenant_id) DO UPDATE SET
    channel_id = EXCLUDED.channel_id,
    resource_id = EXCLUDED.resource_id,
    expiration = EXCLUDED.expiration,
    channel_token_hash = EXCLUDED.channel_token_hash,
    created_at = NOW()
"""


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り (admin_engine, app_engine) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "gws_rls_" + uuid.uuid4().hex[:12]
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
                    "VALUES (968, 'tenant_968', 'T968', 'T968', TRUE), "
                    "(969, 'tenant_969', 'T969', 'T969', TRUE)"
                )
            )
        # 表を本物の migration で作る（表の定義を試験に書き写さない）
        for mig in _BASE_MIGRATIONS:
            await _apply_migration(admin_engine, mig)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
            for tid in (_TENANT_A, _TENANT_B):
                await conn.execute(
                    text(
                        "INSERT INTO public.google_webhook_subscriptions "
                        "(tenant_id, channel_id, expiration) "
                        "VALUES (:t, :c, now() + interval '3 days')"
                    ),
                    {"t": tid, "c": f"ch{tid}"},
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


async def _count_by_tenant(conn) -> dict[int, int]:
    from sqlalchemy import text

    rows = (
        await conn.execute(
            text(f"SELECT tenant_id, count(*) FROM public.{_TABLE} GROUP BY tenant_id")
        )
    ).all()
    return {r[0]: r[1] for r in rows}


# ① 読取は全行: 文脈なし・他社の文脈・空文字の文脈（22P02 にならない）でも 2 行とも見える
async def test_select_sees_all_rows_in_any_context():
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        expected = {_TENANT_A: 1, _TENANT_B: 1}
        # 文脈なし（新しい接続）
        conn, trans = await _ctx_conn(app_engine, None)
        try:
            assert await _count_by_tenant(conn) == expected
            # 受け口（google_webhook.py:212）と同じ文
            rows = (
                await conn.execute(
                    text(
                        "SELECT tenant_id, channel_token_hash FROM google_webhook_subscriptions "
                        "WHERE channel_id = 'ch969'"
                    )
                )
            ).all()
            assert len(rows) == 1
        finally:
            await trans.rollback()
            await conn.close()
        # 969 の文脈でも 968 の行が見える
        conn, trans = await _ctx_conn(app_engine, _TENANT_B)
        try:
            assert await _count_by_tenant(conn) == expected
        finally:
            await trans.rollback()
            await conn.close()
        # 同じ接続で SET app.tenant_id = '' の後もエラーにならず 2 行
        conn = await app_engine.connect()
        try:
            await conn.execute(text("SET app.tenant_id = ''"))
            assert await _count_by_tenant(conn) == expected
            await conn.execute(text("RESET app.tenant_id"))
            await conn.rollback()
        finally:
            await conn.close()


# ② 他社の tenant_id で INSERT すると 42501
async def test_insert_other_tenant_rejected():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(
                    text(
                        "INSERT INTO google_webhook_subscriptions (tenant_id, channel_id, expiration) "
                        "VALUES (969, 'x969', now() + interval '3 days')"
                    )
                )
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ③ 他社の行への UPDATE・DELETE は 0 行（他社の行は元のまま 1 行）
async def test_update_delete_other_tenant_rows_affect_nothing():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            r = await conn.execute(
                text("UPDATE public.google_webhook_subscriptions SET sync_token = 'hacked' WHERE tenant_id = :t"),
                {"t": _TENANT_B},
            )
            assert r.rowcount == 0
            r = await conn.execute(
                text("DELETE FROM public.google_webhook_subscriptions WHERE tenant_id = :t"),
                {"t": _TENANT_B},
            )
            assert r.rowcount == 0
        finally:
            await trans.rollback()
            await conn.close()
        rows = await _admin_exec(
            admin_engine,
            "SELECT count(*) FROM public.google_webhook_subscriptions WHERE tenant_id = :t",
            {"t": _TENANT_B},
        )
        assert rows == [(1,)]
        vals = await _admin_exec(
            admin_engine,
            "SELECT sync_token FROM public.google_webhook_subscriptions WHERE tenant_id = :t",
            {"t": _TENANT_B},
        )
        assert vals == [(None,)]


# ④ 運営の文脈: 他社の行の UPDATE が 1 行
async def test_operator_context_can_update_other_tenant_row():
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, None, operator=True)
        try:
            r = await conn.execute(
                text("UPDATE public.google_webhook_subscriptions SET sync_token = 'op' WHERE tenant_id = :t"),
                {"t": _TENANT_B},
            )
            assert r.rowcount == 1
        finally:
            await trans.rollback()
            await conn.close()


# ⑤ 同じ移行をもう一度当てても通り、ポリシーは 4 本のまま
async def test_migration_idempotent_four_policies():
    async with _fresh() as (admin_engine, _app):
        await _apply_migration(admin_engine, _MIGRATION)
        flags = await _admin_exec(
            admin_engine,
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
            f"WHERE oid = to_regclass('public.{_TABLE}')",
        )
        assert tuple(flags[0]) == (True, True)
        n = (
            await _admin_exec(
                admin_engine,
                "SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = :tn",
                {"tn": _TABLE},
            )
        )[0][0]
        assert n == 4


# ⑥ 自社の行の tenant_id を他社へ付け替える UPDATE は 42501
async def test_update_tenant_id_to_other_rejected():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(
                    text("UPDATE public.google_webhook_subscriptions SET tenant_id = :b WHERE tenant_id = :a"),
                    {"a": _TENANT_A, "b": _TENANT_B},
                )
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ⑦ 書込の入口と同じ文脈の張り方（SET app.tenant_id / SET app.is_operator）で、自社の行の書込が通る
async def test_write_entry_context_ok():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        conn = await app_engine.connect()
        try:
            await conn.execute(text(f"SET app.tenant_id = '{_TENANT_A}'"))
            await conn.execute(text("SET app.is_operator = ''"))

            # register_webhook（INSERT ... ON CONFLICT DO UPDATE）
            await conn.execute(text(_UPSERT))
            await conn.commit()
            rows = await _admin_exec(
                admin_engine,
                "SELECT channel_id FROM public.google_webhook_subscriptions WHERE tenant_id = :t",
                {"t": _TENANT_A},
            )
            assert rows == [("ch968x",)]

            # sync_tenant_from_google（UPDATE sync_token）
            r = await conn.execute(
                text("UPDATE google_webhook_subscriptions SET sync_token = 's968' WHERE tenant_id = 968")
            )
            assert r.rowcount == 1
            await conn.commit()
            rows = await _admin_exec(
                admin_engine,
                "SELECT sync_token FROM public.google_webhook_subscriptions WHERE tenant_id = :t",
                {"t": _TENANT_A},
            )
            assert rows == [("s968",)]

            # stop_webhook（DELETE）
            r = await conn.execute(
                text("DELETE FROM google_webhook_subscriptions WHERE tenant_id = 968")
            )
            assert r.rowcount == 1
            await conn.commit()
            rows = await _admin_exec(
                admin_engine,
                "SELECT tenant_id, count(*) FROM public.google_webhook_subscriptions GROUP BY tenant_id",
            )
            assert [tuple(x) for x in rows] == [(_TENANT_B, 1)]
        finally:
            await conn.execute(text("SET app.tenant_id = ''"))
            await conn.commit()
            await conn.close()
