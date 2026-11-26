"""ひとりひとりの初期値 6 列の移行と受け口の試験（schedule-settings 便3b・設計 design-bin3b.md §3・§5・受入条件 B3・B4・B5・B6）。

実 PostgreSQL（RLS_ADMIN_DATABASE_URL か TEST_PG_URL と RLS_TEST_DATABASE_URL）があるときだけ動く。
- 移行: 土台で作った部屋（新しい形）から 6 列を消して古い形に戻し、行を入れて 2 回流す
- 受け口: PUT /calendar/preferences が自分の行だけを変え、色（color_key）に触れない
"""
from __future__ import annotations

import os
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

_TENANT = 984
_SCHEMA = f"tenant_{_TENANT}"
_USER_A = 98401
_USER_B = 98402
_USERS = (_USER_A, _USER_B)
_MIGRATION = "20261129_100000_owner_settings_preferences.sql"
_PUBLIC_MIGRATIONS = (
    "076_add_google_calendar_config.sql",
    "077_calendar_sync_mode_and_webhook_subscriptions.sql",
    "20260606_010000_add_google_drive_config.sql",
    "20261016_010000_add_google_config_rls.sql",
)
_READY = {"done": False}
_NEW_COLUMNS = ("default_view", "week_start", "event_minutes", "auto_meet", "open_owners", "open_team_id")
_CHECKS = (
    "calendar_owner_settings_default_view_check",
    "calendar_owner_settings_week_start_check",
    "calendar_owner_settings_event_minutes_check",
    "calendar_owner_settings_open_owners_check",
)
_DEFAULTS = ("week", 0, 60, False, "self", None)


def _user(user_id: int):
    return SimpleNamespace(id=user_id, email=f"owner-prefs-{user_id}@example.com")


async def _cleanup(admin_engine) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_owner_settings"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.team_members"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.teams"))


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
                            " VALUES (:id, :t, :uname, :email, 'Owner Prefs', 'admin',"
                            "         TRUE, FALSE, 'ja', 'light')"
                            " ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": uid, "t": _TENANT, "uname": f"owner-prefs-{uid}", "email": f"owner-prefs-{uid}@example.com"},
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
    """新しい形の部屋を、この移行の前の形（便3a の形）に戻す（6 列を消す。CHECK・FK は列と一緒に消える）。"""
    await _exec(
        admin_engine,
        "ALTER TABLE {S}.calendar_owner_settings"
        " DROP COLUMN default_view, DROP COLUMN week_start, DROP COLUMN event_minutes,"
        " DROP COLUMN auto_meet, DROP COLUMN open_owners, DROP COLUMN open_team_id",
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


async def _prefs(admin_engine, staff_id: int):
    rows = await _rows(
        admin_engine,
        "SELECT default_view, week_start, event_minutes, auto_meet, open_owners, open_team_id"
        " FROM {S}.calendar_owner_settings WHERE staff_id = :s",
        s=staff_id,
    )
    return rows[0] if rows else None


async def _session(factory):
    from app.auth.dependencies import set_tenant_context

    db = factory()
    await set_tenant_context(db, _TENANT)
    return db


async def _put(factory, user_id: int, **fields):
    from app.routers import calendar as r

    body = r.CalendarPreferences(**fields)
    db = await _session(factory)
    try:
        return await r.put_calendar_preferences(body=body, tenant_id=_TENANT, current_user=_user(user_id), db=db)
    finally:
        await db.close()


async def _insert_team(admin_engine, name: str, active: bool = True) -> int:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        return (
            await conn.execute(
                text(f"INSERT INTO {_SCHEMA}.teams (name, is_active) VALUES (:n, :a) RETURNING id"),
                {"n": name, "a": active},
            )
        ).scalar_one()


# ---- 移行 ----


async def test_migration_adds_columns_with_defaults_to_existing_rows_and_runs_twice():
    async with _env() as (admin, _factory):
        await _to_old_shape(admin)
        assert not (set(_NEW_COLUMNS) & await _columns(admin))
        await _exec(admin, "INSERT INTO {S}.calendar_owner_settings (staff_id, color_key) VALUES (:a, 'basil')", a=_USER_A)

        await _run_migration(admin)
        first_cols = await _columns(admin)
        assert set(_NEW_COLUMNS) <= first_cols
        # 既存の行は既定値（今の動きと同じ）。色はそのまま
        assert await _prefs(admin, _USER_A) == _DEFAULTS
        assert await _rows(admin, "SELECT color_key FROM {S}.calendar_owner_settings WHERE staff_id = :a", a=_USER_A) == [
            ("basil",)
        ]

        await _run_migration(admin)  # 2 回目で何も変わらない
        assert await _columns(admin) == first_cols
        assert await _prefs(admin, _USER_A) == _DEFAULTS
        names = await _rows(
            admin,
            "SELECT conname FROM pg_constraint WHERE conrelid = to_regclass(:t)"
            " AND conname = ANY(:names) ORDER BY conname",
            t=f"{_SCHEMA}.calendar_owner_settings",
            names=list(_CHECKS) + ["fk_calendar_owner_settings_open_team"],
        )
        assert len(names) == 5


async def test_checks_refuse_out_of_range_values():
    from sqlalchemy.exc import IntegrityError

    async with _env() as (admin, _factory):
        await _exec(admin, "INSERT INTO {S}.calendar_owner_settings (staff_id) VALUES (:a)", a=_USER_A)
        for column, bad in (
            ("default_view", "'year'"),
            ("week_start", "2"),
            ("event_minutes", "50"),
            ("open_owners", "'x'"),
        ):
            with pytest.raises(IntegrityError):
                await _exec(
                    admin,
                    f"UPDATE {{S}}.calendar_owner_settings SET {column} = {bad} WHERE staff_id = :a",
                    a=_USER_A,
                )
        # 範囲の中の値は通る
        await _exec(
            admin,
            "UPDATE {S}.calendar_owner_settings SET default_view = 'threeDay', week_start = 1,"
            " event_minutes = 15, open_owners = 'all' WHERE staff_id = :a",
            a=_USER_A,
        )
        assert (await _prefs(admin, _USER_A))[:5] == ("threeDay", 1, 15, False, "all")


async def test_deleting_the_team_sets_open_team_id_to_null():
    async with _env() as (admin, _factory):
        team_id = await _insert_team(admin, "Sales")
        await _exec(
            admin,
            "INSERT INTO {S}.calendar_owner_settings (staff_id, open_owners, open_team_id) VALUES (:a, 'team', :t)",
            a=_USER_A, t=team_id,
        )
        assert (await _prefs(admin, _USER_A))[5] == team_id

        await _exec(admin, "DELETE FROM {S}.teams WHERE id = :t", t=team_id)

        prefs = await _prefs(admin, _USER_A)
        assert prefs[4] == "team" and prefs[5] is None  # 値は残り、チームの番号だけ NULL（画面は「自分だけ」に戻す）


# ---- 受け口 ----


async def test_put_by_a_leaves_b_unchanged():
    """B3: 自分の行だけを変える。"""
    async with _env() as (admin, factory):
        await _exec(admin, "INSERT INTO {S}.calendar_owner_settings (staff_id) VALUES (:b)", b=_USER_B)

        saved = await _put(factory, _USER_A, default_view="month", week_start=1, event_minutes=30, auto_meet=True)

        assert saved.default_view == "month"
        assert await _prefs(admin, _USER_A) == ("month", 1, 30, True, "self", None)
        assert await _prefs(admin, _USER_B) == _DEFAULTS


async def test_color_and_preferences_do_not_change_each_other():
    """B4: 初期値を保存しても色は変わらず、色を保存しても初期値は変わらない。"""
    from app.routers import calendar as r

    async with _env() as (admin, factory):
        await _put(factory, _USER_A, default_view="list", event_minutes=90)
        await _exec(admin, "UPDATE {S}.calendar_owner_settings SET color_key = 'tomato' WHERE staff_id = :a", a=_USER_A)

        # 初期値をもう一度保存しても色は変わらない
        await _put(factory, _USER_A, default_view="day", event_minutes=45)
        assert await _rows(admin, "SELECT color_key FROM {S}.calendar_owner_settings WHERE staff_id = :a", a=_USER_A) == [
            ("tomato",)
        ]

        # 色を PATCH しても初期値は変わらない
        db = await _session(factory)
        try:
            with patch("app.routers.calendar.load_user_permissions", return_value={"staff.view"}):
                await _seed_staff(admin)
                await r.update_calendar_owner(
                    user_id=_USER_A,
                    body=r.OwnerSettingsBody(color_key="cobalt"),
                    tenant_id=_TENANT,
                    user=_user(_USER_A),
                    db=db,
                )
        finally:
            await db.close()
        assert (await _prefs(admin, _USER_A))[:3] == ("day", 0, 45)
        assert await _rows(admin, "SELECT color_key FROM {S}.calendar_owner_settings WHERE staff_id = :a", a=_USER_A) == [
            ("cobalt",)
        ]


async def _seed_staff(admin_engine) -> None:
    """PATCH が staff の行を読むので、試験用の 1 行を足す（無ければ）。"""
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        exists = (
            await conn.execute(text(f"SELECT count(*) FROM {_SCHEMA}.staff WHERE user_id = :u"), {"u": _USER_A})
        ).scalar_one()
        if not exists:
            await conn.execute(
                text(
                    f"INSERT INTO {_SCHEMA}.staff (tenant_id, user_id, staff_code, surname_jp, given_name_jp)"
                    " VALUES (:t, :u, 'P01', '試験', '太郎')"
                ),
                {"t": _TENANT, "u": _USER_A},
            )


async def test_put_with_an_unknown_or_inactive_team_is_refused():
    from fastapi import HTTPException

    async with _env() as (admin, factory):
        inactive = await _insert_team(admin, "Old", active=False)
        for team_id in (inactive, 999999):
            with pytest.raises(HTTPException) as exc:
                await _put(factory, _USER_A, open_owners="team", open_team_id=team_id)
            assert exc.value.status_code == 422 and exc.value.detail == "invalid_team"
        assert await _prefs(admin, _USER_A) is None


async def test_put_with_an_active_team_is_saved_and_other_modes_clear_it():
    async with _env() as (admin, factory):
        team_id = await _insert_team(admin, "Sales")
        await _put(factory, _USER_A, open_owners="team", open_team_id=team_id)
        assert (await _prefs(admin, _USER_A))[4:] == ("team", team_id)

        await _put(factory, _USER_A, open_owners="all", open_team_id=team_id)
        assert (await _prefs(admin, _USER_A))[4:] == ("all", None)


async def test_roster_team_ids_contain_only_active_teams():
    from app.routers import calendar as r

    async with _env() as (admin, factory):
        await _seed_staff(admin)
        active = await _insert_team(admin, "Sales")
        stopped = await _insert_team(admin, "Old", active=False)
        await _exec(
            admin,
            "INSERT INTO {S}.team_members (team_id, user_id) VALUES (:a, :u), (:s, :u)",
            a=active, s=stopped, u=_USER_A,
        )

        db = await _session(factory)
        try:
            with patch("app.routers.calendar.load_user_permissions", return_value={"staff.view"}):
                result = await r.list_calendar_owners(tenant_id=_TENANT, user=_user(_USER_A), db=db)
        finally:
            await db.close()

        mine = [o for o in result.owners if o.user_id == _USER_A]
        assert len(mine) == 1 and mine[0].team_ids == [active]
