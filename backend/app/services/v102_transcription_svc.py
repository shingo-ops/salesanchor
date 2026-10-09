"""v102 の投稿ごとの「Gemini の書き写し」の一覧・詳細・保存（便C1）。

設計: docs/handoff/v102-prod-switch/design.md §13-3・§13-5、実装カード: docs/handoff/v102-prod-switch/card-C1.md
人の直しは public.item_corrections に追記で残す（field_name の文字列は v102_human_decisions_svc の定数）。
原文の行の数え方は Gemini に渡す側（gemini_raw_copy_v101.py の raw_text.split("\\n")）と frontend の sourceRawLines と同じ:
1 始まり・改行 "\\n" で分け・空行も 1 行として数える。
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import tcg_analyzer_svc as analyzer
from app.services import v102_human_decisions_svc as decisions
from app.services.line_analysis_v102_svc import is_v102_prompt_version
from app.services.review_reason_codes_svc import ReasonTable, build_review_reason_details

# テスト互換性のため属性を維持する（monkeypatch.setattr 対象。本番は public）
TCG_SCHEMA = "public"

FIX_STAGE_EXTRACTION = "extraction"
PROVIDER_UNKNOWN = "不明"  # 要確認 API（tcg_analysis_review_svc）と同じ仕入元名の出し方
_NEW_ITEM_ORDER = 10**9  # gemini_index が無い件・新しい件の並びを後ろにするための大きな数

_JOB_SQL = """
    SELECT ej.id::text AS job_id, ej.source_message_id::text AS source_message_id, ej.prompt_version,
           ej.review_reasons, ej.gemini_unsure, sm.raw_text, sm.line_posted_at,
           COALESCE(ps.name, :unknown) AS provider
    FROM {schema}.extraction_jobs ej
    JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id
    LEFT JOIN {schema}.supplier_channels sc ON sc.id = sm.supplier_channel_id
    LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
    WHERE ej.id = CAST(:job_id AS uuid)
"""
_ITEMS_SQL = """
    SELECT ei.id::text AS id, ei.gemini_index, ei.source_lines, ei.raw_price, ei.raw_quantity, ar.review_reasons
    FROM {schema}.extraction_items ei
    LEFT JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ei.extraction_job_id = CAST(:job_id AS uuid)
    ORDER BY ei.gemini_index NULLS LAST, ei.id
"""
# 一覧の対象: v102 の投稿で、(a) 投稿の理由がある、または (b) 件の理由に fix_stage='extraction' のコードがある
_LIST_BASE_SQL = """
    WITH ext AS (
        SELECT ei.extraction_job_id AS job_id, COUNT(*) AS n
        FROM {schema}.extraction_items ei
        JOIN {schema}.extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
        WHERE ej.prompt_version LIKE 'v102:%'
          AND EXISTS (
              SELECT 1 FROM unnest(string_to_array(ar.review_reasons, ',')) AS r(code)
              WHERE btrim(r.code) = ANY(CAST(:codes AS text[]))
          )
        GROUP BY ei.extraction_job_id
    ),
    posts AS (
        SELECT ej.id AS job_id, ej.source_message_id, ej.review_reasons, sm.line_posted_at,
               COALESCE(ps.name, :unknown) AS provider, COALESCE(ext.n, 0) AS extraction_item_count,
               (SELECT COUNT(*) FROM {schema}.extraction_items ei WHERE ei.extraction_job_id = ej.id) AS item_count
        FROM {schema}.extraction_jobs ej
        JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id AND sm.is_active = TRUE
        LEFT JOIN {schema}.supplier_channels sc ON sc.id = sm.supplier_channel_id
        LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
        LEFT JOIN ext ON ext.job_id = ej.id
        WHERE ej.prompt_version LIKE 'v102:%'
          AND (ej.review_reasons IS NOT NULL OR COALESCE(ext.n, 0) > 0)
    )
"""
_LIST_SQL = _LIST_BASE_SQL + """
    SELECT job_id::text AS job_id, source_message_id::text AS source_message_id, provider, line_posted_at,
           review_reasons, item_count, extraction_item_count
    FROM posts
    ORDER BY line_posted_at DESC NULLS LAST, job_id
    LIMIT :limit OFFSET :offset
"""
_COUNT_SQL = _LIST_BASE_SQL + "SELECT COUNT(*) FROM posts"
# 削除する件の解決済みの (product_id, condition_id)。DELETE の前に読み、削除後の is_current の付け直しに渡す
_PAIRS_OF_ITEMS_SQL = """
    SELECT DISTINCT ar.product_id, ar.condition_id
    FROM {schema}.analysis_results ar
    WHERE ar.extraction_item_id = ANY(CAST(:ids AS uuid[]))
      AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL AND ar.condition_id IS NOT NULL
"""
_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"
_UPDATE_ITEM_SQL = """
    UPDATE {schema}.extraction_items
    SET source_lines = CAST(:lines AS INTEGER[]), line_start = :line_start, line_end = :line_end,
        raw_price = :raw_price, raw_quantity = :raw_quantity
    WHERE id = CAST(:id AS uuid) AND extraction_job_id = CAST(:job_id AS uuid)
"""
_INSERT_ITEM_SQL = """
    INSERT INTO {schema}.extraction_items
        (id, extraction_job_id, line_start, line_end, raw_price, raw_quantity, source_lines, gemini_index, created_at)
    VALUES (CAST(:id AS uuid), CAST(:job_id AS uuid), :line_start, :line_end, :raw_price, :raw_quantity,
            CAST(:lines AS INTEGER[]), :gemini_index, now())
"""
_DELETE_ITEM_SQL = "DELETE FROM {schema}.extraction_items WHERE id = CAST(:id AS uuid) AND extraction_job_id = CAST(:job_id AS uuid)"
_RENUMBER_SQL = "UPDATE {schema}.extraction_items SET gemini_index = :gemini_index WHERE id = CAST(:id AS uuid)"
_INSERT_CORRECTION_SQL = """
    INSERT INTO {schema}.item_corrections
        (extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by)
    VALUES (CAST(:eid AS uuid), CAST(:smid AS uuid), :field, :sv, :hv, :cb)
"""


class PostNotFound(Exception):
    """その job_id の投稿が無い（形が uuid でない場合を含む）。"""


class PostNotV102(Exception):
    """v102 でない投稿（v6 など）。"""


class InvalidTranscription(Exception):
    """保存内容の検査違反。何も書かない。"""


@dataclass(frozen=True)
class PostJob:
    job_id: str
    source_message_id: str
    prompt_version: str | None
    review_reasons: str | None
    gemini_unsure: Any
    raw_text: str
    line_posted_at: Any
    provider: str


@dataclass(frozen=True)
class ItemInput:
    """保存する件の1つ。id が None なら新しい件。source_lines は検査済み（昇順・重複なし）。"""

    id: str | None
    source_lines: list[int]
    raw_price: str | None
    raw_quantity: str | None


@dataclass(frozen=True)
class EditResult:
    changed: bool
    item_ids: list[str]


def split_raw_lines(raw_text: str | None) -> list[dict]:
    """原文の行 [{number, text}]（1 始まり・"\\n" で分け・空行も数える。text に改行は含めない）。"""
    return [{"number": n, "text": part} for n, part in enumerate((raw_text or "").split("\n"), 1)]


def v102_analysis_lock_key(job_id: str) -> str:
    """システム段(run_v102_analysis, line_analysis_v102_svc.py)と同じ advisory lock の鍵。"""
    return f"v102_analysis:{job_id}"


def _json_value(value: object) -> Any:
    """text() で読んだ JSONB は asyncpg では文字列で返ることがある。その場合だけ JSON として読む（壊れていたらそのまま）。"""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _int_list(value: object) -> list[int]:
    return [int(n) for n in value] if isinstance(value, (list, tuple)) else []


def _lines_json(lines: list[int] | None) -> str:
    return json.dumps(list(lines), ensure_ascii=False) if lines else ""


def _item_json(item_id: str, gemini_index: int | None, lines: list[int], raw_price: str | None, raw_quantity: str | None) -> str:
    return json.dumps(
        {"id": item_id, "gemini_index": gemini_index, "source_lines": lines, "raw_price": raw_price, "raw_quantity": raw_quantity},
        ensure_ascii=False,
    )


async def load_job(db: AsyncSession, job_id: str) -> PostJob:
    """投稿を読む。無ければ PostNotFound、v102 でなければ PostNotV102。"""
    try:
        row = (await db.execute(text(_JOB_SQL.format(schema=TCG_SCHEMA)), {"job_id": job_id, "unknown": PROVIDER_UNKNOWN})).first()
    except Exception as exc:  # noqa: BLE001  uuid の形でない job_id は「無い」と同じ扱い
        await db.rollback()
        raise PostNotFound(job_id) from exc
    if row is None:
        raise PostNotFound(job_id)
    if not is_v102_prompt_version(row.prompt_version):
        raise PostNotV102(job_id)
    return PostJob(
        row.job_id, row.source_message_id, row.prompt_version, row.review_reasons, _json_value(row.gemini_unsure),
        row.raw_text or "", row.line_posted_at, row.provider,
    )


async def list_posts(db: AsyncSession, table: ReasonTable, *, limit: int, offset: int) -> dict:
    codes = sorted(code for code, (_source, stage) in table.items() if stage == FIX_STAGE_EXTRACTION)
    params = {"codes": codes, "unknown": PROVIDER_UNKNOWN}
    total = (await db.execute(text(_COUNT_SQL.format(schema=TCG_SCHEMA)), params)).scalar_one()
    rows = (await db.execute(text(_LIST_SQL.format(schema=TCG_SCHEMA)), {**params, "limit": limit, "offset": offset})).fetchall()
    items = [
        {
            "job_id": r.job_id, "source_message_id": r.source_message_id, "provider": r.provider,
            "line_posted_at": r.line_posted_at,
            "job_review_reason_details": build_review_reason_details(r.review_reasons, table),
            "item_count": r.item_count, "extraction_item_count": r.extraction_item_count,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def get_post(db: AsyncSession, job: PostJob, table: ReasonTable) -> dict:
    rows = (await db.execute(text(_ITEMS_SQL.format(schema=TCG_SCHEMA)), {"job_id": job.job_id})).fetchall()
    return {
        "job_id": job.job_id, "source_message_id": job.source_message_id, "provider": job.provider,
        "line_posted_at": job.line_posted_at, "lines": split_raw_lines(job.raw_text),
        "job_review_reason_details": build_review_reason_details(job.review_reasons, table),
        "gemini_unsure": job.gemini_unsure,
        "items": [
            {
                "id": r.id, "gemini_index": r.gemini_index, "source_lines": _int_list(r.source_lines),
                "raw_price": r.raw_price, "raw_quantity": r.raw_quantity,
                "review_reason_details": build_review_reason_details(r.review_reasons, table),
            }
            for r in rows
        ],
    }


def _validate(items: list[ItemInput], line_count: int, existing_ids: set[str]) -> None:
    """行番号は 1〜行数、id はこの投稿の件、同じ id は 1 回だけ。違反は InvalidTranscription。"""
    seen: set[str] = set()
    for position, item in enumerate(items):
        bad = [n for n in item.source_lines if not 1 <= n <= line_count]
        if bad:
            raise InvalidTranscription(f"items[{position}].source_lines out of range 1..{line_count}: {bad}")
        if item.id is None:
            continue
        if item.id not in existing_ids:
            raise InvalidTranscription(f"items[{position}].id is not an item of this post: {item.id}")
        if item.id in seen:
            raise InvalidTranscription(f"items[{position}].id is duplicated: {item.id}")
        seen.add(item.id)


def _plan_order(items: list[ItemInput], existing: dict[str, Any]) -> list[tuple[ItemInput, str]]:
    """(件, 使う id) を gemini_index の新しい順に並べる。キー: (最小の行番号, 新しい件は後ろ, 元の gemini_index, body の順)。"""
    keyed = []
    for position, item in enumerate(items):
        is_new = item.id is None
        original = _NEW_ITEM_ORDER if is_new or existing[item.id].gemini_index is None else existing[item.id].gemini_index
        keyed.append(((min(item.source_lines), is_new, original, position), item, item.id or str(uuid.uuid4())))
    keyed.sort(key=lambda k: k[0])
    return [(item, item_id) for _key, item, item_id in keyed]


async def _add_correction(
    db: AsyncSession, *, item_id: str, source_message_id: str, field: str, system_value: str, human_value: str, corrected_by: str,
) -> None:
    await db.execute(
        text(_INSERT_CORRECTION_SQL.format(schema=TCG_SCHEMA)),
        {"eid": item_id, "smid": source_message_id, "field": field, "sv": system_value, "hv": human_value, "cb": corrected_by},
    )


async def _record_item_changes(db: AsyncSession, job: PostJob, before: Any, item: ItemInput, corrected_by: str) -> bool:
    """既存の件で値が変わった項目ごとに item_corrections を 1 行。1 つでも変わったら True。"""
    old_lines = _int_list(before.source_lines)
    changes = []
    if old_lines != item.source_lines:
        changes.append((decisions.FIELD_V102_LINES, _lines_json(old_lines), _lines_json(item.source_lines)))
    if before.raw_price != item.raw_price:
        changes.append((decisions.FIELD_V102_PRICE, before.raw_price or "", item.raw_price or ""))
    if before.raw_quantity != item.raw_quantity:
        changes.append((decisions.FIELD_V102_QUANTITY, before.raw_quantity or "", item.raw_quantity or ""))
    for field, system_value, human_value in changes:
        await _add_correction(
            db, item_id=before.id, source_message_id=job.source_message_id, field=field,
            system_value=system_value, human_value=human_value, corrected_by=corrected_by,
        )
    if changes:
        await db.execute(
            text(_UPDATE_ITEM_SQL.format(schema=TCG_SCHEMA)),
            {
                "id": before.id, "job_id": job.job_id, "lines": item.source_lines, "line_start": min(item.source_lines),
                "line_end": max(item.source_lines), "raw_price": item.raw_price, "raw_quantity": item.raw_quantity,
            },
        )
    return bool(changes)


async def _delete_missing(
    db: AsyncSession, job: PostJob, existing: dict[str, Any], kept_ids: set[str], corrected_by: str,
) -> list[tuple[int, int]]:
    """body に無い既存の件を削除する。削除した件の (product_id, condition_id) の組を返す（is_current の付け直し用）。"""
    removed = [row for item_id, row in existing.items() if item_id not in kept_ids]
    if not removed:
        return []
    pair_rows = (await db.execute(text(_PAIRS_OF_ITEMS_SQL.format(schema=TCG_SCHEMA)), {"ids": [r.id for r in removed]})).fetchall()
    for row in removed:
        await _add_correction(
            db, item_id=row.id, source_message_id=job.source_message_id, field=decisions.FIELD_V102_ITEM_DELETED,
            system_value=_item_json(row.id, row.gemini_index, _int_list(row.source_lines), row.raw_price, row.raw_quantity),
            human_value="{}", corrected_by=corrected_by,
        )
        await db.execute(text(_DELETE_ITEM_SQL.format(schema=TCG_SCHEMA)), {"id": row.id, "job_id": job.job_id})
    return [(int(r[0]), int(r[1])) for r in pair_rows]


async def _insert_new(db: AsyncSession, job: PostJob, item: ItemInput, item_id: str, corrected_by: str) -> None:
    await db.execute(
        text(_INSERT_ITEM_SQL.format(schema=TCG_SCHEMA)),
        {
            "id": item_id, "job_id": job.job_id, "line_start": min(item.source_lines), "line_end": max(item.source_lines),
            "raw_price": item.raw_price, "raw_quantity": item.raw_quantity, "lines": item.source_lines, "gemini_index": 0,
        },
    )
    await _add_correction(
        db, item_id=item_id, source_message_id=job.source_message_id, field=decisions.FIELD_V102_ITEM_ADDED, system_value="",
        human_value=_item_json(item_id, None, item.source_lines, item.raw_price, item.raw_quantity), corrected_by=corrected_by,
    )


async def apply_transcription_edit(db: AsyncSession, job: PostJob, items: list[ItemInput], corrected_by: str) -> EditResult:
    """1 つのトランザクションで保存する。違反は InvalidTranscription（何も書かずロールバック）。

    最初にシステム段と同じ advisory lock を取り、投稿の件を読み直してから検査・書き込みをする。
    何も変わらなければ書かずに終わる（changed=False）。変わったら commit する（enqueue は呼び出し側）。
    """
    await db.execute(text(_LOCK_SQL), {"key": v102_analysis_lock_key(job.job_id)})
    rows = (await db.execute(text(_ITEMS_SQL.format(schema=TCG_SCHEMA)), {"job_id": job.job_id})).fetchall()
    existing = {r.id: r for r in rows}
    try:
        _validate(items, len(split_raw_lines(job.raw_text)), set(existing))
    except InvalidTranscription:
        await db.rollback()
        raise
    ordered = _plan_order(items, existing)
    changed = False
    for item in (i for i in items if i.id is not None):
        changed = await _record_item_changes(db, job, existing[item.id], item, corrected_by) or changed
    removed_pairs = await _delete_missing(db, job, existing, {i.id for i in items if i.id is not None}, corrected_by)
    changed = changed or len(existing) > len({i.id for i in items if i.id is not None})
    for item, item_id in ordered:
        if item.id is None:
            await _insert_new(db, job, item, item_id, corrected_by)
            changed = True
    if not changed:
        await db.rollback()  # 何も書いていない。ロックだけ手放す
        return EditResult(False, [item_id for _item, item_id in ordered if item_id in existing])
    for index, (_item, item_id) in enumerate(ordered):
        await db.execute(text(_RENUMBER_SQL.format(schema=TCG_SCHEMA)), {"id": item_id, "gemini_index": index})
    if removed_pairs:  # 削除した件が最新だった組は、同じ仕入元の次に新しい投稿の件を最新に戻す（G5）。同じトランザクション内
        await db.run_sync(lambda sync: analyzer._merge_supplier_products(sync, job.job_id, TCG_SCHEMA, extra_pairs=removed_pairs))
    await db.commit()  # public スキーマのみでテナント文脈を使わないため reset_tenant_context は不要(item_corrections と同じ)
    return EditResult(True, [item_id for _item, item_id in ordered])
