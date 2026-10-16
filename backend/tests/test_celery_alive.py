"""ADR-1012 段階3 便D: 生きている印（container_alive / celery_alive）の試験。

本物の worker・beat・redis は起こさない。
"""

import os
from unittest.mock import MagicMock, patch

from celery.beat import PersistentScheduler

from app.celery_alive import AliveScheduler, WorkerAliveStep
from app.container_alive import TOUCH_INTERVAL_SECONDS, WORKER_ALIVE_PATH, touch_alive


def test_touch_alive_creates_and_updates(tmp_path):
    path = tmp_path / "alive"
    touch_alive(str(path))
    assert path.exists()

    os.utime(path, (1000, 1000))
    before = os.stat(path).st_mtime
    touch_alive(str(path))
    assert os.stat(path).st_mtime > before


def test_touch_alive_does_not_raise_when_unwritable(tmp_path):
    touch_alive(str(tmp_path / "no-dir" / "x"))


def test_alive_scheduler_tick_returns_parent_value_and_touches(tmp_path):
    marker = tmp_path / "beat-alive"
    scheduler = AliveScheduler.__new__(AliveScheduler)
    with patch.object(PersistentScheduler, "tick", return_value=42.0) as parent_tick, patch(
        "app.celery_alive.BEAT_ALIVE_PATH", str(marker)
    ):
        assert scheduler.tick() == 42.0
    parent_tick.assert_called_once()
    assert marker.exists()


def test_worker_alive_step_start_and_stop():
    worker = MagicMock()
    step = WorkerAliveStep(worker)
    with patch("app.celery_alive.touch_alive") as touch_mock:
        step.start(worker)
    worker.timer.call_repeatedly.assert_called_once_with(
        30.0, touch_mock, (WORKER_ALIVE_PATH,), priority=10,
    )
    touch_mock.assert_called_once_with(WORKER_ALIVE_PATH)
    assert TOUCH_INTERVAL_SECONDS == 30.0
    tref = worker.timer.call_repeatedly.return_value
    step.stop(worker)
    tref.cancel.assert_called_once()


def test_worker_alive_step_registered_in_celery_app():
    from app.celery_app import celery_app

    assert WorkerAliveStep in celery_app.steps["worker"]
