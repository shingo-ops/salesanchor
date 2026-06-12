from __future__ import annotations

"""
SA-02 §10: 並走期間 日次突合タスク。

meta_messages と conversation_logs の当日新規件数を全テナント合計で突合し、
差異ゼロ・差異あり問わず毎日 Discord に通知する（通知ゼロ＝監視停止を区別するため）。

スケジュール: 毎日 AM 8:00 JST（celery_app.py の beat_schedule に登録）。
実行期間: 並走期間（段階1デプロイ〜段階2移行完了・読み取り切替完了）のみ。
       並走終了後は beat_schedule から除去する（SA-02-design.md §10 廃止手順）。
"""

import logging
import os
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import text

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"
_MAX_CHARS = 1800


async def _post_discord(content: str) -> None:
    url = os.getenv(_WEBHOOK_ENV, "").strip()
    if not url:
        logger.warning("[sa02_recon] Discord webhook URL 未設定 (skip)")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json={"content": content[:_MAX_CHARS], "username": "SA-02 並走監視"},
            )
        if resp.status_code >= 400:
            logger.warning("[sa02_recon] webhook HTTP %s", resp.status_code)
    except Exception as exc:
        logger.warning("[sa02_recon] webhook 失敗: %s", exc)


async def _run_daily_recon() -> dict:
    from app.database import AsyncSessionLocal

    today = date.today()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    meta_total = 0
    conv_total = 0
    tenant_details: list[str] = []

    async with AsyncSessionLocal() as db:
        tenants_result = await db.execute(
            text(
                "SELECT id FROM public.tenants WHERE is_active = true ORDER BY id"
            )
        )
        tenants = tenants_result.fetchall()

        for row in tenants:
            tenant_id = int(row[0])
            schema = f"tenant_{tenant_id:03d}"

            meta_result = await db.execute(
                text(
                    f"SELECT COUNT(*) FROM {schema}.meta_messages "
                    f"WHERE created_at >= :since"
                ),
                {"since": today_start},
            )
            meta_count = int(meta_result.scalar() or 0)

            conv_result = await db.execute(
                text(
                    f"SELECT COUNT(*) FROM {schema}.conversation_logs "
                    f"WHERE occurred_at >= :since AND direction = 'inbound'"
                ),
                {"since": today_start},
            )
            conv_count = int(conv_result.scalar() or 0)

            meta_total += meta_count
            conv_total += conv_count

            diff = meta_count - conv_count
            if diff != 0:
                tenant_details.append(
                    f"  tenant_{tenant_id:03d}: meta={meta_count} conv={conv_count} 差異={diff:+d}"
                )

    diff_total = meta_total - conv_total

    if diff_total == 0:
        # 正常: 1行サマリー通知（監視が稼働中であることを毎日確認できる）
        summary_lines = [
            f"📊 SA-02日次突合 {today.isoformat()}: 旧{meta_total}件/新{conv_total}件 一致✅",
        ]
    else:
        # 差異あり: ⚠ 強調 + 内訳付き通知
        summary_lines = [
            f"⚠️ **[SA-02 並走監視] {today.isoformat()}  差異 {diff_total:+d}件**",
            f"meta_messages 当日新規(inbound換算): {meta_total}件",
            f"conversation_logs 当日新規(inbound): {conv_total}件",
        ]
        if tenant_details:
            summary_lines.append("テナント別内訳:")
            summary_lines.extend(tenant_details)

    message = "\n".join(summary_lines)

    if diff_total != 0:
        logger.warning("[sa02_recon] 突合差異あり diff=%d", diff_total)
    else:
        logger.info("[sa02_recon] %s", message)

    # 差異ゼロ・差異あり問わず毎日 Discord に通知（通知ゼロ＝監視停止を区別するため）
    await _post_discord(message)

    return {
        "date": today.isoformat(),
        "meta_total": meta_total,
        "conv_total": conv_total,
        "diff": diff_total,
    }


def run_sa02_daily_recon() -> dict:
    """Celery タスクから呼ばれるエントリポイント（同期ラッパー）。"""
    import asyncio

    return asyncio.run(_run_daily_recon())
