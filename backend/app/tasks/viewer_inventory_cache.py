"""閲覧ページ用の在庫の作り置き（ADR-1019 段2・設計 D3）。

配信の正本（build_distribution_rows）から1分ごとに在庫の写しを Redis に作る。
閲覧 API（GET /api/v1/viewer/inventory）はこの写しをそのまま返す。
失敗しても前回の写しは残す（TTL 24時間）。3回続けて失敗したら Discord に1回だけ知らせる。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from celery import shared_task

from app.services.tcg_distribution_svc import (
    _GAS_COLUMNS,
    FRESH_WINDOW_HOURS,
    build_distribution_rows,
    status_to_offer_type,
)

logger = logging.getLogger(__name__)

CACHE_KEY = "viewer:inventory:v1"
LOCK_KEY = "viewer:inventory:lock"
FAIL_KEY = "viewer:inventory:fail_count"
CACHE_TTL_SECONDS = 86400
LOCK_TTL_SECONDS = 55
NOTIFY_AT_FAILURE = 3


def to_cache_rows(rows: list) -> list[dict]:
    """配信行（14列の並び）を、列名つきの辞書に直し、offer_type を足す（15キー）。"""
    result: list[dict] = []
    for row in rows:
        item = dict(zip(_GAS_COLUMNS, row))
        item["offer_type"] = status_to_offer_type(item["status"])
        result.append(item)
    return result


async def _record_failure(db, redis_client, reason: str) -> None:
    """失敗を数え、NOTIFY_AT_FAILURE 回目のときだけ Discord に知らせる。前回の写しには触らない。"""
    logger.error("[viewer-cache] %s", reason)
    try:
        count = await redis_client.incr(FAIL_KEY)
    except Exception as exc:  # noqa: BLE001
        logger.error("[viewer-cache] 失敗回数を数えられませんでした: %s", exc)
        return
    if count != NOTIFY_AT_FAILURE:
        return
    try:
        from app.routers.notifications import send_discord_notification  # noqa: PLC0415

        await send_discord_notification(
            db=db,
            tenant_id=4,  # tenant_004（tcg_distribution_svc の配信エラー通知と同じ）
            event_type="tcg_distribution_error",
            title="閲覧ページの在庫の作り置きが続けて失敗",
            message=f"[viewer-cache] {NOTIFY_AT_FAILURE}回続けて失敗しました: {reason}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[viewer-cache] Discord 通知失敗: %s", exc)


async def refresh_once(db, redis_client) -> str:
    """1回分の作り置き。戻り値は "locked"・"ok"・"hold"・"failed"。"""
    if not await redis_client.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL_SECONDS):
        return "locked"  # ロックは解放しない（同じ1分に2回作らないため）

    try:
        result = await build_distribution_rows(db)
        if result.kind == "hold":
            return "hold"
        if result.kind == "ok":
            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "fresh_window_hours": FRESH_WINDOW_HOURS,
                "rows": to_cache_rows(result.rows),
            }
            await redis_client.set(CACHE_KEY, json.dumps(payload, ensure_ascii=False), ex=CACHE_TTL_SECONDS)
            await redis_client.set(FAIL_KEY, 0)
            return "ok"
        reason = result.message  # unset・error
    except Exception as exc:  # noqa: BLE001
        reason = f"{type(exc).__name__}: {exc}"
    await _record_failure(db, redis_client, reason)
    return "failed"


def _run() -> str:
    """ワンショットのエンジンとセッションで refresh_once を1回回す（_run_auto_distribution と同じ形）。"""
    from redis import asyncio as aioredis  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.database import DATABASE_URL  # noqa: PLC0415

    async def _go() -> str:
        engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=0,
            connect_args={
                "prepared_statement_cache_size": 0,
                "server_settings": {"application_name": "salesanchor_celery_viewer_cache"},
            },
        )
        redis_client = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=5,
        )
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as db:
                return await refresh_once(db, redis_client)
        finally:
            await engine.dispose()
            await redis_client.aclose()

    return asyncio.run(_go())


@shared_task(name="app.tasks.viewer_inventory_cache.refresh_viewer_inventory", ignore_result=True)
def refresh_viewer_inventory() -> None:
    try:
        _run()
    except Exception as exc:  # noqa: BLE001
        logger.error("[viewer-cache] 作り置きの実行に失敗: %s: %s", type(exc).__name__, exc)
