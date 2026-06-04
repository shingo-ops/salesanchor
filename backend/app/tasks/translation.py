from __future__ import annotations

"""
ADR-110: 翻訳バックグラウンドタスク（Celery）。

3点セットの「本体」担当:
  - 未処理受信メッセージ（translated_text = NULL）を定期バッチ翻訳
  - 3点セットの「状態検証」担当: 未処理件数チェック
  - 3点セットの「監視/通知」担当: 翻訳異常を Discord 通知
"""

import logging

from app.celery_app import app as celery_app
from app.services.inventory_parser_llm import LLMConfigError, LLMParseError

logger = logging.getLogger(__name__)

# 1 回のバッチで処理する最大件数
_BATCH_SIZE = 20


@celery_app.task(
    name="app.tasks.translation.translate_pending_messages",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def translate_pending_messages(self: object) -> dict:  # type: ignore[override]
    """未翻訳の受信メッセージを一括翻訳するバッチタスク。

    各テナントの meta_messages で translated_text が NULL の行（受信のみ）を
    対象に translate_inbound() を呼び出す。
    失敗は non-fatal でスキップ（ADR-110 受け入れ条件 9）。
    """
    import asyncio

    return asyncio.run(_run_batch())


async def _run_batch() -> dict:
    from app.database import AsyncSessionLocal
    from app.services.message_translator import BudgetExceededError, translate_inbound

    processed = 0
    skipped = 0
    failed = 0

    async with AsyncSessionLocal() as db:
        # 全テナントの処理待ちメッセージを取得
        from sqlalchemy import text

        # テナント一覧
        tenants_result = await db.execute(
            text(
                "SELECT t.id, t.schema_name "
                "FROM public.tenants t "
                "ORDER BY t.id"
            )
        )
        tenants = tenants_result.fetchall()

        for tenant_row in tenants:
            tenant_id, schema_name = int(tenant_row[0]), str(tenant_row[1])
            meta_t = f"{schema_name}.meta_messages"
            trans_t = f"{schema_name}.message_translations"

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
                    await translate_inbound(
                        db=db,
                        tenant_id=tenant_id,
                        table_ref=trans_t,
                        message_id=str(message_id),
                        message_text=str(message_text),
                        target_language="ja",
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

    logger.info(
        "[translation_task] batch done: processed=%d skipped=%d failed=%d",
        processed, skipped, failed,
    )
    return {"processed": processed, "skipped": skipped, "failed": failed}


@celery_app.task(
    name="app.tasks.translation.check_translation_health",
    bind=True,
)
def check_translation_health_task(self: object) -> dict:  # type: ignore[override]
    """翻訳健全性チェックと Discord 通知（3点セット 状態検証 + 監視/通知）。"""
    import asyncio

    return asyncio.run(_run_health_check())


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
                "SELECT t.id, t.schema_name, t.tenant_code "
                "FROM public.tenants t "
                "ORDER BY t.id"
            )
        )
        tenants = tenants_result.fetchall()

        for tenant_row in tenants:
            tenant_id = int(tenant_row[0])
            schema_name = str(tenant_row[1])
            tenant_code = str(tenant_row[2]) if tenant_row[2] else "unknown"
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
