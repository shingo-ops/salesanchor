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
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.services.tcg_condition_review_svc import not_excluded_condition_sql

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
# 件の削除（便C）。削除した件は analysis_results ごと消えるので TRANSCRIPTION_FIELDS には入れない
FIELD_V102_ITEM_DELETED = "v102_item_deleted"
TRANSCRIPTION_FIELDS = (FIELD_V102_LINES, FIELD_V102_PRICE, FIELD_V102_QUANTITY, FIELD_V102_ITEM_ADDED)
# 比較表から直した値（数量・単価・単位・メモ・販売状況）。定義・検証・読み方・重ね方はこのファイルだけ
FIELD_OVERRIDE_QUANTITY = "override_quantity"
FIELD_OVERRIDE_PRICE = "override_price"
FIELD_OVERRIDE_UNIT = "override_unit"
FIELD_OVERRIDE_NOTE = "override_note"
FIELD_OVERRIDE_STATUS = "override_status"
OVERRIDE_FIELDS = (
    FIELD_OVERRIDE_QUANTITY, FIELD_OVERRIDE_PRICE, FIELD_OVERRIDE_UNIT, FIELD_OVERRIDE_NOTE, FIELD_OVERRIDE_STATUS,
)
OVERRIDE_PREFIX = "override_"
OVERRIDE_VERSION = 1
# API の field（quantity など）→ field_name
OVERRIDE_FIELD_OF_KEY = {key: f"{OVERRIDE_PREFIX}{key}" for key in ("quantity", "price", "unit", "note", "status")}
MAX_NOTE_LENGTH = 2000
_MAX_DECIMAL_PLACES = 2  # analysis_results.quantity_normalized・price_normalized は NUMERIC(14,2)
_STATUS_EFFECTS_OK = ("OUTPUT", "EXCLUDE")
_STATUS_EFFECT_EXCLUDE = "EXCLUDE"
_DECISION_FIELDS = (FIELD_PRODUCT_ID, FIELD_CONDITION_REVIEW, FIELD_REVIEW_ACK)
_LOAD_FIELDS = (*_DECISION_FIELDS, *OVERRIDE_FIELDS)
_EXCLUDED_ACK_CODE = "excluded"

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
_ACTIVE_CONDITIONS_SQL = (
    f"SELECT id FROM public.conditions WHERE id = ANY(:ids) AND is_active IS TRUE AND {not_excluded_condition_sql('conditions')}"
)
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
_CURRENT_REASONS_SQL = (
    "SELECT review_reasons FROM {schema}.analysis_results WHERE extraction_item_id = CAST(:eid AS uuid) FOR UPDATE"
)


@dataclass(frozen=True)
class ValueOverrides:
    """人が直した値（数量・単価・単位・メモ・販売状況）。None は「直していない」。note の空文字は「空にした」。"""

    quantity: Decimal | None = None
    price: Decimal | None = None
    unit: str | None = None
    note: str | None = None
    status: str | None = None

    @property
    def is_empty(self) -> bool:
        return all(v is None for v in (self.quantity, self.price, self.unit, self.note, self.status))


@dataclass(frozen=True)
class Decisions:
    """1件ぶんの、有効な人の判断。"""

    product_id: int | None = None
    condition_id: int | None = None
    ack_codes: frozenset[str] = frozenset()
    values: ValueOverrides = ValueOverrides()

    @property
    def is_empty(self) -> bool:
        return self.product_id is None and self.condition_id is None and not self.ack_codes and self.values.is_empty


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


def _decimal_or_none(raw: str) -> Decimal | None:
    """数量・単価として使える数字（有限・0 以上・NUMERIC(14,2) に入る・小数 2 桁まで）だけ Decimal にする。使えなければ None。"""
    from app.services.line_analysis_v102_svc import _bounded_number  # noqa: PLC0415  循環 import を避ける

    try:
        number = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number < 0 or _bounded_number(number) is None:
        return None
    if number.normalize().as_tuple().exponent < -_MAX_DECIMAL_PLACES:
        return None
    return number


def format_decimal(number: Decimal | None) -> str:
    """画面・system_value 用の書式。1000 が 1E+3 にならない。None は空文字。"""
    return "" if number is None else format(number.normalize(), "f")


def _override_body_value(field: str, value: str, item_id: str) -> str | None:
    """override_* の human_value（{"v":1,"value":<文字列>}）から value の文字列。形が違えば warning を出して None。"""
    body = _parse_json_object(value, field, item_id)
    if body is None:
        return None
    raw = body.get("value")
    if body.get("v") != OVERRIDE_VERSION or not isinstance(raw, str):
        logger.warning("[v102_decisions] %s の形が違うため無視します: item=%s", field, item_id)
        return None
    return raw


def _value_overrides(latest: dict[str, str], item_id: str) -> ValueOverrides:
    parsed: dict[str, object] = {}
    for field in OVERRIDE_FIELDS:
        if field not in latest:
            continue
        raw = _override_body_value(field, latest[field], item_id)
        if raw is None:
            continue
        key = field[len(OVERRIDE_PREFIX):]
        if field in (FIELD_OVERRIDE_QUANTITY, FIELD_OVERRIDE_PRICE):
            number = _decimal_or_none(raw)
            if number is None:
                logger.warning("[v102_decisions] %s が数字として使えないため無視します: item=%s", field, item_id)
                continue
            parsed[key] = number
        elif field == FIELD_OVERRIDE_NOTE:
            parsed[key] = raw
        elif raw.strip():
            parsed[key] = raw.strip()
        else:
            logger.warning("[v102_decisions] %s が空のため無視します: item=%s", field, item_id)
    return ValueOverrides(**parsed)


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
        {"ids": ids, "fields": [*_LOAD_FIELDS, *TRANSCRIPTION_FIELDS]},
    ).fetchall()
    by_item: dict[str, list] = {}
    for row in rows:
        by_item.setdefault(row.item_id, []).append(row)

    products: dict[str, int] = {}
    conditions: dict[str, int] = {}
    acks: dict[str, frozenset[str]] = {}
    overrides: dict[str, ValueOverrides] = {}
    for item_id, item_rows in by_item.items():
        transcription = [r.corrected_at for r in item_rows if r.field_name in TRANSCRIPTION_FIELDS]
        latest = _latest_valid(
            [r for r in item_rows if r.field_name in _LOAD_FIELDS], max(transcription) if transcription else None
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
        values = _value_overrides(latest, item_id)
        if not values.is_empty:
            overrides[item_id] = values

    active = _active_condition_ids(session, set(conditions.values()))
    for item_id in [i for i, cid in conditions.items() if cid not in active]:
        logger.warning("[v102_decisions] 選ばれた状態が有効でないため無視します: item=%s", item_id)
        del conditions[item_id]
    result = {
        item_id: Decisions(
            products.get(item_id), conditions.get(item_id), acks.get(item_id, frozenset()), overrides.get(item_id, ValueOverrides())
        )
        for item_id in {*products, *conditions, *acks, *overrides}
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
    await _insert_review_ack_union(
        db, extraction_item_id=extraction_item_id, source_message_id=source_message_id, codes=codes, corrected_by=corrected_by,
    )
    await db.commit()  # public スキーマのみでテナント文脈を使わないため reset_tenant_context は不要(save_corrections と同じ)
    return 1


async def _insert_review_ack_union(
    db: AsyncSession, *, extraction_item_id: str, source_message_id: str, codes: list[str], corrected_by: str,
) -> None:
    """review_ack を1行追記する（commit しない。呼び出し元が commit する）。有効な前の確認済みとの和集合。"""
    schema = TCG_SCHEMA
    current = (await db.execute(text(_CURRENT_REASONS_SQL.format(schema=schema)), {"eid": extraction_item_id})).first()
    # 有効な前の確認済みと和集合にする（1理由ずつ押しても先の分が消えない）。書き写し直し後は load_v102_decisions が空を返す
    previous = (await db.run_sync(lambda sync: load_v102_decisions(sync, [extraction_item_id]))).get(extraction_item_id)
    previous_codes = sorted(previous.ack_codes) if previous is not None else []
    human_value = json.dumps(
        {"v": REVIEW_ACK_VERSION, "codes": normalize_ack_codes([*previous_codes, *codes])}, ensure_ascii=False
    )
    await db.execute(
        text(_INSERT_ACK_SQL.format(schema=schema)),
        {
            "eid": extraction_item_id, "smid": source_message_id, "field": FIELD_REVIEW_ACK,
            "sv": (current.review_reasons or "") if current is not None else "", "hv": human_value, "cb": corrected_by,
        },
    )


async def save_review_ack_revoke(
    db: AsyncSession, *, extraction_item_id: str, source_message_id: str, corrected_by: str,
) -> int:
    """確認済みの取り消し。{"v":1,"codes":[]} の review_ack 行を1行追記する（記録は消さない）。

    前の有効な ack が無ければ何も書かず rollback（FOR UPDATE を外す）して 0 を返す。書いたら 1。
    """
    schema = TCG_SCHEMA
    current = (await db.execute(text(_CURRENT_REASONS_SQL.format(schema=schema)), {"eid": extraction_item_id})).first()
    previous = (await db.run_sync(lambda sync: load_v102_decisions(sync, [extraction_item_id]))).get(extraction_item_id)
    if previous is None or not previous.ack_codes:
        await db.rollback()
        return 0
    human_value = json.dumps({"v": REVIEW_ACK_VERSION, "codes": []}, ensure_ascii=False)
    await db.execute(
        text(_INSERT_ACK_SQL.format(schema=schema)),
        {
            "eid": extraction_item_id, "smid": source_message_id, "field": FIELD_REVIEW_ACK,
            "sv": (current.review_reasons or "") if current is not None else "", "hv": human_value, "cb": corrected_by,
        },
    )
    await db.commit()
    return 1


def unknown_codes(codes: Iterable[str], registered: Mapping[str, object]) -> list[str]:
    """review_reason_codes に無いコード（順番を保つ）。"""
    return [c for c in dict.fromkeys(codes) if c not in registered]


# ---------------------------------------------------------------------------
# 判断を保存する前の検査（API と CSV の両方がここを呼ぶ。検査の判定の唯一の置き場所）
# 読み込み（DB）は呼ぶ側が行い、ここは受け取った値だけで判定する（応答の文言・ステータスはここだけで決まる）。
# ---------------------------------------------------------------------------


class DecisionRejected(Exception):
    """保存前の検査で断った。status は HTTP のステータスコード、message は応答の文言。"""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def product_rejection(invalid_values: list[str]) -> DecisionRejected | None:
    """invalid_product_values の結果（無効な商品の値）から、断る理由。無効が無ければ None。v102 の件にだけ使う。"""
    if not invalid_values:
        return None
    return DecisionRejected(422, f"Product is not an active product: {', '.join(invalid_values)}")


def review_ack_rejection(
    codes: list[str], registered: Mapping[str, object], found: JobOfItem | None, source_message_id: str,
) -> DecisionRejected | None:
    """「このままで良い」を保存してよいか。よければ None。

    断る順番: 外せない理由(422)→未登録コード(422)→件なし(404)→v102 でない(409)→source_message_id 不一致(422)。
    registered は load_review_reason_codes の結果、found は find_job_of_item の結果。
    """
    from app.services.review_reason_codes_svc import non_ackable_codes  # noqa: PLC0415

    refused = non_ackable_codes(codes)
    if refused:
        return DecisionRejected(422, f"Review reason codes that cannot be acknowledged: {', '.join(refused)}")
    unknown = unknown_codes(codes, registered)
    if unknown:
        return DecisionRejected(422, f"Unregistered review reason codes: {', '.join(unknown)}")
    return item_rejection(found, source_message_id)


def item_rejection(found: JobOfItem | None, source_message_id: str) -> DecisionRejected | None:
    """review-ack の確定と取り消しに共通の検査。件なし(404)→v102 でない(409)→source_message_id 不一致(422)。"""
    from app.services.line_analysis_v102_svc import is_v102_prompt_version  # noqa: PLC0415  循環 import を避ける

    if found is None:
        return DecisionRejected(404, "Item not found")
    if not is_v102_prompt_version(found.prompt_version):
        return DecisionRejected(409, "review-ack is only for v102 items")
    if source_message_id != found.source_message_id:
        return DecisionRejected(422, "source_message_id does not match the item's post")
    return None


# ---------------------------------------------------------------------------
# 比較表から直した値（数量・単価・単位・メモ・販売状況）。検査・選択肢・重ね方・保存の唯一の置き場所
# ---------------------------------------------------------------------------

_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"
_CURRENT_VALUES_SQL = """
    SELECT quantity_normalized, price_normalized, unit_id, unit_canonical, unit_resolved, note_ja, status, exclusion
    FROM {schema}.analysis_results WHERE extraction_item_id = CAST(:eid AS uuid) FOR UPDATE
"""
_UPDATE_VALUES_SQL = """
    UPDATE {schema}.analysis_results SET
        quantity_normalized = :quantity_normalized, price_normalized = :price_normalized, unit_id = :unit_id,
        unit_canonical = :unit_canonical, unit_resolved = :unit_resolved, note_ja = :note_ja, status = :status,
        exclusion = :exclusion, updated_at = now()
    WHERE extraction_item_id = CAST(:eid AS uuid)
"""


def _status_canonicals(status_entries: list[dict]) -> list[str]:
    """選べる販売状況（effect が OUTPUT か EXCLUDE の canonical。マスタの順・重複なし）。"""
    return list(dict.fromkeys(e["canonical"] for e in status_entries if e.get("effect") in _STATUS_EFFECTS_OK and e.get("canonical")))


def _status_is_exclude(canonical: str, status_entries: list[dict]) -> bool:
    return any(e.get("canonical") == canonical and e.get("effect") == _STATUS_EFFECT_EXCLUDE for e in status_entries)


def override_rejection(
    field: str, value: str, unit_ids: Mapping[str, str], status_entries: list[dict],
) -> DecisionRejected | None:
    """直した値を保存してよいか。よければ None。field は quantity / price / unit / note / status（override_ 付きでも可）。"""
    key = field[len(OVERRIDE_PREFIX):] if field.startswith(OVERRIDE_PREFIX) else field
    if key not in OVERRIDE_FIELD_OF_KEY:
        return DecisionRejected(422, f"Unknown field: {field}")
    if key in ("quantity", "price"):
        if _decimal_or_none(value) is None:
            return DecisionRejected(422, f"{key} must be a number from 0 with at most {_MAX_DECIMAL_PLACES} decimal places")
    elif key == "unit":
        if value.strip() not in unit_ids:
            return DecisionRejected(422, f"Unknown unit: {value}")
    elif key == "status":
        if value.strip() not in _status_canonicals(status_entries):
            return DecisionRejected(422, f"Unknown status: {value}")
    elif len(value) > MAX_NOTE_LENGTH:
        return DecisionRejected(422, f"note must be at most {MAX_NOTE_LENGTH} characters")
    return None


def override_options(unit_ids: Mapping[str, str], status_entries: list[dict]) -> dict[str, list[str]]:
    """画面の選択肢。検査（override_rejection）と同じ集合から作る。"""
    return {"units": sorted(unit_ids), "statuses": _status_canonicals(status_entries)}


def apply_value_overrides(
    values: dict, overrides: ValueOverrides, unit_ids: Mapping[str, str], status_entries: list[dict],
) -> dict:
    """人が直した値を analysis_results の列に重ねる（元の values は変えない。review_reasons・needs_review は変えない）。

    単位・販売状況がマスタから消えていたら、その項目だけ warning を出して重ねない（例外にしない）。
    """
    if overrides.is_empty:
        return values
    out = dict(values)
    if overrides.quantity is not None:
        out["quantity_normalized"] = overrides.quantity
    if overrides.price is not None:
        out["price_normalized"] = overrides.price
    if overrides.unit is not None:
        unit_id = unit_ids.get(overrides.unit)
        if unit_id is None:
            logger.warning("[v102_decisions] 直された単位がマスタに無いため重ねません: unit=%s", overrides.unit)
        else:
            out.update(unit_canonical=overrides.unit, unit_id=int(unit_id), unit_resolved=True)
    if overrides.note is not None:
        out["note_ja"] = overrides.note or None
    if overrides.status is not None:
        if overrides.status not in _status_canonicals(status_entries):
            logger.warning("[v102_decisions] 直された販売状況がマスタに無いため重ねません: status=%s", overrides.status)
        else:
            out.update(status=overrides.status, exclusion="excluded" if _status_is_exclude(overrides.status, status_entries) else None)
    return out


def status_available_by_human(decision: Decisions | None, status_entries: list[dict]) -> bool:
    """人が販売状況を EXCLUDE 以外（在庫あり側）に直した件か。マスタに無い状態は重ならないので False。"""
    status = decision.values.status if decision is not None else None
    return status is not None and status in _status_canonicals(status_entries) and not _status_is_exclude(status, status_entries)


def _current_text(key: str, row) -> str:
    if row is None:
        return ""
    if key in ("quantity", "price"):
        return format_decimal(row.quantity_normalized if key == "quantity" else row.price_normalized)
    return {"unit": row.unit_canonical, "note": row.note_ja, "status": row.status}[key] or ""


def _stored_value(key: str, value: str) -> str:
    if key in ("quantity", "price"):
        return format_decimal(_decimal_or_none(value))
    return value if key == "note" else value.strip()


async def save_value_override(
    db: AsyncSession, *, extraction_item_id: str, source_message_id: str, field: str, value: str, corrected_by: str,
) -> int:
    """直した値を item_corrections に1行追記し、同じ取引で analysis_results の該当列を直す。保存した行数（1）。

    断るとき（件なし 404・v102 でない 409・source 不一致 422・値が不正 422）は rollback して何も書かず DecisionRejected を送出する。
    """
    from app.services.tcg_analyzer_svc import (  # noqa: PLC0415  循環 import を避ける
        load_status_master,
        load_unit_canonical_ids,
    )

    schema = TCG_SCHEMA
    found = await find_job_of_item(db, extraction_item_id)
    rejected = item_rejection(found, source_message_id) if found is not None else DecisionRejected(404, "Item not found")
    if rejected is not None:
        await db.rollback()
        raise rejected
    # 走行中の再解析と順番にする（run_v102_analysis と同じ鍵）
    await db.execute(text(_LOCK_SQL), {"key": f"v102_analysis:{found.job_id}"})
    # マスタは INSERT の前に読む（load_status_master は例外時に rollback するため）
    unit_ids = await db.run_sync(load_unit_canonical_ids)
    status_entries = await db.run_sync(load_status_master)
    rejected = override_rejection(field, value, unit_ids, status_entries)
    if rejected is not None:
        await db.rollback()
        raise rejected
    key = field[len(OVERRIDE_PREFIX):] if field.startswith(OVERRIDE_PREFIX) else field
    field_name = OVERRIDE_FIELD_OF_KEY[key]
    current = (await db.execute(text(_CURRENT_VALUES_SQL.format(schema=schema)), {"eid": extraction_item_id})).first()
    await db.execute(
        text(_INSERT_ACK_SQL.format(schema=schema)),
        {
            "eid": extraction_item_id, "smid": source_message_id, "field": field_name, "sv": _current_text(key, current),
            "hv": json.dumps({"v": OVERRIDE_VERSION, "value": _stored_value(key, value)}, ensure_ascii=False), "cb": corrected_by,
        },
    )
    if current is not None:
        decision = (await db.run_sync(lambda sync: load_v102_decisions(sync, [extraction_item_id]))).get(extraction_item_id)
        columns = {
            "quantity_normalized": current.quantity_normalized, "price_normalized": current.price_normalized,
            "unit_id": current.unit_id, "unit_canonical": current.unit_canonical, "unit_resolved": current.unit_resolved,
            "note_ja": current.note_ja, "status": current.status, "exclusion": current.exclusion,
        }
        if decision is not None:
            columns = apply_value_overrides(columns, decision.values, unit_ids, status_entries)
        await db.execute(text(_UPDATE_VALUES_SQL.format(schema=schema)), {**columns, "eid": extraction_item_id})
    if key == "status" and _status_is_exclude(value.strip(), status_entries):
        # 人が自分で売り切れにした件を、除外の理由で要確認に戻さない
        await _insert_review_ack_union(
            db, extraction_item_id=extraction_item_id, source_message_id=source_message_id,
            codes=[_EXCLUDED_ACK_CODE], corrected_by=corrected_by,
        )
    await db.commit()
    return 1
