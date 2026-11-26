"""人の色の移行と、止めたチームの扱いの試験（schedule-settings 便3a・設計 design-bin3a.md §3・§5・受入条件 A4・A6・A8・A9）。

実 PostgreSQL（RLS_ADMIN_DATABASE_URL か TEST_PG_URL と RLS_TEST_DATABASE_URL）があるときだけ動く。
- 移行: 土台で作った部屋（新しい形）を古い形に戻し、合う色・合わない色の行を入れて 2 回流す
- 止めたチーム: チーム予定を作り、チームを止めても一覧の件数が変わらず、team_ids からそのチームだけが消える
"""
from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
)

os.environ.setdefault("METADATA_FERNET_KEY", Fernet.generate_key().decode())

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not ADMIN_PG_URL or not APP_PG_URL,
        reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。",
    ),
    pytest.mark.asyncio,
]

_TENANT = 983
_SCHEMA = f"tenant_{_TENANT}"
_USER_A = 98301
_USER_B = 98302
_USER_C = 98303
_USERS = (_USER_A, _USER_B, _USER_C)
_MIGRATION = "20261128_100000_owner_color_key_drop_dead_columns.sql"
_PUBLIC_MIGRATIONS = (
    "076_add_google_calendar_config.sql",
    "077_calendar_sync_mode_and_webhook_subscriptions.sql",
    "20260606_010000_add_google_drive_config.sql",
    "20261016_010000_add_google_config_rls.sql",
)
_RANGE = {"start": "2026-12-01T00:00:00+09:00", "end": "2026-12-31T00:00:00+09:00"}
_READY = {"done": False}
_OLD_COLUMNS = ("color", "is_visible", "share_mode")


def _user(user_id: int):
    return SimpleNamespace(id=user_id, email=f"owner-color-{user_id}@example.com")


async def _cleanup(admin_engine) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_events"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.team_members"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.teams"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_owner_settings"))


@asynccontextmanager
async def _env():
    """(admin_engine, factory) を返す。終わったら表を空にして、移行の後の形（新しい形）に戻す。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False, poolclass=NullPool)
    if not _READY["done"]:
        await bootstrap_tenant_schema(admin_engine, _TENANT)
        async with public_bootstrap_lock(admin_engine):
            async with admin_engine.begin() as conn:
                exists = (
                    await conn.execute(text("SELECT to_regclass('public.tenant_google_calendar_config') IS NOT NULL"))
                ).scalar_one()
                if not exists:
                    for filename in _PUBLIC_MIGRATIONS:
                        await _apply_migration_on_conn(conn, filename)
                # calendar_owner_settings.staff_id は public.users(id) への外部キーなので先に入れる
                for uid in _USERS:
                    await conn.execute(
                        text(
                            "INSERT INTO public.users ("
                            " id, tenant_id, username, email, full_name,"
                            " role, is_active, is_super_admin, locale, theme)"
                            " VALUES (:id, :t, :uname, :email, 'Owner Color', 'admin',"
                            "         TRUE, FALSE, 'ja', 'light')"
                            " ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": uid, "t": _TENANT, "uname": f"owner-color-{uid}", "email": f"owner-color-{uid}@example.com"},
                    )
                await conn.execute(
                    text("DELETE FROM public.tenant_google_calendar_config WHERE tenant_id = :t"), {"t": _TENANT}
                )
        _READY["done"] = True
    await _cleanup(admin_engine)
    factory = async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield admin_engine, factory
    finally:
        try:
            await _cleanup(admin_engine)
            # 古い形に戻したまま終わらせない（移行を流せば新しい形に戻る）
            async with admin_engine.begin() as conn:
                await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)
        finally:
            await admin_engine.dispose()
            await app_engine.dispose()


async def _rows(admin_engine, sql: str, **params):
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        return [tuple(r) for r in (await conn.execute(text(sql.replace("{S}", _SCHEMA)), params)).all()]


async def _exec(admin_engine, sql: str, **params):
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text(sql.replace("{S}", _SCHEMA)), params)


async def _to_old_shape(admin_engine) -> None:
    """新しい形の部屋を、移行の前の古い形に戻す（color_key と、その CHECK を落とす）。"""
    await _exec(
        admin_engine,
        "ALTER TABLE {S}.calendar_owner_settings"
        " ADD COLUMN color varchar(32) DEFAULT '#1a73e8' NOT NULL,"
        " ADD COLUMN is_visible boolean DEFAULT false NOT NULL,"
        " ADD COLUMN share_mode varchar(16) DEFAULT 'self' NOT NULL,"
        " DROP COLUMN color_key",
    )


async def _run_migration(admin_engine) -> None:
    async with admin_engine.begin() as conn:
        await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)


async def _columns(admin_engine) -> set[str]:
    rows = await _rows(
        admin_engine,
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_schema = :s AND table_name = 'calendar_owner_settings'",
        s=_SCHEMA,
    )
    return {r[0] for r in rows}


async def _color_keys(admin_engine) -> dict[int, str | None]:
    rows = await _rows(admin_engine, "SELECT staff_id, color_key FROM {S}.calendar_owner_settings")
    return {r[0]: r[1] for r in rows}


# ---- A4・A9: 移行 ----


async def test_migration_maps_matching_hex_to_key_and_drops_old_columns():
    async with _env() as (admin, _factory):
        await _to_old_shape(admin)
        assert set(_OLD_COLUMNS) <= await _columns(admin)
        # 大文字・前後の空白つきでも合う / 24 色に無い値は合わない
        await _exec(
            admin,
            "INSERT INTO {S}.calendar_owner_settings (staff_id, color) VALUES"
            " (:a, '  #D50000 '), (:b, '#123456'), (:c, '#4285f4')",
            a=_USER_A, b=_USER_B, c=_USER_C,
        )

        await _run_migration(admin)

        cols = await _columns(admin)
        assert "color_key" in cols
        assert not (set(_OLD_COLUMNS) & cols)
        assert await _color_keys(admin) == {_USER_A: "tomato", _USER_B: None, _USER_C: "cobalt"}


async def test_migration_twice_gives_the_same_result():
    async with _env() as (admin, _factory):
        await _to_old_shape(admin)
        await _exec(
            admin,
            "INSERT INTO {S}.calendar_owner_settings (staff_id, color) VALUES (:a, '#d50000'), (:b, '#123456')",
            a=_USER_A, b=_USER_B,
        )
        await _run_migration(admin)
        first_cols = await _columns(admin)
        first_keys = await _color_keys(admin)

        await _run_migration(admin)

        assert await _columns(admin) == first_cols
        assert await _color_keys(admin) == first_keys == {_USER_A: "tomato", _USER_B: None}


async def test_check_rejects_value_outside_24_keys_and_allows_null():
    from sqlalchemy.exc import IntegrityError

    async with _env() as (admin, _factory):
        await _to_old_shape(admin)
        await _run_migration(admin)

        await _exec(admin, "INSERT INTO {S}.calendar_owner_settings (staff_id) VALUES (:a)", a=_USER_A)
        assert await _color_keys(admin) == {_USER_A: None}
        await _exec(admin, "UPDATE {S}.calendar_owner_settings SET color_key = 'basil' WHERE staff_id = :a", a=_USER_A)
        assert await _color_keys(admin) == {_USER_A: "basil"}
        with pytest.raises(IntegrityError):
            await _exec(
                admin, "UPDATE {S}.calendar_owner_settings SET color_key = 'red' WHERE staff_id = :a", a=_USER_A
            )


async def test_migrated_shape_equals_the_template_shape():
    """移行の後の color_key は text で、CHECK の鍵の並びは同じ部屋の calendar_events_color_key_check と同じ。"""
    async with _env() as (admin, _factory):
        await _to_old_shape(admin)
        await _run_migration(admin)

        types = await _rows(
            admin,
            "SELECT format_type(a.atttypid, a.atttypmod) FROM pg_attribute a"
            " WHERE a.attrelid = to_regclass(:t) AND a.attname = 'color_key' AND NOT a.attisdropped",
            t=f"{_SCHEMA}.calendar_owner_settings",
        )
        assert types == [("text",)]

        owner_def = await _rows(
            admin,
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
            " WHERE conrelid = to_regclass(:t) AND conname = 'calendar_owner_settings_color_key_check'",
            t=f"{_SCHEMA}.calendar_owner_settings",
        )
        event_def = await _rows(
            admin,
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
            " WHERE conrelid = to_regclass(:t) AND conname = 'calendar_events_color_key_check'",
            t=f"{_SCHEMA}.calendar_events",
        )
        assert len(owner_def) == 1 and len(event_def) == 1
        assert re.findall(r"'([a-z_]+)'", owner_def[0][0]) == re.findall(r"'([a-z_]+)'", event_def[0][0])
        assert len(re.findall(r"'([a-z_]+)'", owner_def[0][0])) == 24


# ---- A6・A8: 止めたチームの扱い ----


async def _session(factory):
    from app.auth.dependencies import set_tenant_context

    db = factory()
    await set_tenant_context(db, _TENANT)
    return db


async def test_deactivated_team_leaves_team_ids_but_not_the_list():
    from app.routers import calendar as r
    from app.services import calendar_service as cal
    from sqlalchemy import text

    async with _env() as (admin, factory):
        ids = {}
        async with admin.begin() as conn:
            for key, name in (("t1", "Sales"), ("t2", "Buying")):
                ids[key] = (
                    await conn.execute(
                        text(f"INSERT INTO {_SCHEMA}.teams (name, is_active) VALUES (:n, TRUE) RETURNING id"),
                        {"n": name},
                    )
                ).scalar_one()

        body = r.CreateEventBody(
            title="team event",
            start_datetime="2026-12-03T10:00:00+09:00",
            end_datetime="2026-12-03T11:00:00+09:00",
            calendar_type="team",
            team_ids=[ids["t1"], ids["t2"]],
        )
        db = await _session(factory)
        try:
            with patch("app.routers.calendar.get_user_system_keys", return_value={"owner"}):
                created = await r.create_event(body=body, tenant_id=_TENANT, user=_user(_USER_A), db=db)
        finally:
            await db.close()
        event_id = created["id"]

        async def listed():
            session = await _session(factory)
            try:
                return await cal.list_events(session, _TENANT, user_id=_USER_A, **_RANGE)
            finally:
                await session.close()

        async def team_ids_of_event():
            session = await _session(factory)
            try:
                return await cal.event_team_ids(session, event_id)
            finally:
                await session.close()

        before = await listed()
        assert [i["team_ids"] for i in before if i["id"] == event_id] == [sorted([ids["t1"], ids["t2"]])]
        assert await team_ids_of_event() == sorted([ids["t1"], ids["t2"]])

        await _exec(admin, "UPDATE {S}.teams SET is_active = FALSE WHERE id = :t", t=ids["t2"])

        after = await listed()
        assert len(after) == len(before)  # A8: 一覧から予定は消えない
        assert [i["team_ids"] for i in after if i["id"] == event_id] == [[ids["t1"]]]
        assert await team_ids_of_event() == [ids["t1"]]
