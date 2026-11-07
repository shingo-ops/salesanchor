"""スタッフ自己登録の Discord 受付（ADR-1068 2回目・設計 §4-3）の試験。

非 PG: Discord・Redis・DB をモックして、振り分け・回数制限・既に登録済み・管理者ロールなし・個室の失敗・
       commit 後の投稿失敗・片付け・専用スクリプト・部屋の見える人。
PG（CI の使い捨て DB。pg fixture）: 番号が合ったときの users・staff・招待の書き込みと、各失敗で何も変わらないこと。
テストデータはすべて架空。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import discord  # 他の試験の discord 差し替えより先に実物を読み込む
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app import staff_join_discord_cli
from app.auth.viewer_signup_code import normalize_signup_code, signup_code_sha256
from app.discord_gateway import private_channel, staff_join, ticket_channel_creator, viewer_trial
from app.discord_gateway import staff_join_texts as T
from app.discord_gateway.client import JarvisDiscordClient
from tests.rls_bootstrap import _ensure_public_users
from tests.test_super_admin_viewers import needs_ci_pg
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_viewer_discord_trial import _guild, _interaction, _member, _Redis, _text_channel

GUILD_ID = 111222333444555666
TENANT_ID = 907
CODE = "ABCD-EFGH-JKMN-PQRS"
MODAL_ID = T.CODE_MODAL_CUSTOM_ID


def _components(value: str):
    return [{"type": 1, "components": [{"type": 4, "custom_id": T.CODE_INPUT_CUSTOM_ID, "value": value}]}]


def _submit_interaction(channel=None, *, uid: int = 777, code: str = CODE):
    return _interaction(MODAL_ID, guild=_guild(channel), user=_member(uid), components=_components(code))


# ── 非 PG の作り物 ────────────────────────────────────────────


class _Rows:
    def __init__(self, rows) -> None:
        self._rows = list(rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


def _dispatch(*, registered=False, roles=("4001",), invite=(11, 5001, 7001), person=("new@example.com", None), other=False):
    """SQL の中身で返す行を決める（呼ばれる順に頼らない）。"""

    def _execute(stmt, params=None):
        sql = str(stmt)
        if "FROM roles r" in sql:
            return _Rows([(r,) for r in roles])
        if "FOR UPDATE" in sql:
            return _Rows([invite] if invite else [])
        if "JOIN staff s ON" in sql:
            return _Rows([person] if person else [])
        if "id <> :sid" in sql:
            return _Rows([(1,)] if other else [])
        if "SELECT 1 FROM staff WHERE discord_user_id = :uid LIMIT 1" in sql:
            return _Rows([(1,)] if registered else [])
        return _Rows([])  # UPDATE

    return _execute


def _factory(execute) -> MagicMock:
    session = MagicMock()
    session.execute = AsyncMock(side_effect=execute)
    session.rollback = AsyncMock()
    session.commit = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    factory.session = session
    return factory


def _sqls(factory) -> list[str]:
    return [str(c.args[0]) for c in factory.session.execute.await_args_list]


@pytest.fixture
def mocked(monkeypatch):
    """会社の文脈・カテゴリ・ハッシュ・ロール合わせを差し替える（非 PG の試験用）。"""
    for name in ("set_tenant_context", "reset_tenant_context", "clear_tenant_context"):
        monkeypatch.setattr(staff_join, name, AsyncMock())
    monkeypatch.setattr(staff_join, "hash_password", lambda p: "$argon2id$fake")
    sync = MagicMock()
    monkeypatch.setattr(staff_join, "schedule_own_staff_sync", sync)
    monkeypatch.setattr(
        staff_join, "_resolve_rooms_category", AsyncMock(return_value=MagicMock(spec=discord.CategoryChannel))
    )
    return sync


def _client() -> JarvisDiscordClient:
    client = JarvisDiscordClient(database_url="postgresql://unused")
    client._db_factory = MagicMock()
    return client


# ── 非 PG: 振り分け（KGI 13）──────────────────────────────────


async def test_on_interaction_routes_staff_join_prefix_and_not_ticket():
    it = _interaction(MODAL_ID)
    it.type = discord.InteractionType.modal_submit
    with patch.object(staff_join, "handle_interaction", new=AsyncMock()) as handle, patch.object(
        ticket_channel_creator, "get_or_create_ticket_channel", new=AsyncMock()
    ) as ticket, patch.object(viewer_trial, "handle_interaction", new=AsyncMock()) as viewer:
        await _client().on_interaction(it)
    handle.assert_awaited_once()
    ticket.assert_not_awaited()
    viewer.assert_not_awaited()


async def test_ticket_open_still_goes_to_ticket_flow():
    it = _interaction("ticket_open", guild=None, user=MagicMock())
    it.type = discord.InteractionType.component
    with patch.object(staff_join, "handle_interaction", new=AsyncMock()) as handle:
        await _client().on_interaction(it)
    handle.assert_not_awaited()
    it.followup.send.assert_awaited_once()  # 顧客用の流れ（GUILD_ONLY）に入った


async def test_customer_guild_does_not_run_staff_join():
    """お客様のサーバー（purpose='customer'）の guild は own の表に無く、何も動かない。"""
    it = _interaction(T.OPEN_BUTTON_CUSTOM_ID, guild=_guild(), user=_member())
    factory = _factory(lambda stmt, params=None: _Rows([]))
    with patch.object(staff_join, "on_open", new=AsyncMock()) as on_open:
        await staff_join.handle_interaction(it, factory)
    on_open.assert_not_awaited()
    it.response.send_message.assert_awaited_once_with(T.WRONG_SERVER, ephemeral=True)
    sql = _sqls(factory)[0]
    assert "purpose = 'own'" in sql and "customer" not in sql


async def test_open_button_sends_modal_for_own_guild():
    it = _interaction(T.OPEN_BUTTON_CUSTOM_ID, guild=_guild(), user=_member())
    factory = _factory(lambda stmt, params=None: _Rows([(TENANT_ID,)]))
    await staff_join.handle_interaction(it, factory)
    modal = it.response.send_modal.await_args.args[0]
    assert isinstance(modal, staff_join.StaffJoinCodeModal)
    assert modal.custom_id == T.CODE_MODAL_CUSTOM_ID
    field = modal.children[0]
    assert field.custom_id == T.CODE_INPUT_CUSTOM_ID
    assert (field.min_length, field.max_length, field.required) == (16, 19, True)


def test_texts_are_within_limits_and_prefixed():
    assert len(T.OPEN_BUTTON_LABEL) <= 80 and len(T.CODE_MODAL_TITLE) <= 45 and len(T.CODE_INPUT_LABEL) <= 45
    for cid in (T.OPEN_BUTTON_CUSTOM_ID, T.CODE_MODAL_CUSTOM_ID, T.CODE_INPUT_CUSTOM_ID):
        assert cid.startswith(T.CUSTOM_ID_PREFIX)
    payload = T.reception_message_payload()
    button = payload["components"][0]["components"][0]
    assert (button["type"], button["style"], button["custom_id"]) == (2, 1, T.OPEN_BUTTON_CUSTOM_ID)
    assert payload is not T.reception_message_payload()
    assert T.ROOM_TOPIC.format(invite_id=3) == "スタッフ登録（招待 3）"
    assert T.ROOM_NAME.format(invite_id=3) == "staff-join-3"


def test_login_url_follows_frontend_base_url(monkeypatch):
    monkeypatch.delenv("FRONTEND_BASE_URL", raising=False)
    assert T.login_url() == "https://app.salesanchor.jp/login"
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://x.example/")
    assert T.login_url() == "https://x.example/login"
    text_ = T.room_welcome("a@example.com", "pw-1")
    assert "a@example.com" in text_ and "`pw-1`" in text_ and "https://x.example/login" in text_
    assert "最初のログインで変更してください" in text_


# ── 非 PG: 回数制限（KGI 6）──────────────────────────────────


async def test_sixth_attempt_is_refused_after_five_failures(mocked):
    redis = _Redis()
    factory = _factory(_dispatch(invite=None))
    with patch.object(staff_join, "get_redis", return_value=redis):
        for _ in range(5):
            it = _submit_interaction()
            await staff_join.on_code_submit(it, factory, TENANT_ID)
            it.followup.send.assert_awaited_once_with(T.CODE_INVALID, ephemeral=True)
        assert redis.store["staff_code_fail:777"] == 5
        assert redis.expire_calls == [("staff_code_fail:777", 3600)]
        calls_before = factory.session.execute.await_count
        it = _submit_interaction()
        await staff_join.on_code_submit(it, factory, TENANT_ID)
    it.followup.send.assert_awaited_once_with(T.TOO_MANY_ATTEMPTS, ephemeral=True)
    assert factory.session.execute.await_count == calls_before  # 6回目は DB に触れない


async def test_malformed_code_counts_without_db(mocked):
    redis = _Redis()
    it = _submit_interaction(code="ABCD-EFGH-JKMN-PQRI")
    with patch.object(staff_join, "get_redis", return_value=redis):
        await staff_join.on_code_submit(it, MagicMock(side_effect=AssertionError("DB")), TENANT_ID)
    it.followup.send.assert_awaited_once_with(T.CODE_INVALID, ephemeral=True)
    assert redis.store["staff_code_fail:777"] == 1


async def test_redis_none_is_try_later(mocked):
    it = _submit_interaction()
    with patch.object(staff_join, "get_redis", return_value=None):
        await staff_join.on_code_submit(it, MagicMock(side_effect=AssertionError("DB")), TENANT_ID)
    it.followup.send.assert_awaited_once_with(T.TRY_LATER, ephemeral=True)


# ── 非 PG: 照合の前に見る2つ（KGI 7・R7）──────────────────────


async def test_already_registered_does_not_create_room_or_count(mocked):
    redis = _Redis()
    channel = _text_channel(9001)
    it = _submit_interaction(channel)
    factory = _factory(_dispatch(registered=True))
    with patch.object(staff_join, "get_redis", return_value=redis):
        await staff_join.on_code_submit(it, factory, TENANT_ID)
    it.followup.send.assert_awaited_once_with(T.ALREADY_REGISTERED, ephemeral=True)
    it.guild.create_text_channel.assert_not_awaited()
    factory.session.commit.assert_not_awaited()
    assert "staff_code_fail:777" not in redis.store
    assert not any("FOR UPDATE" in s for s in _sqls(factory))  # 番号の照合まで進まない


async def test_no_admin_role_changes_nothing_and_does_not_count(mocked):
    redis = _Redis()
    it = _submit_interaction(_text_channel(9001))
    factory = _factory(_dispatch(roles=()))
    with patch.object(staff_join, "get_redis", return_value=redis):
        await staff_join.on_code_submit(it, factory, TENANT_ID)
    it.followup.send.assert_awaited_once_with(T.NOT_READY, ephemeral=True)
    it.guild.create_text_channel.assert_not_awaited()
    factory.session.commit.assert_not_awaited()
    assert "staff_code_fail:777" not in redis.store
    assert not any(s.lstrip().startswith("UPDATE") for s in _sqls(factory))


async def test_admin_roles_query_uses_staff_create_and_permission_tables(mocked):
    factory = _factory(_dispatch(invite=None))
    with patch.object(staff_join, "get_redis", return_value=_Redis()):
        await staff_join.on_code_submit(_submit_interaction(), factory, TENANT_ID)
    sql = next(s for s in _sqls(factory) if "FROM roles r" in s)
    assert "role_permissions" in sql and "public.permissions" in sql and "'staff.create'" in sql
    assert "discord_role_id IS NOT NULL" in sql


# ── 非 PG: 書き込みと失敗 ─────────────────────────────────────


async def test_match_creates_room_for_member_and_admin_roles_then_syncs(mocked):
    redis = _Redis()
    channel = _text_channel(9001)
    it = _submit_interaction(channel)
    factory = _factory(_dispatch(roles=("4001", "4002")))
    with patch.object(staff_join, "get_redis", return_value=redis):
        await staff_join.on_code_submit(it, factory, TENANT_ID)
    kwargs = it.guild.create_text_channel.await_args.kwargs
    assert kwargs["name"] == "staff-join-11"
    assert kwargs["topic"] == "スタッフ登録（招待 11）"
    assert {c.args[0] for c in it.guild.get_role.call_args_list} == {4001, 4002}
    sqls = _sqls(factory)
    assert any("UPDATE public.users SET password_argon2_hash" in s and "password_must_change = true" in s for s in sqls)
    assert any("UPDATE staff SET discord_user_id" in s for s in sqls)
    assert not any("UPDATE staff SET" in s and "status" in s for s in sqls)  # staff.status は pending のまま
    assert any("status = 'linked'" in s and "reg_code_hash = NULL" in s for s in sqls)
    factory.session.commit.assert_awaited_once()
    sent = channel.send.await_args.args[0]
    assert "new@example.com" in sent and "最初のログインで変更してください" in sent
    it.followup.send.assert_awaited_once_with(T.ROOM_CREATED.format(channel_id=9001), ephemeral=True)
    mocked.assert_called_once_with(TENANT_ID)
    assert "staff_code_fail:777" not in redis.store


async def test_room_create_failure_rolls_back_and_is_not_counted(mocked):
    redis = _Redis()
    channel = None
    it = _submit_interaction(channel)  # create_text_channel は None を返す＝作れない
    it.guild.create_text_channel = AsyncMock(side_effect=discord.Forbidden(MagicMock(status=403), "no"))
    factory = _factory(_dispatch())
    with patch.object(staff_join, "get_redis", return_value=redis):
        await staff_join.on_code_submit(it, factory, TENANT_ID)
    it.followup.send.assert_awaited_once_with(T.ROOM_FAILED, ephemeral=True)
    factory.session.rollback.assert_awaited()
    factory.session.commit.assert_not_awaited()
    assert not any(s.lstrip().startswith("UPDATE") for s in _sqls(factory))
    assert "staff_code_fail:777" not in redis.store
    mocked.assert_not_called()


async def test_invalid_code_rolls_back_counts_and_creates_no_room(mocked):
    redis = _Redis()
    it = _submit_interaction(_text_channel(9001))
    factory = _factory(_dispatch(invite=None))
    with patch.object(staff_join, "get_redis", return_value=redis):
        await staff_join.on_code_submit(it, factory, TENANT_ID)
    it.followup.send.assert_awaited_once_with(T.CODE_INVALID, ephemeral=True)
    it.guild.create_text_channel.assert_not_awaited()
    factory.session.rollback.assert_awaited()
    assert redis.store["staff_code_fail:777"] == 1


async def test_other_staff_holding_discord_id_is_already_registered(mocked):
    it = _submit_interaction(_text_channel(9001))
    factory = _factory(_dispatch(other=True))
    with patch.object(staff_join, "get_redis", return_value=_Redis()):
        await staff_join.on_code_submit(it, factory, TENANT_ID)
    it.followup.send.assert_awaited_once_with(T.ALREADY_REGISTERED, ephemeral=True)
    it.guild.create_text_channel.assert_not_awaited()
    factory.session.commit.assert_not_awaited()


async def test_post_failure_after_commit_falls_back_to_ephemeral_followup(mocked):
    channel = _text_channel(9001)
    channel.send = AsyncMock(side_effect=RuntimeError("down"))
    it = _submit_interaction(channel)
    factory = _factory(_dispatch())
    with patch.object(staff_join, "get_redis", return_value=_Redis()):
        await staff_join.on_code_submit(it, factory, TENANT_ID)
    factory.session.commit.assert_awaited_once()
    channel.delete.assert_not_awaited()  # commit 済みなので個室は消さない
    it.followup.send.assert_awaited_once()
    sent = it.followup.send.await_args.args[0]
    assert "new@example.com" in sent and "仮パスワード" in sent
    assert it.followup.send.await_args.kwargs == {"ephemeral": True}


async def test_post_and_followup_failure_is_logged_without_password(mocked, caplog):
    channel = _text_channel(9001)
    channel.send = AsyncMock(side_effect=RuntimeError("down"))
    it = _submit_interaction(channel)
    it.followup.send = AsyncMock(side_effect=RuntimeError("down"))
    factory = _factory(_dispatch())
    with caplog.at_level(logging.DEBUG), patch.object(staff_join, "get_redis", return_value=_Redis()):
        with patch.object(staff_join.secrets, "token_urlsafe", return_value="SECRET-PASSWORD-VALUE-123"):
            await staff_join.on_code_submit(it, factory, TENANT_ID)
    assert "welcome delivery failed" in caplog.text
    assert "SECRET-PASSWORD-VALUE-123" not in caplog.text
    assert "new@example.com" not in caplog.text


# ── 非 PG: 部屋の見える人（extra_view_role_ids）──────────────


async def test_existing_callers_get_same_overwrites_without_extra_roles():
    guild = _guild(_text_channel(9001))
    guild.default_role = MagicMock()
    guild.me = None
    guild.get_role = MagicMock(return_value=MagicMock())
    member = _member()
    category = MagicMock(spec=discord.CategoryChannel)
    await private_channel.create_private_text_channel(guild, category, member, None, "ticket-x", "r", "ctx")
    keys = set(guild.create_text_channel.await_args.kwargs["overwrites"])
    assert keys == {guild.default_role, member}
    guild.get_role.assert_not_called()

    guild.create_text_channel.reset_mock()
    await private_channel.create_private_text_channel(guild, category, member, "55", "ticket-x", "r", "ctx")
    assert len(guild.create_text_channel.await_args.kwargs["overwrites"]) == 3  # 本人・@everyone・スタッフ
    guild.get_role.assert_called_once_with(55)


async def test_extra_view_roles_are_added_and_missing_ones_skipped():
    guild = _guild(_text_channel(9001))
    guild.default_role = MagicMock()
    guild.me = None
    found = MagicMock()
    guild.get_role = MagicMock(side_effect=lambda rid: found if rid == 4001 else None)
    member = _member()
    await private_channel.create_private_text_channel(
        guild, MagicMock(spec=discord.CategoryChannel), member, None, "n", "r", "ctx",
        extra_view_role_ids=["4001", "4999"],
    )
    overwrites = guild.create_text_channel.await_args.kwargs["overwrites"]
    assert set(overwrites) == {guild.default_role, member, found}
    assert overwrites[found].view_channel is True


# ── 非 PG: 片付け ─────────────────────────────────────────────


NOW = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


def _room(cid: int, invite_id: int, age_min: int):
    ch = _text_channel(cid, f"staff-join-{invite_id}")
    ch.created_at = NOW - timedelta(minutes=age_min)
    return ch


def _sweep_guild(channels):
    guild = MagicMock()
    guild.id = GUILD_ID
    category = MagicMock(spec=discord.CategoryChannel)
    category.channels = channels
    guild.get_channel = MagicMock(return_value=category)
    return guild


@pytest.fixture
def sweep_env(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "dummy-token-for-test")
    for name in ("set_tenant_context", "reset_tenant_context", "clear_tenant_context"):
        monkeypatch.setattr(staff_join, name, AsyncMock())
    monkeypatch.setattr(staff_join, "find_blueprint_channel_id", AsyncMock(return_value="2002"))


async def test_sweep_does_not_delete_rooms_younger_than_ten_minutes(sweep_env):
    young = _room(1, 1, 5)
    old_orphan = _room(2, 2, 30)
    old_owned = _room(3, 3, 30)
    manual = _text_channel(4, "general")
    manual.created_at = NOW - timedelta(days=3)
    guild = _sweep_guild([young, old_orphan, old_owned, manual])

    def _execute(stmt, params=None):
        owned = {3: "3"}  # 招待 3 の部屋は 3
        return _Rows([(owned.get(params["id"]),)] if params["id"] in owned else [])

    factory = _factory(_execute)
    deleted = await staff_join.sweep_orphan_rooms(guild, factory, TENANT_ID, now=NOW)
    assert deleted == 1
    old_orphan.delete.assert_awaited_once()
    for kept in (young, old_owned, manual):
        kept.delete.assert_not_awaited()
    ids_read = [c.args[1]["id"] for c in factory.session.execute.await_args_list]
    assert 1 not in ids_read  # 10 分未満の部屋は招待の表も見ない
    staff_join.set_tenant_context.assert_awaited_once()  # 読む前に会社の文脈
    staff_join.reset_tenant_context.assert_awaited_once()  # 読んだ後に戻す


async def test_sweep_deletes_room_when_invite_points_to_other_channel(sweep_env):
    room = _room(10, 7, 60)
    guild = _sweep_guild([room])
    factory = _factory(lambda stmt, params=None: _Rows([("999",)]))  # 招待の個室は別の部屋
    assert await staff_join.sweep_orphan_rooms(guild, factory, TENANT_ID, now=NOW) == 1
    room.delete.assert_awaited_once()


async def test_sweep_cap_is_ten(sweep_env):
    rooms = [_room(i, i, 60) for i in range(1, 14)]
    guild = _sweep_guild(rooms)
    factory = _factory(lambda stmt, params=None: _Rows([]))
    assert await staff_join.sweep_orphan_rooms(guild, factory, TENANT_ID, now=NOW) == 10
    assert sum(r.delete.await_count for r in rooms) == 10


async def test_sweep_db_error_deletes_nothing(sweep_env):
    room = _room(10, 7, 60)
    guild = _sweep_guild([room])

    def _boom(stmt, params=None):
        raise RuntimeError("db down")

    assert await staff_join.sweep_orphan_rooms(guild, _factory(_boom), TENANT_ID, now=NOW) == 0
    room.delete.assert_not_awaited()


async def test_sweep_without_category_deletes_nothing(sweep_env, monkeypatch):
    monkeypatch.setattr(staff_join, "find_blueprint_channel_id", AsyncMock(return_value=None))
    assert await staff_join.sweep_orphan_rooms(_sweep_guild([]), MagicMock(), TENANT_ID, now=NOW) == 0


# ── 非 PG: 専用スクリプト ─────────────────────────────────────


async def test_cli_posts_button_only_when_absent(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "dummy-token-for-test")
    monkeypatch.setattr(staff_join_discord_cli, "find_blueprint_channel_id", AsyncMock(return_value="3001"))
    calls: list = []
    existing: list = []

    async def request(*, method, path, bot_token, json=None, expected_statuses=(200, 201, 204)):
        calls.append((method, path))
        if method == "GET":
            assert path.startswith("/channels/3001/messages?")
            return existing
        assert method == "POST" and path == "/channels/3001/messages"
        assert json == T.reception_message_payload()
        return {"id": "m1"}

    factory = _factory(lambda stmt, params=None: _Rows([("10",)]))
    payload = {"action": "post-staff-button", "tenant_id": TENANT_ID}

    existing[:] = [{"components": [{"components": [{"custom_id": T.OPEN_BUTTON_CUSTOM_ID}]}]}]
    out = await staff_join_discord_cli.run(payload, session_factory=factory, request=request)
    assert out == {"posted": False, "reason": "exists"}
    assert [m for m, _ in calls] == ["GET"]  # 投稿していない

    existing[:] = [{"components": []}]
    out = await staff_join_discord_cli.run(payload, session_factory=factory, request=request)
    assert out == {"posted": True, "message_id": "m1"}


async def test_cli_not_configured_and_bad_input(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "dummy-token-for-test")
    for bad in ({"action": "x", "tenant_id": 1}, {"action": "post-staff-button"}, {"action": "post-staff-button", "tenant_id": "1"}, {"action": "post-staff-button", "tenant_id": True}, "no"):
        with pytest.raises(staff_join_discord_cli.StaffJoinDiscordError) as exc:
            await staff_join_discord_cli.run(bad)
        assert exc.value.code == "invalid_input"
    no_own = _factory(lambda stmt, params=None: _Rows([]))
    with pytest.raises(staff_join_discord_cli.StaffJoinDiscordError) as exc:
        await staff_join_discord_cli.run({"action": "post-staff-button", "tenant_id": 1}, session_factory=no_own)
    assert exc.value.code == "not_configured"
    monkeypatch.setattr(staff_join_discord_cli, "find_blueprint_channel_id", AsyncMock(return_value=None))
    has_own = _factory(lambda stmt, params=None: _Rows([("10",)]))
    with pytest.raises(staff_join_discord_cli.StaffJoinDiscordError) as exc:
        await staff_join_discord_cli.run({"action": "post-staff-button", "tenant_id": 1}, session_factory=has_own)
    assert exc.value.code == "not_configured"


# ── 非 PG: 共通の引き方 ───────────────────────────────────────


async def test_find_blueprint_channel_id_by_type(monkeypatch, tmp_path):
    from app.services import staff_join as svc

    class _Item:
        def __init__(self, key, name, discord_id=None):
            self.key, self.name, self.discord_id = key, name, discord_id

    bp = MagicMock()
    bp.categories = [_Item("staff_join_rooms", "スタッフ登録"), _Item("with_id", "x", "55")]
    bp.channels = [_Item("staff_join_reception", "スタッフ受付")]
    path = tmp_path / "bp.json"
    path.write_text("{}")
    monkeypatch.setattr(svc, "blueprint_path", lambda tid: path)
    monkeypatch.setattr(svc, "load_blueprint", lambda p: bp)
    listing = [
        {"id": "1", "name": "スタッフ登録", "type": 4},
        {"id": "2", "name": "スタッフ登録", "type": 0},  # type が違う物は数えない
        {"id": "3", "name": "スタッフ受付", "type": 0},
    ]
    monkeypatch.setattr(svc, "discord_api_request", AsyncMock(return_value=listing))
    assert await svc.find_blueprint_channel_id("9", "t", 1, "staff_join_rooms", 4) == "1"
    assert await svc.find_blueprint_channel_id("9", "t", 1, "staff_join_reception", 0) == "3"
    assert await svc._find_reception_channel_id("9", "t", 1) == "3"
    assert await svc.find_blueprint_channel_id("9", "t", 1, "with_id", 4) == "55"
    assert await svc.find_blueprint_channel_id("9", "t", 1, "nope", 4) is None
    listing.append({"id": "4", "name": "スタッフ登録", "type": 4})  # 同名が2つなら None
    assert await svc.find_blueprint_channel_id("9", "t", 1, "staff_join_rooms", 4) is None


# ── PG ────────────────────────────────────────────────────────

PG_TENANT = 907
PG_SCHEMA = "tenant_907"
PG_USER = 5001


def _prep_pg(conn, async_url, *, admin_roles=True):
    async def _users():
        engine = create_async_engine(async_url, echo=False)
        try:
            async with engine.begin() as aconn:
                await _ensure_public_users(aconn)
        finally:
            await engine.dispose()

    asyncio.run(_users())
    cur = conn.cursor()
    cur.execute(
        "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_argon2_hash TEXT, "
        "ADD COLUMN IF NOT EXISTS password_must_change BOOLEAN NOT NULL DEFAULT false"
    )
    cur.execute(
        "INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) "
        "VALUES (%s, 'tenant_907', 't', 't', TRUE) ON CONFLICT (id) DO NOTHING",
        (PG_TENANT,),
    )
    cur.execute((MIGRATIONS / "20261107_120000_create_staff_join_invites.sql").read_text())
    cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(PG_TENANT),))
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {PG_SCHEMA}")
    cur.execute(
        f"CREATE TABLE {PG_SCHEMA}.staff (id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL, "
        "user_id INTEGER NOT NULL, discord_user_id VARCHAR(50), status TEXT NOT NULL DEFAULT 'pending', "
        "UNIQUE (tenant_id, discord_user_id))"
    )
    cur.execute(
        f"CREATE TABLE {PG_SCHEMA}.roles (id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL, name TEXT, "
        "system_key TEXT, discord_role_id TEXT)"
    )
    cur.execute(f"CREATE TABLE {PG_SCHEMA}.role_permissions (role_id INTEGER NOT NULL, permission_id INTEGER NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS public.permissions (id SERIAL PRIMARY KEY, key TEXT UNIQUE NOT NULL)")
    cur.execute("INSERT INTO public.permissions (key) VALUES ('staff.create'), ('staff.view') ON CONFLICT DO NOTHING")
    cur.execute(
        "INSERT INTO public.users (id, tenant_id, email, is_active) VALUES (%s, %s, 'new@example.com', FALSE)",
        (PG_USER, PG_TENANT),
    )
    cur.execute(
        f"INSERT INTO {PG_SCHEMA}.staff (tenant_id, user_id, status) VALUES (%s, %s, 'pending') RETURNING id",
        (PG_TENANT, PG_USER),
    )
    staff_id = cur.fetchone()[0]
    if admin_roles:
        d = "4001" if admin_roles else None
        cur.execute(
            f"INSERT INTO {PG_SCHEMA}.roles (tenant_id, name, system_key, discord_role_id) VALUES "
            "(%s, 'admin', 'admin', %s), (%s, 'manager', NULL, '4002'), (%s, 'viewer', NULL, '4003') RETURNING id",
            (PG_TENANT, d, PG_TENANT, PG_TENANT),
        )
        ids = [r[0] for r in cur.fetchall()]
        # manager（4002）は staff.create を持つ。viewer（4003）は staff.view だけ＝管理者のロールではない
        cur.execute("SELECT id, key FROM public.permissions WHERE key IN ('staff.create','staff.view')")
        perm = {k: i for i, k in cur.fetchall()}
        cur.execute(
            f"INSERT INTO {PG_SCHEMA}.role_permissions (role_id, permission_id) VALUES (%s, %s), (%s, %s)",
            (ids[1], perm["staff.create"], ids[2], perm["staff.view"]),
        )
    cur.execute(
        "INSERT INTO public.staff_join_invites (tenant_id, role_id, created_by, token_hash, expires_at, status, "
        "user_id, staff_id, reg_code_hash, reg_code_expires_at, submitted_at) VALUES "
        "(%s, 1, %s, %s, NOW() + interval '72 hours', 'submitted', %s, %s, %s, NOW() + interval '7 days', NOW()) "
        "RETURNING id",
        (
            PG_TENANT,
            PG_USER,
            b"t" * 32,
            PG_USER,
            staff_id,
            signup_code_sha256(normalize_signup_code(CODE)),
        ),
    )
    invite_id = cur.fetchone()[0]
    return cur, invite_id, staff_id


def _run_pg(async_url, *, uid=777, code=CODE, channel=None, create_error=False):
    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            factory = lambda: AsyncSession(engine, expire_on_commit=False)  # noqa: E731
            ch = channel if channel is not None else _text_channel(9001, "x")
            it = _interaction(MODAL_ID, guild=_guild(ch), user=_member(uid), components=_components(code))
            if create_error:
                it.guild.create_text_channel = AsyncMock(side_effect=discord.Forbidden(MagicMock(status=403), "no"))
            sync = MagicMock()
            with patch.object(staff_join, "get_redis", return_value=_Redis()), patch.object(
                staff_join, "schedule_own_staff_sync", sync
            ), patch.object(
                staff_join,
                "_resolve_rooms_category",
                AsyncMock(return_value=MagicMock(spec=discord.CategoryChannel)),
            ):
                await staff_join.on_code_submit(it, factory, PG_TENANT)
            return it, ch, sync
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def _state(cur, invite_id):
    cur.execute("SELECT is_active, password_must_change, password_argon2_hash FROM public.users WHERE id=%s", (PG_USER,))
    user = cur.fetchone()
    cur.execute(f"SELECT discord_user_id, status FROM {PG_SCHEMA}.staff WHERE user_id=%s", (PG_USER,))
    staff = cur.fetchone()
    cur.execute(
        "SELECT status, discord_channel_id, reg_code_hash IS NULL, linked_at IS NOT NULL "
        "FROM public.staff_join_invites WHERE id=%s",
        (invite_id,),
    )
    return user, staff, cur.fetchone()


@needs_ci_pg
def test_code_match_writes_users_staff_and_invite(pg):  # noqa: F811
    conn, _, async_url = pg
    cur, invite_id, _ = _prep_pg(conn, async_url)
    it, channel, sync = _run_pg(async_url, code=CODE.lower())
    assert it.followup.send.await_args.args[0] == T.ROOM_CREATED.format(channel_id=9001)
    user, staff, invite = _state(cur, invite_id)
    assert user[0] is True and user[1] is True and user[2].startswith("$argon2")
    assert staff == ("777", "pending")  # staff.status は pending のまま
    assert invite == ("linked", "9001", True, True)
    kwargs = it.guild.create_text_channel.await_args.kwargs
    assert kwargs["name"] == f"staff-join-{invite_id}" and kwargs["topic"] == f"スタッフ登録（招待 {invite_id}）"
    # 管理者のロール＝admin（system_key）と staff.create を持つ manager。staff.view だけの viewer は入らない
    assert {c.args[0] for c in it.guild.get_role.call_args_list} == {4001, 4002}
    assert "new@example.com" in channel.send.await_args.args[0]
    sync.assert_called_once_with(PG_TENANT)


@needs_ci_pg
def test_second_attempt_is_already_registered_and_makes_no_room(pg):  # noqa: F811
    conn, _, async_url = pg
    cur, invite_id, _ = _prep_pg(conn, async_url)
    first, _, _ = _run_pg(async_url)
    assert first.followup.send.await_args.args[0] == T.ROOM_CREATED.format(channel_id=9001)
    second, ch2, sync2 = _run_pg(async_url, channel=_text_channel(9002, "y"))
    assert second.followup.send.await_args.args[0] == T.ALREADY_REGISTERED
    second.guild.create_text_channel.assert_not_awaited()
    sync2.assert_not_called()
    assert _state(cur, invite_id)[2][1] == "9001"  # 招待の個室は最初のまま


@needs_ci_pg
def test_room_failure_rolls_back_everything(pg):  # noqa: F811
    conn, _, async_url = pg
    cur, invite_id, _ = _prep_pg(conn, async_url)
    it, _, sync = _run_pg(async_url, create_error=True)
    assert it.followup.send.await_args.args[0] == T.ROOM_FAILED
    user, staff, invite = _state(cur, invite_id)
    assert user[0] is False and user[2] is None
    assert staff == (None, "pending")
    assert invite[0] == "submitted" and invite[2] is False  # 番号はまだ使える
    sync.assert_not_called()


@needs_ci_pg
def test_no_admin_role_changes_nothing(pg):  # noqa: F811
    conn, _, async_url = pg
    cur, invite_id, _ = _prep_pg(conn, async_url, admin_roles=False)
    it, _, _ = _run_pg(async_url)
    assert it.followup.send.await_args.args[0] == T.NOT_READY
    it.guild.create_text_channel.assert_not_awaited()
    user, staff, invite = _state(cur, invite_id)
    assert user[0] is False and staff == (None, "pending") and invite[0] == "submitted"


@needs_ci_pg
def test_wrong_or_expired_code_is_invalid_and_changes_nothing(pg):  # noqa: F811
    conn, _, async_url = pg
    cur, invite_id, _ = _prep_pg(conn, async_url)
    it, _, _ = _run_pg(async_url, code="2222-3333-4444-5555")
    assert it.followup.send.await_args.args[0] == T.CODE_INVALID
    cur.execute("UPDATE public.staff_join_invites SET reg_code_expires_at = NOW() - interval '1 hour' WHERE id=%s", (invite_id,))
    it2, _, _ = _run_pg(async_url)
    assert it2.followup.send.await_args.args[0] == T.CODE_INVALID
    it2.guild.create_text_channel.assert_not_awaited()
    assert _state(cur, invite_id)[2][0] == "submitted"
