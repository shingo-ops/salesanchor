"""Google カレンダー → アプリの取り込み Celery 作業（ADR-1059 便2）。

- sync_google_calendar_tenant: 1 社分の取り込み（知らせの受け口と方式変更から積まれる）
- sync_google_calendar_all: 15 分おき。取り込みが有効な全社を回す
- renew_google_calendar_webhooks: 1 日 1 回。期限が近い知らせの登録を更新する
"""
from __future__ import annotations

import asyncio
import logging

from celery import shared_task
from sqlalchemy import text

from app.auth.dependencies import clear_tenant_context, set_tenant_context
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def _run_tenant(tenant_id: int) -> dict:
    from app.services import google_webhook as webhook_svc

    async with AsyncSessionLocal() as db:
        try:
            return await webhook_svc.sync_tenant_from_google(db, tenant_id)
        finally:
            await clear_tenant_context(db)


async def _run_all() -> dict:
    from app.services import google_webhook as webhook_svc

    synced = 0
    failed: list[int] = []
    async with AsyncSessionLocal() as db:
        try:
            rows = await db.execute(
                text("SELECT id FROM public.tenants WHERE is_active = true ORDER BY id")
            )
            tenant_ids = [r[0] for r in rows.fetchall()]
            for tenant_id in tenant_ids:
                try:
                    await set_tenant_context(db, tenant_id)
                    mode_row = (
                        await db.execute(
                            text("SELECT sync_mode FROM tenant_google_calendar_config")
                        )
                    ).first()
                    if not mode_row or mode_row[0] not in ("bidirectional", "read_only"):
                        continue
                    sub = (
                        await db.execute(
                            text(
                                "SELECT channel_token_hash FROM google_webhook_subscriptions"
                                " WHERE tenant_id = :tid"
                            ),
                            {"tid": tenant_id},
                        )
                    ).first()
                    if sub is None or sub[0] is None:
                        await webhook_svc.register_webhook(db, tenant_id)
                    await webhook_svc.sync_tenant_from_google(db, tenant_id)
                    synced += 1
                except Exception as e:  # noqa: BLE001
                    logger.error("Google 取り込み失敗 (tenant=%s): %s", tenant_id, e)
                    failed.append(tenant_id)
                    try:
                        await db.rollback()
                    except Exception:  # noqa: BLE001
                        pass
        finally:
            await clear_tenant_context(db)
    if failed:
        raise RuntimeError(f"Google 取り込みに失敗した会社: {failed}")
    return {"synced": synced}


async def _run_renew() -> int:
    from app.services import google_webhook as webhook_svc

    async with AsyncSessionLocal() as db:
        try:
            return await webhook_svc.renew_expiring_webhooks(db)
        finally:
            await clear_tenant_context(db)


@shared_task(name="app.tasks.google_calendar_sync.sync_google_calendar_tenant")
def sync_google_calendar_tenant(tenant_id: int) -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_tenant(tenant_id))
    finally:
        asyncio.run(engine.dispose())


@shared_task(name="app.tasks.google_calendar_sync.sync_google_calendar_all")
def sync_google_calendar_all() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_all())
    finally:
        asyncio.run(engine.dispose())


@shared_task(name="app.tasks.google_calendar_sync.renew_google_calendar_webhooks")
def renew_google_calendar_webhooks() -> dict:
    from app.database import engine

    try:
        return {"renewed": asyncio.run(_run_renew())}
    finally:
        asyncio.run(engine.dispose())
