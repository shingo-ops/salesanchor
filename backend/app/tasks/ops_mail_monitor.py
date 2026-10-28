from __future__ import annotations

"""
運用の受け箱 → さくらの点検・障害のメール監視タスク（outage-recovery-watch 便3）。

Celery Beat から 5 分ごとに呼ばれ、IMAP で受け箱を確認して運用 Discord に通知する。
失敗しても Sales Anchor 本体を止めない（例外は握り潰してログのみ）。
"""

import logging

from app.celery_app import celery_app
from app.services.ops_mail_notifier import check_and_notify

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.ops_mail_monitor.check_ops_mail_inbox",
    bind=True,
    max_retries=0,  # IMAP 失敗は次の beat 周期で自動リトライされるため再試行不要
)
def check_ops_mail_inbox(self: object) -> dict:  # type: ignore[override]
    """運用の受け箱を確認し、さくらの点検・障害のメールを Discord に通知する。

    Returns:
        {"notified": int} — 今回通知した件数
    """
    try:
        count = check_and_notify()
        return {"notified": count}
    except Exception as exc:
        logger.warning("[ops_mail_monitor] 予期しないエラー (skip): %s", type(exc).__name__)
        return {"notified": 0}
