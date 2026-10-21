"""誤り報告の表 3 つの RLS・権限（ADR-1025 便1）: 運用者の旗が立った接続だけが読み書きでき、events は追記だけ。"""
from __future__ import annotations

import os
import re
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

_MIGRATION = "20261017_140000_create_analysis_error_report_tables.sql"

_INSERT_REPORT_SQL = (
    "INSERT INTO public.analysis_error_reports (id, extraction_item_id, extraction_job_id, reported_by) "
    "VALUES (:id, :item, :job, 'test@example.com') RETURNING report_code"
)
_INSERT_EVENT_SQL = (
    "INSERT INTO public.analysis_error_report_events (report_id, actor, kind) "
    "VALUES (:id, 'test@example.com', 'created')"
)


async def _setup():
    from sqlalchemy.ext.asyncio import create_async_engine

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    async with public_bootstrap_lock(admin_engine):
        await _apply_migration(admin_engine, _MIGRATION)
    return admin_engine, app_engine


async def _cleanup(admin_engine, report_id) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text("DELETE FROM public.analysis_error_report_events WHERE report_id = :id"), {"id": report_id})
        await conn.execute(text("DELETE FROM public.analysis_error_report_fields WHERE report_id = :id"), {"id": report_id})
        await conn.execute(text("DELETE FROM public.analysis_error_reports WHERE id = :id"), {"id": report_id})


async def _set_operator(conn) -> None:
    from sqlalchemy import text

    await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))


def _sqlstate(exc_info) -> str | None:
    orig = exc_info.value.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def _params(report_id) -> dict:
    return {"id": report_id, "item": uuid.uuid4(), "job": uuid.uuid4()}


async def test_insert_denied_without_operator_flag():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    try:
        async with app_engine.connect() as conn:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(text(_INSERT_REPORT_SQL), _params(uuid.uuid4()))
            assert _sqlstate(exc_info) == "42501"
            await conn.rollback()
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_operator_can_insert_and_select_with_report_code():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    report_id = uuid.uuid4()
    try:
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await _set_operator(conn)
                code = (await conn.execute(text(_INSERT_REPORT_SQL), _params(report_id))).scalar_one()
                assert re.fullmatch(r"ER-\d{6}", code)
                await conn.execute(text(_INSERT_EVENT_SQL), {"id": report_id})
                reports = (
                    await conn.execute(
                        text("SELECT count(*) FROM public.analysis_error_reports WHERE id = :id"), {"id": report_id}
                    )
                ).scalar_one()
                events = (
                    await conn.execute(
                        text("SELECT count(*) FROM public.analysis_error_report_events WHERE report_id = :id"),
                        {"id": report_id},
                    )
                ).scalar_one()
                assert reports == 1
                assert events == 1
            finally:
                await trans.rollback()
    finally:
        await _cleanup(admin_engine, report_id)
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_report_code_starts_at_er_000001_on_fresh_sequence():
    """連番の最初の値の形。共有 DB では他テストの採番で進んでいるため、形（ER-＋6桁）と単調増加を確かめる。"""
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    try:
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await _set_operator(conn)
                first = (await conn.execute(text(_INSERT_REPORT_SQL), _params(first_id))).scalar_one()
                second = (await conn.execute(text(_INSERT_REPORT_SQL), _params(second_id))).scalar_one()
                assert re.fullmatch(r"ER-\d{6}", first)
                assert int(second[3:]) == int(first[3:]) + 1
            finally:
                await trans.rollback()
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_event_update_and_delete_denied_even_with_operator_flag():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    try:
        for sql in (
            "UPDATE public.analysis_error_report_events SET actor = 'x'",
            "DELETE FROM public.analysis_error_report_events",
        ):
            async with app_engine.connect() as conn:
                trans = await conn.begin()
                try:
                    await _set_operator(conn)
                    with pytest.raises(DBAPIError) as exc_info:
                        await conn.execute(text(sql))
                    assert _sqlstate(exc_info) == "42501"
                finally:
                    await trans.rollback()
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()
