"""
TCG 確認工程: 期限切れ保留ジョブの破棄タスク。

review_status='pending_review' かつ created_at < NOW() - INTERVAL '24 hours'
の import_jobs を review_status='discarded' に更新し、
pending_messages を NULL にする（行は残す: 監査のため）。

beat_schedule で 1 時間ごとに実行される。
"""
from __future__ import annotations

import logging
import os

from celery import shared_task
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

TCG_SCHEMA = "tenant_004"

_DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)


def _get_sync_engine():
    return create_engine(_DATABASE_URL, echo=False)


@shared_task(name="app.tasks.tcg_import_discard.discard_stale_pending_jobs")
def discard_stale_pending_jobs() -> dict:
    """
    24 時間を超えた pending_review ジョブを discarded に更新する。

    Returns:
        {"discarded_count": int}
    """
    engine = _get_sync_engine()
    Session = sessionmaker(engine)

    with Session() as db:
        result = db.execute(
            text(
                f"""
                UPDATE {TCG_SCHEMA}.import_jobs
                SET review_status    = 'discarded',
                    pending_messages = NULL
                WHERE review_status = 'pending_review'
                  AND created_at < NOW() - INTERVAL '24 hours'
                RETURNING id
                """
            )
        )
        discarded_ids = [str(r[0]) for r in result.fetchall()]
        db.commit()

    count = len(discarded_ids)
    if count > 0:
        logger.info(
            "[tcg_import_discard] %d 件の pending_review ジョブを discarded に更新: %s",
            count,
            discarded_ids,
        )
    return {"discarded_count": count}
