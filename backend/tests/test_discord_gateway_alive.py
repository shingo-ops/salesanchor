"""ADR-1012 段階3 便D: discord-gateway の生きている印の試験。"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.discord_gateway import main as gw_main


@pytest.mark.asyncio
async def test_alive_loop_touches_before_sleep(tmp_path):
    marker = tmp_path / "gw-alive"
    sleep_mock = AsyncMock(side_effect=asyncio.CancelledError)
    with patch.object(gw_main, "GATEWAY_ALIVE_PATH", str(marker)), patch.object(
        gw_main.asyncio, "sleep", sleep_mock
    ):
        with pytest.raises(asyncio.CancelledError):
            await gw_main._alive_loop()
    assert marker.exists()
    sleep_mock.assert_awaited_once_with(30.0)


@pytest.mark.asyncio
async def test_main_async_runs_alive_task_without_token_and_stops_it():
    seen: list[str] = []

    async def fake_run(config):
        seen.extend(t.get_name() for t in asyncio.all_tasks())
        return 0

    with patch.object(
        gw_main, "load_single_bot_config", side_effect=RuntimeError("no token")
    ), patch.object(gw_main, "_run_with_shutdown", side_effect=fake_run), patch.object(
        gw_main, "touch_alive"
    ):
        assert await gw_main._main_async() == 0

    assert "gw-alive" in seen
    assert "gw-alive" not in [t.get_name() for t in asyncio.all_tasks()]
