"""lang_judge.py — 相手言語の多数決判定ヘルパー（読み取り専用）

会話の一本化 便1 以降の設計:
  - meta_messages（自動連携: Messenger/Instagram/Discord inbound と、手の記録の inbound）
    だけから original_language の多数決を取る。
  - 手の記録のうち phone/in_person など原文でない窓口は除外する。

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

from app.services.channel_masters import CHANNEL_MASTERS_TABLE

logger = logging.getLogger(__name__)

# 判定確定に必要な最小レコード数
_MIN_RECORDS_FOR_CONFIDENT_JUDGMENT = 3

# 多数決から除外するチャネルは、名簿の is_verbatim = FALSE の行（文字が原文と保証されない手動チャネル）。
_NOT_VERBATIM_CLAUSE = (
    f"AND NOT EXISTS (SELECT 1 FROM {CHANNEL_MASTERS_TABLE} cm "
    f"WHERE cm.platform = m.platform AND cm.is_verbatim = FALSE "
    f"AND (cm.tenant_id IS NULL OR cm.tenant_id = :tenant_id))"
)


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

    meta_messages（自動連携と手の記録）から、
    direction='inbound' かつ original_language IS NOT NULL の行を集計する。

    RLS 互換: set_tenant_context は呼び出し元が責任を持つ。本関数はクエリのみ。
    """
    schema = f"tenant_{tenant_id:03d}"

    result = await db.execute(
        text(f"""
            SELECT m.original_language, COUNT(*) AS cnt
            FROM {schema}.meta_messages m
            WHERE m.lead_id          = :lead_id
              AND m.direction        = 'inbound'
              AND m.original_language IS NOT NULL
              AND m.deleted_at       IS NULL
              {_NOT_VERBATIM_CLAUSE}
            GROUP BY m.original_language
            ORDER BY cnt DESC
            LIMIT 1
        """),
        {
            "lead_id": lead_id,
            "tenant_id": tenant_id,
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
            FROM {schema}.meta_messages m
            WHERE m.lead_id          = :lead_id
              AND m.direction        = 'inbound'
              AND m.original_language IS NOT NULL
              AND m.deleted_at       IS NULL
              {_NOT_VERBATIM_CLAUSE}
        """),
        {
            "lead_id": lead_id,
            "tenant_id": tenant_id,
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
