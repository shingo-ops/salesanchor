"""public.tenant_paypal_config / public.registration_tokens の書込だけ RLS（ADR-1018 段階③便A）。

使い捨て DB を試験ごとに作り（共有の検証用 DB に表を足さない）、
本物の migration を適用して、アプリ接続役（NOBYPASSRLS）で確かめる。
読取は全行可・書込は自社の文脈だけ。会社番号は 984 / 985。
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
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

_TENANT_A = 984
_TENANT_B = 985
_MIGRATIONS = (
    "20260610_071110_add_paypal_config.sql",
    "20260611_150000_add_paypal_webhook_id.sql",
    "20260604_080000_create_registration_tokens.sql",
    "20261016_100000_add_paypal_regtoken_write_rls.sql",
)
_GRANT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
"""
_TABLES = ("tenant_paypal_config", "registration_tokens")


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り (admin_engine, app_engine) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "s3a_rls_" + uuid.uuid4().hex[:12]
    async with control.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine = create_async_engine(_with_db(ADMIN_PG_URL, name), echo=False)
    # 接続 1 本で使い回す（SET の戻り忘れ・張り直し漏れを実際に検出するため）
    app_engine = create_async_engine(
        _with_db(APP_PG_URL, name), echo=False, pool_size=1, max_overflow=0
    )
    try:
        # 外部キーの参照先 public.tenants / public.users は試験共通の部品で用意する
        async with admin_engine.begin() as conn:
            await _ensure_public_users(conn)
            for tid in (_TENANT_A, _TENANT_B):
                await conn.execute(
                    text(
                        "INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name) "
                        "VALUES (:i, :c, :c, :c)"
                    ),
                    {"i": tid, "c": f"tenant_{tid}"},
                )
        for filename in _MIGRATIONS[:-1]:
            await _apply_migration(admin_engine, filename)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
        await _apply_migration(admin_engine, _MIGRATIONS[-1])
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


async def _seed_paypal(admin_engine, tenant_id: int, webhook_id: str | None = None) -> None:
    await _admin_exec(
        admin_engine,
        "INSERT INTO public.tenant_paypal_config "
        "(tenant_id, client_id_encrypted, client_secret_encrypted, environment, webhook_id) "
        "VALUES (:t, 'c', 's', 'sandbox', :w)",
        {"t": tenant_id, "w": webhook_id},
    )


async def _seed_token(admin_engine, tenant_id: int, token_hash: str | None = None) -> str:
    rows = await _admin_exec(
        admin_engine,
        "INSERT INTO public.registration_tokens "
        "(tenant_id, lead_id, token_hash, type, expires_at, created_by) "
        "VALUES (:t, 1, :h, 'register', NOW() + INTERVAL '7 days', 999) RETURNING id",
        {"t": tenant_id, "h": token_hash or uuid.uuid4().hex + uuid.uuid4().hex},
    )
    return str(rows[0][0])


async def _ctx_conn(app_engine, tenant_id: int | None):
    """アプリ接続役で会社の文脈を張った接続と trans を返す（tenant_id=None は文脈なし）。"""
    from sqlalchemy import text

    conn = await app_engine.connect()
    trans = await conn.begin()
    if tenant_id is not None:
        await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})
    return conn, trans


def _session(app_engine):
    from sqlalchemy.ext.asyncio import AsyncSession

    return AsyncSession(app_engine, expire_on_commit=False)


def _sqlstate(exc) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


_INSERT_PAYPAL = (
    "INSERT INTO public.tenant_paypal_config "
    "(tenant_id, client_id_encrypted, client_secret_encrypted) VALUES (:t, 'c', 's')"
)
_INSERT_TOKEN = (
    "INSERT INTO public.registration_tokens "
    "(tenant_id, lead_id, token_hash, type, expires_at, created_by) "
    "VALUES (:t, 1, :h, 'register', NOW() + INTERVAL '7 days', 999)"
)


# ① 構造
async def test_catalog_rls_forced_and_four_policies_each():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, _app):
        async with admin_engine.connect() as conn:
            for table in _TABLES:
                flags = (
                    await conn.execute(
                        text(
                            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                            "WHERE oid = to_regclass(:t)"
                        ),
                        {"t": f"public.{table}"},
                    )
                ).one()
                assert tuple(flags) == (True, True), table
                names = (
                    await conn.execute(
                        text(
                            "SELECT policyname FROM pg_policies "
                            "WHERE schemaname = 'public' AND tablename = :t ORDER BY policyname"
                        ),
                        {"t": table},
                    )
                ).scalars().all()
                assert names == [
                    f"{table}_delete",
                    f"{table}_insert",
                    f"{table}_select",
                    f"{table}_update",
                ]


# ② 読取は文脈なしでも全行
async def test_select_all_rows_without_context():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        await _seed_paypal(admin_engine, _TENANT_A)
        await _seed_paypal(admin_engine, _TENANT_B)
        await _seed_token(admin_engine, _TENANT_A)
        await _seed_token(admin_engine, _TENANT_B)
        for ctx in (None, _TENANT_A):
            conn, trans = await _ctx_conn(app_engine, ctx)
            try:
                for table in _TABLES:
                    n = (await conn.execute(text(f"SELECT count(*) FROM public.{table}"))).scalar_one()
                    assert n == 2, (table, ctx)
            finally:
                await trans.rollback()
                await conn.close()


# ③ 他社・文脈なしでは書けない
async def test_other_tenant_and_no_context_cannot_write():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (admin_engine, app_engine):
        await _seed_paypal(admin_engine, _TENANT_B)
        b_token = await _seed_token(admin_engine, _TENANT_B)

        # 会社 A の文脈で会社 B の行: UPDATE / DELETE は無言で 0 行
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            r = await conn.execute(
                text("UPDATE public.tenant_paypal_config SET webhook_id = 'x' WHERE tenant_id = :t"),
                {"t": _TENANT_B},
            )
            assert r.rowcount == 0
            r = await conn.execute(
                text("DELETE FROM public.tenant_paypal_config WHERE tenant_id = :t"), {"t": _TENANT_B}
            )
            assert r.rowcount == 0
            r = await conn.execute(
                text("UPDATE public.registration_tokens SET used_at = NOW() WHERE id = :i"), {"i": b_token}
            )
            assert r.rowcount == 0
            r = await conn.execute(
                text("DELETE FROM public.registration_tokens WHERE id = :i"), {"i": b_token}
            )
            assert r.rowcount == 0
        finally:
            await trans.rollback()
            await conn.close()
        assert (await _admin_exec(admin_engine, "SELECT count(*) FROM public.tenant_paypal_config"))[0][0] == 1
        assert (await _admin_exec(admin_engine, "SELECT count(*) FROM public.registration_tokens"))[0][0] == 1

        # 会社 A の文脈で会社 B の tenant_id の INSERT、および文脈なしの INSERT は 42501
        for ctx in (_TENANT_A, None):
            for sql, params in (
                (_INSERT_PAYPAL, {"t": _TENANT_A if ctx is None else _TENANT_B}),
                (_INSERT_TOKEN, {"t": _TENANT_A if ctx is None else _TENANT_B, "h": uuid.uuid4().hex}),
            ):
                conn, trans = await _ctx_conn(app_engine, ctx)
                try:
                    with pytest.raises(DBAPIError) as exc_info:
                        await conn.execute(text(sql), params)
                    assert _sqlstate(exc_info.value) == "42501", (ctx, sql)
                finally:
                    await trans.rollback()
                    await conn.close()

        # 文脈なしの UPDATE / DELETE も 0 行
        conn, trans = await _ctx_conn(app_engine, None)
        try:
            r = await conn.execute(text("UPDATE public.tenant_paypal_config SET webhook_id = 'x'"))
            assert r.rowcount == 0
            r = await conn.execute(text("DELETE FROM public.registration_tokens"))
            assert r.rowcount == 0
        finally:
            await trans.rollback()
            await conn.close()


# ④ 自社の行は書ける
async def test_own_tenant_can_insert_update_delete():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            await conn.execute(text(_INSERT_PAYPAL), {"t": _TENANT_A})
            await conn.execute(text(_INSERT_TOKEN), {"t": _TENANT_A, "h": uuid.uuid4().hex})
            r = await conn.execute(
                text("UPDATE public.tenant_paypal_config SET webhook_id = 'x' WHERE tenant_id = :t"),
                {"t": _TENANT_A},
            )
            assert r.rowcount == 1
            r = await conn.execute(text("UPDATE public.registration_tokens SET used_at = NOW()"))
            assert r.rowcount == 1
            r = await conn.execute(
                text("DELETE FROM public.tenant_paypal_config WHERE tenant_id = :t"), {"t": _TENANT_A}
            )
            assert r.rowcount == 1
            r = await conn.execute(text("DELETE FROM public.registration_tokens"))
            assert r.rowcount == 1
        finally:
            await trans.rollback()
            await conn.close()


# ⑤ PUT /integrations/paypal/credentials の流れで webhook_id が保存される
async def test_put_paypal_credentials_saves_webhook_id_after_connection_swap(monkeypatch):
    from app.auth.dependencies import set_tenant_context
    from app.routers import integrations
    from app.services import paypal_payments

    original_save = paypal_payments.save_credentials

    async def save_then_lose_context(db, *args, **kwargs):
        # 元の処理（INSERT…ON CONFLICT + commit）の後に、接続が替わって文脈が消えた状態を再現する
        from sqlalchemy import text

        await original_save(db, *args, **kwargs)
        await db.execute(text("SET app.tenant_id = ''"))

    monkeypatch.setattr(paypal_payments, "save_credentials", save_then_lose_context)
    monkeypatch.setattr(
        paypal_payments,
        "register_webhook",
        lambda *a, **k: {"ok": True, "webhook_id": "WH-TEST"},
    )
    monkeypatch.setattr(paypal_payments.encryption, "encrypt", lambda s, **k: "enc:" + s)

    async with _fresh() as (admin_engine, app_engine):
        async with _session(app_engine) as db:
            await set_tenant_context(db, _TENANT_A)  # get_current_tenant 相当
            await integrations.save_paypal_credentials(
                integrations.PaypalCredentialsRequest(
                    client_id="cid", client_secret="csec", environment="sandbox"
                ),
                tenant_id=_TENANT_A,
                user=SimpleNamespace(id=999),
                db=db,
            )
        rows = await _admin_exec(
            admin_engine,
            "SELECT webhook_id FROM public.tenant_paypal_config WHERE tenant_id = :t",
            {"t": _TENANT_A},
        )
        assert rows == [("WH-TEST",)]


# ⑥ 会社の物理削除で連鎖削除が止まらない
async def test_tenant_delete_cascades_to_both_tables():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        await _seed_paypal(admin_engine, _TENANT_B)
        await _seed_token(admin_engine, _TENANT_B)
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            r = await conn.execute(text("DELETE FROM public.tenants WHERE id = :t"), {"t": _TENANT_B})
            assert r.rowcount == 1
            await trans.commit()
        finally:
            await conn.close()
        for table in _TABLES:
            n = (await _admin_exec(admin_engine, f"SELECT count(*) FROM public.{table}"))[0][0]
            assert n == 0, table


# ⑦ 招待リンクの公開 API 相当（文脈なしで探す → 文脈を張る → 使用済みにする）
async def test_public_register_flow_marks_token_used():
    from app.auth.dependencies import set_tenant_context
    from app.services import registration_token as rt

    raw_token, token_hash = rt.generate_token()
    async with _fresh() as (admin_engine, app_engine):
        token_id = await _seed_token(admin_engine, _TENANT_A, token_hash)
        async with _session(app_engine) as db:
            info = await rt.verify_token(db, raw_token)
            assert info is not None and info["tenant_id"] == _TENANT_A
            await set_tenant_context(db, info["tenant_id"])
            await rt.mark_token_used(db, str(info["id"]))
            await db.commit()
        rows = await _admin_exec(
            admin_engine, "SELECT used_at FROM public.registration_tokens WHERE id = :i", {"i": token_id}
        )
        assert rows[0][0] is not None
