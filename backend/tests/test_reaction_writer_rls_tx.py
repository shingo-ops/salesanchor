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

実行:
    pytest backend/tests/test_reaction_writer_rls_tx.py -v
"""
from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

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
