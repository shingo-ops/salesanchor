"""
Discord リアクション配線修正のテスト群（discord-reaction テーマ・ADR-091）。

カバー:
- leads._group_reactions: 集約・count・is_mine（Bot 行の有無）・reactors オブジェクト形
- ReactionWriter.process_reaction: is_bot_reaction を INSERT へ引き渡す（固定 false 廃止）
- JarvisDiscordClient.on_raw_reaction_add: Bot 自身の add を skip せず is_bot_reaction を算出
- discord_reactions ルーター: Discord REST を正しい URL で叩き、DB を書かない（Gateway が唯一の書き手）

実行:
    pytest backend/tests/test_discord_reaction_wiring.py -v
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from fastapi import HTTPException

from app.discord_gateway.client import JarvisDiscordClient
from app.discord_gateway.reaction_writer import ReactionWriter
from app.routers import discord_reactions as reactions_router
from app.routers.leads import _group_reactions

BOT_ID = 900000000000000001
CHANNEL_ID = "111111111111111111"
SNOWFLAKE = "222222222222222222"


def _row(meta_message_id=1, emoji_name="👍", emoji_id=None, animated=False,
         user_id="u1", display_name="Alice", is_bot=False) -> dict:
    return {
        "meta_message_id": meta_message_id,
        "emoji_name": emoji_name,
        "emoji_id": emoji_id,
        "emoji_animated": animated,
        "reactor_discord_user_id": user_id,
        "reactor_display_name": display_name,
        "is_bot_reaction": is_bot,
    }


# ---------------------------------------------------------------------------
# _group_reactions
# ---------------------------------------------------------------------------


def test_group_reactions_returns_empty_dict_for_no_rows():
    assert _group_reactions([]) == {}


def test_group_reactions_counts_and_returns_reactor_objects():
    rows = [
        _row(user_id="u1", display_name="Alice"),
        _row(user_id="u2", display_name=None),
    ]

    result = _group_reactions(rows)

    assert result == {
        1: [
            {
                "emoji_name": "👍",
                "emoji_id": None,
                "emoji_animated": False,
                "count": 2,
                "is_mine": False,
                "reactors": [
                    {"user_id": "u1", "display_name": "Alice"},
                    {"user_id": "u2", "display_name": None},
                ],
            }
        ]
    }


def test_group_reactions_is_mine_true_only_for_group_with_bot_row():
    rows = [
        _row(emoji_name="👍", user_id="u1"),
        _row(emoji_name="👍", user_id=str(BOT_ID), display_name="Bot", is_bot=True),
        _row(emoji_name="🎉", user_id="u1"),
    ]

    by_emoji = {r["emoji_name"]: r for r in _group_reactions(rows)[1]}

    assert by_emoji["👍"]["is_mine"] is True
    assert by_emoji["🎉"]["is_mine"] is False
    assert "is_bot_reaction" not in by_emoji["👍"]


def test_group_reactions_separates_custom_emoji_and_messages():
    rows = [
        _row(meta_message_id=1, emoji_name="party", emoji_id="123456789012345678", animated=True),
        _row(meta_message_id=1, emoji_name="party", emoji_id="987654321098765432"),
        _row(meta_message_id=2, emoji_name="👍"),
    ]

    result = _group_reactions(rows)

    assert len(result[1]) == 2
    assert result[1][0]["emoji_animated"] is True
    assert len(result[2]) == 1


# ---------------------------------------------------------------------------
# ReactionWriter
# ---------------------------------------------------------------------------


def _writer_with_conn() -> tuple[ReactionWriter, AsyncMock]:
    conn = AsyncMock()
    conn.fetchrow.return_value = {"id": 77}
    tx_cm = MagicMock()
    tx_cm.__aenter__ = AsyncMock(return_value=None)
    tx_cm.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=tx_cm)
    acquire_cm = MagicMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire.return_value = acquire_cm
    writer = ReactionWriter("postgresql://unused")
    writer._pool = pool
    return writer, conn


@pytest.mark.asyncio
@pytest.mark.parametrize("is_bot", [True, False])
async def test_reaction_writer_add_passes_is_bot_reaction_to_insert(is_bot):
    writer, conn = _writer_with_conn()
    emoji = SimpleNamespace(id=None, name="👍", animated=False)
    member = SimpleNamespace(display_name="Bot", name="bot")

    with patch("app.discord_gateway.reaction_writer.sse_pubsub.publish_inbox_update", new=AsyncMock()):
        await writer.process_reaction(
            tenant_id=1, channel_id=CHANNEL_ID, message_id=SNOWFLAKE,
            user_id=str(BOT_ID), emoji=emoji, member=member,
            action="add", is_bot_reaction=is_bot,
        )

    insert_calls = [c for c in conn.execute.await_args_list if "INSERT INTO" in c.args[0]]
    assert len(insert_calls) == 1
    sql, *params = insert_calls[0].args
    assert "$8" in sql
    assert params == [1, 77, "👍", None, False, str(BOT_ID), "Bot", is_bot]


# ---------------------------------------------------------------------------
# JarvisDiscordClient.on_raw_reaction_add
# ---------------------------------------------------------------------------


def _payload(user_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        guild_id=5, channel_id=6, message_id=7, user_id=user_id,
        emoji=SimpleNamespace(id=None, name="👍", animated=False), member=None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id,expected", [(BOT_ID, True), (123, False)],
)
async def test_on_raw_reaction_add_records_bot_and_human(user_id, expected):
    client = JarvisDiscordClient(database_url="postgresql://unused")
    client.reaction_writer = MagicMock()
    client.reaction_writer.process_reaction = AsyncMock()
    client._resolve_tenant_id = AsyncMock(return_value=1)

    with patch.object(JarvisDiscordClient, "user", new_callable=PropertyMock,
                      return_value=SimpleNamespace(id=BOT_ID)):
        await client.on_raw_reaction_add(_payload(user_id))

    client.reaction_writer.process_reaction.assert_awaited_once()
    kwargs = client.reaction_writer.process_reaction.await_args.kwargs
    assert kwargs["is_bot_reaction"] is expected
    assert kwargs["action"] == "add"
    assert kwargs["user_id"] == str(user_id)


# ---------------------------------------------------------------------------
# discord_reactions router: Discord REST のみ・DB 非書込
# ---------------------------------------------------------------------------


def _discord_http_mock(status_code: int = 204) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = ""
    http_client = AsyncMock()
    http_client.put.return_value = response
    http_client.delete.return_value = response
    return http_client


@pytest.fixture
def router_env(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "Bot-token-test")
    with patch.object(reactions_router, "_get_discord_message_id",
                      new=AsyncMock(return_value=SNOWFLAKE)), \
         patch.object(reactions_router, "_get_discord_channel_id_for_lead",
                      new=AsyncMock(return_value=CHANNEL_ID)):
        yield


async def _call_send(db, http_client, emoji_name="👍", emoji_id=None):
    data = reactions_router.ReactionRequest(emoji_name=emoji_name, emoji_id=emoji_id)
    with patch("app.routers.discord_reactions.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=http_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        return await reactions_router.send_reaction(
            lead_id=10, message_id=345, data=data, db=db, tenant_id=1,
            current_user=MagicMock(),
        )


@pytest.mark.asyncio
async def test_send_reaction_puts_to_discord_and_does_not_write_db(router_env):
    db = AsyncMock()
    http_client = _discord_http_mock()

    result = await _call_send(db, http_client)

    assert result.success is True
    http_client.put.assert_awaited_once()
    assert http_client.put.await_args.args[0] == (
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}"
        f"/messages/{SNOWFLAKE}/reactions/%F0%9F%91%8D/@me"
    )
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_reaction_custom_emoji_uses_name_colon_id(router_env):
    db = AsyncMock()
    http_client = _discord_http_mock()

    await _call_send(db, http_client, emoji_name="party", emoji_id="123456789012345678")

    assert http_client.put.await_args.args[0].endswith(
        f"/messages/{SNOWFLAKE}/reactions/party:123456789012345678/@me"
    )


@pytest.mark.asyncio
async def test_send_reaction_returns_502_when_discord_rejects(router_env):
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await _call_send(db, _discord_http_mock(status_code=403))

    assert exc_info.value.status_code == 502
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_reaction_calls_discord_and_does_not_write_db(router_env):
    db = AsyncMock()
    http_client = _discord_http_mock()

    with patch("app.routers.discord_reactions.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=http_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await reactions_router.delete_reaction(
            lead_id=10, message_id=345, emoji="party", emoji_id="123456789012345678",
            db=db, tenant_id=1, current_user=MagicMock(),
        )

    assert result.success is True
    http_client.delete.assert_awaited_once()
    assert http_client.delete.await_args.args[0] == (
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}"
        f"/messages/{SNOWFLAKE}/reactions/party:123456789012345678/@me"
    )
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()
