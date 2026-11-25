"""予定の作成・削除で commit 後に会社の付け直しが要る件の試験（ADR-072・ADR-1018・ADR-1057）。

commit のあと別の接続になると、会社の設定表（RLS）が読めず Google に送られない。
実 PostgreSQL（RLS_ADMIN_DATABASE_URL か TEST_PG_URL と RLS_TEST_DATABASE_URL）があるときだけ動く。
Google への通信は偽物に差し替える。
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

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
        reason=(
            "実 PostgreSQL 環境が必要 "
            "(RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。"
        ),
    ),
    pytest.mark.asyncio,
]

_TENANT = 978
_SCHEMA = f"tenant_{_TENANT}"
_OWNER = 97801  # Google をつないだ本人
_OTHER = 97802  # つないでいない人

# (ファイル名, 試験のテナントのスキーマだけに流すか)。この順で流す。
_MIGRATIONS = (
    ("076_add_google_calendar_config.sql", False),
    ("077_calendar_sync_mode_and_webhook_subscriptions.sql", False),
    ("20260606_010000_add_google_drive_config.sql", False),
    ("20261016_010000_add_google_config_rls.sql", False),
    ("078_create_calendar_events_tenant.sql", True),
    ("20260621_020000_add_schedule_calendar_category_and_owner_settings.sql", True),
    ("20261103_200000_add_google_calendar_import_sync.sql", True),
    ("20261104_161223_add_calendar_events_meet_url.sql", True),
    ("20261112_170000_add_calendar_events_recurrence.sql", True),
    ("20261119_120000_add_calendar_events_color_key.sql", True),
)


def _payload(**extra) -> dict:
    base = {
        "title": "試験の予定",
        "start_datetime": datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
        "end_datetime": datetime(2026, 12, 1, 11, 0, tzinfo=timezone.utc).isoformat(),
    }
    base.update(extra)
    return base


async def _cleanup(admin_engine) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_events"))
        await conn.execute(
            text("DELETE FROM public.tenant_google_calendar_config WHERE tenant_id = :t"),
            {"t": _TENANT},
        )
        await conn.execute(
            text("DELETE FROM public.users WHERE id IN (:a, :b)"),
            {"a": _OWNER, "b": _OTHER},
        )


async def _setup():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
    from sqlalchemy.pool import NullPool

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False, poolclass=NullPool)
    await bootstrap_tenant_schema(admin_engine, _TENANT)
    async with public_bootstrap_lock(admin_engine):
        async with admin_engine.begin() as conn:
            for filename, scoped in _MIGRATIONS:
                await _apply_migration_on_conn(
                    conn, filename, schema_name=_SCHEMA if scoped else None
                )
    async with admin_engine.begin() as conn:
        for uid in (_OWNER, _OTHER):
            await conn.execute(
                text(
                    "INSERT INTO public.users ("
                    " id, tenant_id, username, email, full_name,"
                    " role, is_active, is_super_admin, locale, theme)"
                    " VALUES (:id, :t, :uname, :email, 'Cal Reset', 'admin',"
                    "         TRUE, FALSE, 'ja', 'light')"
                    " ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": uid,
                    "t": _TENANT,
                    "uname": f"cal-reset-{uid}",
                    "email": f"cal-reset-{uid}@example.com",
                },
            )
        await conn.execute(
            text("DELETE FROM public.tenant_google_calendar_config WHERE tenant_id = :t"),
            {"t": _TENANT},
        )
        await conn.execute(
            text(
                "INSERT INTO public.tenant_google_calendar_config"
                " (tenant_id, sync_mode, connected_by_user_id,"
                "  access_token_encrypted, refresh_token_encrypted, calendar_id)"
                " VALUES (:t, 'bidirectional', :u, 'x', 'y', 'primary')"
            ),
            {"t": _TENANT, "u": _OWNER},
        )
    factory = async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)
    return admin_engine, app_engine, factory


async def _teardown(admin_engine, app_engine) -> None:
    try:
        await _cleanup(admin_engine)
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def _fetch_row(admin_engine, event_id: int):
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        return (
            await conn.execute(
                text(
                    f"SELECT sync_status, google_event_id, meet_url"
                    f" FROM {_SCHEMA}.calendar_events WHERE id = :id"
                ),
                {"id": event_id},
            )
        ).one()


# 試験1 作成（Meet なし）: commit のあとも設定表が読めて Google に送られる
async def test_create_event_sends_to_google_after_commit():
    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    admin_engine, app_engine, factory = await _setup()
    try:
        fake_create = AsyncMock(return_value={"id": "g-1"})
        with patch("app.services.google_calendar.create_event", new=fake_create):
            async with factory() as db:
                await set_tenant_context(db, _TENANT)
                result = await calendar_service.create_event(db, _TENANT, _OWNER, _payload())
        assert fake_create.await_count == 1
        status, gid, _meet = await _fetch_row(admin_engine, result["id"])
        assert status == "synced"
        assert gid == "g-1"
    finally:
        await _teardown(admin_engine, app_engine)


# 試験1b 作成（Meet あり）
async def test_create_event_with_meet_saves_meet_url():
    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    meet = "https://meet.google.com/test-abc"
    admin_engine, app_engine, factory = await _setup()
    try:
        fake_create = AsyncMock(return_value={"id": "g-1b", "hangoutLink": meet})
        with patch("app.services.google_calendar.create_event", new=fake_create):
            async with factory() as db:
                await set_tenant_context(db, _TENANT)
                result = await calendar_service.create_event(
                    db, _TENANT, _OWNER, _payload(add_meet=True)
                )
        assert fake_create.await_count == 1
        assert result["meet_url"] == meet
        status, gid, meet_url = await _fetch_row(admin_engine, result["id"])
        assert status == "synced"
        assert gid == "g-1b"
        assert meet_url == meet
    finally:
        await _teardown(admin_engine, app_engine)


# 試験2 削除: commit のあとも設定表が読めて Google の削除が呼ばれる
async def test_delete_event_calls_google_delete_after_commit():
    from sqlalchemy import text

    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    admin_engine, app_engine, factory = await _setup()
    try:
        async with admin_engine.begin() as conn:
            event_id = (
                await conn.execute(
                    text(
                        f"INSERT INTO {_SCHEMA}.calendar_events"
                        " (user_id, calendar_type, category, title, start_datetime,"
                        "  end_datetime, source, sync_status, google_event_id,"
                        "  created_by_user_id)"
                        " VALUES (:u, 'shared', 'meeting', '消す予定', NOW(),"
                        "  NOW() + INTERVAL '1 hour', 'app', 'synced', 'g-2', :u)"
                        " RETURNING id"
                    ),
                    {"u": _OWNER},
                )
            ).scalar_one()
        fake_delete = AsyncMock(return_value=None)
        with patch("app.services.google_calendar.delete_event", new=fake_delete):
            async with factory() as db:
                await set_tenant_context(db, _TENANT)
                await calendar_service.delete_event(db, _TENANT, event_id)
        assert fake_delete.await_count == 1
        args = fake_delete.await_args.args
        assert args[1] == _TENANT
        assert args[2] == "g-2"
    finally:
        await _teardown(admin_engine, app_engine)


# 試験3 対照: つないでいない人の予定は Google に送らない（ADR-1057）
async def test_create_event_by_non_connected_user_is_not_sent():
    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    admin_engine, app_engine, factory = await _setup()
    try:
        fake_create = AsyncMock(return_value={"id": "g-3"})
        with patch("app.services.google_calendar.create_event", new=fake_create):
            async with factory() as db:
                await set_tenant_context(db, _TENANT)
                result = await calendar_service.create_event(db, _TENANT, _OTHER, _payload())
        assert fake_create.await_count == 0
        status, gid, _meet = await _fetch_row(admin_engine, result["id"])
        assert status == "pending"
        assert gid is None
    finally:
        await _teardown(admin_engine, app_engine)


# ---- 便15A: 予定の繰り返し（ADR-1075）。移行・3 択の消し方・例外の行の UNIQUE ----

_RECURRENCE_CHECKS = {
    "calendar_events_recurrence_role_check",
    "calendar_events_exception_pair_check",
    "calendar_events_cancelled_exception_check",
    "calendar_events_recurrence_rule_format_check",
}


def _weekly_payload() -> dict:
    return _payload(
        start_datetime="2026-12-03T10:00:00+09:00",
        end_datetime="2026-12-03T11:00:00+09:00",
        recurrence="weekly",
    )


async def _create_weekly_master(factory):
    """つないでいない人が作る（Google へ送らない）毎週の元の行を作って、読んだ行を返す。"""
    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    async with factory() as db:
        await set_tenant_context(db, _TENANT)
        created = await calendar_service.create_event(db, _TENANT, _OTHER, _weekly_payload())
        master = await calendar_service.read_event(db, created["id"])
    return master


async def _exception_rows(admin_engine, master_id: int):
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        return (
            await conn.execute(
                text(
                    f"SELECT is_cancelled, sync_status FROM {_SCHEMA}.calendar_events"
                    f" WHERE recurring_event_id = :id"
                ),
                {"id": master_id},
            )
        ).all()


async def test_recurrence_migration_adds_columns_checks_and_index():
    from sqlalchemy import text

    admin_engine, app_engine, _factory = await _setup()
    try:
        async with admin_engine.connect() as conn:
            cols = {
                r[0]
                for r in (
                    await conn.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns"
                            " WHERE table_schema = :s AND table_name = 'calendar_events'"
                        ),
                        {"s": _SCHEMA},
                    )
                ).all()
            }
            checks = {
                r[0]
                for r in (
                    await conn.execute(
                        text(
                            "SELECT conname FROM pg_constraint"
                            " WHERE conrelid = to_regclass(:t) AND contype = 'c'"
                        ),
                        {"t": f"{_SCHEMA}.calendar_events"},
                    )
                ).all()
            }
            indexes = {
                r[0]
                for r in (
                    await conn.execute(
                        text(
                            "SELECT indexname FROM pg_indexes"
                            " WHERE schemaname = :s AND tablename = 'calendar_events'"
                        ),
                        {"s": _SCHEMA},
                    )
                ).all()
            }
        assert {"recurrence_rule", "recurring_event_id", "original_start_datetime", "is_cancelled"} <= cols
        assert _RECURRENCE_CHECKS <= checks
        assert "calendar_events_exception_unique_idx" in indexes
    finally:
        await _teardown(admin_engine, app_engine)


# ---- ADR-1081 便1: 予定ごとの色。移行は冪等・欄と値の決まりができる・24 の鍵以外は DB が拒む ----

_COLOR_MIGRATION = "20261119_120000_add_calendar_events_color_key.sql"


async def _color_key_state(conn):
    from sqlalchemy import text

    cols = (
        await conn.execute(
            text(
                "SELECT data_type, is_nullable FROM information_schema.columns"
                " WHERE table_schema = :s AND table_name = 'calendar_events' AND column_name = 'color_key'"
            ),
            {"s": _SCHEMA},
        )
    ).all()
    checks = (
        await conn.execute(
            text(
                "SELECT conname, convalidated FROM pg_constraint"
                " WHERE conrelid = to_regclass(:t) AND conname = 'calendar_events_color_key_check'"
            ),
            {"t": f"{_SCHEMA}.calendar_events"},
        )
    ).all()
    return [tuple(r) for r in cols], [tuple(r) for r in checks]


async def test_color_key_migration_is_idempotent_and_adds_column_and_check():
    admin_engine, app_engine, _factory = await _setup()
    try:
        async with admin_engine.connect() as conn:
            first = await _color_key_state(conn)
        assert first == ([("text", "YES")], [("calendar_events_color_key_check", True)])
        # もう 1 回流しても同じ（冪等）
        async with admin_engine.begin() as conn:
            await _apply_migration_on_conn(conn, _COLOR_MIGRATION, schema_name=_SCHEMA)
        async with admin_engine.connect() as conn:
            assert await _color_key_state(conn) == first
    finally:
        await _teardown(admin_engine, app_engine)


async def test_color_key_check_accepts_24_keys_and_null_and_rejects_others():
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    from app.services.event_colors import EVENT_COLOR_KEYS

    admin_engine, app_engine, _factory = await _setup()
    insert = text(
        f"INSERT INTO {_SCHEMA}.calendar_events (title, start_datetime, end_datetime, color_key)"
        " VALUES ('色', NOW(), NOW() + INTERVAL '1 hour', :c)"
    )
    try:
        async with admin_engine.begin() as conn:
            for key in (*EVENT_COLOR_KEYS, None):
                await conn.execute(insert, {"c": key})
        for bad in ("red", ""):
            with pytest.raises(IntegrityError):
                async with admin_engine.begin() as conn:
                    await conn.execute(insert, {"c": bad})
    finally:
        await _teardown(admin_engine, app_engine)


async def test_color_key_roundtrip_through_service_with_empty_string_normalized_by_router():
    """作成で色を保存し、更新でデフォルトに戻す（受け口が "" を None にしてから渡す）。値の決まりに当たらない。"""
    from sqlalchemy import text

    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    admin_engine, app_engine, factory = await _setup()
    try:
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            created = await calendar_service.create_event(db, _TENANT, _OTHER, _payload(color_key="tomato"))
            listed = await calendar_service.list_events(
                db, _TENANT, start="2026-11-30T00:00:00+09:00", end="2026-12-31T00:00:00+09:00", calendar_type="shared"
            )
            assert [e["color_key"] for e in listed if e["id"] == created["id"]] == ["tomato"]
            await calendar_service.update_event(db, _TENANT, created["id"], _OTHER, {"color_key": None})
        async with admin_engine.connect() as conn:
            value = (
                await conn.execute(
                    text(f"SELECT color_key FROM {_SCHEMA}.calendar_events WHERE id = :id"), {"id": created["id"]}
                )
            ).scalar_one()
        assert value is None
    finally:
        await _teardown(admin_engine, app_engine)


async def test_delete_this_marks_exception_cancelled_and_all_cascades():
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo

    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        occ = _dt(2026, 12, 10, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            await calendar_service.delete_recurring_event(db, _TENANT, master, "this", occ)
        rows = await _exception_rows(admin_engine, master["id"])
        assert [(r[0], r[1]) for r in rows] == [(True, "pending")]

        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            await calendar_service.delete_recurring_event(db, _TENANT, master, "all", occ)
        assert await _exception_rows(admin_engine, master["id"]) == []
        async with admin_engine.connect() as conn:
            from sqlalchemy import text

            left = (
                await conn.execute(
                    text(f"SELECT count(*) FROM {_SCHEMA}.calendar_events WHERE id = :id"),
                    {"id": master["id"]},
                )
            ).scalar_one()
        assert left == 0
    finally:
        await _teardown(admin_engine, app_engine)


async def test_same_occurrence_exception_twice_is_rejected_by_unique_index():
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        insert = text(
            f"INSERT INTO {_SCHEMA}.calendar_events"
            " (title, start_datetime, end_datetime, sync_status, recurring_event_id, original_start_datetime)"
            " VALUES ('例外', :s, :e, 'pending', :mid, :orig)"
        )
        params = {
            "s": datetime(2026, 12, 10, 1, 0, tzinfo=timezone.utc),
            "e": datetime(2026, 12, 10, 2, 0, tzinfo=timezone.utc),
            "mid": master["id"],
            "orig": datetime(2026, 12, 10, 1, 0, tzinfo=timezone.utc),
        }
        async with admin_engine.begin() as conn:
            await conn.execute(insert, params)
        with pytest.raises(IntegrityError):
            async with admin_engine.begin() as conn:
                await conn.execute(insert, params)
    finally:
        await _teardown(admin_engine, app_engine)


async def _mark_synced_from_app(admin_engine, event_id: int, gid: str) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                f"UPDATE {_SCHEMA}.calendar_events SET google_event_id = :gid,"
                " sync_origin_id = :oid, sync_status = 'synced' WHERE id = :id"
            ),
            {"gid": gid, "oid": f"app:{_TENANT}:{event_id}", "id": event_id},
        )


async def _count_rows(admin_engine, where_sql: str, params: dict) -> int:
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        return (
            await conn.execute(
                text(f"SELECT count(*) FROM {_SCHEMA}.calendar_events WHERE {where_sql}"), params
            )
        ).scalar_one()


async def _import_one(factory, item: dict, g_master: dict | None = None) -> str:
    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    getter = AsyncMock(return_value=g_master)
    async with factory() as db:
        await set_tenant_context(db, _TENANT)
        with patch("app.services.google_calendar.get_event", new=getter):
            out = await calendar_service.upsert_from_google(db, _TENANT, item, _OWNER, series_cache={})
        await db.commit()
    return out


def _g_master_for(master: dict) -> dict:
    return {
        "id": "gm978", "status": "confirmed", "summary": master["title"],
        "recurrence": ["RRULE:" + master["recurrence_rule"]],
        "start": {"dateTime": "2026-12-03T10:00:00+09:00"},
        "end": {"dateTime": "2026-12-03T11:00:00+09:00"},
    }


# Google で消したアプリの単発の予定は、DB の決まりに外れずに行ごと消える（ADR-1059 改訂 2026-11-25）
async def test_google_cancel_deletes_app_single_row_on_real_db():
    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    admin_engine, app_engine, factory = await _setup()
    try:
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            created = await calendar_service.create_event(db, _TENANT, _OTHER, _payload())
        await _mark_synced_from_app(admin_engine, created["id"], "g_single_978")
        out = await _import_one(factory, {"id": "g_single_978", "status": "cancelled"})
        assert out == "deleted"
        assert await _count_rows(admin_engine, "id = :id", {"id": created["id"]}) == 0
    finally:
        await _teardown(admin_engine, app_engine)


# 繰り返しの 1 回だけの消し・直しは、例外の行として DB の決まりに通る（ADR-1075 改訂 2026-11-25）
async def test_google_instance_cancel_and_edit_insert_exceptions_on_real_db():
    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        await _mark_synced_from_app(admin_engine, master["id"], "gm978")
        g_master = _g_master_for(master)
        cancelled = {
            "id": "gm978_20261210T010000Z", "status": "cancelled", "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-10T10:00:00+09:00"},
        }
        assert await _import_one(factory, cancelled, g_master) == "deleted"
        edited = {
            "id": "gm978_20261217T010000Z", "status": "confirmed", "summary": "臨時",
            "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-17T10:00:00+09:00"},
            "start": {"dateTime": "2026-12-17T10:00:00+09:00"},
            "end": {"dateTime": "2026-12-17T11:00:00+09:00"},
        }
        assert await _import_one(factory, edited, g_master) == "upserted"
        rows = sorted(await _exception_rows(admin_engine, master["id"]))
        assert rows == [(False, "synced"), (True, "synced")]
        assert await _count_rows(
            admin_engine,
            "recurring_event_id = :mid AND title = '臨時' AND google_event_id = :gid",
            {"mid": master["id"], "gid": "gm978_20261217T010000Z"},
        ) == 1
        # 同じ知らせがもう一度来ても、何も書かない
        assert await _import_one(factory, cancelled, g_master) == "skipped"
        assert await _import_one(factory, edited, g_master) == "skipped"
    finally:
        await _teardown(admin_engine, app_engine)


# 回の Google の id を持つ行が既にあれば、例外の行を作らずに飛ばす（取り込みを止めない）
async def test_google_instance_with_taken_id_is_skipped_on_real_db():
    from sqlalchemy import text

    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        await _mark_synced_from_app(admin_engine, master["id"], "gm978")
        async with admin_engine.begin() as conn:
            await conn.execute(
                text(
                    f"INSERT INTO {_SCHEMA}.calendar_events"
                    " (title, start_datetime, end_datetime, source, sync_status, google_event_id)"
                    " VALUES ('先にある行', :s, :e, 'google', 'synced', 'gm978_20261224T010000Z')"
                ),
                {
                    "s": datetime(2026, 12, 24, 1, 0, tzinfo=timezone.utc),
                    "e": datetime(2026, 12, 24, 2, 0, tzinfo=timezone.utc),
                },
            )
        cancelled = {
            "id": "gm978_20261224T010000Z", "status": "cancelled", "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-24T10:00:00+09:00"},
        }
        assert await _import_one(factory, cancelled, _g_master_for(master)) == "skipped"
        assert await _exception_rows(admin_engine, master["id"]) == []
    finally:
        await _teardown(admin_engine, app_engine)
