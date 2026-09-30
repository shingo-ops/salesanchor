"""
ReactionWriter の RLS トランザクション修正テスト（ADR-072 / ADR-091）。

背景: set_config('app.tenant_id', $1, true) はトランザクション局所。
明示トランザクション無しだと次の文は空設定を見て RLS 評価が
`invalid input syntax for type integer: ""` で失敗し、リアクションが 0 件のままだった。

カバー:
- add: set_config → SELECT → INSERT が conn.transaction() の内側で、この順に実行される
- remove: set_config → SELECT → DELETE が conn.transaction() の内側で実行される
- is_bot_reaction が INSERT に引き渡される
- SSE publish はトランザクション commit 後に呼ばれる
- DB 失敗時は exc_info 付き warning を出し SSE を publish しない
- 実 PostgreSQL（RLS_TEST_DATABASE_URL 設定時のみ）: トランザクション無しは失敗・有りは成功

実行:
    pytest backend/tests/test_reaction_writer_rls_tx.py -v
"""
from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import asyncpg
import pytest

from app.discord_gateway.reaction_writer import ReactionWriter

SNOWFLAKE = "222222222222222222"
CHANNEL_ID = "111111111111111111"
SSE_PATH = "app.discord_gateway.reaction_writer.sse_pubsub.publish_inbox_update"


def _writer_with_recorder() -> tuple[ReactionWriter, AsyncMock, list[str]]:
    """conn の呼び出しを events に時系列で記録する ReactionWriter を返す。"""
    events: list[str] = []
    conn = AsyncMock()

    async def _execute(sql, *args):
        if "set_config" in sql:
            events.append("set_config")
        elif "INSERT INTO" in sql:
            events.append("insert")
        elif "DELETE FROM" in sql:
            events.append("delete")
        return "OK"

    async def _fetchrow(sql, *args):
        events.append("select")
        return {"id": 77}

    conn.execute.side_effect = _execute
    conn.fetchrow.side_effect = _fetchrow

    tx_cm = MagicMock()

    async def _tx_enter(*_):
        events.append("tx_begin")

    async def _tx_exit(*_):
        events.append("tx_commit")
        return False

    tx_cm.__aenter__ = AsyncMock(side_effect=_tx_enter)
    tx_cm.__aexit__ = AsyncMock(side_effect=_tx_exit)
    conn.transaction = MagicMock(return_value=tx_cm)

    acquire_cm = MagicMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire.return_value = acquire_cm
    writer = ReactionWriter("postgresql://unused")
    writer._pool = pool
    return writer, conn, events


async def _run(writer: ReactionWriter, action: str, is_bot: bool = True) -> None:
    await writer.process_reaction(
        tenant_id=1, channel_id=CHANNEL_ID, message_id=SNOWFLAKE, user_id="u1",
        emoji=SimpleNamespace(id=None, name="❤️", animated=False),
        member=SimpleNamespace(display_name="Bot", name="bot"),
        action=action, is_bot_reaction=is_bot,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("is_bot", [True, False])
async def test_add_runs_set_config_select_insert_inside_transaction(is_bot):
    writer, conn, events = _writer_with_recorder()

    with patch(SSE_PATH, new=AsyncMock()) as sse:
        events_at_sse: list[str] = []
        sse.side_effect = lambda *_: events_at_sse.extend(events)
        await _run(writer, "add", is_bot)

    assert events == ["tx_begin", "set_config", "select", "insert", "tx_commit"]
    assert events_at_sse == events  # SSE は commit 後
    conn.transaction.assert_called_once_with()
    insert_args = [c.args for c in conn.execute.await_args_list if "INSERT INTO" in c.args[0]][0]
    assert insert_args[-1] is is_bot
    sse.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_remove_runs_set_config_select_delete_inside_transaction():
    writer, _conn, events = _writer_with_recorder()

    with patch(SSE_PATH, new=AsyncMock()):
        await _run(writer, "remove")

    assert events == ["tx_begin", "set_config", "select", "delete", "tx_commit"]


@pytest.mark.asyncio
async def test_db_failure_logs_warning_with_exc_info_and_skips_sse(caplog):
    writer, conn, _events = _writer_with_recorder()
    conn.fetchrow.side_effect = RuntimeError("boom")

    with patch(SSE_PATH, new=AsyncMock()) as sse, caplog.at_level(logging.WARNING):
        await _run(writer, "add")

    record = next(r for r in caplog.records if "DB 書き込み失敗" in r.getMessage())
    assert record.exc_info is not None
    sse.assert_not_awaited()


# ---------------------------------------------------------------------------
# 実 PostgreSQL（RLS の実挙動）。RLS_TEST_DATABASE_URL 未設定なら skip。
# ---------------------------------------------------------------------------

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")
_TENANT_ID = 98
_SCHEMA = f"tenant_{_TENANT_ID:03d}"


def _dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _bootstrap(admin_dsn: str) -> None:
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}")
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {_SCHEMA}.meta_messages (
                id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL, message_id TEXT)
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {_SCHEMA}.meta_message_reactions (
                id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL,
                meta_message_id INTEGER NOT NULL, emoji_name TEXT NOT NULL,
                emoji_id TEXT, emoji_animated BOOLEAN NOT NULL DEFAULT FALSE,
                reactor_discord_user_id TEXT NOT NULL, reactor_display_name TEXT,
                is_bot_reaction BOOLEAN NOT NULL DEFAULT FALSE,
                CONSTRAINT uq_reaction_per_user_emoji
                    UNIQUE (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id))
        """)
        for table in ("meta_messages", "meta_message_reactions"):
            await conn.execute(f"ALTER TABLE {_SCHEMA}.{table} ENABLE ROW LEVEL SECURITY")
            await conn.execute(f"ALTER TABLE {_SCHEMA}.{table} FORCE ROW LEVEL SECURITY")
            await conn.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {_SCHEMA}.{table}")
            await conn.execute(f"""
                CREATE POLICY tenant_isolation ON {_SCHEMA}.{table}
                USING (tenant_id = (current_setting('app.tenant_id', true))::integer)
                WITH CHECK (tenant_id = (current_setting('app.tenant_id', true))::integer)
            """)
        await conn.execute(f"GRANT USAGE ON SCHEMA {_SCHEMA} TO PUBLIC")
        await conn.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA {_SCHEMA} TO PUBLIC")
        await conn.execute(f"GRANT ALL ON ALL SEQUENCES IN SCHEMA {_SCHEMA} TO PUBLIC")
        await conn.execute(f"TRUNCATE {_SCHEMA}.meta_messages, {_SCHEMA}.meta_message_reactions")
        await conn.execute(
            f"INSERT INTO {_SCHEMA}.meta_messages (tenant_id, message_id) VALUES ($1, $2)",
            _TENANT_ID, SNOWFLAKE,
        )
    finally:
        await conn.close()


@pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_real_pg_bare_set_config_fails_and_transaction_succeeds():
    await _bootstrap(_dsn(ADMIN_PG_URL))
    writer = ReactionWriter(_dsn(APP_PG_URL))
    await writer.initialize()
    emoji = SimpleNamespace(id=None, name="❤️", animated=False)
    member = SimpleNamespace(display_name="Bot", name="bot")
    verify = await asyncpg.connect(_dsn(ADMIN_PG_URL))
    try:
        # 修正前の挙動: トランザクション無しの set_config は次の文で消える
        async with writer._pool.acquire() as conn:
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(_TENANT_ID))
            with pytest.raises(asyncpg.exceptions.InvalidTextRepresentationError):
                await conn.fetchrow(f"SELECT id FROM {_SCHEMA}.meta_messages LIMIT 1")

        # 修正後: process_reaction が行を書き込む
        with patch(SSE_PATH, new=AsyncMock()):
            await writer.process_reaction(
                tenant_id=_TENANT_ID, channel_id=CHANNEL_ID, message_id=SNOWFLAKE,
                user_id="u1", emoji=emoji, member=member, action="add", is_bot_reaction=True,
            )
        rows = await verify.fetch(
            f"SELECT emoji_name, is_bot_reaction FROM {_SCHEMA}.meta_message_reactions"
        )
        assert [(r["emoji_name"], r["is_bot_reaction"]) for r in rows] == [("❤️", True)]

        with patch(SSE_PATH, new=AsyncMock()):
            await writer.process_reaction(
                tenant_id=_TENANT_ID, channel_id=CHANNEL_ID, message_id=SNOWFLAKE,
                user_id="u1", emoji=emoji, member=member, action="remove", is_bot_reaction=True,
            )
        assert await verify.fetchval(f"SELECT count(*) FROM {_SCHEMA}.meta_message_reactions") == 0
    finally:
        await verify.close()
        await writer.close()
