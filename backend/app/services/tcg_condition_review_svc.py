"""PostgreSQL-owned condition acknowledgments and effective review state.

Every read gate uses review_joins BEFORE filtering/paging. Fingerprints never leave
PostgreSQL for reserialization. History is append-only and malformed latest events
fail closed, without falling back to an older acknowledgment.
"""
from __future__ import annotations

import json
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
from app.tcg_config import TCG_SCHEMA

_UUID_PATTERN = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
_HEX_PATTERN = "^[0-9a-f]{64}$"
_SOURCE_CTE_NAME = "condition_review_sources"


def digest_sql(expression: str) -> str:
    return f"encode(sha256(convert_to(({expression})::text, 'UTF8')), 'hex')"


def source_cte(*, schema: str | None = None, item_only: bool = False, source_hash: str | None = None) -> str:
    schema = schema or TCG_SCHEMA
    scope = (f"WHERE id=(SELECT ej.source_message_id FROM {schema}.extraction_items ei "
             f"JOIN {schema}.extraction_jobs ej ON ej.id=ei.extraction_job_id WHERE ei.id=CAST(:eid AS uuid))"
             if item_only else "WHERE is_active IS TRUE")
    hash_expression = source_hash or digest_sql("raw_text")
    # Materialization makes the full original-message hash reusable by its items.
    return f"""WITH {_SOURCE_CTE_NAME} AS MATERIALIZED (
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
    pairs.update({"product_title": "cr_product.japanese_title", "product_work": "cr_product.work_id",
                  "product_category": "to_jsonb(cr_product)->'product_category_id'",
                  "product_category_class": "to_jsonb(cr_product)->'category_class'",
                  "selected_condition": _definition(selected), "empty_condition": _definition("to_jsonb(cr_empty)")})
    return digest_sql(_object_sql(pairs))


def review_joins(*, analysis_expression: str = "to_jsonb(ar)", selected_expression: str | None = None, schema: str | None = None) -> str:
    """SQL requires ar/ei/ej/sm aliases plus source_cte; optional candidate for reanalysis.

    Expressions come exclusively from trusted source code, never request text.
    selected_expression is used for a POST's new binding, after old-version checking.
    """
    schema = schema or TCG_SCHEMA
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
    return f"""
    JOIN {_SOURCE_CTE_NAME} cr_source ON cr_source.id = sm.id
    CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar) cr_data
    LEFT JOIN {schema}.tcg_products cr_product ON cr_product.id::text = cr_data.ar->>'product_id'
    LEFT JOIN {schema}.conditions cr_empty ON cr_empty.code = 'CN0011'
    LEFT JOIN {schema}.conditions cr_selected ON cr_selected.id::text = ({selected})
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
    LEFT JOIN {schema}.conditions cr_ack_condition ON cr_ack_condition.id::text = cr_event.value->>'condition_id'
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
    CROSS JOIN LATERAL (SELECT
        ARRAY(SELECT DISTINCT reason FROM unnest(
            string_to_array(COALESCE(cr_data.ar->>'review_reasons', ''), ',') || ARRAY[
                CASE WHEN cr_data.ar->>'pid_resolved' IS DISTINCT FROM 'true' THEN 'pid_unresolved' END,
                CASE WHEN cr_data.ar->>'unit_resolved' IS DISTINCT FROM 'true' THEN 'unit_unresolved' END,
                CASE WHEN cr_data.ar->>'price_normalized' IS NULL THEN 'price_unresolved' END,
                CASE WHEN cr_data.ar->>'exclusion' IS NOT NULL THEN 'excluded' END
            ]) reason
              WHERE reason != '' AND reason NOT IN ({empty_reasons})
                AND NOT (reason = 'note_unmatched' AND {pure_memo})
                AND NOT (reason = 'pid_unresolved' AND cr_data.ar->>'pid_resolved' = 'true')
                AND NOT (reason = 'unit_unresolved' AND cr_data.ar->>'unit_resolved' = 'true')
                AND NOT (reason = 'price_unresolved' AND cr_data.ar->>'price_normalized' IS NOT NULL)
                AND NOT (reason = 'excluded' AND cr_data.ar->>'exclusion' IS NULL) ORDER BY reason) AS other_reasons,
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
        cr_hash.binding_hash, cr_hash.ack_binding_hash, {version} AS review_version,
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
             ELSE cr_data.ar->>'condition_basis' END AS basis
    ) cr
    """


def context_sql(*, analysis_expression: str = "to_jsonb(ar)", selected_expression: str | None = None,
                schema: str | None = None, source_hash: str | None = None) -> str:
    schema = schema or TCG_SCHEMA
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
    rows = await db.execute(text(f"SELECT id::text, code, canonical FROM {TCG_SCHEMA}.conditions "
                                 "WHERE is_active IS TRUE ORDER BY priority NULLS LAST, code"))
    return [dict(row) for row in rows.mappings()]


def _response(row: Mapping, *, saved: int, replayed: bool) -> dict:
    return {"saved": saved, "condition_review": {
        "condition_id": row["condition_id"], "canonical": row["canonical"],
        "needs_review": row["needs_review"], "review_reasons": row["review_reasons"] or "",
        "review_version": row["review_version"], "replayed": replayed,
    }}


async def save_condition_review(db: AsyncSession, *, extraction_item_id: str, source_message_id: str,
                                request: dict, corrected_by: str) -> dict:
    params = {"eid": extraction_item_id, "smid": source_message_id,
              "condition_id": request["condition_id"], "request_id": request["request_id"]}
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
        await db.execute(text(f"SELECT id FROM {TCG_SCHEMA}.conditions ORDER BY id FOR SHARE"))
        await db.execute(text(f"SELECT p.id FROM {TCG_SCHEMA}.tcg_products p "
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
            row = (await db.execute(text(context_sql()), params)).mappings().one()
            await db.commit()
            return _response(row, saved=0, replayed=True)
        row = (await db.execute(text(context_sql()), params)).mappings().one()
        if request["expected_review_version"] != row["review_version"]:
            raise HTTPException(409, "Condition review changed; reload before confirming")
        target = (await db.execute(text(f"SELECT id FROM {TCG_SCHEMA}.conditions "
            "WHERE id = CAST(:condition_id AS uuid) AND is_active IS TRUE"), params)).scalar_one_or_none()
        if target is None:
            raise HTTPException(422, "Condition is not active")
        if row["mentions"] and not row["master_valid"]:
            raise HTTPException(422, "Empty box master is unavailable")
        if request["decision"] == "confirm" and (
            row["classification"] == "ambiguous" or request["condition_id"] != row["condition_id"]
        ):
            raise HTTPException(422, "Select and correct the condition")
        post = (await db.execute(text(context_sql(selected_expression=":condition_id")), params)).mappings().one()
        history = {"v": 1, "request_id": request["request_id"], "decision": request["decision"],
                   "condition_id": request["condition_id"], "binding_hash": post["binding_hash"],
                   "request_fingerprint": fingerprint}
        await db.execute(text(f"""INSERT INTO {TCG_SCHEMA}.item_corrections
            (extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by)
            VALUES (CAST(:eid AS uuid), CAST(:smid AS uuid), 'condition_review', :old, :new, :actor)"""),
            dict(params, old=json.dumps(dict(row), default=str), new=json.dumps(history), actor=corrected_by))
        await db.execute(text(f"""UPDATE {TCG_SCHEMA}.analysis_results SET
            condition_id = CAST(:condition_id AS uuid),
            condition_canonical = (SELECT canonical FROM {TCG_SCHEMA}.conditions WHERE id=CAST(:condition_id AS uuid)),
            condition_basis='MANUAL_CONDITION_REVIEW', updated_at=clock_timestamp()
            WHERE extraction_item_id=CAST(:eid AS uuid)"""), params)
        effective = (await db.execute(text(context_sql()), params)).mappings().one()
        await db.execute(text(f"""UPDATE {TCG_SCHEMA}.analysis_results
            SET needs_review=:needs_review, review_reasons=:review_reasons
            WHERE extraction_item_id=CAST(:eid AS uuid)"""),
            dict(params, needs_review=effective["needs_review"], review_reasons=effective["review_reasons"] or None))
        final = (await db.execute(text(context_sql()), params)).mappings().one()
        await db.commit()
        return _response(final, saved=1, replayed=False)
    except Exception:
        await db.rollback()
        raise
