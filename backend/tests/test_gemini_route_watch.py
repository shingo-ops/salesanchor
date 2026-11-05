"""gemini_route_watch（解析の止まりと道の切り替えの見張り）の試験。ADR-1062。"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.tasks import gemini_route_watch as watch

AT = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)  # 日本時間 09:00


class _Redis:
    def __init__(self, data=None):
        self.data = dict(data or {})
        self.set_calls = []

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value
        self.set_calls.append((key, ex))

    def delete(self, key):
        self.data.pop(key, None)


def _session(completed, failed, last_reason="理由"):
    session = MagicMock()
    counts = MagicMock()
    counts.mappings.return_value.first.return_value = {"completed": completed, "failed": failed}
    last = MagicMock()
    last.mappings.return_value.first.return_value = {"last_reason": last_reason}
    session.execute.side_effect = [counts, last] if failed else [counts]
    return session


# T9a
def test_t9a_find_stall_sql_and_judgement():
    session = _session(0, 3)
    info = watch.find_stall(session, at=AT)
    first_call = session.execute.call_args_list[0]
    assert "make_interval" in str(first_call.args[0])
    assert ":window" in str(first_call.args[0])
    assert first_call.args[1]["window"] == 30
    assert info["stalled"] is True and info["last_reason"] == "理由"
    assert watch.find_stall(_session(1, 3), at=AT)["stalled"] is False
    assert watch.find_stall(_session(0, 0), at=AT)["stalled"] is False


def _run(info_session, redis, sends):
    with patch.object(watch, "_send", side_effect=sends) as send:
        result = watch.run_watch(info_session, redis, "https://example.invalid/hook")
    return result, send


# T9b
def test_t9b_stalled_sends_once_and_marks():
    redis = _Redis()
    result, send = _run(_session(0, 2), redis, [True])
    assert result["stall_notified"] is True and send.call_count == 1
    assert (watch.STALL_REDIS_KEY, watch.STALL_REDIS_TTL_SECONDS) in redis.set_calls


def test_t9b_stalled_already_marked_does_not_send():
    redis = _Redis({watch.STALL_REDIS_KEY: "1"})
    result, send = _run(_session(0, 2), redis, [True])
    assert result["stall_notified"] is False
    send.assert_not_called()


def test_t9b_send_failure_does_not_mark():
    redis = _Redis()
    result, send = _run(_session(0, 2), redis, [False])
    assert result["stall_notified"] is False
    assert watch.STALL_REDIS_KEY not in redis.data
    assert send.call_count == 1


# T9c
def test_t9c_recovered_sends_once_and_clears_mark():
    redis = _Redis({watch.STALL_REDIS_KEY: "1"})
    result, send = _run(_session(1, 0), redis, [True])
    assert result["recovered_notified"] is True and send.call_count == 1
    assert watch.STALL_REDIS_KEY not in redis.data


def test_t9c_recovered_without_mark_does_not_send():
    redis = _Redis()
    result, send = _run(_session(1, 0), redis, [True])
    assert result["recovered_notified"] is False
    send.assert_not_called()


# T9d
def test_t9d_switch_notified_once_per_direction():
    from app.services import gemini_route

    key = gemini_route.SWITCH_COUNT_PREFIX + "direct_to_relay"
    redis = _Redis({key: "2"})
    result, send = _run(_session(1, 0), redis, [True])
    assert result["switch_notified"] == ["direct_to_relay"]
    assert send.call_count == 1 and "2 回" in send.call_args.args[1]
    assert (watch.SWITCH_NOTIFIED_PREFIX + "direct_to_relay", watch.SWITCH_NOTIFIED_TTL_SECONDS) in redis.set_calls

    redis2 = _Redis({key: "2", watch.SWITCH_NOTIFIED_PREFIX + "direct_to_relay": "1"})
    result2, send2 = _run(_session(1, 0), redis2, [True])
    assert result2["switch_notified"] == []
    send2.assert_not_called()


# T9e
def test_t9e_run_skips_without_webhook(monkeypatch):
    monkeypatch.delenv("ADMIN_NOTIFICATION_DISCORD_WEBHOOK", raising=False)
    with patch.object(watch, "_send") as send:
        assert watch._run() == {"skipped": "no_webhook"}
    send.assert_not_called()


def test_t9e_run_skips_without_redis(monkeypatch):
    monkeypatch.setenv("ADMIN_NOTIFICATION_DISCORD_WEBHOOK", "https://example.invalid/hook")
    with patch.object(watch.gemini_route, "_get_redis", return_value=None), patch.object(watch, "_send") as send:
        assert watch._run() == {"skipped": "no_redis"}
    send.assert_not_called()


def test_t9e_run_swallows_exceptions(monkeypatch):
    monkeypatch.setenv("ADMIN_NOTIFICATION_DISCORD_WEBHOOK", "https://example.invalid/hook")
    with patch.object(watch.gemini_route, "_get_redis", return_value=_Redis()), \
            patch.object(watch, "_get_sync_engine", return_value=MagicMock()), \
            patch.object(watch, "find_stall", side_effect=RuntimeError("boom")):
        assert watch._run() == {"error": "RuntimeError"}


# T9f
def test_t9f_beat_schedule_registered():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["watch-gemini-route"]
    assert entry["task"] == "app.tasks.gemini_route_watch.watch_gemini_route"
    assert entry["schedule"] == 300.0


# T9g
def test_t9g_stall_message_unknown_reason_and_jst():
    msg = watch.build_stall_message({"failed": 3, "last_reason": None, "at": AT})
    assert "不明" in msg
    assert "2026-11-05 09:00" in msg
    assert "ADR-1062" in msg.splitlines()[0]


@pytest.mark.parametrize("direction", ["direct_to_relay", "relay_to_direct"])
def test_switch_message_has_direction_and_count(direction):
    msg = watch.build_switch_message(direction, 4)
    assert "4 回" in msg
    assert ("直接 → prod2 の中継" in msg) == (direction == "direct_to_relay")
