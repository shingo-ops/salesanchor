"""ADR-1012 段階3 便D: celery の worker と beat が「生きている印」を更新する仕組み。

worker: bootstep が worker の timer で 30 秒ごとに更新する（celery 公式 extending の DeadlockDetection と同じ形）。
beat: celery beat -S app.celery_alive:AliveScheduler で起動し、予定の確認（tick）のたびに更新する。
"""

from celery import bootsteps
from celery.beat import PersistentScheduler

from app.container_alive import (
    BEAT_ALIVE_PATH,
    TOUCH_INTERVAL_SECONDS,
    WORKER_ALIVE_PATH,
    touch_alive,
)


class WorkerAliveStep(bootsteps.StartStopStep):
    requires = {"celery.worker.components:Timer"}

    def __init__(self, worker, **kwargs):
        super().__init__(worker, **kwargs)
        self.tref = None

    def start(self, worker):
        touch_alive(WORKER_ALIVE_PATH)
        self.tref = worker.timer.call_repeatedly(
            TOUCH_INTERVAL_SECONDS, touch_alive, (WORKER_ALIVE_PATH,), priority=10,
        )

    def stop(self, worker):
        if self.tref is not None:
            self.tref.cancel()
            self.tref = None


class AliveScheduler(PersistentScheduler):
    def tick(self, *args, **kwargs):
        interval = super().tick(*args, **kwargs)
        touch_alive(BEAT_ALIVE_PATH)
        return interval
