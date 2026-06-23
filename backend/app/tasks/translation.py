from __future__ import annotations

"""
ADR-110: 翻訳バックグラウンドタスク（Celery）。

3点セットの「本体」担当:
  - 未処理受信メッセージ（translated_text = NULL）を定期バッチ翻訳
  - 3点セットの「状態検証」担当: 未処理件数チェック
  - 3点セットの「監視/通知」担当: 翻訳異常を Discord 通知
"""

import logging

from app.auth.dependencies import clear_tenant_context, reset_tenant_context, set_tenant_context
from app.celery_app import celery_app
from app.services.inventory_parser_llm import LLMConfigError, LLMParseError

logger = logging.getLogger(__name__)

# 1 回のバッチで処理する最大件数
_BATCH_SIZE = 20


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
    name="app.tasks.translation.translate_pending_messages",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def translate_pending_messages(self: object) -> dict:
    """未処理の受信メッセージを一括翻訳するバッチタスク。

    各テナントの inbound メッセージについて、新ルールに基づき
    必要な target_language が欠けているものだけ補完する。
    失敗は non-fatal でスキップ（ADR-110 受け入れ条件 9）。
    """
    import asyncio

    from app.database import engine

    try:
        return asyncio.run(_run_batch())
    finally:
        # Celery fork-pool は asyncio.run() を呼ぶたびに新ループを生成する。
        # asyncpg 接続プールはループに紐づいた asyncio.Lock/Event を保持するため、
        # ループ close 後も古いオブジェクトがプールに残り次回タスクで
        # "Future attached to a different loop" を起こす（recon.md A-1）。
        # engine.dispose() でプール接続を全破棄してから終了することで回避する。
        asyncio.run(engine.dispose())


async def _run_batch() -> dict:
    from app.database import AsyncSessionLocal
    from app.services.message_translator import (
        BudgetExceededError,
        ensure_inbound_translations,
        get_existing_inbound_translation_targets,
        get_required_inbound_targets,
    )

    processed = 0
    skipped = 0
    failed = 0

    async with AsyncSessionLocal() as db:
        # 全テナントの処理待ちメッセージを取得
        from sqlalchemy import text

        # テナント一覧
        tenants_result = await db.execute(
            text(
                "SELECT t.id "
                "FROM public.tenants t "
                "WHERE t.is_active = true "
                "ORDER BY t.id"
            )
        )
        tenants = tenants_result.fetchall()

        for tenant_row in tenants:
            tenant_id = int(tenant_row[0])
            schema_name = f"tenant_{tenant_id:03d}"
            meta_t = f"{schema_name}.meta_messages"
            trans_t = f"{schema_name}.message_translations"

            await set_tenant_context(db, tenant_id)
            try:
                # 未翻訳の受信メッセージを取得
                result = await db.execute(
                    text(
                        f"SELECT m.message_id, m.message_text "
                        f"FROM {meta_t} m "
                        f"WHERE m.direction = 'inbound' "
                        f"  AND m.message_text IS NOT NULL AND m.message_text <> '' "
                        f"  AND NOT EXISTS ( "
                        f"      SELECT 1 FROM {trans_t} t "
                        f"      WHERE t.message_id = m.message_id "
                        f"        AND t.target_language = 'ja' "
                        f"  ) "
                        f"ORDER BY m.created_at ASC "
                        f"LIMIT :limit"
                    ),
                        {"limit": _BATCH_SIZE},
                )
                rows = result.fetchall()

                for message_id, message_text in rows:
                    try:
                        existing_targets, ja_original_language = await get_existing_inbound_translation_targets(
                            db,
                            trans_t,
                            str(message_id),
                        )
                        required_targets = get_required_inbound_targets(
                            str(message_text),
                            ja_original_language,
                        )
                        if required_targets.issubset(existing_targets):
                            continue
                        await ensure_inbound_translations(
                            db=db,
                            tenant_id=tenant_id,
                            table_ref=trans_t,
                            message_id=str(message_id),
                            message_text=str(message_text),
                        )
                        processed += 1
                    except BudgetExceededError:
                        logger.info(
                            "[translation_task] budget exceeded for tenant %s, skip remaining",
                            tenant_id,
                        )
                        # 残メッセージをスキップとしてカウント
                        remaining = len(rows) - rows.index((message_id, message_text)) - 1
                        skipped += remaining
                        break
                    except (LLMConfigError, LLMParseError) as exc:
                        logger.warning(
                            "[translation_task] non-fatal error message_id=%s: %s",
                            message_id, exc,
                        )
                        failed += 1
                    except Exception as exc:
                        logger.exception(
                            "[translation_task] unexpected error message_id=%s: %s",
                            message_id, exc,
                        )
                        failed += 1
                    finally:
                        await reset_tenant_context(db, tenant_id)
            finally:
                await clear_tenant_context(db)

    logger.info(
        "[translation_task] batch done: processed=%d skipped=%d failed=%d",
        processed, skipped, failed,
    )
    return {"processed": processed, "skipped": skipped, "failed": failed}


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
        # translate_pending_messages と同様の EventLoop クラッシュ対策（recon.md A-1）。
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
