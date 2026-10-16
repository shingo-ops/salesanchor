"""障害記録の表 3 つの RLS・権限（ADR-1012 段階2 便A）: 運用者の旗が立った接続だけが読み書きでき、記録は消せない。"""
from __future__ import annotations

import os
import uuid

import pytest

from tests.ops_control_lock import ops_control_lock
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

_MIGRATION = "20261016_100000_create_ops_incident_tables.sql"

_INSERT_INCIDENT_SQL = (
    "INSERT INTO public.ops_incidents "
    "(id, fingerprint, starts_at, alertname, status, first_notified_at, last_notified_at) "
    "VALUES (:id, :fp, '2026-10-16T00:00:00+00:00', 'TestAlert', 'firing', now(), now())"
)
_INSERT_EVENT_SQL = (
    "INSERT INTO public.ops_incident_events (incident_id, kind, actor) "
    "VALUES (:id, 'notified', 'alertmanager')"
)


async def _setup():
    from sqlalchemy.ext.asyncio import create_async_engine

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    async with public_bootstrap_lock(admin_engine):
        await _apply_migration(admin_engine, _MIGRATION)
    return admin_engine, app_engine


async def _cleanup(admin_engine, fingerprint: str | None = None, *, control: bool = False):
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        if fingerprint is not None:
            await conn.execute(
                text(
                    "DELETE FROM public.ops_incident_events WHERE incident_id IN "
                    "(SELECT id FROM public.ops_incidents WHERE fingerprint = :fp)"
                ),
                {"fp": fingerprint},
            )
            await conn.execute(
                text("DELETE FROM public.ops_incidents WHERE fingerprint = :fp"),
                {"fp": fingerprint},
            )
        if control:
            await conn.execute(text("DELETE FROM public.ops_control WHERE id = 1"))


async def _set_operator(conn) -> None:
    from sqlalchemy import text

    await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))


def _sqlstate(exc_info) -> str | None:
    orig = exc_info.value.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


async def _create_incident_and_event(app_engine, fingerprint: str):
    """旗ありで障害 1 行と出来事 1 行を INSERT して commit する。障害の id を返す。"""
    from sqlalchemy import text

    incident_id = uuid.uuid4()
    async with app_engine.connect() as conn:
        trans = await conn.begin()
        try:
            await _set_operator(conn)
            await conn.execute(text(_INSERT_INCIDENT_SQL), {"id": incident_id, "fp": fingerprint})
            await conn.execute(text(_INSERT_EVENT_SQL), {"id": incident_id})
            await trans.commit()
        except Exception:
            await trans.rollback()
            raise
    return incident_id


async def test_insert_denied_without_operator_flag():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    fingerprint = "test-ops-rls-" + uuid.uuid4().hex
    try:
        async with app_engine.connect() as conn:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(
                    text(_INSERT_INCIDENT_SQL), {"id": uuid.uuid4(), "fp": fingerprint}
                )
            assert _sqlstate(exc_info) == "42501"
            await conn.rollback()
    finally:
        await _cleanup(admin_engine, fingerprint)
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_operator_can_insert_and_select_incident_and_event():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    fingerprint = "test-ops-rls-" + uuid.uuid4().hex
    try:
        incident_id = uuid.uuid4()
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await _set_operator(conn)
                await conn.execute(text(_INSERT_INCIDENT_SQL), {"id": incident_id, "fp": fingerprint})
                await conn.execute(text(_INSERT_EVENT_SQL), {"id": incident_id})
                incidents = (
                    await conn.execute(
                        text("SELECT count(*) FROM public.ops_incidents WHERE fingerprint = :fp"),
                        {"fp": fingerprint},
                    )
                ).scalar_one()
                events = (
                    await conn.execute(
                        text("SELECT count(*) FROM public.ops_incident_events WHERE incident_id = :id"),
                        {"id": incident_id},
                    )
                ).scalar_one()
                assert incidents == 1
                assert events == 1
            finally:
                await trans.rollback()
    finally:
        await _cleanup(admin_engine, fingerprint)
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_rows_invisible_without_operator_flag():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    fingerprint = "test-ops-rls-" + uuid.uuid4().hex
    try:
        await _create_incident_and_event(app_engine, fingerprint)
        async with app_engine.connect() as conn:
            visible = (
                await conn.execute(
                    text("SELECT count(*) FROM public.ops_incidents WHERE fingerprint = :fp"),
                    {"fp": fingerprint},
                )
            ).scalar_one()
            assert visible == 0
            await conn.rollback()
    finally:
        await _cleanup(admin_engine, fingerprint)
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_delete_denied_even_with_operator_flag():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    try:
        for table in ("ops_incidents", "ops_incident_events", "ops_control"):
            async with app_engine.connect() as conn:
                trans = await conn.begin()
                try:
                    await _set_operator(conn)
                    with pytest.raises(DBAPIError) as exc_info:
                        await conn.execute(text(f"DELETE FROM public.{table}"))
                    assert _sqlstate(exc_info) == "42501"
                finally:
                    await trans.rollback()
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_event_update_denied_even_with_operator_flag():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    try:
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await _set_operator(conn)
                with pytest.raises(DBAPIError) as exc_info:
                    await conn.execute(text("UPDATE public.ops_incident_events SET actor = 'ops_token'"))
                assert _sqlstate(exc_info) == "42501"
            finally:
                await trans.rollback()
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_duplicate_fingerprint_starts_at_rejected():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    fingerprint = "test-ops-rls-" + uuid.uuid4().hex
    try:
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await _set_operator(conn)
                await conn.execute(text(_INSERT_INCIDENT_SQL), {"id": uuid.uuid4(), "fp": fingerprint})
                with pytest.raises(DBAPIError) as exc_info:
                    await conn.execute(
                        text(_INSERT_INCIDENT_SQL), {"id": uuid.uuid4(), "fp": fingerprint}
                    )
                assert _sqlstate(exc_info) == "23505"
            finally:
                await trans.rollback()
    finally:
        await _cleanup(admin_engine, fingerprint)
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_ops_control_allows_only_id_1():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    async with ops_control_lock(admin_engine):
        try:
            async with app_engine.connect() as conn:
                trans = await conn.begin()
                try:
                    await _set_operator(conn)
                    await conn.execute(
                        text("INSERT INTO public.ops_control (id, changed_by) VALUES (1, 'test')")
                    )
                    with pytest.raises(DBAPIError) as exc_info:
                        await conn.execute(
                            text("INSERT INTO public.ops_control (id, changed_by) VALUES (2, 'test')")
                        )
                    assert _sqlstate(exc_info) == "23514"
                finally:
                    await trans.rollback()
        finally:
            await _cleanup(admin_engine, control=True)
    await admin_engine.dispose()
    await app_engine.dispose()
