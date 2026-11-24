"""ADR-1013 パスキーの週報の試験。DB なし。"""

from __future__ import annotations

import importlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from celery.schedules import crontab

from app.tasks import passkey_weekly_report as m

JST = ZoneInfo("Asia/Tokyo")


def _jst(*args) -> datetime:
    return datetime(*args, tzinfo=JST)


def _window():
    return m.windows(_jst(2026, 11, 30, 9, 10))


def test_w1_windows():
    expect = (_jst(2026, 10, 31), _jst(2026, 11, 23), _jst(2026, 11, 30))
    assert m.windows(_jst(2026, 11, 30, 9, 10)) == expect
    assert m.windows(_jst(2026, 11, 30, 0, 0)) == expect
    assert m.windows(_jst(2026, 11, 29, 23, 59))[2] == _jst(2026, 11, 23)


def test_w2_calendar_day_boundary():
    start30, start7, end = _window()
    rows = [
        (3, m.PASSKEY_PATH, 200, None, _jst(2026, 11, 29, 23, 59)),
        (3, m.PASSKEY_PATH, 200, None, _jst(2026, 11, 30, 0, 0)),
    ]
    out = m.tally([3], rows, start30, start7, end)
    assert out[3]["7"]["passkey"] == 1
    assert out[3]["30"]["passkey"] == 1


def test_w3_zero_denominator():
    start30, start7, end = _window()
    counts = m.tally([5], [], start30, start7, end)
    msg = m.build_message(counts, start30, start7, end)
    line = [x for x in msg.splitlines() if x.startswith("id 5")][0]
    assert line.count("割合 -") == 2


def test_w4_classification():
    start30, start7, end = _window()
    at = _jst(2026, 11, 25, 12, 0)
    rows = [
        (1, m.LOGIN_PATH, 200, None, at),
        (1, m.POLL_PATH, 200, "approved_admin", at),
        (1, m.POLL_PATH, 200, "approved_device", at),
        (1, m.RECOVERY_PATH, 200, None, at),
        (1, m.LOGIN_PATH, 202, None, at),
        (1, m.POLL_PATH, 200, "pending", at),
        (1, m.PASSKEY_PATH, 200, None, at),
    ]
    c7 = m.tally([1], rows, start30, start7, end)[1]["7"]
    assert c7 == {"passkey": 1, "password": 1, "other": 3}
    assert m.ratio(c7) == "50%"


def test_w5_only_listed_admins():
    start30, start7, end = _window()
    rows = [(99, m.PASSKEY_PATH, 200, None, _jst(2026, 11, 25))]
    out = m.tally([1], rows, start30, start7, end)
    assert list(out) == [1]
    assert out[1]["7"]["passkey"] == 0


def test_w6_no_personal_info():
    start30, start7, end = _window()
    rows = [(1, m.PASSKEY_PATH, 200, None, _jst(2026, 11, 25))]
    msg = m.build_message(m.tally([1], rows, start30, start7, end), start30, start7, end)
    assert "@" not in msg
    for word in ("email", "full_name", "client_ip", "user_agent"):
        assert word not in m.ADMINS_SQL
        assert word not in m.EVENTS_SQL


def _engine_with(execute: AsyncMock) -> MagicMock:
    conn = MagicMock()
    conn.execute = execute
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = cm
    return engine


def _result(rows):
    res = MagicMock()
    res.all.return_value = rows
    return res


@pytest.mark.asyncio
async def test_w7_sends_report():
    execute = AsyncMock(
        side_effect=[
            _result([(1,)]),
            _result([(1, m.PASSKEY_PATH, 200, None, _jst(2026, 11, 25))]),
        ]
    )
    with patch("app.database.engine", _engine_with(execute)), patch.object(
        m, "_post_discord", new_callable=AsyncMock
    ) as post:
        out = await m._run_report(_jst(2026, 11, 30, 9, 10))
    post.assert_awaited_once()
    assert post.await_args.args[0].splitlines()[0].startswith("🔑 パスキーの週報")
    assert out["counts"][1]["7"]["passkey"] == 1


@pytest.mark.asyncio
async def test_w8_failure_notifies_and_raises():
    execute = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("app.database.engine", _engine_with(execute)), patch.object(
        m, "_post_discord", new_callable=AsyncMock
    ) as post:
        with pytest.raises(RuntimeError):
            await m._run_report(_jst(2026, 11, 30, 9, 10))
    post.assert_awaited_once()
    assert post.await_args.args[0].startswith("🔴")


def test_w9_beat_schedule_registered():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["passkey-weekly-report"]
    assert entry["task"] == "app.tasks.passkey_weekly_report.run_passkey_weekly_report"
    assert "app.tasks.passkey_weekly_report" in celery_app.conf.include
    importlib.import_module("app.tasks.passkey_weekly_report")
    assert entry["task"] in celery_app.tasks
    s = entry["schedule"]
    assert isinstance(s, crontab)
    assert s._orig_hour == 9 and s._orig_minute == 10 and str(s._orig_day_of_week) == "1"
