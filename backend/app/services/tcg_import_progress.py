"""Import-scoped read models; one SQL statement per consistent response."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tcg_condition_review_svc import digest_sql, review_joins
from app.services.tcg_result_order import result_order_sql
from app.tcg_config import TCG_SCHEMA


def _scope_ctes() -> str:
    return f"""
        job AS (
            SELECT id, review_status, messages_linked_at FROM {TCG_SCHEMA}.import_jobs
            WHERE id = :job_id
        ), messages AS (
            SELECT sm.*, l.relation_kind FROM {TCG_SCHEMA}.import_job_messages l
            JOIN job ON job.id = l.import_job_id
            JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = l.source_message_id
        ), jobs AS (
            SELECT ej.* FROM {TCG_SCHEMA}.extraction_jobs ej
            WHERE ej.source_message_id IN (SELECT id FROM messages)
        ), items AS (
            SELECT ei.*, ej.status AS extraction_status, ej.source_message_id,
                   ar.id AS analysis_result_id, ar.note_ja, ar.needs_review,
                   ar.review_reasons, ar.status AS analysis_status, ar.exclusion,
                   ar.quantity_normalized, ar.price_normalized
            FROM {TCG_SCHEMA}.extraction_items ei
            JOIN jobs ej ON ej.id = ei.extraction_job_id
            LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.extraction_item_id = ei.id
        )
    """


def _envelope(row: dict[str, Any], job_id: str) -> dict[str, Any]:
    complete = row.pop("linked")
    review = row.pop("review_status")
    coverage = "complete" if complete else (
        review if review in ("pending_review", "discarded") else "legacy_unknown"
    )
    return {"scope": {"type": "import", "import_job_id": job_id},
            "as_of": row.pop("as_of"), "coverage": coverage, "review_status": review,
            "reason": None if complete else "message_association_not_recorded",
            **row}


async def read_progress(db: AsyncSession, job_id: str) -> dict[str, Any]:
    result = await db.execute(text(f"""
        WITH {_scope_ctes()}, states AS (
            SELECT status, count(*) AS n FROM jobs GROUP BY status
        ), reasons AS (
            SELECT trim(reason) AS reason, count(DISTINCT i.id) AS n
            FROM items i CROSS JOIN LATERAL
                unnest(string_to_array(i.review_reasons, ',')) AS reason
            WHERE i.needs_review AND trim(reason) <> '' GROUP BY trim(reason)
        )
        SELECT jsonb_build_object(
            'as_of', statement_timestamp(), 'review_status', job.review_status,
            'linked', job.messages_linked_at IS NOT NULL,
            'messages', jsonb_build_object(
                'unit', 'source_message', 'total', (SELECT count(*) FROM messages),
                'created', (SELECT count(*) FROM messages WHERE relation_kind = 'created'),
                'reused', (SELECT count(*) FROM messages WHERE relation_kind = 'reused'),
                'inactive', (SELECT count(*) FROM messages WHERE NOT is_active),
                'without_extraction_job', (SELECT count(*) FROM messages m
                    WHERE NOT EXISTS (SELECT 1 FROM jobs j WHERE j.source_message_id = m.id))
            ),
            'extraction', jsonb_build_object(
                'unit', 'extraction_job', 'total', (SELECT count(*) FROM jobs),
                'states', COALESCE((SELECT jsonb_object_agg(status, n) FROM states), '{{}}'::jsonb),
                'completed', (SELECT count(*) FROM jobs WHERE status IN ('done','empty','error')),
                'pending', (SELECT count(*) FROM jobs WHERE status = 'pending'),
                'running', (SELECT count(*) FROM jobs WHERE status = 'running'),
                'unknown', (SELECT count(*) FROM jobs WHERE status NOT IN ('pending','running','done','empty','error')),
                'succeeded', (SELECT count(*) FROM jobs WHERE status = 'done'),
                'empty', (SELECT count(*) FROM jobs WHERE status = 'empty'),
                'failed', (SELECT count(*) FROM jobs WHERE status = 'error'),
                'residual_items_on_error', (SELECT count(*) FROM items WHERE extraction_status = 'error'),
                'residual_results_on_error', (SELECT count(*) FROM items
                    WHERE extraction_status = 'error' AND analysis_result_id IS NOT NULL)
            ),
            'analysis', jsonb_build_object(
                'unit', 'extraction_item', 'total', (SELECT count(*) FROM items),
                'results_present', (SELECT count(*) FROM items WHERE analysis_result_id IS NOT NULL),
                'results_missing', (SELECT count(*) FROM items WHERE analysis_result_id IS NULL),
                'needs_review', (SELECT count(*) FROM items WHERE needs_review),
                'review_reasons', COALESCE((SELECT jsonb_object_agg(reason,n) FROM reasons), '{{}}'::jsonb),
                'reasons_may_overlap', true,
                'execution_state', 'unrecorded', 'execution_reason', 'attempt_tracking_not_available',
                'completed', NULL, 'succeeded', NULL, 'failed', NULL, 'running', NULL, 'pending', NULL
            )
        ) FROM job
    """), {"job_id": job_id})
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    response = _envelope(row, job_id)
    if response["coverage"] != "complete":
        for stage in ("messages", "extraction", "analysis"):
            response[stage] = {"unit": response[stage]["unit"], "total": None,
                               "reason": response["reason"]}
    return response


async def read_items(db: AsyncSession, job_id: str, limit: int, offset: int, filter_by: str) -> dict[str, Any]:
    result = await db.execute(text(f"""
        WITH {_scope_ctes()}, condition_review_sources AS MATERIALIZED (
            SELECT id, {digest_sql("raw_text")} AS source_hash FROM messages
        ), filtered AS (
            SELECT * FROM items WHERE :filter_by = 'all'
                OR (:filter_by = 'needs_review' AND needs_review)
                OR (:filter_by = 'extraction_error' AND extraction_status = 'error')
                OR (:filter_by = 'results_present' AND analysis_result_id IS NOT NULL)
        ), ordered AS (
            SELECT ei.id, row_number() OVER (ORDER BY {result_order_sql()}) AS sort_ordinal
            FROM filtered f
            JOIN {TCG_SCHEMA}.extraction_items ei ON ei.id = f.id
            JOIN jobs ej ON ej.id = ei.extraction_job_id
            JOIN messages sm ON sm.id = ej.source_message_id
            LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.extraction_item_id = ei.id
            LEFT JOIN public.products p ON p.tcg_uuid = ar.product_id
            {review_joins(schema=TCG_SCHEMA)}
        ), page AS (
            SELECT f.id, f.extraction_job_id, f.source_message_id, f.extraction_status,
                   f.analysis_result_id, f.raw_product_name, f.raw_quantity, f.raw_price, f.raw_unit,
                   f.raw_state, f.raw_memo, f.note_ja, f.needs_review, f.review_reasons, f.analysis_status,
                   f.exclusion, f.quantity_normalized, f.price_normalized, f.created_at,
                   'unrecorded'::text AS analysis_execution_state, ordered.sort_ordinal
            FROM filtered f JOIN ordered ON ordered.id = f.id
            ORDER BY ordered.sort_ordinal LIMIT :limit OFFSET :offset
        )
        SELECT jsonb_build_object(
            'as_of', statement_timestamp(), 'review_status', job.review_status,
            'linked', job.messages_linked_at IS NOT NULL,
            'total', (SELECT count(*) FROM filtered),
            'items', COALESCE((SELECT jsonb_agg(to_jsonb(page) - 'sort_ordinal' ORDER BY sort_ordinal)
                               FROM page), '[]'::jsonb)
        ) FROM job
    """), {"job_id": job_id, "limit": limit, "offset": offset, "filter_by": filter_by})
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    response = _envelope(row, job_id)
    response.update(limit=limit, offset=offset, filter=filter_by, unit="extraction_item")
    if response["coverage"] != "complete":
        response.update(total=None, items=None)
    return response


async def read_messages(db: AsyncSession, job_id: str, limit: int, offset: int) -> dict[str, Any]:
    result = await db.execute(text(f"""
        WITH {_scope_ctes()}, page AS (
          SELECT m.id::text, m.raw_text, m.received_at, m.created_at, m.is_active,
                 m.relation_kind, ts.name AS supplier_name
          FROM messages m LEFT JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.id=m.supplier_channel_id
          LEFT JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id=sc.supplier_id
          ORDER BY m.created_at, m.id LIMIT :limit OFFSET :offset
        ) SELECT jsonb_build_object('as_of', statement_timestamp(), 'review_status', job.review_status,
          'linked', job.messages_linked_at IS NOT NULL, 'total',(SELECT count(*) FROM messages),
          'messages',COALESCE((SELECT jsonb_agg(to_jsonb(page) ORDER BY created_at,id) FROM page),'[]'::jsonb)) FROM job
    """), {"job_id": job_id, "limit": limit, "offset": offset})
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    response = _envelope(row, job_id)
    response.update(limit=limit, offset=offset, unit="source_message")
    if response["coverage"] != "complete":
        response.update(total=None, messages=None)
    return response


async def read_extraction_jobs(db: AsyncSession, job_id: str, limit: int, offset: int, filter_by: str) -> dict[str, Any]:
    result = await db.execute(text(f"""
        WITH {_scope_ctes()}, filtered AS (SELECT * FROM jobs WHERE :filter_by='all' OR status='error'), page AS (
          SELECT j.id::text, j.source_message_id::text, j.status, j.created_at, j.extracted_at, m.raw_text,
                 ts.name AS supplier_name, (SELECT count(*) FROM {TCG_SCHEMA}.extraction_items ei WHERE ei.extraction_job_id=j.id) AS item_count,
                 CASE WHEN j.status='error' THEN 'unclassified' ELSE NULL END AS error_reason_code
          FROM filtered j JOIN messages m ON m.id=j.source_message_id
          LEFT JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.id=m.supplier_channel_id LEFT JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id=sc.supplier_id
          ORDER BY j.created_at,j.id LIMIT :limit OFFSET :offset
        ) SELECT jsonb_build_object('as_of',statement_timestamp(),'review_status',job.review_status,'linked',job.messages_linked_at IS NOT NULL,
          'total',(SELECT count(*) FROM filtered),'jobs',COALESCE((SELECT jsonb_agg(to_jsonb(page) ORDER BY created_at,id) FROM page),'[]'::jsonb)) FROM job
    """), {"job_id": job_id, "limit": limit, "offset": offset, "filter_by": filter_by})
    row=result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    response = _envelope(row, job_id)
    response.update(limit=limit, offset=offset, filter=filter_by, unit="extraction_job")
    if response["coverage"] != "complete":
        response.update(total=None, jobs=None)
    return response
