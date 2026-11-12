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
    ("20261112_160000_add_calendar_events_recurrence.sql", True),
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
