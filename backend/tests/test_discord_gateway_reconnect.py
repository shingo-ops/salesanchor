"""
run_gateway の再接続制御テスト。

Discord から「短時間に1000回接続」として Token リセットされた障害の再発防止。
- reconnect=False により discord.py 内部の無制限再接続を無効化
- 正常切断時（else ブランチ）も backoff スリープを挟む
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import discord
import pytest

from app.discord_gateway.client import run_gateway
from app.discord_gateway.config import SingleBotConfig


def _make_config() -> SingleBotConfig:
    return SingleBotConfig(bot_token="TEST_TOKEN")


@pytest.mark.asyncio
async def test_run_gateway_uses_reconnect_false():
    """client.start は reconnect=False で呼ばれること（無制限再接続防止）。"""
    config = _make_config()
    started_with: list[dict] = []

    async def fake_start(token, *, reconnect):
        started_with.append({"token": token, "reconnect": reconnect})
        # 1回だけ正常終了させてループを抜けさせる
        raise asyncio.CancelledError

    mock_client = AsyncMock()
    mock_client.start = fake_start
    mock_client.close = AsyncMock()

    with patch("app.discord_gateway.client.JarvisDiscordClient", return_value=mock_client):
        with pytest.raises(asyncio.CancelledError):
            await run_gateway(config)

    assert len(started_with) == 1
    assert started_with[0]["reconnect"] is False, "reconnect=True は短時間多接続を引き起こすため禁止"


@pytest.mark.asyncio
async def test_run_gateway_normal_exit_sleeps_before_reconnect():
    """正常切断（else ブランチ）でも asyncio.sleep を挟んでから再接続すること。"""
    config = _make_config()
    call_count = 0
    sleep_calls: list[float] = []

    async def fake_start(token, *, reconnect):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return  # 正常終了（else ブランチへ）
        raise asyncio.CancelledError  # 2回目でループ終了

    mock_client = AsyncMock()
    mock_client.start = fake_start
    mock_client.close = AsyncMock()

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("app.discord_gateway.client.JarvisDiscordClient", return_value=mock_client):
        with patch("asyncio.sleep", side_effect=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await run_gateway(config)

    assert len(sleep_calls) >= 1, "正常切断後もスリープなしで即再接続してはならない"
    assert sleep_calls[0] > 0


@pytest.mark.asyncio
async def test_run_gateway_login_failure_raises_immediately():
    """LoginFailure は再試行せず即座に re-raise すること。"""
    config = _make_config()

    async def fake_start(token, *, reconnect):
        raise discord.LoginFailure("invalid token")

    mock_client = AsyncMock()
    mock_client.start = fake_start
    mock_client.close = AsyncMock()

    with patch("app.discord_gateway.client.JarvisDiscordClient", return_value=mock_client):
        with pytest.raises(discord.LoginFailure):
            await run_gateway(config)


@pytest.mark.asyncio
async def test_run_gateway_stops_after_max_reconnect_attempts():
    """例外が _MAX_RECONNECT_ATTEMPTS 回続いたら RuntimeError を raise すること。"""
    from app.discord_gateway.client import _MAX_RECONNECT_ATTEMPTS

    config = _make_config()
    call_count = 0

    async def fake_start(token, *, reconnect):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("network error")

    mock_client = AsyncMock()
    mock_client.start = fake_start
    mock_client.close = AsyncMock()

    with patch("app.discord_gateway.client.JarvisDiscordClient", return_value=mock_client):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="max reconnect attempts"):
                await run_gateway(config)

    assert call_count == _MAX_RECONNECT_ATTEMPTS
