from __future__ import annotations

"""
ADR-110 / ADR-SA-17: 翻訳バックグラウンドタスク（Celery）。

ADR-SA-17 改訂:
  - translate_message_now: 受信 webhook から即時発火する 1 件翻訳（双方向自動判定・I-2）。
  - translate_pending_messages: 既存の「主役」バッチを **sweeper（取りこぼし拾い）** に降格（I-3）。
    即時翻訳が失敗/未処理だった分を後追いで双方向翻訳し、滞留を operator へ通知する。

3点セット:
  - 本体: translate_message_now（即時）+ translate_pending_messages（sweeper）
  - 状態検証 / 監視・通知: check_translation_health（translation_monitor 拡張）
"""

import logging
import os

from app.celery_app import celery_app
from app.services.inventory_parser_llm import LLMConfigError, LLMParseError

logger = logging.getLogger(__name__)

# 1 回のバッチで処理する最大件数
_BATCH_SIZE = 20

# 即時翻訳が取りこぼしたとみなす経過時間（分）。これを超えて未翻訳なら sweeper が滞留として通知。
_SWEEPER_STALE_MINUTES = int(os.getenv("TRANSLATION_SWEEPER_STALE_MINUTES", "5"))


@celery_app.task(
    name="app.tasks.translation.translate_message_now",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def translate_message_now(  # type: ignore[override]
    self: object,
    tenant_id: int,
    schema_name: str,
    message_id: str,
    message_text: str,
) -> dict:
    """受信 webhook から即時発火する 1 件翻訳（ADR-SA-17 I-2）。

    原文の言語を判定して反対側へ訳す（双方向）。失敗時は行を残さず、sweeper が後追いする。
    """
    import asyncio

    return asyncio.run(
        _translate_one_now(tenant_id, schema_name, message_id, message_text)
    )


async def _translate_one_now(
    tenant_id: int,
    schema_name: str,
    message_id: str,
    message_text: str,
) -> dict:
    from app.auth.dependencies import reset_tenant_context
    from app.database import AsyncSessionLocal
    from app.services.message_translator import (
        BudgetExceededError,
        detect_inbound_target_language,
        translate_inbound,
    )

    if not message_text or not message_text.strip():
        return {"translated": False, "reason": "empty"}

    trans_t = f"{schema_name}.message_translations"
    target_language = detect_inbound_target_language(message_text)

    async with AsyncSessionLocal() as db:
        # RLS 用に app.tenant_id を設定（私有グロッサリを正しくスコープ）。
        await reset_tenant_context(db, tenant_id)
        try:
            result = await translate_inbound(
                db=db,
                tenant_id=tenant_id,
                table_ref=trans_t,
                message_id=str(message_id),
                message_text=str(message_text),
                target_language=target_language,
            )
        except BudgetExceededError:
            logger.info(
                "[translate_now] budget exceeded tenant=%s msg=%s (sweeper picks up later)",
                tenant_id, message_id,
            )
            return {"translated": False, "reason": "budget"}
        except (LLMConfigError, LLMParseError) as exc:
            logger.warning(
                "[translate_now] non-fatal failure tenant=%s msg=%s: %s (sweeper retries)",
                tenant_id, message_id, exc,
            )
            return {"translated": False, "reason": "error"}

        # 受信箱を即時更新（「翻訳中」表示をほぼ一瞬で解消）。
        try:
            from app.services.sse_pubsub import publish_inbox_update
            await publish_inbox_update(tenant_id)
        except Exception:
            logger.debug("[translate_now] SSE publish skipped", exc_info=True)

    return {
        "translated": True,
        "target": target_language,
        "confidence": result.confidence,
        "cached": result.cached,
    }


@celery_app.task(
    name="app.tasks.translation.translate_pending_messages",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def translate_pending_messages(self: object) -> dict:  # type: ignore[override]
    """sweeper（取りこぼし拾い）— ADR-SA-17 I-3 で「主役」から降格。

    即時翻訳（translate_message_now）が失敗/未処理だった受信メッセージを後追いで
    **双方向**翻訳する。即時翻訳が取りこぼしたとみなせる滞留（_SWEEPER_STALE_MINUTES 超過）が
    あれば operator へ Discord 通知する。失敗は non-fatal でスキップ。
    """
    import asyncio

    return asyncio.run(_run_sweeper())


async def _run_sweeper() -> dict:
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import text

    from app.database import AsyncSessionLocal
    from app.services.message_translator import (
        BudgetExceededError,
        detect_inbound_target_language,
        translate_inbound,
    )

    processed = 0
    skipped = 0
    failed = 0
    stale_picked = 0  # 即時翻訳が取りこぼした（滞留していた）件数

    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=_SWEEPER_STALE_MINUTES)

    async with AsyncSessionLocal() as db:
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

            # 未翻訳の受信メッセージ（向きを問わず翻訳行が存在しないもの）を古い順に取得。
            # bidirectional: target_language を 'ja' に固定せず「行が無い」ことだけを条件にする。
            result = await db.execute(
                text(
                    f"SELECT m.message_id, m.message_text, m.created_at "
                    f"FROM {meta_t} m "
                    f"WHERE m.direction = 'inbound' "
                    f"  AND m.message_text IS NOT NULL AND m.message_text <> '' "
                    f"  AND NOT EXISTS ( "
                    f"      SELECT 1 FROM {trans_t} t "
                    f"      WHERE t.message_id = m.message_id "
                    f"  ) "
                    f"ORDER BY m.created_at ASC "
                    f"LIMIT :limit"
                ),
                {"limit": _BATCH_SIZE},
            )
            rows = result.fetchall()

            for idx, (message_id, message_text, created_at) in enumerate(rows):
                target_language = detect_inbound_target_language(str(message_text))
                try:
                    await translate_inbound(
                        db=db,
                        tenant_id=tenant_id,
                        table_ref=trans_t,
                        message_id=str(message_id),
                        message_text=str(message_text),
                        target_language=target_language,
                    )
                    processed += 1
                    # created_at がしきい値より古ければ即時翻訳の取りこぼし（滞留）
                    if created_at is not None:
                        ca = created_at
                        if ca.tzinfo is None:
                            ca = ca.replace(tzinfo=timezone.utc)
                        if ca < stale_cutoff:
                            stale_picked += 1
                except BudgetExceededError:
                    logger.info(
                        "[sweeper] budget exceeded for tenant %s, skip remaining",
                        tenant_id,
                    )
                    skipped += len(rows) - idx - 1
                    break
                except (LLMConfigError, LLMParseError) as exc:
                    logger.warning(
                        "[sweeper] non-fatal error message_id=%s: %s", message_id, exc
                    )
                    failed += 1
                except Exception as exc:
                    logger.exception(
                        "[sweeper] unexpected error message_id=%s: %s", message_id, exc
                    )
                    failed += 1

    logger.info(
        "[sweeper] done: processed=%d stale_picked=%d skipped=%d failed=%d",
        processed, stale_picked, skipped, failed,
    )

    # I-3: 即時翻訳の取りこぼし（滞留）/ 失敗があれば operator へ通知。
    if stale_picked > 0 or failed > 0:
        try:
            from app.services.translation_monitor import notify_sweeper_pickup
            await notify_sweeper_pickup(
                stale_picked=stale_picked, failed=failed, processed=processed
            )
        except Exception:
            logger.warning("[sweeper] notify_sweeper_pickup 失敗", exc_info=True)

    return {
        "processed": processed,
        "stale_picked": stale_picked,
        "skipped": skipped,
        "failed": failed,
    }


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

        # ADR-SA-17 I-9 / 3点セット③: 昇格レビューキューの滞留を operator へ通知。
        try:
            from app.services.translation_monitor import notify_promotion_backlog
            if await notify_promotion_backlog(db):
                alerts_sent += 1
        except Exception:
            logger.warning("[health_check] notify_promotion_backlog 失敗", exc_info=True)

    return {"alerts_sent": alerts_sent}
