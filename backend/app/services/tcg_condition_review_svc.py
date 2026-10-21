"""PostgreSQL-owned condition acknowledgments and effective review state.

Every read gate uses review_joins BEFORE filtering/paging. Fingerprints never leave
PostgreSQL for reserialization. History is append-only and malformed latest events
fail closed, without falling back to an older acknowledgment.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.services.tcg_empty_box_rules import (
    EMPTY_REASONS,
    EMPTY_WORD,
    POSITIVE_SUFFIXES,
    WHITESPACE,
    classification_sql,
    empty_definition_sql,
    literal,
)

# conditions.effect が EXCLUDE の状態 = 配信しない状態（Error。PO 2026-10-11）。唯一の置き場所。
# effect 列が無い古い試験 DB でも落ちないよう、列は to_jsonb(行) 経由で読む（無ければ NULL = 除外しない）。
CONDITION_EFFECT_EXCLUDE = "EXCLUDE"


# 人が状態を選んだ時に外す理由（v102 の _apply_decisions / 〆の引き継ぎと同じ集合。唯一の置き場所。line_analysis_v102_svc はここから import する）
REASON_CONDITION_UNKNOWN = "condition_unknown"
REASON_CONDITION_MULTIPLE = "condition_multiple_candidates"
CONDITION_REVIEW_REASONS = (REASON_CONDITION_UNKNOWN, REASON_CONDITION_MULTIPLE)


def condition_effect_sql(alias: str) -> str:
    return f"to_jsonb({alias})->>'effect'"


def not_excluded_condition_sql(alias: str) -> str:
    return f"{condition_effect_sql(alias)} IS DISTINCT FROM '{CONDITION_EFFECT_EXCLUDE}'"


# Step 4/5: TCG テーブルは public スキーマに移行済み。
# テスト互換性のため TCG_SCHEMA 属性を維持する（monkeypatch.setattr 対象）。
TCG_SCHEMA = "public"

_UUID_PATTERN = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
_HEX_PATTERN = "^[0-9a-f]{64}$"
# 〆の確認済み扱いで「在庫表にまだ在庫がある」とみなす投稿の新しさ（時間）。
# 本番の tcg_distribution_settings.max_age_hours（48）と同じ値。設定を変えたらここも変える（docs/handoff/shime-review-exclude/design.md §12-3）
SHIME_STOCK_WINDOW_HOURS = 48
_SOURCE_CTE_NAME = "condition_review_sources"


def digest_sql(expression: str) -> str:
    return f"encode(sha256(convert_to(({expression})::text, 'UTF8')), 'hex')"


def latest_stock_cte(schema: str) -> str:
    """cr_prev: 在庫の投稿（最新 job の、商品・状態が決まった「Sold out でない」行を持つ投稿）を、チャネル×商品ごとに引ける形で1回だけ集める。

    review_joins(shime=True) の cr_n1x が行ごとの相関サブクエリだと、本番で 1,476,379（main 508,702）まで膨らむため（docs/handoff/shime-review-exclude/design.md §13-10-2）。
    窓（line_posted_at >= NOW() - SHIME_STOCK_WINDOW_HOURS）は、cr_n1 を相手にする条件（cr_shime の cr_sm.line_posted_at >= ...）と同じ式。
    窓の外の投稿は、相手の条件で必ず落ちるので、ここで落としても結果は変わらない（窓の外が最新なら、それより前も全て窓の外）。
    """
    return f"""cr_prev AS MATERIALIZED (
        SELECT cr_n1.supplier_channel_id, cr_n1a.product_id, cr_n1.id, cr_n1.line_posted_at
        FROM {schema}.source_messages cr_n1
        JOIN (SELECT DISTINCT ON (source_message_id) id, source_message_id FROM {schema}.extraction_jobs
              ORDER BY source_message_id, created_at DESC, id DESC) cr_n1j ON cr_n1j.source_message_id = cr_n1.id
        JOIN {schema}.extraction_items cr_n1i ON cr_n1i.extraction_job_id = cr_n1j.id
        JOIN {schema}.analysis_results cr_n1a ON cr_n1a.extraction_item_id = cr_n1i.id
        WHERE cr_n1a.pid_resolved IS TRUE AND cr_n1a.condition_id IS NOT NULL
          AND cr_n1a.status IS DISTINCT FROM 'Sold out'
          AND cr_n1.line_posted_at >= NOW() - make_interval(hours => {SHIME_STOCK_WINDOW_HOURS})
    )"""


def source_cte(*, schema: str | None = None, item_only: bool = False, source_hash: str | None = None, include_inactive: bool = False,
               latest_stock: bool = True) -> str:
    schema = schema or "public"
    if item_only:
        scope = (f"WHERE id=(SELECT ej.source_message_id FROM {schema}.extraction_items ei "
                 f"JOIN {schema}.extraction_jobs ej ON ej.id=ei.extraction_job_id WHERE ei.id=CAST(:eid AS uuid))")
    elif include_inactive:
        scope = ""
    else:
        scope = "WHERE is_active IS TRUE"
    hash_expression = source_hash or digest_sql("raw_text")
    # Materialization makes the full original-message hash reusable by its items.
    # latest_stock=True（既定）は review_joins(shime=True) の cr_prev を先頭に足す。review_joins(shime=False) の呼び出し側は False を渡し、文字列を変えない。
    prev = f"{latest_stock_cte(schema)},\n    " if latest_stock else ""
    return f"""WITH {prev}{_SOURCE_CTE_NAME} AS MATERIALIZED (
        SELECT id, {hash_expression} AS source_hash FROM {schema}.source_messages {scope}
    )"""


def _object_sql(pairs: Mapping[str, str]) -> str:
    return "jsonb_build_object(" + ",".join(f"{literal(k)}, {v}" for k, v in pairs.items()) + ")"


def _definition(expression: str) -> str:
    return _object_sql({key: f"{expression}->{literal(key)}" for key in (
        "id", "code", "canonical", "is_active", "priority", "app_kubun", "search_kw", "exclude_kw",
    )})


def _binding(selected: str) -> str:
    pairs = {"contract_version": "1", "source_message_id": "sm.id", "source_hash": "cr_source.source_hash",
             "item_id": "ei.id", "line_start": "ei.line_start", "line_end": "ei.line_end"}
    for key in ("raw_product_name", "raw_state", "raw_memo", "raw_unit", "raw_quantity", "raw_price",
                "raw_work_name", "raw_work_source_line_span"):
        pairs[key] = f"to_jsonb(ei)->'{key}'"
    for key in ("product_id", "unit_id", "unit_canonical", "unit_resolved"):
        pairs[key] = f"cr_data.ar->'{key}'"
    for key in ("quantity_normalized", "price_normalized"):
        pairs[key] = f"trim_scale((cr_data.ar->>'{key}')::numeric(14,2))"
    pairs.update({"product_title": "cr_product.name", "product_work": "cr_product.work_id",
                  "product_category": "to_jsonb(cr_product)->'product_category_id'",
                  "product_category_class": "to_jsonb(cr_product)->'category_class'",
                  "selected_condition": _definition(selected), "empty_condition": _definition("to_jsonb(cr_empty)")})
    return digest_sql(_object_sql(pairs))


def _fence_sub(pattern: str, repl: str, sql: str, expect: int) -> str:
    new, count = re.subn(pattern, repl, sql)
    if count != expect:
        raise RuntimeError(f"review_joins fence: pattern {pattern!r} expected={expect} got={count}")
    return new


def _fence_review_joins(sql: str) -> str:
    """配信行 SQL 用: 展開(pull-up)で to_jsonb(...) が参照ごとに再計算されるのを OFFSET 0 の壁で防ぐ。

    変換の個数が想定と違えば例外にする（SQL 正本は review_joins の1か所に保つ）。
    docs/handoff/v102-sp2-perf/design.md
    """
    sql = _fence_sub(r"\)\s*(cr_input|cr_hash|cr_valid|cr_reasons|cr)(?=\s*(?:CROSS|LEFT|JOIN|$))", r" OFFSET 0) \1", sql, 5)
    sql = re.sub(r"to_jsonb\(ei\)->", "cr_ei.j->", sql)
    if "cr_ei.j->" not in sql:
        raise RuntimeError("review_joins fence: to_jsonb(ei)-> not found")
    marker = "LEFT JOIN public.products cr_product"
    if sql.count(marker) != 1:
        raise RuntimeError("review_joins fence: cr_product marker count != 1")
    sql = sql.replace(marker, "CROSS JOIN LATERAL (SELECT to_jsonb(ei) AS j OFFSET 0) cr_ei\n    " + marker)
    for alias in ("cr_product", "cr_selected", "cr_ack_condition", "cr_empty", "cr_arc"):
        sql = re.sub(rf"to_jsonb\({alias}\)", f"cr_js.j_{alias}", sql)
    lines = sql.split("\n")
    idx = [i for i, ln in enumerate(lines) if "public.conditions cr_arc" in ln]
    if len(idx) != 1:
        raise RuntimeError("review_joins fence: cr_arc line count != 1")
    lines.insert(idx[0] + 1, (
        "    CROSS JOIN LATERAL (SELECT to_jsonb(cr_product) AS j_cr_product, to_jsonb(cr_selected) AS j_cr_selected, "
        "to_jsonb(cr_ack_condition) AS j_cr_ack_condition, to_jsonb(cr_empty) AS j_cr_empty, "
        "to_jsonb(cr_arc) AS j_cr_arc OFFSET 0) cr_js"))
    return "\n".join(lines)


def review_joins(*, analysis_expression: str = "to_jsonb(ar)", selected_expression: str | None = None,
                 schema: str | None = None, fenced: bool = False, shime: bool = True) -> str:
    """SQL requires ar/ei/ej/sm aliases plus source_cte; optional candidate for reanalysis.

    fenced=True は配信行 SQL 専用（OFFSET 0 の壁を追加）。既定 False は従来と同一の文字列。

    Expressions come exclusively from trusted source code, never request text.
    selected_expression is used for a POST's new binding, after old-version checking.
    """
    from app.services.v102_human_decisions_svc import (  # noqa: PLC0415  循環 import を避ける
        FIELD_REVIEW_ACK,
        REVIEW_ACK_VERSION,
        TRANSCRIPTION_FIELDS,
    )
    schema = schema or "public"
    ack_field = literal(FIELD_REVIEW_ACK)
    ack_version = int(REVIEW_ACK_VERSION)
    transcription_fields = ",".join(literal(f) for f in TRANSCRIPTION_FIELDS)
    classification = classification_sql("ei.raw_product_name", "ei.raw_state", "ei.raw_memo")
    mentions = " OR ".join(f"strpos(COALESCE(ei.{key}, ''), {literal(EMPTY_WORD)}) > 0"
                           for key in ("raw_product_name", "raw_state", "raw_memo"))
    valid_master = empty_definition_sql("to_jsonb(cr_empty)")
    selected = selected_expression or "cr_data.ar->>'condition_id'"
    empty_reasons = ",".join(literal(reason) for reason in EMPTY_REASONS)
    pure_memo = f"btrim(COALESCE(ei.raw_memo, ''), {literal(WHITESPACE)}) IN ({','.join(literal(v) for v in POSITIVE_SUFFIXES)})"
    binding = _binding("to_jsonb(cr_selected)")
    ack_binding = _binding("to_jsonb(cr_ack_condition)")
    version = digest_sql(_object_sql({
        "binding": "cr_hash.binding_hash", "condition_id": "cr_data.ar->'condition_id'",
        "condition_canonical": "cr_data.ar->'condition_canonical'", "condition_basis": "cr_data.ar->'condition_basis'",
        "computed_at": "extract(epoch FROM (cr_data.ar->>'computed_at')::timestamptz)",
        "updated_at": "extract(epoch FROM (cr_data.ar->>'updated_at')::timestamptz)",
        **{key: f"cr_data.ar->'{key}'" for key in ("review_reasons", "needs_review", "status", "exclusion", "note_ja")},
        "latest_correction_id": "cr_latest.id",
    }))
    shime_lateral = (
        "CROSS JOIN LATERAL (SELECT FALSE AS settled OFFSET 0) cr_shime" if not shime else
        f"""CROSS JOIN LATERAL (SELECT
        -- 〆の確認済み扱い（docs/handoff/shime-review-exclude/design.md §12-3）。真なら price_unresolved と excluded を付けない
        CASE WHEN
            lower(btrim(COALESCE(cr_data.ar->>'status', ''))) IN ('sold out', 'soldout')
            AND cr_data.ar->>'exclusion' = 'excluded'
            AND cr_data.ar->>'product_id' IS NOT NULL AND cr_data.ar->>'condition_id' IS NOT NULL
            AND strpos(COALESCE(cr_data.ar->>'condition_canonical', '') || COALESCE(cr_data.ar->>'condition_basis', ''), 'FLAG') = 0
            AND cr_latest.id IS NULL
        THEN NOT EXISTS (SELECT 1 FROM (
                -- 〆より前の最新の在庫の投稿（cr_n1x）。cr_prev（source_cte の先頭のCTE）から引く。窓は相手の条件と同じ式なので結果は変わらない（design.md §13-10-2）
                SELECT (SELECT cr_p.id FROM cr_prev cr_p
                        WHERE cr_p.supplier_channel_id = sm.supplier_channel_id
                          AND cr_p.product_id = (cr_data.ar->>'product_id')::integer
                          AND cr_p.line_posted_at < sm.line_posted_at
                        ORDER BY cr_p.line_posted_at DESC, cr_p.id DESC LIMIT 1) AS id) cr_n1x
                CROSS JOIN {schema}.analysis_results cr_sa
                JOIN {schema}.extraction_items cr_si ON cr_si.id = cr_sa.extraction_item_id
                JOIN {schema}.extraction_jobs cr_sj ON cr_sj.id = cr_si.extraction_job_id
                JOIN {schema}.source_messages cr_sm ON cr_sm.id = cr_sj.source_message_id
                WHERE cr_sm.supplier_channel_id = sm.supplier_channel_id
                  AND cr_sa.product_id = (cr_data.ar->>'product_id')::integer
                  AND cr_sa.extraction_item_id <> ei.id
                  AND (cr_sa.condition_id = (cr_data.ar->>'condition_id')::integer
                       -- 別の状態の相手は、〆以後の投稿か、〆より前の最新の在庫の投稿（cr_n1）のものだけ（design.md §13-10 A-2）
                       OR (cr_sm.id <> sm.id AND (sm.line_posted_at IS NULL OR cr_sm.line_posted_at >= sm.line_posted_at OR cr_sm.id = cr_n1x.id)))
                  AND cr_sa.is_current IS TRUE AND cr_sa.pid_resolved IS TRUE AND cr_sa.unit_resolved IS TRUE
                  AND cr_sa.exclusion IS DISTINCT FROM 'excluded'
                  AND cr_sa.price_normalized IS NOT NULL
                  AND cr_sm.line_posted_at >= NOW() - make_interval(hours => {SHIME_STOCK_WINDOW_HOURS})
                  AND COALESCE(cr_sa.condition_canonical, '') NOT LIKE 'FLAG_%'
                  AND lower(btrim(COALESCE(cr_sa.status, ''))) NOT IN ('sold out', 'soldout'))
        ELSE FALSE END AS settled OFFSET 0) cr_shime""")
    sql = f"""
    JOIN {_SOURCE_CTE_NAME} cr_source ON cr_source.id = sm.id
    -- OFFSET 0 は PostgreSQL の展開（pull-up）を止め、to_jsonb(ar) を行ごとに1回だけ作るため。外すと要確認一覧が約3倍遅くなる（docs/handoff/review-speed/design.md）
    CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar OFFSET 0) cr_data
    LEFT JOIN public.products cr_product ON cr_product.id::text = cr_data.ar->>'product_id'
    LEFT JOIN public.conditions cr_empty ON cr_empty.code = 'CN0011'
    LEFT JOIN public.conditions cr_selected ON cr_selected.id::text = ({selected})
    LEFT JOIN LATERAL (
        SELECT id FROM {schema}.item_corrections WHERE extraction_item_id = ei.id ORDER BY id DESC LIMIT 1
    ) cr_latest ON TRUE
    LEFT JOIN LATERAL (
        SELECT id, source_message_id,
            CASE WHEN human_value IS JSON OBJECT AND pg_input_is_valid(human_value, 'jsonb')
                 THEN human_value::jsonb ELSE NULL END AS value
        FROM {schema}.item_corrections
        WHERE extraction_item_id = ei.id AND field_name = 'condition_review' ORDER BY id DESC LIMIT 1
    ) cr_event ON TRUE
    -- 「このままで良い」(review_ack) の最新1行に excluded が入っているか(excluded_acked)・空でない確認済みか(review_acked)。
    -- 規則の正本は v102_human_decisions_svc.load_v102_decisions。GROUP BY 無しの集計なので必ず1行・NULL なし
    CROSS JOIN LATERAL (SELECT
        COALESCE(bool_or(CASE WHEN a.value->'v' = '{ack_version}'::jsonb AND jsonb_typeof(a.value->'codes') = 'array'
                    THEN NOT EXISTS (SELECT 1 FROM jsonb_array_elements(a.value->'codes') cr_e
                                     WHERE jsonb_typeof(cr_e) != 'string' OR cr_e = '""'::jsonb)
                         AND a.value->'codes' @> '["excluded"]'::jsonb
                    ELSE FALSE END), FALSE) AS excluded_acked,
        COALESCE(bool_or(CASE WHEN a.value->'v' = '{ack_version}'::jsonb AND jsonb_typeof(a.value->'codes') = 'array'
                    THEN NOT EXISTS (SELECT 1 FROM jsonb_array_elements(a.value->'codes') cr_e
                                     WHERE jsonb_typeof(cr_e) != 'string' OR cr_e = '""'::jsonb)
                         AND jsonb_array_length(a.value->'codes') > 0
                    ELSE FALSE END), FALSE) AS review_acked
        FROM (SELECT ic.corrected_at,
                CASE WHEN ic.human_value IS JSON OBJECT AND pg_input_is_valid(ic.human_value, 'jsonb')
                     THEN ic.human_value::jsonb ELSE NULL END AS value
              FROM {schema}.item_corrections ic
              WHERE ic.extraction_item_id = ei.id AND ic.field_name = {ack_field}
              ORDER BY ic.corrected_at DESC, ic.id DESC LIMIT 1) a
        WHERE NOT EXISTS (SELECT 1 FROM {schema}.item_corrections tr
                          WHERE tr.extraction_item_id = ei.id AND tr.field_name IN ({transcription_fields})
                            AND tr.corrected_at >= a.corrected_at)) cr_review_ack
    LEFT JOIN public.conditions cr_ack_condition ON cr_ack_condition.id::text = cr_event.value->>'condition_id'
    LEFT JOIN public.conditions cr_arc ON cr_arc.id::text = cr_data.ar->>'condition_id'
    CROSS JOIN LATERAL (SELECT {classification} AS classification, ({mentions}) AS mentions,
        {valid_master} AS master_valid) cr_input
    CROSS JOIN LATERAL (SELECT {binding} AS binding_hash, {ack_binding} AS ack_binding_hash) cr_hash
    CROSS JOIN LATERAL (SELECT COALESCE(
        cr_event.value->'v' = '1'::jsonb
        AND cr_event.source_message_id = sm.id
        AND cr_event.value->>'request_id' ~ '{_UUID_PATTERN}'
        AND cr_event.value->>'decision' IN ('confirm', 'correct')
        AND (cr_input.classification != 'ambiguous' OR cr_event.value->>'decision' = 'correct')
        AND cr_event.value->>'binding_hash' ~ '{_HEX_PATTERN}'
        AND cr_event.value->>'request_fingerprint' ~ '{_HEX_PATTERN}'
        AND cr_event.value->>'binding_hash' = cr_hash.ack_binding_hash
        AND cr_ack_condition.is_active IS TRUE
        AND (NOT cr_input.mentions OR cr_input.master_valid), FALSE) AS valid_ack) cr_valid
    {shime_lateral}
    CROSS JOIN LATERAL (SELECT
        ARRAY(SELECT DISTINCT reason FROM unnest(
            string_to_array(COALESCE(cr_data.ar->>'review_reasons', ''), ',') || ARRAY[
                CASE WHEN cr_data.ar->>'pid_resolved' IS DISTINCT FROM 'true' THEN 'pid_unresolved' END,
                CASE WHEN cr_data.ar->>'unit_resolved' IS DISTINCT FROM 'true' THEN 'unit_unresolved' END,
                CASE WHEN cr_data.ar->>'price_normalized' IS NULL AND NOT cr_shime.settled THEN 'price_unresolved' END,
                CASE WHEN cr_data.ar->>'exclusion' IS NOT NULL AND NOT cr_review_ack.excluded_acked AND NOT cr_shime.settled THEN 'excluded' END
            ]) reason
              WHERE reason != '' AND reason NOT IN ({empty_reasons})
                AND NOT (reason = 'note_unmatched' AND {pure_memo})
                AND NOT (reason = 'pid_unresolved' AND cr_data.ar->>'pid_resolved' = 'true')
                AND NOT (reason = 'unit_unresolved' AND cr_data.ar->>'unit_resolved' = 'true')
                AND NOT (reason = 'price_unresolved' AND (cr_data.ar->>'price_normalized' IS NOT NULL OR cr_shime.settled))
                AND NOT (reason = 'excluded' AND (cr_data.ar->>'exclusion' IS NULL OR cr_review_ack.excluded_acked OR cr_shime.settled)) ORDER BY reason) AS other_reasons,
        COALESCE((cr_data.ar->>'needs_review')::boolean, FALSE)
            AND COALESCE(cr_data.ar->>'review_reasons', '') = '' AS unknown_review,
        CASE WHEN cr_input.mentions AND NOT cr_input.master_valid THEN 'empty_box_master_unavailable'
             WHEN cr_valid.valid_ack THEN NULL
             WHEN cr_input.classification = 'ambiguous' THEN 'empty_box_ambiguous'
             WHEN cr_input.classification = 'positive' OR cr_event.id IS NOT NULL
               OR cr_data.ar->>'condition_canonical' = 'Empty box' THEN 'empty_box'
             ELSE NULL END AS empty_reason
    ) cr_reasons
    CROSS JOIN LATERAL (SELECT
        cr_valid.valid_ack, cr_input.classification, cr_input.mentions, cr_input.master_valid,
        cr_hash.binding_hash, cr_hash.ack_binding_hash, cr_review_ack.excluded_acked, cr_review_ack.review_acked, {version} AS review_version,
        (cardinality(cr_reasons.other_reasons) > 0 OR cr_reasons.unknown_review OR cr_reasons.empty_reason IS NOT NULL)
            AS needs_review,
        array_to_string(cr_reasons.other_reasons || CASE WHEN cr_reasons.empty_reason IS NULL
            THEN ARRAY[]::text[] ELSE ARRAY[cr_reasons.empty_reason] END, ',') AS review_reasons,
        CASE WHEN cr_valid.valid_ack THEN cr_ack_condition.id::text
             WHEN cr_input.classification = 'positive' AND cr_input.master_valid THEN cr_empty.id::text
             ELSE cr_data.ar->>'condition_id' END AS condition_id,
        CASE WHEN cr_valid.valid_ack THEN cr_ack_condition.canonical
             WHEN cr_input.classification = 'positive' AND cr_input.master_valid THEN cr_empty.canonical
             ELSE cr_data.ar->>'condition_canonical' END AS canonical,
        CASE WHEN cr_valid.valid_ack THEN 'MANUAL_CONDITION_REVIEW'
             WHEN cr_input.classification = 'positive' AND cr_input.master_valid THEN 'EMPTY_BOX:explicit'
             ELSE cr_data.ar->>'condition_basis' END AS basis,
        CASE WHEN cr_valid.valid_ack THEN {condition_effect_sql('cr_ack_condition')}
             WHEN cr_input.classification = 'positive' AND cr_input.master_valid THEN {condition_effect_sql('cr_empty')}
             ELSE {condition_effect_sql('cr_arc')} END AS effect
    ) cr
    """
    return _fence_review_joins(sql) if fenced else sql


def context_sql(*, analysis_expression: str = "to_jsonb(ar)", selected_expression: str | None = None,
                schema: str | None = None, source_hash: str | None = None) -> str:
    schema = schema or "public"
    return f"""{source_cte(schema=schema, item_only=True, source_hash=source_hash)} SELECT cr.* FROM {schema}.analysis_results ar
        JOIN {schema}.extraction_items ei ON ei.id = ar.extraction_item_id
        JOIN {schema}.extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id
        {review_joins(analysis_expression=analysis_expression, selected_expression=selected_expression, schema=schema)}
        WHERE ei.id = CAST(:eid AS uuid)"""


def reanalysis_condition(session: Session, item_id: str, candidate: dict | None = None,
                         *, schema: str | None = None, source_hash: str | None = None) -> dict | None:
    """Validate saved selection against the candidate BEFORE replacing its condition."""
    expression = "to_jsonb(ar)"
    params: dict[str, Any] = {"eid": item_id, "source_hash": source_hash}
    if candidate is not None:
        expression += " || CAST(:candidate AS jsonb)"
        params["candidate"] = json.dumps(candidate, default=str)
    result = session.execute(text(context_sql(analysis_expression=expression, schema=schema, source_hash=":source_hash" if source_hash is not None else None)), params).mappings().one_or_none()
    return dict(result) if result else None


async def condition_options(db: AsyncSession) -> list[dict]:
    rows = await db.execute(text("SELECT id::text, code, canonical FROM public.conditions "
                                 f"WHERE is_active IS TRUE AND {not_excluded_condition_sql('conditions')} "
                                 "ORDER BY priority NULLS LAST, code"))
    return [dict(row) for row in rows.mappings()]


def _response(row: Mapping, *, saved: int, replayed: bool) -> dict:
    return {"saved": saved, "condition_review": {
        "condition_id": row["condition_id"], "canonical": row["canonical"],
        "needs_review": row["needs_review"], "review_reasons": row["review_reasons"] or "",
        "review_version": row["review_version"], "replayed": replayed,
    }}


async def save_condition_review(db: AsyncSession, *, extraction_item_id: str, source_message_id: str,
                                request: dict, corrected_by: str) -> dict:
    try:
        _cid_int = int(request["condition_id"])
    except (ValueError, TypeError):
        _cid_int = -1  # Sentinel; will fail the SELECT and return 422 "Condition is not active"
    params = {"eid": extraction_item_id, "smid": source_message_id,
              "condition_id": str(request["condition_id"]),
              "condition_id_int": _cid_int,
              "request_id": request["request_id"]}
    try:
        # Protect raw/source/job membership during both version checking and commit.
        item = (await db.execute(text(f"""SELECT ei.id FROM {TCG_SCHEMA}.extraction_items ei
            JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id
            JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
            WHERE ei.id = CAST(:eid AS uuid) AND sm.id = CAST(:smid AS uuid)
            FOR SHARE OF ei, ej, sm"""), params)).scalar_one_or_none()
        if item is None:
            raise HTTPException(404, "Condition review item not found")
        locked = (await db.execute(text(f"SELECT id FROM {TCG_SCHEMA}.analysis_results "
            "WHERE extraction_item_id = CAST(:eid AS uuid) FOR UPDATE"), params)).scalar_one_or_none()
        if locked is None:
            raise HTTPException(404, "Condition review analysis not found")
        # Lock all definitions used by either current or acknowledged bindings. No gaps
        # are accepted: absent CN0011 with mentions remains fail-closed at read time.
        await db.execute(text("SELECT id FROM public.conditions ORDER BY id FOR SHARE"))
        await db.execute(text("SELECT p.id FROM public.products p "
            f"JOIN {TCG_SCHEMA}.analysis_results ar ON ar.product_id=p.id "
            "WHERE ar.extraction_item_id=CAST(:eid AS uuid) FOR SHARE OF p"), params)
        fingerprint = (await db.execute(text("SELECT " + digest_sql("CAST(:request AS jsonb)")),
            {"request": json.dumps(request, sort_keys=True)})).scalar_one()
        prior = (await db.execute(text(f"""SELECT value FROM (
            SELECT CASE WHEN human_value IS JSON OBJECT AND pg_input_is_valid(human_value, 'jsonb')
                 THEN human_value::jsonb ELSE NULL END AS value
            FROM {TCG_SCHEMA}.item_corrections
            WHERE extraction_item_id=CAST(:eid AS uuid) AND field_name='condition_review'
        ) history WHERE value->>'request_id'=:request_id ORDER BY value->>'request_id' LIMIT 1"""), params)).scalar_one_or_none()
        if prior is not None:
            if prior.get("request_fingerprint") != fingerprint:
                raise HTTPException(409, "Condition review request id reused")
            row = (await db.execute(text(context_sql(schema=TCG_SCHEMA)), params)).mappings().one()
            await db.commit()
            return _response(row, saved=0, replayed=True)
        row = (await db.execute(text(context_sql(schema=TCG_SCHEMA)), params)).mappings().one()
        if request["expected_review_version"] != row["review_version"]:
            raise HTTPException(409, "Condition review changed; reload before confirming")
        target = (await db.execute(text("SELECT id FROM public.conditions "
            f"WHERE id = :condition_id_int AND is_active IS TRUE AND {not_excluded_condition_sql('conditions')}"), params)).scalar_one_or_none()
        if target is None:
            raise HTTPException(422, "Condition is not active")
        if row["mentions"] and not row["master_valid"]:
            raise HTTPException(422, "Empty box master is unavailable")
        if request["decision"] == "confirm" and (
            row["classification"] == "ambiguous" or request["condition_id"] != row["condition_id"]
        ):
            raise HTTPException(422, "Select and correct the condition")
        post = (await db.execute(text(context_sql(schema=TCG_SCHEMA, selected_expression=":condition_id")), params)).mappings().one()
        history = {"v": 1, "request_id": request["request_id"], "decision": request["decision"],
                   "condition_id": request["condition_id"], "binding_hash": post["binding_hash"],
                   "request_fingerprint": fingerprint}
        await db.execute(text(f"""INSERT INTO {TCG_SCHEMA}.item_corrections
            (extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by)
            VALUES (CAST(:eid AS uuid), CAST(:smid AS uuid), 'condition_review', :old, :new, :actor)"""),
            dict(params, old=json.dumps(dict(row), default=str), new=json.dumps(history), actor=corrected_by))
        # 選んだ状態で決まる理由（condition_unknown 等）は保存の時点で外す。再解析が積めなくても詰まらないように。
        await db.execute(text(f"""UPDATE {TCG_SCHEMA}.analysis_results ar SET
            condition_id = :condition_id_int,
            condition_canonical = (SELECT canonical FROM public.conditions WHERE id=:condition_id_int),
            condition_basis='MANUAL_CONDITION_REVIEW', updated_at=clock_timestamp(),
            review_reasons = s.kept,
            needs_review = CASE WHEN s.removed AND s.kept IS NULL THEN FALSE ELSE ar.needs_review END
            FROM (SELECT NULLIF(array_to_string(ARRAY(SELECT r FROM unnest(string_to_array(COALESCE(x.review_reasons,''),',')) r
                      WHERE r <> '' AND r <> ALL(CAST(:drop AS text[]))),','),'') AS kept,
                  EXISTS (SELECT 1 FROM unnest(string_to_array(COALESCE(x.review_reasons,''),',')) r
                      WHERE r = ANY(CAST(:drop AS text[]))) AS removed
                  FROM {TCG_SCHEMA}.analysis_results x WHERE x.extraction_item_id=CAST(:eid AS uuid)) s
            WHERE ar.extraction_item_id=CAST(:eid AS uuid)"""), dict(params, drop=list(CONDITION_REVIEW_REASONS)))
        effective = (await db.execute(text(context_sql(schema=TCG_SCHEMA)), params)).mappings().one()
        await db.execute(text(f"""UPDATE {TCG_SCHEMA}.analysis_results
            SET needs_review=:needs_review, review_reasons=:review_reasons
            WHERE extraction_item_id=CAST(:eid AS uuid)"""),
            dict(params, needs_review=effective["needs_review"], review_reasons=effective["review_reasons"] or None))
        final = (await db.execute(text(context_sql(schema=TCG_SCHEMA)), params)).mappings().one()
        await db.commit()
        return _response(final, saved=1, replayed=False)
    except Exception:
        await db.rollback()
        raise
