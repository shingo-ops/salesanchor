"""public.permissions の RLS（ADR-1018 段階①）: salesanchor_app からは読み取り専用。"""
from __future__ import annotations

import os

import pytest

from tests.rls_bootstrap import bootstrap_public_products

ADMIN_PG_URL = (
    os.getenv("RLS_ADMIN_DATABASE_URL")
    or os.getenv("TEST_PG_URL")
)
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

_DIGEST_SQL = (
    "SELECT md5(string_agg(id::text || key || description, ',' ORDER BY id)) "
    "FROM public.permissions"
)


async def _admin_scalar(admin_engine, sql: str):
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        return (await conn.execute(text(sql))).scalar_one()


async def _setup():
    from sqlalchemy.ext.asyncio import create_async_engine

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    await bootstrap_public_products(admin_engine)
    return admin_engine, app_engine


async def test_permissions_select_returns_all_rows_under_app_role():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    try:
        expected = await _admin_scalar(admin_engine, "SELECT count(*) FROM public.permissions")
        assert expected > 0
        async with app_engine.connect() as conn:
            actual = (await conn.execute(text("SELECT count(*) FROM public.permissions"))).scalar_one()
        assert actual == expected
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_permissions_writes_denied_without_operator_flag():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    try:
        before = await _admin_scalar(admin_engine, _DIGEST_SQL)
        count_before = await _admin_scalar(admin_engine, "SELECT count(*) FROM public.permissions")

        # INSERT: WITH CHECK 違反 = 42501
        async with app_engine.connect() as conn:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(text(
                    "INSERT INTO public.permissions (key, resource, action, description, category) "
                    "VALUES ('rls.test.denied', 'rls', 'test', 'denied', 'rls')"
                ))
            orig = exc_info.value.orig
            sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
            assert sqlstate == "42501"
            await conn.rollback()

        # UPDATE / DELETE: USING で行が見えず 0 行
        async with app_engine.connect() as conn:
            upd = await conn.execute(text("UPDATE public.permissions SET description = 'changed' WHERE id > 0"))
            assert upd.rowcount == 0
            dele = await conn.execute(text("DELETE FROM public.permissions WHERE id > 0"))
            assert dele.rowcount == 0
            await conn.commit()

        assert await _admin_scalar(admin_engine, _DIGEST_SQL) == before
        assert await _admin_scalar(admin_engine, "SELECT count(*) FROM public.permissions") == count_before
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_permissions_insert_allowed_with_operator_flag_and_rolled_back():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    try:
        count_before = await _admin_scalar(admin_engine, "SELECT count(*) FROM public.permissions")
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(text("SET LOCAL app.is_operator = 'true'"))
                res = await conn.execute(text(
                    "INSERT INTO public.permissions (key, resource, action, description, category) "
                    "VALUES ('rls.test.operator', 'rls', 'test', 'operator', 'rls')"
                ))
                assert res.rowcount == 1
            finally:
                await trans.rollback()
        assert await _admin_scalar(admin_engine, "SELECT count(*) FROM public.permissions") == count_before
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_permissions_rls_catalog_state():
    admin_engine, app_engine = await _setup()
    try:
        flags = await _admin_scalar(
            admin_engine,
            "SELECT relrowsecurity::text || ',' || relforcerowsecurity::text "
            "FROM pg_class WHERE oid = 'public.permissions'::regclass",
        )
        assert flags == "true,true"
        policies = await _admin_scalar(
            admin_engine,
            "SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = 'permissions'",
        )
        assert policies == 2
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()
