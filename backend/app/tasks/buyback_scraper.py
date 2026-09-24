"""
買取相場一括取得 Celery タスク。

ADR-157: 買取相場ログ

スケジュール: 1日3回（JST 10:00/13:00/22:00、beat_schedule "fetch-buyback-prices"）
対象: シンソク（REST API） + 買取ホムラ（HTML スクレイピング）
"""

from __future__ import annotations

import asyncio
import logging
import os

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://myapp_user:password@postgres:5432/myapp_db",
)


def _build_async_session_factory():
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=2,
        pool_recycle=1800,
        pool_pre_ping=True,
    )
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@shared_task(name="buyback.fetch_all_prices")
def fetch_all_buyback_prices() -> None:
    """全店舗の買取価格を取得して DB に保存する。

    シンソク → 買取ホムラ の順に実行する。
    いずれかが失敗しても他方は続行する（各サービス内部でエラーハンドリング済み）。
    価格取得完了後、アラートチェックを実行して閾値超過時に Discord 通知を送る。
    """
    logger.info("[buyback_scraper] 全店舗価格取得タスク開始")
    asyncio.run(_fetch_all())
    logger.info("[buyback_scraper] 全店舗価格取得タスク完了")

    try:
        fired = asyncio.run(_run_alert_check())
        logger.info("[buyback_scraper] アラートチェック完了: %d 件発火", fired)
    except Exception:  # noqa: BLE001
        logger.exception("[buyback_scraper] アラートチェックでエラー")


async def _run_alert_check() -> int:
    """アラートチェックを非同期で実行する。"""
    from app.services.buyback_scraper.alert_checker import check_alerts

    return await check_alerts()


async def _fetch_all() -> None:
    """非同期で全店舗のデータを取得する。"""
    from app.services.buyback_scraper.homura import fetch_homura_prices
    from app.services.buyback_scraper.shinsoku import fetch_shinsoku_prices

    session_factory = _build_async_session_factory()

    async with session_factory() as db:
        try:
            await fetch_shinsoku_prices(db)
        except Exception:  # noqa: BLE001
            logger.exception("[buyback_scraper] シンソク取得タスクでエラー")

    async with session_factory() as db:
        try:
            await fetch_homura_prices(db)
        except Exception:  # noqa: BLE001
            logger.exception("[buyback_scraper] 買取ホムラ取得タスクでエラー")
