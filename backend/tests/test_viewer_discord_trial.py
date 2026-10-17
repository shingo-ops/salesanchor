"""閲覧者の Discord 受付（ADR-1019 段4c）の試験。

非 PG: Discord・Redis・DB をモックして、ルーティング・ボタン・小窓・回数制限・文面・片付け・専用スクリプト。
PG（CI の使い捨て DB。pg fixture）: 照合からトライアル開始までの書き込み・ロールバック・設定の保存・一覧の URL。
テストデータはすべて架空。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import discord  # 他の試験の discord 差し替えより先に実物を読み込む
import psycopg2
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app import viewer_discord_cli
from app.auth.viewer_signup_code import normalize_signup_code, signup_code_sha256
from app.discord_gateway import ticket_channel_creator, viewer_trial
from app.discord_gateway import viewer_bot_texts as T
from app.discord_gateway.client import JarvisDiscordClient
from app.services import viewer_admin
from tests.test_super_admin_viewers import _account, _changes, _prepare, needs_ci_pg
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

GUILD_ID = 111222333444555666
CONFIG = viewer_trial.ViewerDiscordConfig(str(GUILD_ID), "2001", "2002", "2003")
CODE = "ABCD-EFGH-JKMN-PQRS"


# ── 共通の作り物 ──────────────────────────────────────────────


class _Result:
    def __init__(self, row=None) -> None:
        self._row = row

    def first(self):
        return self._row


def _db_factory(execute) -> MagicMock:
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


def _member(uid: int = 777) -> MagicMock:
    m = MagicMock(spec=discord.Member)
    m.id = uid
    return m


def _text_channel(cid: int = 9001, name: str = "x") -> MagicMock:
    ch = MagicMock(spec=discord.TextChannel)
    ch.id = cid
    ch.name = name
    ch.send = AsyncMock()
    ch.delete = AsyncMock()
    return ch


def _guild(channel: MagicMock | None = None) -> MagicMock:
    guild = MagicMock()
    guild.id = GUILD_ID
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = 2002
    guild.get_channel = MagicMock(return_value=category)
    guild.create_text_channel = AsyncMock(return_value=channel)
    return guild


def _interaction(custom_id, *, guild=None, user=None, components=None) -> MagicMock:
    it = MagicMock()
    it.data = {"custom_id": custom_id}
    if components is not None:
        it.data["components"] = components
    it.guild = guild
    it.user = user
    it.response.defer = AsyncMock()
    it.response.send_message = AsyncMock()
    it.response.send_modal = AsyncMock()
    it.followup.send = AsyncMock()
    return it


def _code_components(value: str):
    return [{"type": 1, "components": [{"type": 4, "custom_id": T.CODE_INPUT_CUSTOM_ID, "value": value}]}]


class _Redis:
    def __init__(self, initial=None) -> None:
        self.store = dict(initial or {})
        self.expire_calls: list = []

    async def get(self, key):
        return self.store.get(key)

    async def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    async def expire(self, key, ttl):
        self.expire_calls.append((key, ttl))


def _no_db() -> MagicMock:
    def _boom(*a, **k):
        raise AssertionError("DB must not be touched")

    return MagicMock(side_effect=_boom)


# ── 非 PG: ルーティング ───────────────────────────────────────


def _client() -> JarvisDiscordClient:
    client = JarvisDiscordClient(database_url="postgresql://unused")
    client._db_factory = MagicMock()
    return client


async def test_on_interaction_routes_viewer_prefix_before_component_check():
    it = _interaction(T.CODE_MODAL_CUSTOM_ID)
    it.type = discord.InteractionType.modal_submit
    with patch.object(viewer_trial, "handle_interaction", new=AsyncMock()) as handle, patch.object(
        ticket_channel_creator, "get_or_create_ticket_channel", new=AsyncMock()
    ) as ticket:
        await _client().on_interaction(it)
    handle.assert_awaited_once()
    ticket.assert_not_awaited()


async def test_ticket_open_still_goes_to_ticket_flow():
    it = _interaction("ticket_open", guild=None, user=MagicMock())
    it.type = discord.InteractionType.component
    with patch.object(viewer_trial, "handle_interaction", new=AsyncMock()) as handle:
        await _client().on_interaction(it)
    handle.assert_not_awaited()
    it.followup.send.assert_awaited_once()  # 顧客用の流れ（GUILD_ONLY）に入った


# ── 非 PG: ボタン ─────────────────────────────────────────────


async def test_open_button_sends_modal_without_defer():
    it = _interaction(T.OPEN_BUTTON_CUSTOM_ID, guild=_guild(), user=_member())
    factory = _db_factory(lambda *a, **k: _Result(None))
    with patch.object(viewer_trial, "load_config", new=AsyncMock(return_value=CONFIG)):
        await viewer_trial.handle_interaction(it, factory)
    it.response.defer.assert_not_awaited()
    it.response.send_modal.assert_awaited_once()
    modal = it.response.send_modal.await_args.args[0]
    assert isinstance(modal, viewer_trial.ViewerTrialCodeModal)
    assert modal.custom_id == T.CODE_MODAL_CUSTOM_ID
    field = modal.children[0]
    assert field.custom_id == T.CODE_INPUT_CUSTOM_ID
    assert (field.min_length, field.max_length, field.required) == (16, 19, True)


async def test_open_button_linked_user_gets_room():
    room = _text_channel(123)
    guild = _guild()
    guild.get_channel = MagicMock(return_value=room)
    it = _interaction(T.OPEN_BUTTON_CUSTOM_ID, guild=guild, user=_member())
    factory = _db_factory(lambda *a, **k: _Result((5, "a@example.com", "123")))
    with patch.object(viewer_trial, "load_config", new=AsyncMock(return_value=CONFIG)):
        await viewer_trial.handle_interaction(it, factory)
    it.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    it.response.send_modal.assert_not_awaited()
    it.followup.send.assert_awaited_once_with(T.YOUR_ROOM.format(channel_id=123), ephemeral=True)


async def test_wrong_guild_replies_wrong_server():
    other = _guild()
    other.id = 1
    it = _interaction(T.OPEN_BUTTON_CUSTOM_ID, guild=other, user=_member())
    with patch.object(viewer_trial, "load_config", new=AsyncMock(return_value=CONFIG)):
        await viewer_trial.handle_interaction(it, MagicMock())
    it.response.send_message.assert_awaited_once_with(T.WRONG_SERVER, ephemeral=True)


async def test_no_config_replies_wrong_server():
    it = _interaction(T.CODE_MODAL_CUSTOM_ID, guild=_guild(), user=_member())
    with patch.object(viewer_trial, "load_config", new=AsyncMock(return_value=None)):
        await viewer_trial.handle_interaction(it, MagicMock())
    it.response.send_message.assert_awaited_once_with(T.WRONG_SERVER, ephemeral=True)


# ── 非 PG: 小窓 ───────────────────────────────────────────────


async def test_code_submit_redis_none_try_later():
    it = _interaction(T.CODE_MODAL_CUSTOM_ID, guild=_guild(), user=_member(), components=_code_components(CODE))
    with patch.object(viewer_trial, "get_redis", return_value=None):
        await viewer_trial.on_code_submit(it, _no_db(), CONFIG)
    it.followup.send.assert_awaited_once_with(T.TRY_LATER, ephemeral=True)


async def test_code_submit_locked_after_five_failures():
    it = _interaction(T.CODE_MODAL_CUSTOM_ID, guild=_guild(), user=_member(), components=_code_components(CODE))
    with patch.object(viewer_trial, "get_redis", return_value=_Redis({"viewer_code_fail:777": "5"})):
        await viewer_trial.on_code_submit(it, _no_db(), CONFIG)
    it.followup.send.assert_awaited_once_with(T.TOO_MANY_ATTEMPTS, ephemeral=True)


async def test_failure_increments_and_sets_expire_once():
    redis = _Redis()
    factory = _db_factory(lambda *a, **k: _Result(None))
    with patch.object(viewer_trial, "get_redis", return_value=redis):
        for _ in range(2):
            it = _interaction(
                T.CODE_MODAL_CUSTOM_ID, guild=_guild(), user=_member(), components=_code_components(CODE)
            )
            await viewer_trial.on_code_submit(it, factory, CONFIG)
            it.followup.send.assert_awaited_once_with(T.CODE_INVALID, ephemeral=True)
    assert redis.store["viewer_code_fail:777"] == 2
    assert redis.expire_calls == [("viewer_code_fail:777", 3600)]


async def test_malformed_code_counts_as_failure_without_db():
    redis = _Redis()
    it = _interaction(
        T.CODE_MODAL_CUSTOM_ID, guild=_guild(), user=_member(), components=_code_components("ABCD-EFGH-JKMN-PQRI")
    )
    with patch.object(viewer_trial, "get_redis", return_value=redis):
        await viewer_trial.on_code_submit(it, _no_db(), CONFIG)
    it.followup.send.assert_awaited_once_with(T.CODE_INVALID, ephemeral=True)
    assert redis.store["viewer_code_fail:777"] == 1


async def test_room_create_failure_not_counted():
    redis = _Redis()
    rows = iter([_Result((5,)), _Result((5, "a@example.com", "pending", None))])
    factory = _db_factory(lambda *a, **k: next(rows))
    it = _interaction(T.CODE_MODAL_CUSTOM_ID, guild=_guild(), user=_member(), components=_code_components(CODE))
    with patch.object(viewer_trial, "get_redis", return_value=redis), patch.object(
        viewer_trial, "_create_room", new=AsyncMock(return_value=None)
    ):
        await viewer_trial.on_code_submit(it, factory, CONFIG)
    it.followup.send.assert_awaited_once_with(T.TRY_LATER, ephemeral=True)
    assert "viewer_code_fail:777" not in redis.store
    factory.session.rollback.assert_awaited()


def test_texts_within_discord_limits():
    assert len(T.OPEN_BUTTON_LABEL) <= 80
    assert len(T.CODE_MODAL_TITLE) <= 45
    assert len(T.CODE_INPUT_LABEL) <= 45
    payload = T.reception_message_payload()
    button = payload["components"][0]["components"][0]
    assert payload["components"][0]["type"] == 1
    assert (button["type"], button["style"]) == (2, 1)
    assert button["custom_id"] == T.OPEN_BUTTON_CUSTOM_ID
    assert button["custom_id"].startswith(T.VIEWER_CUSTOM_ID_PREFIX)
    assert T.CODE_MODAL_CUSTOM_ID.startswith(T.VIEWER_CUSTOM_ID_PREFIX)
    assert payload is not T.reception_message_payload()


def test_normalize_signup_code():
    assert normalize_signup_code("abcd-efgh jkmn pqrs") == "ABCDEFGHJKMNPQRS"
    assert normalize_signup_code("0123-4567-89AB-CDEF") == "0123456789ABCDEF"
    for bad in ("ABCD-EFGH-JKMN-PQRI", "ABCD-EFGH-JKMN-PQRL", "ABCD-EFGH-JKMN-PQRO", "ABCD-EFGH-JKMN-PQRU"):
        assert normalize_signup_code(bad) is None
    assert normalize_signup_code("ABCDEFGHJKMNPQR") is None
    assert normalize_signup_code("ABCDEFGHJKMNPQRST") is None
    assert len(signup_code_sha256("ABCDEFGHJKMNPQRS")) == 32


# ── 非 PG: 片付け ─────────────────────────────────────────────


def _sweep_guild(channels):
    guild = MagicMock()
    category = MagicMock(spec=discord.CategoryChannel)
    category.channels = channels
    guild.get_channel = MagicMock(return_value=category)
    return guild


async def test_sweep_deletes_only_missing_ids_in_category():
    existing = _text_channel(1, "trial-1")
    orphan = _text_channel(2, "trial-2")
    other_name = _text_channel(3, "general")
    voice = MagicMock(spec=discord.VoiceChannel)
    voice.name = "trial-9"
    guild = _sweep_guild([existing, orphan, other_name, voice])
    factory = _db_factory(lambda stmt, params: _Result((1,) if params["id"] == 1 else None))
    deleted = await viewer_trial.sweep_orphan_rooms(guild, factory, CONFIG)
    assert deleted == 1
    orphan.delete.assert_awaited_once()
    for kept in (existing, other_name, voice):
        assert not getattr(kept, "delete", AsyncMock()).await_count if hasattr(kept, "delete") else True
    guild.get_channel.assert_called_once_with(2002)


async def test_sweep_not_a_category_deletes_nothing():
    guild = MagicMock()
    guild.get_channel = MagicMock(return_value=None)
    assert await viewer_trial.sweep_orphan_rooms(guild, _no_db(), CONFIG) == 0


async def test_sweep_cap_is_ten():
    rooms = [_text_channel(i, f"trial-{i}") for i in range(1, 13)]
    guild = _sweep_guild(rooms)
    factory = _db_factory(lambda stmt, params: _Result(None))
    assert await viewer_trial.sweep_orphan_rooms(guild, factory, CONFIG) == 10
    assert sum(r.delete.await_count for r in rooms) == 10


async def test_sweep_db_error_deletes_nothing():
    rooms = [_text_channel(1, "trial-1")]
    guild = _sweep_guild(rooms)

    def _boom(*a, **k):
        raise RuntimeError("db down")

    factory = _db_factory(_boom)
    assert await viewer_trial.sweep_orphan_rooms(guild, factory, CONFIG) == 0
    rooms[0].delete.assert_not_awaited()


# ── 非 PG: 専用スクリプト ─────────────────────────────────────


async def test_cli_list_candidates_and_post_button(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "dummy-token-for-test")
    calls: list = []

    async def request(*, method, path, bot_token, json=None, expected_statuses=(200, 201, 204)):
        calls.append((method, path))
        if path == "/users/@me/guilds":
            return [{"id": "10", "name": "G"}]
        if path == "/guilds/10/channels":
            return [
                {"id": "1", "name": "cat", "type": 4},
                {"id": "2", "name": "txt", "type": 0, "parent_id": "1"},
                {"id": "3", "name": "voice", "type": 2},
            ]
        if path == "/guilds/10/roles":
            return [{"id": "5", "name": "staff"}]
        if path.startswith("/channels/2001/messages?"):
            return existing
        if path == "/channels/2001/messages":
            assert method == "POST" and json == T.reception_message_payload()
            return {"id": "m1"}
        raise AssertionError(path)

    out = await viewer_discord_cli.run({"action": "list-candidates", "guild_id": "10"}, request=request)
    assert out == {
        "guilds": [{"id": "10", "name": "G"}],
        "categories": [{"id": "1", "name": "cat"}],
        "text_channels": [{"id": "2", "name": "txt", "parent_id": "1"}],
        "roles": [{"id": "5", "name": "staff"}],
    }

    factory = _db_factory(lambda *a, **k: _Result(("2001",)))
    existing = [{"components": [{"components": [{"custom_id": T.OPEN_BUTTON_CUSTOM_ID}]}]}]
    assert await viewer_discord_cli.run({"action": "post-button"}, session_factory=factory, request=request) == {
        "posted": False,
        "reason": "exists",
    }
    existing = [{"components": []}]
    assert await viewer_discord_cli.run({"action": "post-button"}, session_factory=factory, request=request) == {
        "posted": True,
        "message_id": "m1",
    }


async def test_cli_rejects_bad_input():
    for payload in ({"action": "x"}, {"action": "set-config", "guild_id": "abc"}, "no"):
        with pytest.raises(viewer_discord_cli.ViewerDiscordError) as exc:
            await viewer_discord_cli.run(payload)
        assert exc.value.code == "invalid_input"
    factory = _db_factory(lambda *a, **k: _Result(None))
    with pytest.raises(viewer_discord_cli.ViewerDiscordError) as exc:
        await viewer_discord_cli.run({"action": "post-button"}, session_factory=factory)
    assert exc.value.code == "not_configured"


# ── PG ────────────────────────────────────────────────────────


def _prep(conn, async_url):
    cur = _prepare(conn, async_url)
    cur.execute((MIGRATIONS / "20261017_100000_add_viewer_discord_config.sql").read_text())
    cur.execute(
        "INSERT INTO public.viewer_discord_config (id, guild_id, reception_channel_id, "
        "ticket_category_id, staff_role_id) VALUES (1, %s, '2001', '2002', '2003')",
        (str(GUILD_ID),),
    )
    return cur


def _token(cur, vid, code, *, expires_in_hours=24):
    h = signup_code_sha256(normalize_signup_code(code))
    cur.execute(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, %s, 'signup_code', NOW() + make_interval(hours => %s::int))",
        (vid, psycopg2.Binary(h), expires_in_hours),
    )


def _submit(async_url, code, *, uid=777):
    """実 PG に対して小窓の送信を1回流す。(interaction, channel) を返す。"""

    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            factory = lambda: AsyncSession(engine, expire_on_commit=False)  # noqa: E731
            channel = _text_channel(9001, "trial-x")
            it = _interaction(
                T.CODE_MODAL_CUSTOM_ID,
                guild=_guild(channel),
                user=_member(uid),
                components=_code_components(code),
            )
            with patch.object(viewer_trial, "get_redis", return_value=_Redis()):
                await viewer_trial.on_code_submit(it, factory, CONFIG)
            return it, channel
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def _sent(it):
    return it.followup.send.await_args.args[0]


@needs_ci_pg
def test_code_match_starts_trial_and_writes_records(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    vid = _account(cur, "m1@example.com", "pending")
    _token(cur, vid, CODE)
    before = datetime.now(timezone.utc)
    it, channel = _submit(async_url, CODE.lower())
    assert _sent(it) == T.YOUR_ROOM.format(channel_id=9001)
    cur.execute(
        "SELECT status, trial_expires_at, discord_user_id, discord_channel_id, "
        "password_must_change, password_argon2_hash FROM public.viewer_accounts WHERE id=%s",
        (vid,),
    )
    status, exp, duid, dch, must, pwh = cur.fetchone()
    assert (status, duid, dch, must) == ("trial", "777", "9001", True)
    assert pwh and pwh.startswith("$argon2")
    assert abs((exp - (before + timedelta(days=14))).total_seconds()) < 120
    cur.execute("SELECT count(*) FROM public.viewer_login_tokens WHERE viewer_account_id=%s", (vid,))
    assert cur.fetchone()[0] == 0
    rows = _changes(cur, vid)
    assert len(rows) == 1 and rows[0][0] == "start_trial" and rows[0][1:3] == ("pending", "trial")
    assert rows[0][6] == "system" and rows[0][7] is None
    cur.execute("SELECT event_type, client_ip FROM public.viewer_login_events WHERE viewer_id=%s", (vid,))
    assert cur.fetchall() == [("code_matched", None)]
    channel.send.assert_awaited_once()
    assert "m1@example.com" in channel.send.await_args.args[0]


@needs_ci_pg
def test_expired_or_used_code_is_invalid(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    expired = _account(cur, "e1@example.com", "pending")
    _token(cur, expired, "2222-3333-4444-5555", expires_in_hours=-1)
    it, _ = _submit(async_url, "2222-3333-4444-5555")
    assert _sent(it) == T.CODE_INVALID
    cur.execute("SELECT status FROM public.viewer_accounts WHERE id=%s", (expired,))
    assert cur.fetchone()[0] == "pending"

    used = _account(cur, "u1@example.com", "pending")
    _token(cur, used, CODE)
    first, _ = _submit(async_url, CODE)
    assert _sent(first) == T.YOUR_ROOM.format(channel_id=9001)
    second, _ = _submit(async_url, CODE, uid=778)
    assert _sent(second) == T.CODE_INVALID
    cur.execute("SELECT status FROM public.viewer_accounts WHERE id=%s", (used,))
    assert cur.fetchone()[0] == "trial"


@needs_ci_pg
def test_non_pending_viewer_code_is_invalid(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    vid = _account(cur, "np@example.com", "active")
    _token(cur, vid, CODE)
    it, channel = _submit(async_url, CODE)
    assert _sent(it) == T.CODE_INVALID
    channel.send.assert_not_awaited()
    cur.execute("SELECT count(*) FROM public.viewer_login_tokens WHERE viewer_account_id=%s", (vid,))
    assert cur.fetchone()[0] == 1


@needs_ci_pg
def test_duplicate_discord_user_rolls_back_and_deletes_room(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    holder = _account(cur, "h1@example.com", "trial", expires_in_days=3)
    cur.execute("UPDATE public.viewer_accounts SET discord_user_id='777' WHERE id=%s", (holder,))
    vid = _account(cur, "d1@example.com", "pending")
    _token(cur, vid, CODE)
    it, channel = _submit(async_url, CODE, uid=777)
    assert _sent(it) == T.DISCORD_ALREADY_LINKED
    channel.delete.assert_awaited_once()
    cur.execute("SELECT status FROM public.viewer_accounts WHERE id=%s", (vid,))
    assert cur.fetchone()[0] == "pending"
    cur.execute("SELECT count(*) FROM public.viewer_login_tokens WHERE viewer_account_id=%s", (vid,))
    assert cur.fetchone()[0] == 1
    assert _changes(cur, vid) == []


@needs_ci_pg
def test_cli_set_config_upserts_single_row(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    cur.execute("TRUNCATE public.viewer_discord_config")

    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            factory = lambda: AsyncSession(engine, expire_on_commit=False)  # noqa: E731
            for g in ("10", "20"):
                out = await viewer_discord_cli.run(
                    {
                        "action": "set-config",
                        "guild_id": g,
                        "reception_channel_id": "1",
                        "ticket_category_id": "2",
                        "staff_role_id": "3",
                    },
                    session_factory=factory,
                )
            return out
        finally:
            await engine.dispose()

    out = asyncio.run(_go())
    assert out["guild_id"] == "20"
    cur.execute("SELECT id, guild_id FROM public.viewer_discord_config")
    assert cur.fetchall() == [(1, "20")]


@needs_ci_pg
def test_list_viewers_returns_channel_url(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    with_ch = _account(cur, "c1@example.com", "trial", expires_in_days=3)
    cur.execute("UPDATE public.viewer_accounts SET discord_channel_id='555' WHERE id=%s", (with_ch,))
    without_ch = _account(cur, "c2@example.com", "trial", expires_in_days=3)

    async def _list():
        engine = create_async_engine(async_url, echo=False)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                return await viewer_admin.list_viewers(db)
        finally:
            await engine.dispose()

    items = {i["id"]: i for i in asyncio.run(_list())}
    assert items[with_ch]["discord_channel_url"] == f"https://discord.com/channels/{GUILD_ID}/555"
    assert items[without_ch]["discord_channel_url"] is None
    assert "discord_guild_id" not in items[with_ch]

    cur.execute("TRUNCATE public.viewer_discord_config")
    items = {i["id"]: i for i in asyncio.run(_list())}
    assert items[with_ch]["discord_channel_url"] is None
