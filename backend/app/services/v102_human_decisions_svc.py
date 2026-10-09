"""v102 の件に対する人の判断（public.item_corrections）の読み方と、「確認済み」の保存。判断の読み方の唯一の置き場所。

設計: docs/handoff/v102-prod-switch/design.md §13-3・§13-4、実装カード: docs/handoff/v102-prod-switch/card-D1.md
人の判断はすべて item_corrections に追記で残る（正本）。analysis_results は「判断を反映した結果」で、正本ではない。

判断が有効な条件: その判断の corrected_at が、同じ件の最後の「書き写しの直し」（TRANSCRIPTION_FIELDS）の corrected_at より後であること
（同時刻は無効）。書き写しを直した後は、それより前の商品・状態・確認済みの判断は無効になる（件の中身が変わったので見直す）。
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# テスト互換性のため属性を維持する（monkeypatch.setattr 対象。本番は public）
TCG_SCHEMA = "public"

# --- item_corrections.field_name（定義はここだけ） -------------------------------------------
FIELD_PRODUCT_ID = "product_id"
FIELD_CONDITION_REVIEW = "condition_review"
FIELD_REVIEW_ACK = "review_ack"
# Gemini の書き写しの直し（便C が書く）。これより前の判断は無効になる
FIELD_V102_LINES = "v102_lines"
FIELD_V102_PRICE = "v102_price"
FIELD_V102_QUANTITY = "v102_quantity"
FIELD_V102_ITEM_ADDED = "v102_item_added"
TRANSCRIPTION_FIELDS = (FIELD_V102_LINES, FIELD_V102_PRICE, FIELD_V102_QUANTITY, FIELD_V102_ITEM_ADDED)
_DECISION_FIELDS = (FIELD_PRODUCT_ID, FIELD_CONDITION_REVIEW, FIELD_REVIEW_ACK)

# --- human_value の中身 ------------------------------------------------------------------------
REVIEW_ACK_VERSION = 1
DECISION_CONFIRM = "confirm"
DECISION_CORRECT = "correct"
CONDITION_DECISIONS = (DECISION_CONFIRM, DECISION_CORRECT)

_CORRECTIONS_SQL = """
    SELECT extraction_item_id::text AS item_id, field_name, human_value, corrected_at
    FROM {schema}.item_corrections
    WHERE extraction_item_id::text = ANY(:ids) AND field_name = ANY(:fields)
    ORDER BY corrected_at DESC, id DESC
"""
_ACTIVE_CONDITIONS_SQL = "SELECT id FROM public.conditions WHERE id = ANY(:ids) AND is_active IS TRUE"
_JOB_OF_ITEM_SQL = """
    SELECT ej.id::text AS job_id, ej.prompt_version, ej.source_message_id::text AS source_message_id
    FROM {schema}.extraction_items ei
    JOIN {schema}.extraction_jobs ej ON ej.id = ei.extraction_job_id
    WHERE ei.id = CAST(:eid AS uuid)
"""
_INSERT_ACK_SQL = """
    INSERT INTO {schema}.item_corrections
        (extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by)
    VALUES (CAST(:eid AS uuid), CAST(:smid AS uuid), :field, :sv, :hv, :cb)
"""
_ACTIVE_PRODUCTS_SQL = "SELECT id FROM public.products WHERE id = ANY(:ids) AND is_active IS TRUE"
_CURRENT_REASONS_SQL = "SELECT review_reasons FROM {schema}.analysis_results WHERE extraction_item_id = CAST(:eid AS uuid)"


@dataclass(frozen=True)
class Decisions:
    """1件ぶんの、有効な人の判断。"""

    product_id: int | None = None
    condition_id: int | None = None
    ack_codes: frozenset[str] = frozenset()

    @property
    def is_empty(self) -> bool:
        return self.product_id is None and self.condition_id is None and not self.ack_codes


def _parse_int(value: object, what: str, item_id: str) -> int | None:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        logger.warning("[v102_decisions] %s が整数でないため無視します: item=%s", what, item_id)
        return None
    return number


def _parse_json_object(value: str, what: str, item_id: str) -> dict | None:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        parsed = None
    if not isinstance(parsed, dict):
        logger.warning("[v102_decisions] %s の JSON が読めないため無視します: item=%s", what, item_id)
        return None
    return parsed


def _ack_codes(value: str, item_id: str) -> frozenset[str]:
    body = _parse_json_object(value, FIELD_REVIEW_ACK, item_id)
    codes = body.get("codes") if body is not None else None
    if body is None or body.get("v") != REVIEW_ACK_VERSION or not isinstance(codes, list) \
            or not all(isinstance(c, str) and c for c in codes):
        if body is not None:
            logger.warning("[v102_decisions] %s の形が違うため無視します: item=%s", FIELD_REVIEW_ACK, item_id)
        return frozenset()
    return frozenset(codes)


def _condition_candidate(value: str, item_id: str) -> int | None:
    """condition_review の human_value から、decision が confirm/correct のときの condition_id（整数）。それ以外は None。"""
    body = _parse_json_object(value, FIELD_CONDITION_REVIEW, item_id)
    if body is None or body.get("decision") not in CONDITION_DECISIONS:
        return None
    return _parse_int(body.get("condition_id"), "condition_review.condition_id", item_id)


def _latest_valid(rows: list, cutoff: datetime | None) -> dict[str, str]:
    """field_name ごとに、有効な最新の行の human_value。rows は corrected_at・id の降順（先頭が最新）。"""
    latest: dict[str, str] = {}
    for row in rows:
        if row.field_name in latest:
            continue
        if cutoff is not None and row.corrected_at <= cutoff:
            continue
        latest[row.field_name] = row.human_value
    return latest


def load_v102_decisions(session: Session, item_ids: Iterable[str]) -> dict[str, Decisions]:
    """件（extraction_items.id）ごとの有効な人の判断。判断が1つも無い件は結果に含めない。読み取りのみ。"""
    ids = sorted({str(i) for i in item_ids})
    if not ids:
        return {}
    rows = session.execute(
        text(_CORRECTIONS_SQL.format(schema=TCG_SCHEMA)),
        {"ids": ids, "fields": [*_DECISION_FIELDS, *TRANSCRIPTION_FIELDS]},
    ).fetchall()
    by_item: dict[str, list] = {}
    for row in rows:
        by_item.setdefault(row.item_id, []).append(row)

    products: dict[str, int] = {}
    conditions: dict[str, int] = {}
    acks: dict[str, frozenset[str]] = {}
    for item_id, item_rows in by_item.items():
        transcription = [r.corrected_at for r in item_rows if r.field_name in TRANSCRIPTION_FIELDS]
        latest = _latest_valid(
            [r for r in item_rows if r.field_name in _DECISION_FIELDS], max(transcription) if transcription else None
        )
        if FIELD_PRODUCT_ID in latest:
            product_id = _parse_int(latest[FIELD_PRODUCT_ID], FIELD_PRODUCT_ID, item_id)
            if product_id is not None:
                products[item_id] = product_id
        if FIELD_CONDITION_REVIEW in latest:
            condition_id = _condition_candidate(latest[FIELD_CONDITION_REVIEW], item_id)
            if condition_id is not None:
                conditions[item_id] = condition_id
        if FIELD_REVIEW_ACK in latest:
            codes = _ack_codes(latest[FIELD_REVIEW_ACK], item_id)
            if codes:
                acks[item_id] = codes

    active = _active_condition_ids(session, set(conditions.values()))
    for item_id in [i for i, cid in conditions.items() if cid not in active]:
        logger.warning("[v102_decisions] 選ばれた状態が有効でないため無視します: item=%s", item_id)
        del conditions[item_id]
    result = {
        item_id: Decisions(products.get(item_id), conditions.get(item_id), acks.get(item_id, frozenset()))
        for item_id in {*products, *conditions, *acks}
    }
    return result


def _active_condition_ids(session: Session, condition_ids: set[int]) -> set[int]:
    if not condition_ids:
        return set()
    rows = session.execute(text(_ACTIVE_CONDITIONS_SQL), {"ids": sorted(condition_ids)}).fetchall()
    return {int(r[0]) for r in rows}


# ---------------------------------------------------------------------------
# 件 → 投稿 → v102 か（API が保存後にやり直しを積むかの判断。ここ1か所）
# ---------------------------------------------------------------------------


class JobOfItem(NamedTuple):
    job_id: str
    prompt_version: str | None
    source_message_id: str


async def find_job_of_item(db: AsyncSession, extraction_item_id: str) -> JobOfItem | None:
    """件の投稿(extraction_job_id・prompt_version・source_message_id)。件が無い・id の形が違うときは None。"""
    try:
        row = (await db.execute(text(_JOB_OF_ITEM_SQL.format(schema=TCG_SCHEMA)), {"eid": extraction_item_id})).first()
    except Exception:  # noqa: BLE001  uuid の形でない id は「無い」と同じ扱い
        await db.rollback()
        return None
    return None if row is None else JobOfItem(row.job_id, row.prompt_version, row.source_message_id)


async def v102_job_id_of_item(db: AsyncSession, extraction_item_id: str) -> str | None:
    """その件の投稿が v102（prompt_version が `v102:` 始まり）のときだけ extraction_job_id。v6・件なしは None。"""
    from app.services.line_analysis_v102_svc import is_v102_prompt_version  # noqa: PLC0415  循環 import を避ける

    found = await find_job_of_item(db, extraction_item_id)
    if found is None or not is_v102_prompt_version(found.prompt_version):
        return None
    return found.job_id


async def invalid_product_values(db: AsyncSession, values: Iterable[str]) -> list[str]:
    """商品の判断の値のうち、整数でない・public.products に is_active=TRUE で無いもの(順番を保つ)。"""
    parsed: dict[str, int | None] = {}
    for value in dict.fromkeys(values):
        try:
            parsed[value] = int(str(value).strip())
        except ValueError:
            parsed[value] = None
    ids = sorted({n for n in parsed.values() if n is not None})
    active = {int(r[0]) for r in (await db.execute(text(_ACTIVE_PRODUCTS_SQL), {"ids": ids})).fetchall()} if ids else set()
    return [value for value, number in parsed.items() if number is None or number not in active]


# ---------------------------------------------------------------------------
# 「このままで良い」（review_ack）の保存
# ---------------------------------------------------------------------------


def normalize_ack_codes(codes: Iterable[str]) -> list[str]:
    """順番を保って重複を除く。"""
    return list(dict.fromkeys(codes))


async def save_review_ack(
    db: AsyncSession, *, extraction_item_id: str, source_message_id: str, codes: list[str], corrected_by: str,
) -> int:
    """item_corrections に field_name='review_ack' を1行追記する（system_value は今の review_reasons）。保存した行数（1）。"""
    schema = TCG_SCHEMA
    current = (await db.execute(text(_CURRENT_REASONS_SQL.format(schema=schema)), {"eid": extraction_item_id})).first()
    human_value = json.dumps({"v": REVIEW_ACK_VERSION, "codes": normalize_ack_codes(codes)}, ensure_ascii=False)
    await db.execute(
        text(_INSERT_ACK_SQL.format(schema=schema)),
        {
            "eid": extraction_item_id, "smid": source_message_id, "field": FIELD_REVIEW_ACK,
            "sv": (current.review_reasons or "") if current is not None else "", "hv": human_value, "cb": corrected_by,
        },
    )
    await db.commit()  # public スキーマのみでテナント文脈を使わないため reset_tenant_context は不要(save_corrections と同じ)
    return 1


def unknown_codes(codes: Iterable[str], registered: Mapping[str, object]) -> list[str]:
    """review_reason_codes に無いコード（順番を保つ）。"""
    return [c for c in dict.fromkeys(codes) if c not in registered]
