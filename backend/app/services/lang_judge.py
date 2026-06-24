"""lang_judge.py — 相手言語の多数決判定ヘルパー（読み取り専用）

B案 UNION ALL 設計（PO承認済み）:
  - meta_messages（自動連携: Messenger/Instagram/Discord inbound）
  - conversation_logs（手動文字記録 inbound、ただし phone/in_person は除外）
  を UNION ALL して original_language の多数決を取る。

除外条件（channel_masters.connection_type で確定）:
  - phone（電話）: 会話内容の verbatim ではなく要約が入る可能性があるため
  - in_person（対面）: 同上

閾値:
  - 3件以上 → 多数言語を "確定" として返す
  - 2件以下 → None（不明・呼び出し側でダイアログ等にフォールバック）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 判定確定に必要な最小レコード数
_MIN_RECORDS_FOR_CONFIDENT_JUDGMENT = 3

# 多数決から除外するチャネル種別（文字の verbatim が保証されない手動チャネル）
_EXCLUDED_MANUAL_CHANNELS = ("phone", "in_person")


@dataclass(frozen=True)
class LangJudgeResult:
    """多数決判定結果。

    Attributes:
        language: 判定された言語コード（'en'/'ja' 等）。None = 不明
        total_records: 判定に使ったレコード総数
        confident: True = 確定（3件以上）/ False = 不明（2件以下）
    """

    language: str | None
    total_records: int
    confident: bool


async def judge_recipient_language(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
) -> LangJudgeResult:
    """リードの受信履歴から相手言語を多数決で判定する（読み取り専用）。

    meta_messages（自動連携）と conversation_logs（手動文字記録）を UNION ALL し、
    direction='inbound' かつ original_language IS NOT NULL の行を集計する。

    RLS 互換: set_tenant_context は呼び出し元が責任を持つ。本関数はクエリのみ。
    """
    schema = f"tenant_{tenant_id:03d}"

    result = await db.execute(
        text(f"""
            SELECT original_language, COUNT(*) AS cnt
            FROM (
                -- 自動連携チャネル（Messenger / Instagram / Discord）
                SELECT original_language
                FROM {schema}.meta_messages
                WHERE lead_id          = :lead_id
                  AND direction        = 'inbound'
                  AND original_language IS NOT NULL
                  AND deleted_at       IS NULL

                UNION ALL

                -- 手動文字記録チャネル（phone/in_person は除外）
                SELECT cl.original_language
                FROM {schema}.conversation_logs cl
                WHERE cl.lead_id          = :lead_id
                  AND cl.direction        = 'inbound'
                  AND cl.original_language IS NOT NULL
                  AND cl.deleted_at       IS NULL
                  AND cl.channel_type    NOT IN :excluded_channels
            ) sub
            GROUP BY original_language
            ORDER BY cnt DESC
            LIMIT 1
        """),
        {
            "lead_id": lead_id,
            "excluded_channels": _EXCLUDED_MANUAL_CHANNELS,
        },
    )
    row = result.first()

    if row is None:
        return LangJudgeResult(language=None, total_records=0, confident=False)

    lang: str = row[0]

    # 全件数（多数派のカウントだけでなく全件を取得して閾値判定に使う）
    total_result = await db.execute(
        text(f"""
            SELECT COUNT(*) AS total
            FROM (
                SELECT 1
                FROM {schema}.meta_messages
                WHERE lead_id          = :lead_id
                  AND direction        = 'inbound'
                  AND original_language IS NOT NULL
                  AND deleted_at       IS NULL

                UNION ALL

                SELECT 1
                FROM {schema}.conversation_logs cl
                WHERE cl.lead_id          = :lead_id
                  AND cl.direction        = 'inbound'
                  AND cl.original_language IS NOT NULL
                  AND cl.deleted_at       IS NULL
                  AND cl.channel_type    NOT IN :excluded_channels
            ) sub
        """),
        {
            "lead_id": lead_id,
            "excluded_channels": _EXCLUDED_MANUAL_CHANNELS,
        },
    )
    total_row = total_result.first()
    total = int(total_row[0]) if total_row else 0

    confident = total >= _MIN_RECORDS_FOR_CONFIDENT_JUDGMENT

    logger.debug(
        "[lang_judge] lead=%d lang=%s total=%d confident=%s",
        lead_id,
        lang,
        total,
        confident,
    )

    return LangJudgeResult(
        language=lang if confident else None,
        total_records=total,
        confident=confident,
    )
