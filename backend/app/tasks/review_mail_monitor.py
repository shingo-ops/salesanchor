from __future__ import annotations

"""
review@salesanchor.jp 新着メール監視タスク。

Celery Beat から 5 分ごとに呼ばれ、IMAP で新着メールを確認して Discord に通知する。
失敗しても Sales Anchor 本体を止めない（例外は握り潰してログのみ）。
"""

import logging

from app.celery_app import celery_app
from app.services.review_mail_notifier import check_and_notify

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.review_mail_monitor.check_review_mail_inbox",
    bind=True,
    max_retries=0,  # IMAP 失敗は次の beat 周期で自動リトライされるため再試行不要
)
def check_review_mail_inbox(self: object) -> dict:  # type: ignore[override]
    """review@salesanchor.jp の INBOX を確認し、未通知メールを Discord に通知する。

    Returns:
        {"notified": int} — 今回通知した件数
    """
    try:
        count = check_and_notify()
        if count > 0:
            logger.info("[review_mail_monitor] Discord 通知 %d 件", count)
        else:
            logger.debug("[review_mail_monitor] 新着通知なし")
        return {"notified": count}
    except Exception as exc:
        logger.warning("[review_mail_monitor] 予期しないエラー (skip): %s", exc)
        return {"notified": 0}
