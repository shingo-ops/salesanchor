from __future__ import annotations

"""
ADR-110: 翻訳バックグラウンドタスク（Celery）。

3点セットの「本体」担当:
  - 受信メッセージの単発翻訳（定期バッチ翻訳は 2026-10 に廃止。docs/handoff/celery-unregistered-tasks/design.md）
  - 3点セットの「状態検証」担当: 未処理件数チェック
  - 3点セットの「監視/通知」担当: 翻訳異常を Discord 通知
"""

import logging

from app.auth.dependencies import clear_tenant_context, set_tenant_context
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.translation.translate_inbound_message",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def translate_inbound_message(
    self: object,
    tenant_id: int,
    table_ref: str = "meta_messages",
    message_id: str = "",
    message_text: str = "",
    target_language: str = "ja",
) -> dict:
    """単発の inbound 翻訳を実行して SSE 更新を通知する。

    gateway 側は保存後にこのタスクを enqueue するだけにし、
    Gemini 呼び出しは worker 側へ寄せる。
    """
    import asyncio

    from app.database import engine

    try:
        return asyncio.run(
            _run_translate_inbound_message(
                tenant_id=tenant_id,
                table_ref=table_ref,
                message_id=message_id,
                message_text=message_text,
                target_language=target_language,
            )
        )
    finally:
        # Celery worker の asyncio ループ再利用に伴う
        # "Future attached to a different loop" を避ける。
        asyncio.run(engine.dispose())


async def _run_translate_inbound_message(
    *,
    tenant_id: int,
    table_ref: str,
    message_id: str,
    message_text: str,
    target_language: str,
) -> dict:
    """ensure_inbound_translations を呼んだ後に inbox SSE を publish する。"""
    from app.database import AsyncSessionLocal
    from app.services.message_translator import ensure_inbound_translations

    schema_name = f"tenant_{tenant_id:03d}"
    translation_table_ref = table_ref
    if translation_table_ref == "meta_messages" or translation_table_ref.endswith(".meta_messages"):
        translation_table_ref = f"{schema_name}.message_translations"
    elif "." not in translation_table_ref:
        translation_table_ref = f"{schema_name}.{translation_table_ref}"

    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tenant_id)
        try:
            results = await ensure_inbound_translations(
                db=db,
                tenant_id=tenant_id,
                table_ref=translation_table_ref,
                message_id=message_id,
                message_text=message_text,
            )
        finally:
            await clear_tenant_context(db)

    try:
        from app.services.sse_pubsub import publish_inbox_update

        await publish_inbox_update(tenant_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[translation_task] SSE publish failed tenant=%s msg=%s: %s",
            tenant_id,
            message_id,
            exc,
            exc_info=True,
        )

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "message_id": message_id,
        "cached": all(result.cached for result in results.values()) if results else False,
        "engine": ",".join(sorted({result.engine for result in results.values()})) if results else "",
        "confidence": max((result.confidence for result in results.values()), default=0.0),
        "translated_text": (
            results["ja"].translated_text
            if "ja" in results
            else next(iter(results.values())).translated_text
        ) if results else "",
    }


@celery_app.task(
    name="app.tasks.translation.check_translation_health",
    bind=True,
)
def check_translation_health_task(self: object) -> dict:
    """翻訳健全性チェックと Discord 通知（3点セット 状態検証 + 監視/通知）。"""
    import asyncio

    from app.database import engine

    try:
        return asyncio.run(_run_health_check())
    finally:
        # Celery fork-pool の EventLoop 再利用で起きる "Future attached to a different loop" 対策（recon.md A-1）。
        asyncio.run(engine.dispose())


async def _run_health_check() -> dict:
    from sqlalchemy import text

    from app.database import AsyncSessionLocal
    from app.services.translation_monitor import (
        check_translation_health,
        notify_translation_anomaly,
    )

    alerts_sent = 0

    async with AsyncSessionLocal() as db:
        tenants_result = await db.execute(
            text(
                "SELECT t.id, t.tenant_code "
                "FROM public.tenants t "
                "WHERE t.is_active = true "
                "ORDER BY t.id"
            )
        )
        tenants = tenants_result.fetchall()

        for tenant_row in tenants:
            tenant_id = int(tenant_row[0])
            schema_name = f"tenant_{tenant_id:03d}"
            tenant_code = str(tenant_row[1]) if tenant_row[1] else "unknown"
            trans_t = f"{schema_name}.message_translations"
            meta_t = f"{schema_name}.meta_messages"

            try:
                snapshot = await check_translation_health(db, tenant_id, trans_t, meta_t)
                sent = await notify_translation_anomaly(
                    db, tenant_id, snapshot, tenant_code=tenant_code
                )
                if sent:
                    alerts_sent += 1
            except Exception as exc:
                logger.warning(
                    "[health_check] tenant %s error: %s", tenant_id, exc
                )

    return {"alerts_sent": alerts_sent}
