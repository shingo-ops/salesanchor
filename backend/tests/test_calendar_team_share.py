"""予定の共有「チーム」の試験（schedule-settings 便2b・設計 design-bin2b.md §3〜§5・受入条件 B1〜B12）。

見え方（一覧・探す・直す・消す）・team_ids の決まりの表・繰り返し・種類の初期のチーム・移行を、実 PostgreSQL で確かめる。
実 PostgreSQL（RLS_ADMIN_DATABASE_URL か TEST_PG_URL と RLS_TEST_DATABASE_URL）があるときだけ動く。
接続はふだんの接続の役（salesanchor_app・RLS あり）で行い、teams・team_members の RLS 越しに見え方が通ることも確かめる。
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

_TENANT = 981
_SCHEMA = f"tenant_{_TENANT}"
_OWNER = 98101  # 予定の持ち主
_MEMBER = 98102  # チーム 1 のメンバー
_OUTSIDER = 98103  # どのチームにも入っていない
_ADMIN_OUT = 98104  # どのチームにも入っていない管理者として呼ぶ
_INACTIVE_MEMBER = 98105  # 使っていないチームのメンバー
_USERS = (_OWNER, _MEMBER, _OUTSIDER, _ADMIN_OUT, _INACTIVE_MEMBER)
_MIGRATION = "20261127_100000_add_calendar_team_share.sql"
_PUBLIC_MIGRATIONS = (
    "076_add_google_calendar_config.sql",
    "077_calendar_sync_mode_and_webhook_subscriptions.sql",
    "20260606_010000_add_google_drive_config.sql",
    "20261016_010000_add_google_config_rls.sql",
)
_RANGE = {"start": "2026-12-01T00:00:00+09:00", "end": "2026-12-31T00:00:00+09:00"}
_READY = {"done": False}
_TYPE_CHECK = "calendar_events_calendar_type_check"
_SHARE_CHECK = "calendar_categories_default_share_check"


def _user(user_id: int):
    return SimpleNamespace(id=user_id, email=f"team-{user_id}@example.com")


async def _cleanup(admin_engine) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_events"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_categories WHERE key LIKE 'custom\\_%'"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.calendar_category_teams"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.team_members"))
        await conn.execute(text(f"DELETE FROM {_SCHEMA}.teams"))
        await conn.execute(
            text(
                f"UPDATE {_SCHEMA}.calendar_categories SET name = NULL, color_key = NULL, is_active = TRUE,"
                " default_share = CASE WHEN key = 'personal' THEN 'self' ELSE 'all' END"
            )
        )


@asynccontextmanager
async def _env():
    """(admin_engine, factory) を返す。終わったら予定・チーム・足した種類を消し、移行の後の形に戻す。"""
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
                for uid in _USERS:
                    await conn.execute(
                        text(
                            "INSERT INTO public.users ("
                            " id, tenant_id, username, email, full_name,"
                            " role, is_active, is_super_admin, locale, theme)"
                            " VALUES (:id, :t, :uname, :email, 'Cal Team', 'admin',"
                            "         TRUE, FALSE, 'ja', 'light')"
                            " ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": uid, "t": _TENANT, "uname": f"cal-team-{uid}", "email": f"cal-team-{uid}@example.com"},
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
            async with admin_engine.begin() as conn:
                await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)
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


async def _exec(admin_engine, sql: str, **params):
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(text(sql.replace("{S}", _SCHEMA)), params)


def _keys(admin: bool):
    return patch("app.routers.calendar.get_user_system_keys", return_value={"owner"} if admin else set())


async def _make_teams(admin_engine) -> dict:
    """チーム 1（営業・メンバー _MEMBER）・チーム 2（仕入・メンバー _OUTSIDER ではなく _ADMIN_OUT は入れない）・
    チーム 3（休止・使っていない・メンバー _INACTIVE_MEMBER）。使っているのはチーム 1 と 2。
    """
    from sqlalchemy import text

    ids: dict = {}
    async with admin_engine.begin() as conn:
        for key, name, active in (("t1", "営業", True), ("t2", "仕入", True), ("t3", "休止", False)):
            ids[key] = (
                await conn.execute(
                    text(f"INSERT INTO {_SCHEMA}.teams (name, is_active) VALUES (:n, :a) RETURNING id"),
                    {"n": name, "a": active},
                )
            ).scalar_one()
        for team_key, uid in (("t1", _MEMBER), ("t3", _INACTIVE_MEMBER)):
            await conn.execute(
                text(f"INSERT INTO {_SCHEMA}.team_members (team_id, user_id) VALUES (:t, :u)"),
                {"t": ids[team_key], "u": uid},
            )
    return ids


async def _create(factory, uid: int = _OWNER, admin: bool = True, **fields) -> int:
    """受け口の作る道（router.create_event）で予定を作って id を返す。"""
    from app.routers import calendar as r

    body = r.CreateEventBody(
        title=fields.pop("title", "試験の予定"),
        start_datetime=fields.pop("start_datetime", "2026-12-03T10:00:00+09:00"),
        end_datetime=fields.pop("end_datetime", "2026-12-03T11:00:00+09:00"),
        **fields,
    )
    db = await _session(factory)
    try:
        with _keys(admin):
            result = await r.create_event(body=body, tenant_id=_TENANT, user=_user(uid), db=db)
    finally:
        await db.close()
    return result["id"]


async def _update(factory, event_id: int, uid: int = _OWNER, admin: bool = True, **fields):
    from app.routers import calendar as r

    body = r.UpdateEventBody(**fields)
    db = await _session(factory)
    try:
        with _keys(admin):
            return await r.update_event(event_id=event_id, body=body, tenant_id=_TENANT, user=_user(uid), db=db)
    finally:
        await db.close()


async def _delete(factory, event_id: int, uid: int = _OWNER, admin: bool = True, **query):
    from app.routers import calendar as r

    db = await _session(factory)
    try:
        with _keys(admin):
            return await r.delete_event(event_id=event_id, tenant_id=_TENANT, user=_user(uid), db=db, **query)
    finally:
        await db.close()


async def _expect(status_code: int, detail, awaitable) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await awaitable
    assert exc.value.status_code == status_code, exc.value.detail
    if detail is not None:
        assert exc.value.detail == detail


async def _list_titles(factory, uid: int) -> list[str]:
    from app.services import calendar_service as cal

    db = await _session(factory)
    try:
        items = await cal.list_events(db, _TENANT, user_id=uid, **_RANGE)
    finally:
        await db.close()
    return sorted({i["title"] for i in items})


async def _search_titles(factory, uid: int, q: str = "試験") -> list[str]:
    from app.services import calendar_service as cal

    db = await _session(factory)
    try:
        items = await cal.list_events(db, _TENANT, user_id=uid, title_query=q, limit=50)
    finally:
        await db.close()
    return sorted({i["title"] for i in items})


async def _see(factory, event_id: int, uid: int) -> bool:
    from app.services import calendar_service as cal

    db = await _session(factory)
    try:
        return await cal.can_see_event(db, event_id, uid)
    finally:
        await db.close()


async def _team_ids_of(admin_engine, event_id: int) -> list[int]:
    return [r[0] for r in await _rows(
        admin_engine, "SELECT team_id FROM {S}.calendar_event_teams WHERE event_id = :i ORDER BY team_id", i=event_id
    )]


async def _field(admin_engine, event_id: int, column: str):
    return (await _rows(admin_engine, f"SELECT {column} FROM {{S}}.calendar_events WHERE id = :i", i=event_id))[0][0]


# ---- B1 見える・見えない（5 人 × 一覧・探す） ----


async def test_b1_visibility_for_five_people_in_list_and_search():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        a = await _create(factory, title="試験A", calendar_type="team", team_ids=[t["t1"]])
        # チーム 3 は使っていない。使っているうちに対応を作ってから使わなくする
        await _exec(admin, "UPDATE {S}.teams SET is_active = TRUE WHERE id = :i", i=t["t3"])
        b = await _create(factory, title="試験B", calendar_type="team", team_ids=[t["t3"]])
        await _exec(admin, "UPDATE {S}.teams SET is_active = FALSE WHERE id = :i", i=t["t3"])
        await _create(factory, title="試験S", calendar_type="shared")
        await _create(factory, title="試験P", calendar_type="personal")
        assert await _team_ids_of(admin, a) == [t["t1"]]
        assert await _team_ids_of(admin, b) == [t["t3"]]

        expected = {
            _OWNER: ["試験A", "試験B", "試験P", "試験S"],  # 持ち主は全部（使っていないチームの予定も）
            _MEMBER: ["試験A", "試験S"],  # チーム 1 のメンバー
            _OUTSIDER: ["試験S"],  # どのチームにも入っていない
            _ADMIN_OUT: ["試験S"],  # メンバーでない管理者も見えない
            _INACTIVE_MEMBER: ["試験S"],  # 使っていないチームのメンバーにも見えない
        }
        for uid, titles in expected.items():
            assert await _list_titles(factory, uid) == titles, uid
            assert await _search_titles(factory, uid) == titles, uid
        assert await _see(factory, a, _MEMBER) and not await _see(factory, a, _OUTSIDER)
        assert await _see(factory, b, _OWNER) and not await _see(factory, b, _INACTIVE_MEMBER)

        # 返す項目 team_ids はチーム予定だけ・id の昇順（ほかは空）
        from app.services import calendar_service as cal

        db = await _session(factory)
        try:
            items = await cal.list_events(db, _TENANT, user_id=_OWNER, **_RANGE)
        finally:
            await db.close()
        by_title = {i["title"]: i["team_ids"] for i in items}
        assert by_title == {"試験A": [t["t1"]], "試験B": [t["t3"]], "試験P": [], "試験S": []}


async def test_owner_is_decided_by_user_id_or_created_by_when_user_id_is_null():
    """user_id が NULL で created_by_user_id が自分の team 予定は、チームに入っていなくても自分に見える。"""
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        await _exec(
            admin,
            "INSERT INTO {S}.calendar_events (title, start_datetime, end_datetime, calendar_type, user_id, created_by_user_id)"
            " VALUES ('試験NULL', '2026-12-04T10:00:00+09:00', '2026-12-04T11:00:00+09:00', 'team', NULL, :o)",
            o=_OWNER,
        )
        eid = (await _rows(admin, "SELECT id FROM {S}.calendar_events WHERE title = '試験NULL'"))[0][0]
        await _exec(admin, "INSERT INTO {S}.calendar_event_teams (event_id, team_id) VALUES (:e, :t)", e=eid, t=t["t2"])
        assert await _list_titles(factory, _OWNER) == ["試験NULL"]
        assert await _list_titles(factory, _OUTSIDER) == []
        assert await _search_titles(factory, _OWNER) == ["試験NULL"]
        assert await _see(factory, eid, _OWNER)


# ---- B2 直す・消すの 404 ----


async def test_b2_non_member_gets_404_even_for_admin_and_member_admin_can_edit():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        eid = await _create(factory, title="試験404", calendar_type="team", team_ids=[t["t1"]])
        for uid, is_admin in ((_OUTSIDER, False), (_ADMIN_OUT, True), (_INACTIVE_MEMBER, True)):
            await _expect(404, "not_found:calendar_event", _update(factory, eid, uid=uid, admin=is_admin, title="x"))
            await _expect(404, "not_found:calendar_event", _delete(factory, eid, uid=uid, admin=is_admin))
        assert await _field(admin, eid, "title") == "試験404"
        # メンバーの管理者は直せる。メンバーでも管理者でも作った人でもなければ 403
        await _update(factory, eid, uid=_MEMBER, admin=True, title="試験404b")
        assert await _field(admin, eid, "title") == "試験404b"
        await _expect(403, None, _update(factory, eid, uid=_MEMBER, admin=False, title="y"))
        await _delete(factory, eid, uid=_MEMBER, admin=True)
        assert await _rows(admin, "SELECT 1 FROM {S}.calendar_events WHERE id = :i", i=eid) == []
        assert await _team_ids_of(admin, eid) == []  # 予定を消すと対応も消える


# ---- B3 繰り返し ----


async def test_b3_recurring_team_event_occurrences_exceptions_and_following_are_visible_to_team():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        master = await _create(factory, title="試験R", calendar_type="team", team_ids=[t["t1"]], recurrence="weekly")
        assert await _team_ids_of(admin, master) == [t["t1"]]
        # 回
        assert await _list_titles(factory, _MEMBER) == ["試験R"]
        assert await _list_titles(factory, _OUTSIDER) == []
        assert await _list_titles(factory, _ADMIN_OUT) == []
        # 「この予定だけ」の例外の行（対応は書かない・見え方は元の行で決まる）
        exc_result = await _update(
            factory, master, title="試験R例外", scope="this", occurrence_start="2026-12-10T10:00:00+09:00"
        )
        exc_id = exc_result["id"]
        assert exc_id != master
        assert await _team_ids_of(admin, exc_id) == []
        assert await _list_titles(factory, _MEMBER) == ["試験R", "試験R例外"]
        assert await _list_titles(factory, _OUTSIDER) == []
        assert await _see(factory, exc_id, _MEMBER) and not await _see(factory, exc_id, _OUTSIDER)
        # 「これ以降」の新しい元の行（元の元の行の対応を写す）
        following = await _update(
            factory, master, title="試験R後半", scope="following", occurrence_start="2026-12-17T10:00:00+09:00"
        )
        new_id = following["id"]
        assert new_id != master
        assert await _team_ids_of(admin, new_id) == [t["t1"]]
        assert await _field(admin, new_id, "calendar_type") == "team"
        titles = await _list_titles(factory, _MEMBER)
        assert "試験R後半" in titles
        assert await _list_titles(factory, _OUTSIDER) == []
        # これ以降でチームを変えると新しい元の行だけが入れ替わる
        following2 = await _update(
            factory, master, title="試験R後半2", scope="following", occurrence_start="2026-12-10T10:00:00+09:00",
            calendar_type="team", team_ids=[t["t2"]],
        )
        assert await _team_ids_of(admin, following2["id"]) == [t["t2"]]
        assert await _team_ids_of(admin, master) == [t["t1"]]


# ---- B4 決まりの表・作るときの確かめ ----


async def test_b4_create_checks_missing_empty_range_unknown_inactive_and_duplicates():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        bad = "invalid_team_ids"
        await _expect(422, bad, _create(factory, calendar_type="team"))  # 送らない
        await _expect(422, bad, _create(factory, calendar_type="team", team_ids=[]))  # 空
        await _expect(422, bad, _create(factory, calendar_type="team", team_ids=[2147483648]))  # int4 の範囲外
        await _expect(422, bad, _create(factory, calendar_type="team", team_ids=[0]))
        await _expect(422, bad, _create(factory, calendar_type="team", team_ids=[-1]))
        await _expect(422, bad, _create(factory, calendar_type="team", team_ids=[999999]))  # 無い id
        await _expect(422, bad, _create(factory, calendar_type="team", team_ids=[t["t1"], t["t3"]]))  # 使っていない
        await _expect(422, bad, _create(factory, calendar_type="shared", team_ids=[t["t1"]]))  # team 以外で空でない
        await _expect(422, bad, _create(factory, calendar_type="personal", team_ids=[t["t1"]]))
        assert await _rows(admin, "SELECT 1 FROM {S}.calendar_events") == []  # どれも書かれていない
        # 重なりは 1 つにまとめる・昇順
        eid = await _create(factory, calendar_type="team", team_ids=[t["t2"], t["t1"], t["t2"]])
        assert await _team_ids_of(admin, eid) == sorted([t["t1"], t["t2"]])
        # team 以外で空の team_ids は通る（対応は書かない）
        sid = await _create(factory, calendar_type="shared", team_ids=[])
        assert await _team_ids_of(admin, sid) == []


async def test_b4_update_table_six_rows():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        bad = "invalid_team_ids"
        eid = await _create(factory, title="試験表", calendar_type="team", team_ids=[t["t1"]])
        # 行 1: 今 team・team か送らない・team_ids 送らない → 通す・対応は今のまま
        await _update(factory, eid, calendar_type="team", title="試験表1")
        assert await _team_ids_of(admin, eid) == [t["t1"]]
        assert await _field(admin, eid, "title") == "試験表1"
        # 行 2: 今 team・1 つ以上 → 送った組に入れ替える
        await _update(factory, eid, team_ids=[t["t2"]])
        assert await _team_ids_of(admin, eid) == [t["t2"]]
        await _update(factory, eid, calendar_type="team", team_ids=[t["t2"], t["t1"]])
        assert await _team_ids_of(admin, eid) == sorted([t["t1"], t["t2"]])
        # 行 3: 決める共有が team で [] → 422・変えない
        await _expect(422, bad, _update(factory, eid, calendar_type="team", team_ids=[]))
        await _expect(422, bad, _update(factory, eid, team_ids=[]))
        assert await _team_ids_of(admin, eid) == sorted([t["t1"], t["t2"]])
        # 範囲外・無い id・使っていない id は 422
        await _expect(422, bad, _update(factory, eid, team_ids=[2147483648]))
        await _expect(422, bad, _update(factory, eid, team_ids=[999999]))
        await _expect(422, bad, _update(factory, eid, team_ids=[t["t3"]]))
        assert await _team_ids_of(admin, eid) == sorted([t["t1"], t["t2"]])
        # 行 6: team 以外（送った）で空でない → 422
        await _expect(422, bad, _update(factory, eid, calendar_type="shared", team_ids=[t["t1"]]))
        assert await _field(admin, eid, "calendar_type") == "team"
        # 行 5: team 以外に変える（team_ids 送らない）→ 通す・対応が消える
        await _update(factory, eid, calendar_type="shared")
        assert await _field(admin, eid, "calendar_type") == "shared"
        assert await _team_ids_of(admin, eid) == []
        # 行 4: 今 team 以外・team にする・team_ids 送らない → 422・変えない
        await _expect(422, bad, _update(factory, eid, calendar_type="team"))
        assert await _field(admin, eid, "calendar_type") == "shared"
        # 今 team 以外で team_ids だけ送る → 決める共有は team 以外なので 422
        await _expect(422, bad, _update(factory, eid, team_ids=[t["t1"]]))
        # 今 team 以外・team にして 1 つ以上 → 通す
        await _update(factory, eid, calendar_type="team", team_ids=[t["t1"]])
        assert await _team_ids_of(admin, eid) == [t["t1"]]
        # 今 team 以外・team 以外のまま・空の team_ids → 通す（空で呼ぶ）
        await _update(factory, eid, calendar_type="personal", team_ids=[])
        assert await _team_ids_of(admin, eid) == []


# ---- B5 外す・入れ替える・team_ids だけ・持ち主だけ ----


async def test_b5_team_ids_only_update_and_owner_only():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        eid = await _create(factory, title="試験B5", calendar_type="team", team_ids=[t["t1"]])
        before_title = await _field(admin, eid, "title")
        # team_ids だけを送った直し（ほかの欄なし）でも入れ替わる
        result = await _update(factory, eid, team_ids=[t["t2"]])
        assert result["id"] == eid
        assert await _team_ids_of(admin, eid) == [t["t2"]]
        assert await _field(admin, eid, "title") == before_title
        # 入れ替えると見える人が変わる
        assert await _list_titles(factory, _MEMBER) == []
        # 持ち主でない人（メンバー・管理者）の team_ids・calendar_type の変更は 403
        await _update(factory, eid, team_ids=[t["t1"]])  # 持ち主が戻す
        for fields in ({"team_ids": [t["t2"]]}, {"calendar_type": "shared"}):
            await _expect(403, "見せ方を変えられるのは予定の持ち主だけです", _update(factory, eid, uid=_MEMBER, admin=True, **fields))
        assert await _team_ids_of(admin, eid) == [t["t1"]]
        assert await _field(admin, eid, "calendar_type") == "team"


async def test_b5_recurring_all_changes_only_team_and_clears_on_leaving_team():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        master = await _create(factory, title="試験B5R", calendar_type="team", team_ids=[t["t1"]], recurrence="weekly")
        exc = (await _update(factory, master, title="試験B5R例外", scope="this", occurrence_start="2026-12-10T10:00:00+09:00"))["id"]
        # 繰り返しの「すべて」で題名を変えずにチームだけ変える
        await _update(factory, master, scope="all", occurrence_start="2026-12-03T10:00:00+09:00", team_ids=[t["t2"]])
        assert await _team_ids_of(admin, master) == [t["t2"]]
        assert await _field(admin, master, "title") == "試験B5R"
        # team 以外に変えると対応が消え、例外の行の見せ方も同じになる
        await _update(factory, master, scope="all", occurrence_start="2026-12-03T10:00:00+09:00", calendar_type="shared")
        assert await _team_ids_of(admin, master) == []
        assert await _field(admin, master, "calendar_type") == "shared"
        assert await _field(admin, exc, "calendar_type") == "shared"
        assert "試験B5R" in await _list_titles(factory, _OUTSIDER)


async def test_single_event_to_recurring_writes_teams():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        eid = await _create(factory, title="試験単発", calendar_type="shared")
        await _update(factory, eid, recurrence="weekly", calendar_type="team", team_ids=[t["t1"]])
        assert await _field(admin, eid, "recurrence_rule") is not None
        assert await _team_ids_of(admin, eid) == [t["t1"]]
        assert await _list_titles(factory, _MEMBER) == ["試験単発"]
        assert await _list_titles(factory, _OUTSIDER) == []


# ---- B11 「この予定だけ」 ----


async def test_b11_this_scope_team_ids_rules():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        master = await _create(factory, title="試験B11", calendar_type="team", team_ids=[t["t1"]], recurrence="weekly")
        occ = "2026-12-10T10:00:00+09:00"
        # ① calendar_type: team を送り team_ids を送らない（画面と同じ）→ 200
        await _update(factory, master, scope="this", occurrence_start=occ, title="b11a", calendar_type="team")
        # ② 今と同じ team_ids → 200
        await _update(factory, master, scope="this", occurrence_start=occ, title="b11b", team_ids=[t["t1"], t["t1"]])
        # ③ 違う team_ids・違う calendar_type → 422 recurrence_this_not_allowed
        await _expect(
            422, "recurrence_this_not_allowed",
            _update(factory, master, scope="this", occurrence_start=occ, title="b11c", team_ids=[t["t2"]]),
        )
        await _expect(
            422, "recurrence_this_not_allowed",
            _update(factory, master, scope="this", occurrence_start=occ, title="b11d", calendar_type="shared"),
        )
        assert await _team_ids_of(admin, master) == [t["t1"]]
        assert await _field(admin, master, "calendar_type") == "team"


# ---- B6 / B12 種類の初期のチーム ----


async def test_b6_b12_category_default_teams():
    from app.routers import calendar as r

    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        db = await _session(factory)
        try:
            bad = "invalid_team_ids"
            admin_user = _user(_OWNER)

            async def create(**kw):
                return await r.create_calendar_category(
                    body=r.CreateCategoryBody(**kw), tenant_id=_TENANT, user=admin_user, db=db
                )

            async def patch_cat(key, **kw):
                return await r.update_calendar_category(
                    key=key, body=r.UpdateCategoryBody(**kw), tenant_id=_TENANT, user=admin_user, db=db
                )

            # 作る: team で 0 個・team 以外で空でない・使っていない・範囲外は 422
            await _expect(422, bad, create(name="営業会議", default_share="team"))
            await _expect(422, bad, create(name="営業会議", default_share="team", default_team_ids=[]))
            await _expect(422, bad, create(name="営業会議", default_share="all", default_team_ids=[t["t1"]]))
            await _expect(422, bad, create(name="営業会議", default_share="team", default_team_ids=[t["t3"]]))
            await _expect(422, bad, create(name="営業会議", default_share="team", default_team_ids=[2147483648]))
            created = await create(name="営業会議", default_share="team", default_team_ids=[t["t2"], t["t1"], t["t1"]])
            key = created["key"]
            assert created["default_share"] == "team"
            assert created["default_team_ids"] == sorted([t["t1"], t["t2"]])
            listed = {c["key"]: c for c in await r.list_calendar_categories(tenant_id=_TENANT, user=admin_user, db=db)}
            assert listed[key]["default_team_ids"] == sorted([t["t1"], t["t2"]])
            assert listed["meeting"]["default_team_ids"] == []

            # B12 ①: PATCH で default_team_ids を送らなければ今の対応のまま（名前だけ・default_share を team のまま）
            await patch_cat(key, name="営業会議2")
            await patch_cat(key, default_share="team")
            assert await _rows(admin, "SELECT category_key, team_id FROM {S}.calendar_category_teams") == [
                (key, t["t1"]),
                (key, t["t2"]),
            ]
            # default_team_ids だけの PATCH は no_fields_to_update にならず入れ替わる
            updated = await patch_cat(key, default_team_ids=[t["t2"]])
            assert updated["default_team_ids"] == [t["t2"]]
            # B12 ②: team で [] は 422（変えない）
            await _expect(422, bad, patch_cat(key, default_share="team", default_team_ids=[]))
            await _expect(422, bad, patch_cat(key, default_team_ids=[]))
            assert await _rows(admin, "SELECT team_id FROM {S}.calendar_category_teams WHERE category_key = :k", k=key) == [(t["t2"],)]
            # B12 ③: 使っていないチームは default_team_ids に入らない（対応は残っていても読むときに外す）
            await patch_cat(key, default_team_ids=[t["t1"], t["t2"]])
            await _exec(admin, "UPDATE {S}.teams SET is_active = FALSE WHERE id = :i", i=t["t1"])
            row = [c for c in await r.list_calendar_categories(tenant_id=_TENANT, user=admin_user, db=db) if c["key"] == key][0]
            assert row["default_team_ids"] == [t["t2"]]
            await _exec(admin, "UPDATE {S}.teams SET is_active = TRUE WHERE id = :i", i=t["t1"])
            # team 以外にすると対応が消える・team 以外で空でない default_team_ids は 422
            await _expect(422, bad, patch_cat(key, default_share="all", default_team_ids=[t["t1"]]))
            await patch_cat(key, default_share="all")
            assert await _rows(admin, "SELECT 1 FROM {S}.calendar_category_teams WHERE category_key = :k", k=key) == []
            # 受け口の値の決まり: team は受ける・それ以外は入力の段階で弾く
            r.UpdateCategoryBody(default_share="team")
            from pydantic import ValidationError

            with pytest.raises(ValidationError):
                r.UpdateCategoryBody(default_share="everyone")
        finally:
            await db.close()


async def test_calendar_teams_endpoint_returns_active_teams_by_name_only():
    from app.routers import calendar as r

    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        db = await _session(factory)
        try:
            # teams.view の無い人も読める道（権限の依存を持たない）
            route = next(x for x in r.router.routes if getattr(x, "path", "") == "/calendar/teams")
            assert "GET" in route.methods
            names = [getattr(d.call, "__name__", "") for d in route.dependant.dependencies]
            assert not any("permission" in n for n in names), names
            result = await r.list_calendar_teams(tenant_id=_TENANT, user=_user(_OUTSIDER), db=db)
        finally:
            await db.close()
        assert result == sorted(
            [{"id": t["t1"], "name": "営業"}, {"id": t["t2"], "name": "仕入"}], key=lambda x: x["name"]
        )
        assert all(set(x) == {"id", "name"} for x in result)


# ---- チームを消す ----


async def test_deleting_a_team_removes_mapping_and_hides_from_former_member_but_not_owner():
    async with _env() as (admin, factory):
        t = await _make_teams(admin)
        eid = await _create(factory, title="試験消", calendar_type="team", team_ids=[t["t1"]])
        assert await _list_titles(factory, _MEMBER) == ["試験消"]
        await _exec(admin, "DELETE FROM {S}.teams WHERE id = :i", i=t["t1"])
        assert await _team_ids_of(admin, eid) == []
        assert await _list_titles(factory, _MEMBER) == []
        assert await _list_titles(factory, _OWNER) == ["試験消"]


# ---- 移行 ----


async def _check_state(admin_engine, table: str, column: str):
    return await _rows(
        admin_engine,
        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint"
        " WHERE conrelid = to_regclass(:t) AND contype = 'c' AND pg_get_constraintdef(oid) ~ :re ORDER BY conname",
        t=f"{_SCHEMA}.{table}",
        re=f"\\m{column}\\M",
    )


async def _to_old_state(admin_engine, events_name: str = _TYPE_CHECK) -> None:
    """移行の前の形に戻す: team を含まない CHECK だけにする（予定の側は名前を選べる）。"""
    async with admin_engine.begin() as conn:
        from sqlalchemy import text

        for table, column in (("calendar_events", "calendar_type"), ("calendar_categories", "default_share")):
            names = (
                await conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint WHERE conrelid = to_regclass(:t)"
                        " AND contype = 'c' AND pg_get_constraintdef(oid) ~ :re"
                    ),
                    {"t": f"{_SCHEMA}.{table}", "re": f"\\m{column}\\M"},
                )
            ).scalars().all()
            for name in names:
                await conn.execute(text(f'ALTER TABLE {_SCHEMA}.{table} DROP CONSTRAINT "{name}"'))
        await conn.execute(
            text(
                f'ALTER TABLE {_SCHEMA}.calendar_events ADD CONSTRAINT "{events_name}"'
                " CHECK (calendar_type IN ('shared', 'personal'))"
            )
        )
        await conn.execute(
            text(
                f"ALTER TABLE {_SCHEMA}.calendar_categories ADD CONSTRAINT {_SHARE_CHECK}"
                " CHECK (default_share IN ('self', 'all'))"
            )
        )


async def test_migration_is_idempotent_and_keeps_one_named_check_with_team_only():
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    async with _env() as (admin, _factory):
        async def state():
            return (
                await _check_state(admin, "calendar_events", "calendar_type"),
                await _check_state(admin, "calendar_categories", "default_share"),
                await _rows(admin, "SELECT to_regclass(:a) IS NOT NULL, to_regclass(:b) IS NOT NULL",
                            a=f"{_SCHEMA}.calendar_event_teams", b=f"{_SCHEMA}.calendar_category_teams"),
            )

        first = await state()
        events_checks, share_checks, tables = first
        assert [c[0] for c in events_checks] == [_TYPE_CHECK]
        assert [c[0] for c in share_checks] == [_SHARE_CHECK]
        assert "team" in events_checks[0][1] and "team" in share_checks[0][1]
        assert tables == [(True, True)]
        async with admin.begin() as conn:
            await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)
        assert await state() == first
        # team は入り、ほかの値は入らない
        insert = text(
            f"INSERT INTO {_SCHEMA}.calendar_events (title, start_datetime, end_datetime, calendar_type)"
            " VALUES ('値', NOW(), NOW() + INTERVAL '1 hour', :c)"
        )
        async with admin.begin() as conn:
            await conn.execute(insert, {"c": "team"})
        with pytest.raises(IntegrityError):
            async with admin.begin() as conn:
                await conn.execute(insert, {"c": "everyone"})
        # 外部キー: 消えたチーム・予定は付けられない
        with pytest.raises(IntegrityError):
            async with admin.begin() as conn:
                await conn.execute(text(f"INSERT INTO {_SCHEMA}.calendar_event_teams (event_id, team_id) VALUES (-1, -1)"))


@pytest.mark.parametrize("old_name", [_TYPE_CHECK, "legacy_calendar_type_chk"])
async def test_migration_replaces_old_check_even_with_another_name_and_keeps_visibility(old_name):
    """移行の前後で shared/personal の行が同じ・3 人それぞれに見える件数が同じ（B7・S8）。名前の違う古い CHECK も入れ替わる。"""
    async with _env() as (admin, factory):
        await _to_old_state(admin, events_name=old_name)
        assert [c[0] for c in await _check_state(admin, "calendar_events", "calendar_type")] == [old_name]
        for title, ctype, uid, created in (
            ("試験S1", "shared", _OWNER, _OWNER),
            ("試験S2", "shared", None, _OWNER),
            ("試験P1", "personal", _OWNER, _OWNER),
            ("試験P2", "personal", _MEMBER, _MEMBER),
        ):
            await _exec(
                admin,
                "INSERT INTO {S}.calendar_events (title, start_datetime, end_datetime, calendar_type, user_id, created_by_user_id)"
                " VALUES (:t, '2026-12-05T10:00:00+09:00', '2026-12-05T11:00:00+09:00', :c, :u, :cb)",
                t=title, c=ctype, u=uid, cb=created,
            )

        async def snapshot():
            rows = await _rows(admin, "SELECT id, title, calendar_type, user_id FROM {S}.calendar_events ORDER BY id")
            counts = {u: await _list_titles(factory, u) for u in (_OWNER, _MEMBER, _ADMIN_OUT)}
            return rows, counts

        before = await snapshot()
        assert {u: len(v) for u, v in before[1].items()} == {_OWNER: 3, _MEMBER: 3, _ADMIN_OUT: 2}
        async with admin.begin() as conn:
            await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)
        assert await snapshot() == before
        assert [c[0] for c in await _check_state(admin, "calendar_events", "calendar_type")] == [_TYPE_CHECK]
        assert [c[0] for c in await _check_state(admin, "calendar_categories", "default_share")] == [_SHARE_CHECK]
        assert "team" in (await _check_state(admin, "calendar_events", "calendar_type"))[0][1]


async def test_migration_skips_rooms_without_teams_table():
    """teams が無い部屋では移行が 2 つの表を作らず飛ばす。部屋は _SCHEMA を使い、取引ごと取り消して元に戻す。"""
    from sqlalchemy import text

    async with _env() as (admin, _factory):
        async with admin.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(text(f"DROP TABLE {_SCHEMA}.calendar_event_teams"))
                await conn.execute(text(f"DROP TABLE {_SCHEMA}.calendar_category_teams"))
                await conn.execute(text(f"ALTER TABLE {_SCHEMA}.teams RENAME TO teams_hidden_for_skip_test"))
                await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)
                created = (
                    await conn.execute(
                        text("SELECT to_regclass(:a), to_regclass(:b)"),
                        {"a": f"{_SCHEMA}.calendar_event_teams", "b": f"{_SCHEMA}.calendar_category_teams"},
                    )
                ).one()
                assert created[0] is None and created[1] is None
            finally:
                await trans.rollback()
        # 取り消したあと、ほかの試験を壊していない（3 つの表が在る）
        assert await _rows(
            admin,
            "SELECT to_regclass(:a) IS NOT NULL, to_regclass(:b) IS NOT NULL, to_regclass(:c) IS NOT NULL",
            a=f"{_SCHEMA}.teams", b=f"{_SCHEMA}.calendar_event_teams", c=f"{_SCHEMA}.calendar_category_teams",
        ) == [(True, True, True)]
