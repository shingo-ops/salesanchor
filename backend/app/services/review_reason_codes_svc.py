"""要確認の理由コード表（public.review_reason_codes）の読み込みと、件ごとの理由の内訳づくり。

設計: docs/handoff/v102-prod-switch/design.md §12。表は読むだけ（初期行は1回だけのデータ変更）。
"""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.line_analysis_v102_svc import (
    REASON_BULK_PRICE_BASIS_UNKNOWN,
    REASON_CONDITION_UNKNOWN,
    REASON_SEPARATOR,
)

ReasonTable = dict[str, tuple[str, str]]

# 「このままで良い」(review-ack) で外せない理由。状態は人が選んで直す（Error のまま通さない。PO 2026-10-11）。唯一の置き場所
# バルクの1枚の値段が決まらない行も外せない（人が価格を直したときだけ外れる。便2）
NON_ACKABLE_REASON_CODES = frozenset({REASON_CONDITION_UNKNOWN, REASON_BULK_PRICE_BASIS_UNKNOWN})

_LOAD_SQL = "SELECT code, source, fix_stage FROM public.review_reason_codes"


async def load_review_reason_codes(session: AsyncSession) -> ReasonTable:
    """code -> (source, fix_stage)。1リクエストにつき1回呼ぶ。"""
    rows = (await session.execute(text(_LOAD_SQL))).fetchall()
    return {row.code: (row.source, row.fix_stage) for row in rows}


def split_reason_codes(reasons: str | None) -> list[str]:
    """カンマ区切りを分け、空白除去・空を捨て、順番を保って重複を除く。"""
    seen: dict[str, None] = {}
    for part in (reasons or "").split(REASON_SEPARATOR):
        code = part.strip()
        if code:
            seen.setdefault(code, None)
    return list(seen)


def build_review_reason_details(reasons: str | None, table: ReasonTable) -> list[dict]:
    """[{code, source, fix_stage, ackable}]。表に無いコードは source / fix_stage を None にする。"""
    details = []
    for code in split_reason_codes(reasons):
        source, fix_stage = table.get(code, (None, None))
        details.append({"code": code, "source": source, "fix_stage": fix_stage, "ackable": code not in NON_ACKABLE_REASON_CODES})
    return details


def non_ackable_codes(codes: Iterable[str]) -> list[str]:
    """review-ack に含められない理由（順番を保つ）。"""
    return [c for c in dict.fromkeys(codes) if c in NON_ACKABLE_REASON_CODES]
