"""ADR-1020 便1: 「調べたが無い」の記録表の RLS・制約・保存関数（実 PostgreSQL）。"""
from __future__ import annotations

import os
import uuid

import pytest

from tests.rls_bootstrap import _apply_migration, public_bootstrap_lock

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

_MIGRATION = "20261016_190000_create_product_blank_confirmations.sql"


async def _setup():
    from sqlalchemy.ext.asyncio import create_async_engine

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    async with public_bootstrap_lock(admin_engine):
        await _apply_migration(admin_engine, _MIGRATION)
    return admin_engine, app_engine


async def _make_product(admin_engine) -> int:
    from sqlalchemy import text

    code = "TEST-BLANK-" + uuid.uuid4().hex[:8]
    async with admin_engine.begin() as conn:
        row = await conn.execute(
            text(
                "INSERT INTO public.products (product_code, name) "
                "VALUES (:code, 'blank-test') RETURNING id"
            ),
            {"code": code},
        )
        return row.scalar_one()


async def _drop_product(admin_engine, product_id: int) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text("DELETE FROM public.products WHERE id = :id"), {"id": product_id})


async def _set_operator(conn) -> None:
    from sqlalchemy import text

    await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))


def _sqlstate(exc_info) -> str | None:
    orig = exc_info.value.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


async def _count(admin_engine, product_id: int) -> int:
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        return (await conn.execute(
            text("SELECT count(*) FROM public.product_blank_confirmations WHERE product_id = :id"),
            {"id": product_id},
        )).scalar_one()


async def _fields(admin_engine, product_id: int) -> set[str]:
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT field_code FROM public.product_blank_confirmations WHERE product_id = :id"),
            {"id": product_id},
        )
        return {r[0] for r in rows}


_INSERT_SQL = (
    "INSERT INTO public.product_blank_confirmations (product_id, field_code, confirmed_by) "
    "VALUES (:pid, :field, 'test')"
)


async def test_write_requires_operator_flag():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    pid = await _make_product(admin_engine)
    try:
        async with app_engine.connect() as conn:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(text(_INSERT_SQL), {"pid": pid, "field": "name_en"})
            assert _sqlstate(exc_info) == "42501"
            await conn.rollback()
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            await _set_operator(conn)
            await conn.execute(text(_INSERT_SQL), {"pid": pid, "field": "name_en"})
            await trans.commit()
        assert await _count(admin_engine, pid) == 1
    finally:
        await _drop_product(admin_engine, pid)
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_field_code_check_rejects_other_fields():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    pid = await _make_product(admin_engine)
    try:
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await _set_operator(conn)
                with pytest.raises(DBAPIError) as exc_info:
                    await conn.execute(text(_INSERT_SQL), {"pid": pid, "field": "name"})
                assert _sqlstate(exc_info) == "23514"
            finally:
                await trans.rollback()
    finally:
        await _drop_product(admin_engine, pid)
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_cascade_on_product_delete():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    pid = await _make_product(admin_engine)
    try:
        async with admin_engine.begin() as conn:
            await conn.execute(text(_INSERT_SQL), {"pid": pid, "field": "mark"})
        assert await _count(admin_engine, pid) == 1
        await _drop_product(admin_engine, pid)
        assert await _count(admin_engine, pid) == 0
    finally:
        await _drop_product(admin_engine, pid)
        await admin_engine.dispose()
        await app_engine.dispose()


async def _run_save(app_engine, pid: int, values: dict, confirmations):
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.tcg_product_master_svc import save_blank_confirmations

    async with AsyncSession(app_engine) as session:
        await _set_operator(session)
        await save_blank_confirmations(
            session, product_id=pid, values=values, confirmations=confirmations, actor="tester",
        )
        await session.commit()


async def test_save_replaces_and_drops_filled_fields():
    admin_engine, app_engine = await _setup()
    pid = await _make_product(admin_engine)
    try:
        await _run_save(app_engine, pid, {"name_en": "", "mark": "X1"}, {"name_en", "mark"})
        assert await _fields(admin_engine, pid) == {"name_en"}
    finally:
        await _drop_product(admin_engine, pid)
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_save_without_set_clears_only_filled():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    pid = await _make_product(admin_engine)
    try:
        async with admin_engine.begin() as conn:
            for field in ("name_en", "release_date"):
                await conn.execute(text(_INSERT_SQL), {"pid": pid, "field": field})
        await _run_save(app_engine, pid, {"name_en": "Foo", "release_date": None}, None)
        assert await _fields(admin_engine, pid) == {"release_date"}
    finally:
        await _drop_product(admin_engine, pid)
        await admin_engine.dispose()
        await app_engine.dispose()
