"""Import-scoped read models; one SQL statement per consistent response."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
        WITH {_scope_ctes()}, filtered AS (
            SELECT * FROM items WHERE :filter_by = 'all'
                OR (:filter_by = 'needs_review' AND needs_review)
                OR (:filter_by = 'extraction_error' AND extraction_status = 'error')
        ), page AS (
            SELECT id, extraction_job_id, source_message_id, extraction_status,
                   analysis_result_id, raw_product_name, raw_quantity, raw_price, raw_unit,
                   raw_state, raw_memo, note_ja, needs_review, review_reasons, analysis_status,
                   exclusion, quantity_normalized, price_normalized, created_at,
                   'unrecorded'::text AS analysis_execution_state
            FROM filtered ORDER BY created_at, id LIMIT :limit OFFSET :offset
        )
        SELECT jsonb_build_object(
            'as_of', statement_timestamp(), 'review_status', job.review_status,
            'linked', job.messages_linked_at IS NOT NULL,
            'total', (SELECT count(*) FROM filtered),
            'items', COALESCE((SELECT jsonb_agg(to_jsonb(page) ORDER BY created_at,id) FROM page), '[]'::jsonb)
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
