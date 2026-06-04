from __future__ import annotations

"""
ADR-110: 翻訳サブシステム監視・Discord 通知（3点セットの「監視/通知」）。

失敗率・遅延・低確信度多発が閾値を超えた場合に Discord webhook で通知する。
通知は 1 時間デバウンス（同一テナントへの連投を防ぐ）。

監視項目:
  - 翻訳失敗率 > TRANSLATION_FAIL_RATE_THRESHOLD (既定 20%)
  - 翻訳 p95 遅延 > TRANSLATION_LATENCY_P95_SEC (既定 30 秒、未実装は skip)
  - 低確信度比率 > TRANSLATION_LOW_CONF_RATE_THRESHOLD (既定 30%)
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"
_MAX_MESSAGE_CHARS = 1800

_FAIL_RATE_THRESHOLD = float(os.getenv("TRANSLATION_FAIL_RATE_THRESHOLD", "0.20"))
_LOW_CONF_RATE_THRESHOLD = float(os.getenv("TRANSLATION_LOW_CONF_RATE_THRESHOLD", "0.30"))
_CONF_THRESHOLD_RECEIVE = float(os.getenv("TRANSLATION_CONFIDENCE_THRESHOLD_RECEIVE", "0.70"))
_DEBOUNCE_HOURS = 1


@dataclass
class TranslationHealthSnapshot:
    total: int
    failed: int
    low_confidence: int
    fail_rate: float
    low_conf_rate: float


async def check_translation_health(
    db: AsyncSession,
    tenant_id: int,
    table_ref: str,
    meta_table_ref: str,
    window_minutes: int = 60,
) -> TranslationHealthSnapshot:
    """直近 window_minutes 分の翻訳健全性スナップショットを返す。

    total   = ウィンドウ内の受信メッセージ数（meta_messages）
    failed  = 翻訳行がない未処理メッセージ数（LEFT JOIN で検出）
    low_conf = 低確信度翻訳数（message_translations から）
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    # 未処理（pending）数 = meta_messages に対応する翻訳行がない件数
    result = await db.execute(
        text(
            f"SELECT "
            f"  COUNT(*) AS total, "
            f"  COUNT(*) FILTER (WHERE mt.message_id IS NULL) AS pending "
            f"FROM {meta_table_ref} m "
            f"LEFT JOIN {table_ref} mt "
            f"  ON mt.message_id = m.message_id AND mt.target_language = 'ja' "
            f"WHERE m.direction = 'inbound' "
            f"  AND m.created_at >= :since"
        ),
        {"since": since},
    )
    row = result.first()
    if row is None or row[0] == 0:
        return TranslationHealthSnapshot(0, 0, 0, 0.0, 0.0)

    total, pending = int(row[0]), int(row[1])

    # 低確信度数は翻訳済み行から集計
    lc_result = await db.execute(
        text(
            f"SELECT COUNT(*) "
            f"FROM {table_ref} "
            f"WHERE created_at >= :since "
            f"  AND confidence IS NOT NULL AND confidence < :conf_threshold"
        ),
        {"since": since, "conf_threshold": _CONF_THRESHOLD_RECEIVE},
    )
    lc_row = lc_result.first()
    low_conf = int(lc_row[0]) if lc_row else 0

    fail_rate = pending / total if total > 0 else 0.0
    low_conf_rate = low_conf / total if total > 0 else 0.0
    return TranslationHealthSnapshot(
        total=total,
        failed=pending,
        low_confidence=low_conf,
        fail_rate=fail_rate,
        low_conf_rate=low_conf_rate,
    )


async def _get_last_notified(db: AsyncSession, tenant_id: int) -> datetime | None:
    """最後に通知した日時を返す（翻訳監視専用デバウンス）。"""
    result = await db.execute(
        text(
            "SELECT last_translation_monitor_notified_at "
            "FROM public.tenant_llm_budgets "
            "WHERE tenant_id = :tenant_id"
        ),
        {"tenant_id": tenant_id},
    )
    row = result.first()
    if row is None or row[0] is None:
        return None
    return row[0]


async def _update_last_notified(db: AsyncSession, tenant_id: int) -> None:
    """通知日時を更新（UPSERT — 行が存在しない場合も確実に記録）。"""
    await db.execute(
        text(
            "INSERT INTO public.tenant_llm_budgets (tenant_id, last_translation_monitor_notified_at) "
            "VALUES (:tenant_id, NOW()) "
            "ON CONFLICT (tenant_id) DO UPDATE "
            "SET last_translation_monitor_notified_at = NOW()"
        ),
        {"tenant_id": tenant_id},
    )


async def _post_webhook(content: str) -> bool:
    url = os.getenv(_WEBHOOK_ENV, "").strip()
    if not url:
        logger.warning("[translation_monitor] webhook URL 未設定 (skip)")
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={
                "content": content[:_MAX_MESSAGE_CHARS],
                "username": "Sales Anchor 翻訳監視",
            })
        if resp.status_code >= 400:
            logger.warning("[translation_monitor] webhook HTTP %s", resp.status_code)
            return False
        return True
    except Exception as exc:
        logger.warning("[translation_monitor] webhook 失敗: %s", exc)
        return False


async def notify_translation_anomaly(
    db: AsyncSession,
    tenant_id: int,
    snapshot: TranslationHealthSnapshot,
    tenant_code: str = "unknown",
) -> bool:
    """翻訳異常を Discord に通知する。デバウンス 1 時間。

    Returns: True if notification was sent.
    """
    # アラート条件チェック
    alerts: list[str] = []
    if snapshot.fail_rate > _FAIL_RATE_THRESHOLD:
        alerts.append(
            f"⚠️ 翻訳失敗率 {snapshot.fail_rate:.0%} "
            f"（{snapshot.failed}/{snapshot.total} 件, 閾値 {_FAIL_RATE_THRESHOLD:.0%}）"
        )
    if snapshot.low_conf_rate > _LOW_CONF_RATE_THRESHOLD:
        alerts.append(
            f"⚠️ 低確信度比率 {snapshot.low_conf_rate:.0%} "
            f"（{snapshot.low_confidence}/{snapshot.total} 件, 閾値 {_LOW_CONF_RATE_THRESHOLD:.0%}）"
        )

    if not alerts:
        return False

    # デバウンスチェック
    try:
        last_notified = await _get_last_notified(db, tenant_id)
        if last_notified is not None:
            elapsed = datetime.now(timezone.utc) - last_notified.replace(tzinfo=timezone.utc)
            if elapsed < timedelta(hours=_DEBOUNCE_HOURS):
                logger.debug(
                    "[translation_monitor] デバウンス中 (tenant_id=%s, elapsed=%s)",
                    tenant_id, elapsed
                )
                return False
    except Exception as exc:
        logger.warning("[translation_monitor] デバウンスチェック失敗（通知を送る）: %s", exc)

    content = (
        f"🌐 **Sales Anchor 翻訳監視アラート** (tenant: {tenant_code})\n\n"
        + "\n".join(alerts)
        + f"\n\n直近 60 分間の統計: 総翻訳数 {snapshot.total} 件"
    )
    sent = await _post_webhook(content)
    if sent:
        try:
            await _update_last_notified(db, tenant_id)
            await db.commit()
        except Exception as exc:
            logger.warning("[translation_monitor] デバウンス更新失敗: %s", exc)
    return sent


__all__ = [
    "TranslationHealthSnapshot",
    "check_translation_health",
    "notify_translation_anomaly",
]
