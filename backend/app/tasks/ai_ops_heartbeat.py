"""1 分ごとの heartbeat タスク（ADR-1012 段階1 便5）。beat が動き、worker が拾ったときだけ時刻が進む。"""

from celery import shared_task

from app.celery_health import record_heartbeat


@shared_task(name="app.tasks.ai_ops_heartbeat.celery_heartbeat", ignore_result=True)
def celery_heartbeat() -> None:
    record_heartbeat()
