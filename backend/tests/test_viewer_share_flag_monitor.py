"""ADR-1019 段6: 閲覧者の使い回しの疑いの通知（重複防止・未設定時・文面・beat 登録）。"""
from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.schedules import crontab

from app.tasks import viewer_share_flag_monitor as mon

HITS = [(3, "many_ips", []), (5, "shared_ip", [7, 9])]


class _Redis:
    def __init__(self, keys=None) -> None:
        self.keys = dict(keys or {})
        self.ttls: dict[str, int] = {}

    def exists(self, key):
        return key in self.keys

    def set(self, key, value, ex=None):
        self.keys[key] = value
        self.ttls[key] = ex


def _session_cm():
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock())
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _run(hits, *, redis, url="https://example.invalid/hook", post_ok=True):
    post = AsyncMock(return_value=post_ok)
    with (
        patch("app.database.AsyncSessionLocal", return_value=_session_cm()),
        patch.object(mon, "share_flag_hits", new=AsyncMock(return_value=hits)),
        patch.object(mon, "_get_webhook_url", return_value=url),
        patch.object(mon, "_get_redis", return_value=redis),
        patch.object(mon, "_post_discord_webhook", new=post),
    ):
        import asyncio

        result = asyncio.run(mon._run_report())
    return result, post


def test_build_message_has_ids_only():
    many = mon.build_message(3, "many_ips", [])
    shared = mon.build_message(5, "shared_ip", [7, 9])
    assert many == "閲覧者の使い回しの疑い：id 3 が24時間に3か所以上からログインしました。管理画面で確認してください。"
    assert shared == "閲覧者の使い回しの疑い：id 5 が id 7, 9 と同じ場所からログインしました。管理画面で確認してください。"
    for text in (many, shared):
        assert "@" not in text and "." not in text.replace("。", "")


def test_sends_once_and_sets_keys_with_30_day_ttl():
    r = _Redis()
    result, post = _run(HITS, redis=r)
    assert result == {"hits": 2, "sent": 2}
    assert post.await_count == 2
    assert set(r.keys) == {"viewer_share_flag:notified:3:many_ips", "viewer_share_flag:notified:5:shared_ip"}
    assert set(r.ttls.values()) == {30 * 24 * 60 * 60}
    # 2回目は送らない
    result2, post2 = _run(HITS, redis=r)
    assert result2 == {"hits": 2, "sent": 0}
    post2.assert_not_awaited()


def test_failed_post_does_not_set_key():
    r = _Redis()
    result, _ = _run(HITS, redis=r, post_ok=False)
    assert result["sent"] == 0 and r.keys == {}


def test_no_redis_sends_nothing():
    result, post = _run(HITS, redis=None)
    assert result["sent"] == 0
    post.assert_not_awaited()


def test_webhook_unset_sends_nothing():
    r = _Redis()
    result, post = _run(HITS, redis=r, url=None)
    assert result["sent"] == 0 and r.keys == {}
    post.assert_not_awaited()


def test_no_hits_sends_nothing():
    result, post = _run([], redis=_Redis())
    assert result == {"hits": 0, "sent": 0}
    post.assert_not_awaited()


def test_beat_schedule_registered_hourly():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["notify-viewer-share-flags-hourly"]
    assert entry["task"] == "app.tasks.viewer_share_flag_monitor.notify_viewer_share_flags"
    assert isinstance(entry["schedule"], crontab)
    assert entry["schedule"].minute == {15}
    assert "app.tasks.viewer_share_flag_monitor" in celery_app.conf.include
    importlib.import_module("app.tasks.viewer_share_flag_monitor")
    assert entry["task"] in celery_app.tasks


@pytest.mark.parametrize("sql_name", ["_MANY_IPS_CONDITION", "_SHARED_IP_CONDITION"])
def test_flag_conditions_are_shared_with_list_sql(sql_name):
    from app.services import viewer_admin

    assert getattr(viewer_admin, sql_name) in viewer_admin._LIST_SQL
