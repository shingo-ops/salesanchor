"""SA-02 §10 日次突合タスクの単体テスト。

検証項目:
  1. 差異ゼロ時も Discord に通知する（監視停止と区別するため毎日1行通知）
  2. 差異あり時は ⚠ 強調付きで Discord 通知する（diff!=0）
  3. タスクが celery_app の beat_schedule に登録されている
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# 1. 差異ゼロ → Discord に1行通知する（監視稼働の証跡）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_discord_called_even_when_diff_zero():
    """meta と conv が同数でも毎日 _post_discord を呼ぶ（監視停止と区別）。"""
    from app.tasks.sa02_recon_monitor import _run_daily_recon

    mock_result = MagicMock()
    mock_result.scalar.return_value = 5
    mock_result.fetchall.return_value = [(1,)]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.tasks.sa02_recon_monitor._post_discord", new=AsyncMock()) as mock_discord,
        patch("app.database.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_cm

        result = await _run_daily_recon()

    assert result["diff"] == 0
    mock_discord.assert_called_once()
    # 差異ゼロ時は1行サマリー（⚠なし）
    notif_text = mock_discord.call_args[0][0]
    assert "一致 ✅" in notif_text
    assert "⚠️" not in notif_text


# ---------------------------------------------------------------------------
# 2. 差異あり → Discord 通知する
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_discord_called_when_diff_nonzero():
    """meta と conv の件数が違う場合は _post_discord を呼ぶ。"""
    from app.tasks.sa02_recon_monitor import _run_daily_recon

    db = AsyncMock()
    call_count = 0

    async def side_effect(q, params=None):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        # 1回目: tenants 一覧
        if call_count == 1:
            m.fetchall.return_value = [(1,)]
        # 2回目: meta_messages count → 10
        elif call_count == 2:
            m.scalar.return_value = 10
        # 3回目: conversation_logs count → 7
        elif call_count == 3:
            m.scalar.return_value = 7
        return m

    db.execute.side_effect = side_effect

    with (
        patch("app.tasks.sa02_recon_monitor._post_discord", new=AsyncMock()) as mock_discord,
        patch("app.database.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_cm

        result = await _run_daily_recon()

    assert result["diff"] == 3
    mock_discord.assert_called_once()


# ---------------------------------------------------------------------------
# 3. beat_schedule に登録されている
# ---------------------------------------------------------------------------
def test_registered_in_beat_schedule():
    from app.celery_app import celery_app

    assert "sa02-daily-recon" in celery_app.conf.beat_schedule
    task_name = celery_app.conf.beat_schedule["sa02-daily-recon"]["task"]
    assert task_name == "app.tasks.sa02_recon_monitor.run_sa02_daily_recon"
