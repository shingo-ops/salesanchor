from __future__ import annotations

"""
Drift detector: check v_supplier_parse_stats for the given supplier.
If exclude_rate > 30% OR avg_confidence < 0.5, notify via discord_notifier.

設計:
  - non-fatal: drift 通知失敗は warning ログのみ。呼び出し側の処理は継続する。
  - 当日分のみチェック（DATE_TRUNC('day', NOW())）。
  - webhook 未設定の場合は no-op（discord_notifier 側で処理）。
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

EXCLUDE_RATE_THRESHOLD = 30.0  # percent
CONFIDENCE_THRESHOLD = 0.5


async def check_drift_and_notify(db: AsyncSession, supplier_id: int) -> None:
    """v_supplier_parse_stats の当日行を参照し、ドリフトを検知したら Discord 通知する。

    Args:
        db: AsyncSession
        supplier_id: チェック対象の仕入元 ID

    閾値:
        exclude_rate_pct > 30.0 → 除外率が高い（ルールのドリフト可能性）
        avg_confidence < 0.5 → 平均確信度が低い（LLM 解析品質低下）

    non-fatal: 例外は全て catch してログのみ。
    """
    try:
        result = await db.execute(
            text(
                """
                SELECT
                    supplier_id,
                    supplier_name,
                    day,
                    total_lines,
                    parsed_count,
                    excluded_count,
                    unparsed_count,
                    exclude_rate_pct,
                    avg_confidence
                FROM public.v_supplier_parse_stats
                WHERE supplier_id = :supplier_id
                  AND day = DATE_TRUNC('day', NOW())
                LIMIT 1
                """
            ),
            {"supplier_id": supplier_id},
        )
        row = result.mappings().first()
        if row is None:
            # 当日ログなし（parse_logs がまだ空）は正常
            return

        exclude_rate = float(row["exclude_rate_pct"] or 0)
        avg_confidence = float(row["avg_confidence"]) if row["avg_confidence"] is not None else None
        supplier_name = row["supplier_name"] or f"supplier_id={supplier_id}"

        exceeded_exclude = exclude_rate > EXCLUDE_RATE_THRESHOLD
        exceeded_confidence = avg_confidence is not None and avg_confidence < CONFIDENCE_THRESHOLD

        if not exceeded_exclude and not exceeded_confidence:
            return

        # ドリフト検知: 通知
        logger.warning(
            "[drift_detector] supplier_id=%s (%s): exclude_rate=%.1f%% avg_confidence=%s",
            supplier_id,
            supplier_name,
            exclude_rate,
            avg_confidence,
        )
        await _notify_drift(
            db=db,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            total_lines=int(row["total_lines"] or 0),
            parsed_count=int(row["parsed_count"] or 0),
            excluded_count=int(row["excluded_count"] or 0),
            unparsed_count=int(row["unparsed_count"] or 0),
            exclude_rate=exclude_rate,
            avg_confidence=avg_confidence,
            exceeded_exclude=exceeded_exclude,
            exceeded_confidence=exceeded_confidence,
        )

    except Exception as exc:  # noqa: BLE001 - drift 検知失敗で取り込みを止めない
        logger.warning("[drift_detector] check failed for supplier_id=%s: %s", supplier_id, exc)


async def _notify_drift(
    db: AsyncSession,
    *,
    supplier_id: int,
    supplier_name: str,
    total_lines: int,
    parsed_count: int,
    excluded_count: int,
    unparsed_count: int,
    exclude_rate: float,
    avg_confidence: float | None,
    exceeded_exclude: bool,
    exceeded_confidence: bool,
) -> None:
    """Discord webhook へドリフトアラートを送信する。

    discord_notifier の _post_discord_webhook を直接使う（budget 通知と同じ経路）。
    """
    # 局所 import（循環防止）
    from app.services import discord_notifier

    alerts: list[str] = []
    if exceeded_exclude:
        alerts.append(f"除外率 **{exclude_rate:.1f}%** > 閾値 {EXCLUDE_RATE_THRESHOLD:.0f}%")
    if exceeded_confidence:
        conf_str = f"{avg_confidence:.3f}" if avg_confidence is not None else "N/A"
        alerts.append(f"平均確信度 **{conf_str}** < 閾値 {CONFIDENCE_THRESHOLD}")

    url = discord_notifier._get_webhook_url()
    if not url:
        logger.info(
            "[drift_detector] webhook 未設定、supplier_id=%s のドリフト通知を skip", supplier_id
        )
        return

    msg = (
        f":rotating_light: **解析ドリフト検知** :rotating_light:\n"
        f"- 仕入元: `{supplier_name}` (supplier_id={supplier_id})\n"
        f"- 本日の集計: 総行数={total_lines} / 解析済={parsed_count} / "
        f"除外={excluded_count} / 未解析={unparsed_count}\n"
        + "\n".join(f"- {a}" for a in alerts)
        + "\n- 解析ルール / supplier_aliases の見直しを検討してください。"
    )

    try:
        await discord_notifier._post_discord_webhook(url, msg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[drift_detector] webhook POST failed: %s", exc)


__all__ = [
    "EXCLUDE_RATE_THRESHOLD",
    "CONFIDENCE_THRESHOLD",
    "check_drift_and_notify",
]
