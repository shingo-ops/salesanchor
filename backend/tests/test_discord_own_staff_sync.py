"""自社用 Discord サーバーのスタッフのロールの付け外し（discord-server-management 第2段 2b）の試験。

Discord への呼び出しは作り物に差し替える（本物の Discord には繋がない）。表は conftest の SQLite 版を使う。
"""
from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.routers.staff import _RETIRE_MEMBER_SQL
from app.services import discord_own_staff_sync
from app.services.discord_blueprint import BLUEPRINT_DIR, Blueprint, build_plan
from app.services.discord_rest import DiscordAPIError
from tests.test_discord_own_server_plan import _BOT_ROLE, _production_channels, _production_roles
from tests.test_discord_own_server_plan import _G as _PLAN_GUILD

_TENANT = 7
_OTHER_TENANT = 8
_G = "222222222222222222"
_C = "333333333333333333"
_OTHER_G = "444444444444444444"
_STAFF_ROLE = "700"
_SALES_ROLE = "901"
_RETIRED_ROLE = "950"
_HAND_MADE = "999"
_U1 = "111111111111111101"
_U2 = "111111111111111102"
_MODULE = "app.services.discord_own_staff_sync"


class FakeDiscord:
    """呼ばれた (method, path) を全部残す Discord の作り物。"""

    def __init__(self, members: dict[str, list[str]] | None = None, guild_roles: list[dict] | None = None,
                 fail: dict[tuple[str, str], DiscordAPIError] | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.members = members or {}
        self.guild_roles = guild_roles or []
        self.fail = fail or {}

    async def __call__(self, **kwargs):
        method, path = kwargs["method"], kwargs["path"]
        self.calls.append((method, path))
        if (method, path) in self.fail:
            raise self.fail[(method, path)]
        if method == "GET" and "/members/" in path:
            user = path.rsplit("/", 1)[1]
            if user in self.members:
                return {"roles": list(self.members[user])}
            raise DiscordAPIError("x", status_code=404)
        if method == "GET" and path.endswith("/roles"):
            return list(self.guild_roles)
        return None

    def sent(self, method: str) -> list[str]:
        return [p for m, p in self.calls if m == method]


def _blueprint_file(tmp_path, staff_discord_id: str | None = _STAFF_ROLE):
    data = json.loads((BLUEPRINT_DIR / "tenant_1.json").read_text(encoding="utf-8"))
    for role in data["roles"]:
        if role["key"] == "staff":
            role["discord_id"] = staff_discord_id
    path = tmp_path / "tenant_7.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


@pytest_asyncio.fixture
async def factory(test_engine, setup_test_db):
    maker = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    await _clean(maker)
    yield maker
    await _clean(maker)


async def _clean(maker) -> None:
    async with maker() as s:
        for table in (
            "user_roles", "roles", "staff", "discord_retired_roles", "discord_retired_members",
            "tenant_discord_config",
        ):
            await s.execute(text("DELETE " + "FROM " + table))
        await s.commit()


async def _seed(
    maker,
    *,
    staff: list[tuple[int, str, str]] | None = None,
    sales_for: list[int] | None = None,
    retired_roles: list[str] | None = None,
    retired_members: list[tuple[str, bool]] | None = None,
    configs: list[tuple[int, str, str]] | None = None,
) -> None:
    async with maker() as s:
        await s.execute(text(
            "INSERT INTO roles (id, tenant_id, name, priority, is_system, discord_role_id)"
            " VALUES (1, 999, '営業', 10, FALSE, :d)"
        ), {"d": _SALES_ROLE})
        for user_id, did, status in staff or []:
            await s.execute(text(
                "INSERT INTO staff (tenant_id, user_id, staff_code, surname_jp, given_name_jp, discord_user_id, status)"
                " VALUES (999, :u, :c, '山田', '太郎', :d, :st)"
            ), {"u": user_id, "c": f"S{user_id}", "d": did, "st": status})
        for user_id in sales_for or []:
            await s.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, 1)"), {"u": user_id})
        for role_id in retired_roles or []:
            await s.execute(text("INSERT INTO discord_retired_roles (discord_role_id) VALUES (:r)"), {"r": role_id})
        for did, kick in retired_members or []:
            await s.execute(
                text("INSERT INTO discord_retired_members (discord_user_id, kick) VALUES (:d, :k)"),
                {"d": did, "k": kick},
            )
        for tenant_id, purpose, guild_id in configs if configs is not None else [(_TENANT, "own", _G)]:
            await s.execute(
                text("INSERT INTO tenant_discord_config (tenant_id, purpose, guild_id) VALUES (:t, :p, :g)"),
                {"t": tenant_id, "p": purpose, "g": guild_id},
            )
        await s.commit()


async def _retired_rows(maker) -> list[tuple]:
    async with maker() as s:
        return [tuple(r) for r in (await s.execute(
            text("SELECT discord_user_id, kick FROM discord_retired_members ORDER BY discord_user_id")
        )).all()]


async def _run(maker, tmp_path, fake: FakeDiscord, *, staff_discord_id: str | None = _STAFF_ROLE,
               redis_client=None, tenant_id: int = _TENANT) -> dict:
    bp = _blueprint_file(tmp_path, staff_discord_id)
    with (
        patch(f"{_MODULE}.discord_api_request", fake),
        patch(f"{_MODULE}.set_tenant_context", AsyncMock(return_value=None)),
        patch(f"{_MODULE}.reset_tenant_context", AsyncMock(return_value=None)),
        patch(f"{_MODULE}.blueprint_path", lambda tid: bp),
    ):
        return await discord_own_staff_sync.sync_own_server_staff_roles(
            tenant_id, redis_client=redis_client, session_factory=maker,
        )


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")


def _member(did: str) -> str:
    return f"/guilds/{_G}/members/{did}"


def _no_all_members_list(fake: FakeDiscord) -> None:
    assert [p for m, p in fake.calls if m == "GET" and p.endswith(f"/guilds/{_G}/members")] == []


# ── 点検の処理 ──


@pytest.mark.asyncio
async def test_active_staff_gets_app_role_and_staff(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")], sales_for=[1])
    fake = FakeDiscord(members={_U1: [_HAND_MADE]})

    result = await _run(factory, tmp_path, fake)

    assert sorted(fake.sent("PUT")) == sorted([
        f"{_member(_U1)}/roles/{_SALES_ROLE}", f"{_member(_U1)}/roles/{_STAFF_ROLE}",
    ])
    assert fake.sent("DELETE") == []
    assert result["added"] == 2
    _no_all_members_list(fake)


@pytest.mark.asyncio
async def test_removed_app_role_is_taken_off_but_hand_made_stays(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")])
    fake = FakeDiscord(members={_U1: [_SALES_ROLE, _STAFF_ROLE, _HAND_MADE]})

    result = await _run(factory, tmp_path, fake)

    assert fake.sent("DELETE") == [f"{_member(_U1)}/roles/{_SALES_ROLE}"]
    assert fake.sent("PUT") == []
    assert result["removed"] == 1


@pytest.mark.asyncio
async def test_retired_role_is_taken_off(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")], retired_roles=[_RETIRED_ROLE])
    fake = FakeDiscord(members={_U1: [_RETIRED_ROLE, _STAFF_ROLE]})

    await _run(factory, tmp_path, fake)

    assert fake.sent("DELETE") == [f"{_member(_U1)}/roles/{_RETIRED_ROLE}"]


@pytest.mark.asyncio
async def test_inactive_staff_loses_managed_roles_only(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "inactive")], sales_for=[1])
    fake = FakeDiscord(members={_U1: [_SALES_ROLE, _STAFF_ROLE, _HAND_MADE]})

    await _run(factory, tmp_path, fake)

    assert sorted(fake.sent("DELETE")) == sorted([
        f"{_member(_U1)}/roles/{_SALES_ROLE}", f"{_member(_U1)}/roles/{_STAFF_ROLE}",
    ])
    assert f"/guilds/{_G}/members/{_U1}" not in fake.sent("DELETE")
    assert fake.sent("PUT") == []


@pytest.mark.asyncio
async def test_deleted_staff_is_kicked_after_roles(factory, tmp_path):
    await _seed(factory, retired_members=[(_U1, True)])
    fake = FakeDiscord(members={_U1: [_STAFF_ROLE, _HAND_MADE]})

    result = await _run(factory, tmp_path, fake)

    assert fake.calls == [
        ("GET", _member(_U1)),
        ("DELETE", f"{_member(_U1)}/roles/{_STAFF_ROLE}"),
        ("DELETE", _member(_U1)),
    ]
    assert result["kicked"] == 1
    assert await _retired_rows(factory) == []


@pytest.mark.asyncio
async def test_changed_id_only_loses_roles(factory, tmp_path):
    await _seed(factory, retired_members=[(_U1, False)])
    fake = FakeDiscord(members={_U1: [_STAFF_ROLE, _HAND_MADE]})

    await _run(factory, tmp_path, fake)

    assert fake.sent("DELETE") == [f"{_member(_U1)}/roles/{_STAFF_ROLE}"]
    assert await _retired_rows(factory) == []


@pytest.mark.asyncio
async def test_reregistered_id_is_treated_as_staff(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")], retired_members=[(_U1, True)])
    fake = FakeDiscord(members={_U1: []})

    await _run(factory, tmp_path, fake)

    assert _member(_U1) not in fake.sent("DELETE")
    assert await _retired_rows(factory) == []
    assert fake.sent("PUT") == [f"{_member(_U1)}/roles/{_STAFF_ROLE}"]


@pytest.mark.asyncio
async def test_member_not_in_server_is_skipped(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")], retired_members=[(_U2, True)])
    fake = FakeDiscord(members={})

    result = await _run(factory, tmp_path, fake)

    assert fake.sent("PUT") == []
    assert fake.sent("DELETE") == []
    assert await _retired_rows(factory) == []
    assert result["skipped"] == 2


@pytest.mark.asyncio
async def test_transient_kick_failure_keeps_row(factory, tmp_path):
    await _seed(factory, retired_members=[(_U1, True)])
    fake = FakeDiscord(members={_U1: []}, fail={("DELETE", _member(_U1)): DiscordAPIError("x", status_code=500)})

    result = await _run(factory, tmp_path, fake)

    assert result["failed"] == 1
    assert await _retired_rows(factory) == [(_U1, 1)]


@pytest.mark.asyncio
async def test_permanent_kick_failure_drops_row(factory, tmp_path):
    await _seed(factory, retired_members=[(_U1, True)])
    fake = FakeDiscord(members={_U1: []}, fail={("DELETE", _member(_U1)): DiscordAPIError("x", status_code=403)})

    result = await _run(factory, tmp_path, fake)

    assert result["failed"] == 1
    assert await _retired_rows(factory) == []


@pytest.mark.asyncio
async def test_staff_role_missing_stops(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")])

    fake = FakeDiscord(members={_U1: []}, guild_roles=[])
    result = await _run(factory, tmp_path, fake, staff_discord_id=None)
    assert result["reason"] == "staff_role_missing"
    assert fake.sent("PUT") == [] and fake.sent("DELETE") == []

    fake = FakeDiscord(
        members={_U1: []},
        guild_roles=[{"id": "701", "name": "スタッフ"}, {"id": "702", "name": "スタッフ"}],
    )
    result = await _run(factory, tmp_path, fake, staff_discord_id=None)
    assert result["reason"] == "staff_role_ambiguous"
    assert fake.sent("PUT") == [] and fake.sent("DELETE") == []

    fake = FakeDiscord(members={_U1: []}, guild_roles=[{"id": "701", "name": "スタッフ"}])
    await _run(factory, tmp_path, fake, staff_discord_id=None)
    assert fake.sent("PUT") == [f"{_member(_U1)}/roles/701"]


@pytest.mark.asyncio
async def test_no_own_server_does_nothing(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")], configs=[(_TENANT, "customer", _C)])
    fake = FakeDiscord(members={_U1: []})

    result = await _run(factory, tmp_path, fake)

    assert fake.calls == []
    assert result["reason"] == "no_own_server"


@pytest.mark.asyncio
async def test_other_tenant_is_not_touched(factory, tmp_path):
    await _seed(
        factory, staff=[(1, _U1, "active")],
        configs=[(_TENANT, "own", _G), (_OTHER_TENANT, "own", _OTHER_G)],
    )
    fake = FakeDiscord(members={_U1: []})

    await _run(factory, tmp_path, fake)

    assert fake.calls
    assert all(path.startswith(f"/guilds/{_G}/") for _, path in fake.calls)


@pytest.mark.asyncio
async def test_never_lists_all_members(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")], retired_members=[(_U2, True)])
    fake = FakeDiscord(members={_U1: [], _U2: [_STAFF_ROLE]})

    await _run(factory, tmp_path, fake)

    _no_all_members_list(fake)
    assert not any(p.endswith("/members") for _, p in fake.calls)


@pytest.mark.asyncio
async def test_bad_discord_id_is_skipped(factory, tmp_path):
    await _seed(factory, staff=[(1, "abc", "active")])
    fake = FakeDiscord()

    result = await _run(factory, tmp_path, fake)

    assert fake.calls == []
    assert result["skipped"] == 1


@pytest.mark.asyncio
async def test_lock_taken_does_nothing(factory, tmp_path):
    await _seed(factory, staff=[(1, _U1, "active")])
    fake = FakeDiscord(members={_U1: []})
    taken = SimpleNamespace(set=AsyncMock(return_value=False), delete=AsyncMock(return_value=1))

    result = await _run(factory, tmp_path, fake, redis_client=taken)

    assert fake.calls == []
    assert result["reason"] == "locked"
    taken.delete.assert_not_called()

    free = SimpleNamespace(set=AsyncMock(return_value=True), delete=AsyncMock(return_value=1))
    await _run(factory, tmp_path, fake, redis_client=free)
    assert free.delete.await_count == 1


@pytest.mark.asyncio
async def test_no_token_does_nothing(factory, tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    await _seed(factory, staff=[(1, _U1, "active")])
    fake = FakeDiscord(members={_U1: []})

    result = await _run(factory, tmp_path, fake)

    assert result["reason"] == "no_token"
    assert fake.calls == []


# ── 書く所（スタッフ・役割のルーター） ──


async def _seed_role(db_session):
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (1, 999, 'staff', '#888888', 0, FALSE)
    """))
    # 操作する側（テストユーザー 999）に priority=1000 のロールを user_roles 経由で付与する
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (2, 999, 'actor', '#000000', 1000, FALSE)
    """))
    await db_session.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (999, 2)"))
    await db_session.commit()


def _body(email: str, **extra):
    return {
        "surname_jp": "山田", "given_name_jp": "太郎",
        "surname_en": "Yamada", "given_name_en": "Taro",
        "primary_email": email, "role_id": 1, **extra,
    }


@pytest.fixture
def scheduled(monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(discord_own_staff_sync, "schedule_own_staff_sync", lambda tenant_id: calls.append(tenant_id))
    return calls


async def _retired(db_session) -> list[tuple]:
    res = await db_session.execute(
        text("SELECT discord_user_id, kick FROM discord_retired_members ORDER BY discord_user_id")
    )
    return [(r[0], bool(r[1])) for r in res.all()]


@pytest.mark.asyncio
async def test_delete_staff_with_discord_id_inserts_kick_row(client, db_session, scheduled):
    await _seed_role(db_session)
    created = await client.post("/api/v1/staff", json=_body("kick1@example.com", discord_user_id=_U1))
    assert created.status_code == 201, created.text
    before = len(scheduled)

    with patch("app.routers.staff.record_audit_log", AsyncMock()) as audit:
        res = await client.delete(f"/api/v1/staff/{created.json()['id']}")

    assert res.status_code == 204, res.text
    assert await _retired(db_session) == [(_U1, True)]
    assert len(scheduled) == before + 1
    kicks = [c for c in audit.call_args_list
             if c.kwargs.get("table_name") == "discord_guild_member" and c.kwargs.get("action") == "delete"]
    assert len(kicks) == 1


@pytest.mark.asyncio
async def test_delete_staff_without_discord_id_inserts_nothing(client, db_session, scheduled):
    await _seed_role(db_session)
    created = await client.post("/api/v1/staff", json=_body("kick2@example.com"))
    assert created.status_code == 201, created.text

    with patch("app.routers.staff.record_audit_log", AsyncMock()) as audit:
        res = await client.delete(f"/api/v1/staff/{created.json()['id']}")

    assert res.status_code == 204, res.text
    assert await _retired(db_session) == []
    assert [c for c in audit.call_args_list if c.kwargs.get("table_name") == "discord_guild_member"] == []


@pytest.mark.asyncio
async def test_delete_twice_same_id_does_not_fail(client, db_session, scheduled):
    await _seed_role(db_session)
    created = await client.post("/api/v1/staff", json=_body("kick3@example.com", discord_user_id=_U1))
    assert created.status_code == 201, created.text
    await db_session.execute(
        text("INSERT INTO discord_retired_members (discord_user_id, kick) VALUES (:d, :k)"),
        {"d": _U1, "k": False},
    )
    await db_session.commit()

    res = await client.delete(f"/api/v1/staff/{created.json()['id']}")

    assert res.status_code == 204, res.text
    assert await _retired(db_session) == [(_U1, True)]


@pytest.mark.asyncio
async def test_patch_changed_id_inserts_non_kick_row(client, db_session, scheduled):
    await _seed_role(db_session)
    with_id = await client.post("/api/v1/staff", json=_body("patch1@example.com", discord_user_id=_U1))
    without_id = await client.post("/api/v1/staff", json=_body("patch2@example.com"))
    assert with_id.status_code == 201 and without_id.status_code == 201

    res = await client.patch(f"/api/v1/staff/{with_id.json()['id']}", json={"discord_user_id": _U2})
    assert res.status_code == 200, res.text
    assert await _retired(db_session) == [(_U1, False)]

    same = await client.patch(f"/api/v1/staff/{with_id.json()['id']}", json={"discord_user_id": _U2})
    assert same.status_code == 200, same.text
    first_time = await client.patch(f"/api/v1/staff/{without_id.json()['id']}", json={"discord_user_id": _U1})
    assert first_time.status_code == 200, first_time.text
    assert await _retired(db_session) == [(_U1, False)]


@pytest.mark.asyncio
async def test_patch_does_not_downgrade_kick(db_session):
    await db_session.execute(_RETIRE_MEMBER_SQL, {"did": _U1, "kick": True})
    await db_session.execute(_RETIRE_MEMBER_SQL, {"did": _U1, "kick": False})
    await db_session.commit()

    assert await _retired(db_session) == [(_U1, True)]


@pytest.mark.asyncio
async def test_role_writes_schedule_sync(client, db_session, scheduled):
    await _seed_role(db_session)
    created = await client.post("/api/v1/staff", json=_body("roles1@example.com"))
    assert created.status_code == 201, created.text
    user_id = created.json()["user_id"]
    before = len(scheduled)

    put = await client.put(f"/api/v1/users/{user_id}/roles", json={"role_ids": [1]})
    assert put.status_code == 200, put.text
    assert len(scheduled) == before + 1

    role = await client.post("/api/v1/roles", json={"name": "消す役割", "priority": 10, "color": "#123456"})
    assert role.status_code == 201, role.text
    before = len(scheduled)
    deleted = await client.delete(f"/api/v1/roles/{role.json()['id']}")
    assert deleted.status_code == 204, deleted.text
    assert len(scheduled) == before + 1


# ── 設計図と定期作業 ──


def test_tenant_1_blueprint_creates_staff_role_once():
    data = json.loads((BLUEPRINT_DIR / "tenant_1.json").read_text(encoding="utf-8"))
    plan = build_plan(
        Blueprint.model_validate(data), _production_roles(), _production_channels(), _PLAN_GUILD, [_BOT_ROLE],
    )

    # ADR-1068 で、スタッフ登録のカテゴリ 1 つと「スタッフ受付」の部屋 1 つが「作る」に増えた
    assert plan["changes"][0]["kind"] == "create_role"
    assert plan["changes"][0]["name"] == "スタッフ"
    assert sorted(c["kind"] for c in plan["changes"][1:]) == (
        ["create_category"] + ["create_channel"] * 4
    )
    assert sorted(c["name"] for c in plan["changes"][1:] if c["kind"] == "create_channel") == sorted(
        ["アサイン連絡", "返信連絡", "部屋の外の書き込み", "スタッフ受付"]
    )
    assert [c["name"] for c in plan["changes"] if c["kind"] == "create_category"] == ["スタッフ登録"]
    assert len(plan["changes"]) == 6
    assert plan["blocked"] == []


def test_beat_schedule_runs_every_5_minutes():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["discord-own-staff-sync"]
    assert entry["task"] == "app.tasks.discord_own_staff_sync.sync_all_own_servers"
    assert entry["schedule"] == 300.0
    assert "app.tasks.discord_own_staff_sync" in celery_app.conf.include


def test_schedule_is_noop_without_token(monkeypatch):
    monkeypatch.setattr(discord_own_staff_sync, "SCHEDULE_ENABLED", True)
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)

    discord_own_staff_sync.schedule_own_staff_sync(1)

    assert discord_own_staff_sync._pending == set()
