"""予定の種類（calendar_categories）の試験（schedule-settings 便2a・設計 design-bin2a.md §3〜§5）。

種類の表・外部キー・受け口・予定の作る／直す（5 通り）を、実 PostgreSQL で確かめる。
実 PostgreSQL（RLS_ADMIN_DATABASE_URL か TEST_PG_URL と RLS_TEST_DATABASE_URL）があるときだけ動く。
Google には会社の接続の行を作らない（同期モード none）ので、通信は起きない。
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

_TENANT = 979
_SCHEMA = f"tenant_{_TENANT}"
_ADMIN_USER = 97901
_STAFF_USER = 97902
_MIGRATION = "20261126_100000_create_calendar_categories.sql"
# 会社の部屋の予定の表（種類の表と外部キーも）は bootstrap_tenant_schema が作る。bootstrap に無い共用の設定表だけ、無いときに足す
_PUBLIC_MIGRATIONS = (
    "076_add_google_calendar_config.sql",
    "077_calendar_sync_mode_and_webhook_subscriptions.sql",
    "20260606_010000_add_google_drive_config.sql",
    "20261016_010000_add_google_config_rls.sql",
)

_READY = {"done": False}
_DEFAULT_SEVEN = ("meeting", "personal", "procurement", "shipping", "billing", "release", "holiday")


def _user(user_id: int):
    return SimpleNamespace(id=user_id, email=f"cat-{user_id}@example.com")


async def _cleanup(admin_engine) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_events"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_categories WHERE key LIKE 'custom\\_%'"))
        await conn.execute(
            text(
                f"UPDATE {_SCHEMA}.calendar_categories SET name = NULL, color_key = NULL, is_active = TRUE,"
                " default_share = CASE WHEN key = 'personal' THEN 'self' ELSE 'all' END"
            )
        )


@asynccontextmanager
async def _env():
    """(admin_engine, factory) を返す。終わったら予定と足した種類を消して元の 7 行に戻す。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False, poolclass=NullPool)
    if not _READY["done"]:
        # 共用の表（public）を触る下ごしらえは、この試験ファイルの中で 1 回だけ行う。
        # 試験ごとにやり直すと、別のファイルの試験が共用の表を触る所と行き違ってデッドロックしやすい
        await bootstrap_tenant_schema(admin_engine, _TENANT)
        async with public_bootstrap_lock(admin_engine):
            async with admin_engine.begin() as conn:
                exists = (
                    await conn.execute(text("SELECT to_regclass('public.tenant_google_calendar_config') IS NOT NULL"))
                ).scalar_one()
                if not exists:
                    for filename in _PUBLIC_MIGRATIONS:
                        await _apply_migration_on_conn(conn, filename)
                for uid in (_ADMIN_USER, _STAFF_USER):
                    await conn.execute(
                        text(
                            "INSERT INTO public.users ("
                            " id, tenant_id, username, email, full_name,"
                            " role, is_active, is_super_admin, locale, theme)"
                            " VALUES (:id, :t, :uname, :email, 'Cal Cat', 'admin',"
                            "         TRUE, FALSE, 'ja', 'light')"
                            " ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": uid, "t": _TENANT, "uname": f"cal-cat-{uid}", "email": f"cal-cat-{uid}@example.com"},
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
        finally:
            await admin_engine.dispose()
            await app_engine.dispose()


async def _session(factory):
    from app.auth.dependencies import set_tenant_context

    db = factory()
    await set_tenant_context(db, _TENANT)
    return db


async def _rows(admin_engine, sql: str, **params):
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        return [tuple(r) for r in (await conn.execute(text(sql.replace("{S}", _SCHEMA)), params)).all()]


def _admin_keys():
    return patch("app.routers.calendar.get_user_system_keys", return_value={"owner"})


def _staff_keys():
    return patch("app.routers.calendar.get_user_system_keys", return_value=set())


async def _create(db, **fields):
    """受け口の作る道（router.create_event）で予定を作って id を返す。"""
    from app.routers import calendar as r

    body = r.CreateEventBody(
        title=fields.pop("title", "試験の予定"),
        start_datetime=fields.pop("start_datetime", "2026-12-03T10:00:00+09:00"),
        end_datetime=fields.pop("end_datetime", "2026-12-03T11:00:00+09:00"),
        **fields,
    )
    with _admin_keys():
        result = await r.create_event(body=body, tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db)
    return result["id"]


async def _update(db, event_id: int, **fields):
    from app.routers import calendar as r

    body = r.UpdateEventBody(**fields)
    with _admin_keys():
        return await r.update_event(event_id=event_id, body=body, tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db)


async def _set_active(admin_engine, key: str, active: bool) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(
            text(f"UPDATE {_SCHEMA}.calendar_categories SET is_active = :a WHERE key = :k"), {"a": active, "k": key}
        )


# ---- 移行・表の形 ----


async def test_migration_seven_rows_fk_and_no_category_check_and_idempotent():
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    async with _env() as (admin_engine, _factory):
        async def state():
            return (
                await _rows(admin_engine, "SELECT key, default_share, sort_order, is_active, name, color_key FROM {S}.calendar_categories ORDER BY sort_order"),
                await _rows(
                    admin_engine,
                    "SELECT conname, convalidated FROM pg_constraint WHERE conrelid = to_regclass(:t)"
                    " AND contype = 'f' AND conname = 'calendar_events_category_fkey'",
                    t=f"{_SCHEMA}.calendar_events",
                ),
                await _rows(
                    admin_engine,
                    "SELECT conname FROM pg_constraint WHERE conrelid = to_regclass(:t)"
                    " AND contype = 'c' AND pg_get_constraintdef(oid) ~ '\\mcategory\\M'",
                    t=f"{_SCHEMA}.calendar_events",
                ),
            )

        first = await state()
        rows, fk, checks = first
        assert [r[0] for r in rows] == list(_DEFAULT_SEVEN)
        assert [r[1] for r in rows] == ["all", "self", "all", "all", "all", "all", "all"]
        assert all(r[3] is True and r[4] is None and r[5] is None for r in rows)
        assert fk == [("calendar_events_category_fkey", True)]
        assert checks == []
        # 2 回流しても同じ
        async with admin_engine.begin() as conn:
            await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)
        assert await state() == first

        insert = text(
            f"INSERT INTO {_SCHEMA}.calendar_events (title, start_datetime, end_datetime, category)"
            " VALUES ('種', NOW(), NOW() + INTERVAL '1 hour', :c)"
        )
        # 表に無い鍵の INSERT は外部キーで失敗する
        with pytest.raises(IntegrityError):
            async with admin_engine.begin() as conn:
                await conn.execute(insert, {"c": "custom_1"})
        # custom_1 を足せば、その鍵で通る
        async with admin_engine.begin() as conn:
            await conn.execute(
                text(f"INSERT INTO {_SCHEMA}.calendar_categories (key, name, sort_order) VALUES ('custom_1', 'X', 8)")
            )
            await conn.execute(insert, {"c": "custom_1"})


async def test_migration_removes_an_old_check_with_a_different_name_or_fails():
    """名前の違う古い CHECK が残る部屋があれば、移行は止まって全体が戻る（custom_N が入らなくなるため）。"""
    from sqlalchemy import text

    async with _env() as (admin_engine, _factory):
        async with admin_engine.begin() as conn:
            await conn.execute(
                text(
                    f"ALTER TABLE {_SCHEMA}.calendar_events ADD CONSTRAINT calendar_events_legacy_cat_ck"
                    " CHECK (category IN ('meeting', 'personal'))"
                )
            )
        with pytest.raises(Exception, match="category を使う CHECK"):
            async with admin_engine.begin() as conn:
                await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"ALTER TABLE {_SCHEMA}.calendar_events DROP CONSTRAINT calendar_events_legacy_cat_ck"))


# ---- 種類の受け口 ----


async def test_list_create_update_and_admin_only():
    from fastapi import HTTPException

    from app.routers import calendar as r

    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            listed = await r.list_calendar_categories(tenant_id=_TENANT, user=_user(_STAFF_USER), db=db)
            assert [c["key"] for c in listed] == list(_DEFAULT_SEVEN)

            with _admin_keys():
                one = await r.create_calendar_category(
                    body=r.CreateCategoryBody(name="  見積り  ", color_key="tomato", default_share="self"),
                    tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db,
                )
                two = await r.create_calendar_category(
                    body=r.CreateCategoryBody(name="契約"), tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db
                )
            assert one["key"] == "custom_1" and one["name"] == "見積り" and one["sort_order"] == 8
            assert one["color_key"] == "tomato" and one["default_share"] == "self" and one["is_active"] is True
            assert two["key"] == "custom_2" and two["sort_order"] == 9 and two["default_share"] == "all"

            with _admin_keys():
                renamed = await r.update_calendar_category(
                    key="custom_1", body=r.UpdateCategoryBody(name="見積書", color_key="", default_share="all", is_active=False),
                    tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db,
                )
                # 7 種は空の名前で NULL に戻せる
                shipping = await r.update_calendar_category(
                    key="shipping", body=r.UpdateCategoryBody(name="出荷便"), tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db
                )
                back = await r.update_calendar_category(
                    key="shipping", body=r.UpdateCategoryBody(name=""), tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db
                )
            assert renamed["name"] == "見積書" and renamed["color_key"] is None
            assert renamed["default_share"] == "all" and renamed["is_active"] is False
            assert shipping["name"] == "出荷便" and back["name"] is None

            async def expect(code, detail, coro):
                with pytest.raises(HTTPException) as ei:
                    await coro
                assert ei.value.status_code == code and ei.value.detail == detail

            # 管理者でなければ 403（足す・直す）
            with _staff_keys():
                await expect(403, "この操作は管理者のみ実行できます", r.create_calendar_category(
                    body=r.CreateCategoryBody(name="x"), tenant_id=_TENANT, user=_user(_STAFF_USER), db=db))
                await expect(403, "この操作は管理者のみ実行できます", r.update_calendar_category(
                    key="meeting", body=r.UpdateCategoryBody(name="x"), tenant_id=_TENANT, user=_user(_STAFF_USER), db=db))
            with _admin_keys():
                await expect(404, "not_found:calendar_category", r.update_calendar_category(
                    key="nope", body=r.UpdateCategoryBody(name="x"), tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db))
                await expect(422, "category_not_disableable", r.update_calendar_category(
                    key="meeting", body=r.UpdateCategoryBody(is_active=False), tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db))
                await expect(422, "category_name_required", r.update_calendar_category(
                    key="custom_2", body=r.UpdateCategoryBody(name="   "), tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db))
                await expect(422, "category_name_required", r.create_calendar_category(
                    body=r.CreateCategoryBody(name="   "), tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db))
                await expect(422, "no_fields_to_update", r.update_calendar_category(
                    key="meeting", body=r.UpdateCategoryBody(), tenant_id=_TENANT, user=_user(_ADMIN_USER), db=db))
            # 値の決まり（色・共有）は入力の段階で 422
            from pydantic import ValidationError

            with pytest.raises(ValidationError):
                r.CreateCategoryBody(name="x", color_key="red")
            with pytest.raises(ValidationError):
                r.CreateCategoryBody(name="x", default_share="team")
            with pytest.raises(ValidationError):
                r.UpdateCategoryBody(default_share="team")
        finally:
            await db.close()


async def test_create_picks_custom_10_after_custom_9():
    """鍵は数に直して最大を取る（文字の並びなら custom_9 が最大になり custom_10 が重複する）。"""
    from sqlalchemy import text

    from app.services import calendar_categories as cc

    async with _env() as (admin_engine, factory):
        async with admin_engine.begin() as conn:
            await conn.execute(
                text(
                    f"INSERT INTO {_SCHEMA}.calendar_categories (key, name, sort_order) VALUES"
                    " ('custom_9', '九', 8), ('custom_10', '十', 9)"
                )
            )
        db = await _session(factory)
        try:
            made = await cc.create_category(db, _TENANT, "十一", None, "all")
            assert made["key"] == "custom_11" and made["sort_order"] == 10
        finally:
            await db.close()
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_categories WHERE key IN ('custom_10', 'custom_11')"))
        db = await _session(factory)
        try:
            made = await cc.create_category(db, _TENANT, "また", None, "all")
            assert made["key"] == "custom_10"  # custom_9 の次
        finally:
            await db.close()


async def test_create_conflict_returns_409_and_next_request_works():
    from fastapi import HTTPException
    from sqlalchemy.exc import IntegrityError

    from app.services import calendar_categories as cc

    async with _env() as (_admin_engine, factory):
        db = await _session(factory)
        try:
            real_execute = db.execute
            calls = {"n": 0}

            async def flaky(*args, **kwargs):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise IntegrityError("INSERT", {}, Exception("duplicate key"))
                return await real_execute(*args, **kwargs)

            with patch.object(db, "execute", side_effect=flaky):
                with pytest.raises(HTTPException) as ei:
                    await cc.create_category(db, _TENANT, "ぶつかる", None, "all")
            assert ei.value.status_code == 409 and ei.value.detail == "category_conflict"
            # 戻したあとの要求が普通に通る
            listed = await cc.list_categories(db)
            assert [c["key"] for c in listed] == list(_DEFAULT_SEVEN)
            made = await cc.create_category(db, _TENANT, "通る", None, "all")
            assert made["key"] == "custom_1"
        finally:
            await db.close()


# ---- 予定の種類: 作る ----


async def test_create_saves_category_defaults_to_meeting_and_rejects_unknown_or_inactive():
    from fastapi import HTTPException

    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            a = await _create(db, category="shipping")
            b = await _create(db)
            assert await _rows(admin_engine, "SELECT category FROM {S}.calendar_events WHERE id = :i", i=a) == [("shipping",)]
            assert await _rows(admin_engine, "SELECT category FROM {S}.calendar_events WHERE id = :i", i=b) == [("meeting",)]

            await _set_active(admin_engine, "billing", False)
            for bad in ("nope", "billing"):
                with pytest.raises(HTTPException) as ei:
                    await _create(db, category=bad)
                assert ei.value.status_code == 422 and ei.value.detail == "invalid_category"
        finally:
            await db.close()


# ---- 予定の種類: 直す 5 通り ----


def _cats(rows):
    return sorted((r[0], r[1]) for r in rows)


async def test_update_single_event_saves_category():
    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            eid = await _create(db)
            await _update(db, eid, category="billing")
            assert await _rows(admin_engine, "SELECT category FROM {S}.calendar_events WHERE id = :i", i=eid) == [("billing",)]
        finally:
            await db.close()


_OCC2 = "2026-12-10T10:00:00+09:00"  # 2 回目の回（毎週木曜 10:00 の 2 つ目）


async def test_update_this_occurrence_only_changes_that_occurrence():
    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            eid = await _create(db, recurrence="weekly")
            await _update(db, eid, category="shipping", scope="this", occurrence_start=_OCC2)
            rows = await _rows(admin_engine, "SELECT id, category, recurring_event_id FROM {S}.calendar_events ORDER BY id")
            master = [r for r in rows if r[0] == eid][0]
            exceptions = [r for r in rows if r[2] == eid]
            assert master[1] == "meeting"
            assert [(e[1]) for e in exceptions] == ["shipping"]
        finally:
            await db.close()


async def test_update_following_applies_category_to_new_series_only():
    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            eid = await _create(db, recurrence="weekly")
            await _update(db, eid, category="release", scope="following", occurrence_start=_OCC2)
            rows = await _rows(
                admin_engine, "SELECT id, category, recurrence_rule FROM {S}.calendar_events WHERE recurring_event_id IS NULL ORDER BY id"
            )
            master = [r for r in rows if r[0] == eid][0]
            others = [r for r in rows if r[0] != eid]
            assert master[1] == "meeting"
            assert [o[1] for o in others] == ["release"]
        finally:
            await db.close()


async def test_update_all_changes_master_and_exceptions():
    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            eid = await _create(db, recurrence="weekly")
            await _update(db, eid, title="差し替え", scope="this", occurrence_start=_OCC2)  # 例外の行を 1 つ作る
            await _update(db, eid, category="holiday", scope="all", occurrence_start="2026-12-03T10:00:00+09:00")
            rows = await _rows(admin_engine, "SELECT id, category FROM {S}.calendar_events ORDER BY id")
            assert len(rows) == 2
            assert {r[1] for r in rows} == {"holiday"}
        finally:
            await db.close()


async def test_update_single_to_recurring_saves_category():
    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            eid = await _create(db)
            await _update(db, eid, category="procurement", recurrence="weekly")
            assert await _rows(
                admin_engine, "SELECT category, recurrence_rule IS NOT NULL FROM {S}.calendar_events WHERE id = :i", i=eid
            ) == [("procurement", True)]
        finally:
            await db.close()


# ---- 使わなくした種類 ----


async def test_update_with_unchanged_inactive_category_passes_but_changing_to_inactive_fails():
    from fastapi import HTTPException

    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            eid = await _create(db, category="shipping")
            await _set_active(admin_engine, "shipping", False)
            await _update(db, eid, category="shipping", title="同じ種類のまま")  # 今の種類のまま → 通る
            with pytest.raises(HTTPException) as ei:
                await _update(db, eid, category="shipping_x")
            assert ei.value.status_code == 422 and ei.value.detail == "invalid_category"
            await _set_active(admin_engine, "billing", False)
            with pytest.raises(HTTPException) as ei:
                await _update(db, eid, category="billing")  # 使わなくした種類へ変えるのは通さない
            assert ei.value.detail == "invalid_category"
        finally:
            await db.close()


async def test_update_this_uses_exception_row_category_as_current_one():
    """元の行の種類が使わなくした種類でも、「この予定だけ」を種類を変えずに直すと通る。
    今の種類は、その回の例外の行が有ればその行、無ければ元の行の値。"""
    from fastapi import HTTPException

    async with _env() as (admin_engine, factory):
        db = await _session(factory)
        try:
            eid = await _create(db, recurrence="weekly", category="shipping")
            await _set_active(admin_engine, "shipping", False)
            # 元の行の種類のまま（例外の行はまだ無い）→ 通り、その回の例外の行が shipping で作られる
            await _update(db, eid, category="shipping", title="この回だけ", scope="this", occurrence_start=_OCC2)
            # 例外の行を billing にしてから billing を使わなくする
            await _update(db, eid, category="billing", scope="this", occurrence_start=_OCC2)
            await _set_active(admin_engine, "billing", False)
            # 例外の行の種類（billing）のまま直す → 通る（元の行は shipping）
            await _update(db, eid, category="billing", title="もう一度", scope="this", occurrence_start=_OCC2)
            # 元の行の種類（shipping）へ変えようとしても、今の種類（billing）と違い、使われていないので通らない
            with pytest.raises(HTTPException) as ei:
                await _update(db, eid, category="shipping", scope="this", occurrence_start=_OCC2)
            assert ei.value.detail == "invalid_category"
        finally:
            await db.close()


async def test_event_bodies_accept_category():
    from app.routers import calendar as r

    assert r.CreateEventBody(title="a", start_datetime="x", end_datetime="y", category="shipping").category == "shipping"
    assert r.UpdateEventBody(category="billing").category == "billing"
