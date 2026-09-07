"""
為替レート定期取得タスク（Celery Beat）。

public.app_fx_rates に USD/JPY レートを 1日2回（AM6:00 / PM6:00 JST）UPSERT する。

設計:
  - app.services.fx_rate.get_fx_rate("USD") を呼ぶだけ（fx_rate.py は改変しない）
  - 成功: public.app_fx_rates に UPSERT（currency='USD', rate_jpy, fetched_at）
  - 失敗(None 返却 / 例外): logger.warning のみ。前回行を残す。タスクは正常終了する。
  - operator コンテキストが必要（public スキーマへの書き込みに RLS policy が要求）

参考:
  - backend/app/tasks/maintenance.py（Celery 同期タスクのパターン）
  - backend/app/services/fx_rate.py（外部API呼び出し実装）
  - migrations/20260628_170000_add_app_fx_rates.sql（テーブル定義・RLS）
"""

from __future__ import annotations

import logging
import os

from celery import shared_task
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)


def _get_sync_engine():
    return create_engine(DATABASE_URL, echo=False)


@shared_task(name="app.tasks.fx_rate_updater.update_usd_jpy_rate")
def update_usd_jpy_rate() -> None:
    """USD/JPY 為替レートを外部APIから取得して public.app_fx_rates に UPSERT する。

    失敗時は前回値を残したまま警告ログだけ出力する（non-fatal）。
    """
    from app.services.fx_rate import get_fx_rate

    logger.info("[fx_rate_updater] USD/JPY レート取得開始")

    try:
        snapshot = get_fx_rate("USD")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[fx_rate_updater] get_fx_rate 呼び出し例外: %s", exc)
        return

    if snapshot is None:
        logger.warning("[fx_rate_updater] get_fx_rate が None を返した（外部API障害）。前回値を維持。")
        return

    rate_jpy = snapshot["rate"]
    fetched_at = snapshot["fetched_at"]

    engine = _get_sync_engine()
    Session = sessionmaker(bind=engine)
    with Session() as session:
        try:
            # operator コンテキストで RLS の書き込みポリシーを通過する
            session.execute(text("SET app.is_operator = 'true'"))
            session.execute(
                text(
                    """
                    INSERT INTO public.app_fx_rates (currency, rate_jpy, fetched_at)
                    VALUES ('USD', :rate, :fetched)
                    ON CONFLICT (currency) DO UPDATE
                        SET rate_jpy   = EXCLUDED.rate_jpy,
                            fetched_at = EXCLUDED.fetched_at
                    """
                ),
                {"rate": str(rate_jpy), "fetched": fetched_at},
            )
            session.commit()
            logger.info(
                "[fx_rate_updater] UPSERT 完了: USD/JPY = %.4f (fetched_at=%s)",
                rate_jpy,
                fetched_at,
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            logger.warning("[fx_rate_updater] DB UPSERT 失敗: %s。前回値を維持。", exc)
