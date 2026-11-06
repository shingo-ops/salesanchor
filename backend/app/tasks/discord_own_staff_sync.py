"""自社用 Discord サーバーのスタッフのロールを 5 分ごとに点検する（discord-server-management 第2段 2b・設計 S2-3 D2-3 (b)）。

自社サーバーを登録した全テナント（public.tenant_discord_config の purpose='own'）を順に 1 回ずつ点検する。
ワンショットのエンジンの扱いは backend/app/tasks/master_required_fields_monitor.py と同じ形。
"""
import asyncio
import logging
import os

from celery import shared_task
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def _run_all() -> list[dict]:
    from redis import asyncio as aioredis  # noqa: PLC0415

    from app.database import AsyncSessionLocal  # noqa: PLC0415
    from app.services.discord_own_staff_sync import sync_own_server_staff_roles  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text(
            "SELECT tenant_id FROM public.tenant_discord_config"
            " WHERE purpose = 'own' AND guild_id IS NOT NULL ORDER BY tenant_id"
        ))).all()
    tenant_ids = [int(r[0]) for r in rows]
    redis_client = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=5,
    )
    results: list[dict] = []
    try:
        for tenant_id in tenant_ids:
            try:
                results.append(await sync_own_server_staff_roles(
                    tenant_id, redis_client=redis_client, session_factory=AsyncSessionLocal,
                ))
            except Exception as exc:  # noqa: BLE001
                logger.error("[own-staff-sync] tenant=%s failed: %s: %s", tenant_id, type(exc).__name__, exc)
    finally:
        await redis_client.aclose()
    return results


@shared_task(name="app.tasks.discord_own_staff_sync.sync_all_own_servers", ignore_result=True)
def sync_all_own_servers() -> None:
    if not os.environ.get("DISCORD_BOT_TOKEN"):
        logger.info("[own-staff-sync] DISCORD_BOT_TOKEN が無いので点検しない")
        return
    from app.database import engine  # noqa: PLC0415

    try:
        asyncio.run(_run_all())
    except Exception as exc:  # noqa: BLE001
        logger.error("[own-staff-sync] 実行に失敗: %s: %s", type(exc).__name__, exc)
    finally:
        asyncio.run(engine.dispose())
