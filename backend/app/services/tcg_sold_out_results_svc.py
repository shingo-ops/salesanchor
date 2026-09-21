"""Read stored Sold out decisions from their existing authoritative relations."""
from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SourceScope = Literal["all", "active", "history"]


class SoldOutResultsUnavailable(Exception):
    """The authoritative source chain cannot be represented completely."""


def escape_search(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def fetch_sold_out_results(
    db: AsyncSession, *, q: str | None = None, source_scope: SourceScope = "all",
    offset: int = 0, limit: int = 50,
) -> dict[str, Any]:
    """One statement supplies integrity, count, timestamp and the ordered page."""
    search = (q or "").strip()
    statement = text("""
        WITH joined AS (
            SELECT ar.id AS analysis_result_id, ei.id AS extraction_item_id,
                sm.id AS source_message_id, ps.id AS supplier_id, p.id AS product_id,
                COALESCE(ps.name, '') AS provider,
                COALESCE(p.name, '') AS product_title,
                COALESCE(ei.raw_product_name, '') AS raw_product_name,
                COALESCE(ei.raw_quantity, '') AS raw_quantity,
                COALESCE(ei.raw_price, '') AS raw_price,
                COALESCE(ei.raw_unit, '') AS raw_unit,
                COALESCE(ei.raw_state, '') AS raw_state,
                COALESCE(ei.raw_memo, '') AS raw_memo,
                COALESCE(sm.raw_text, '') AS raw_text,
                ar.status, sm.is_active AS source_is_active, sm.line_posted_at,
                ei.line_start, ei.line_end
            FROM public.analysis_results ar
            LEFT JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
            LEFT JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
            LEFT JOIN public.source_messages sm ON sm.id = ej.source_message_id
            LEFT JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
            LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
            LEFT JOIN public.products p ON p.id = ar.product_id
            WHERE ar.status = 'Sold out'
        ), filtered AS (
            SELECT * FROM joined
            WHERE source_message_id IS NOT NULL
                AND (:source_scope = 'all'
                    OR (:source_scope = 'active' AND source_is_active IS TRUE)
                    OR (:source_scope = 'history' AND source_is_active IS FALSE))
                AND (:search = '' OR raw_product_name ILIKE :pattern ESCAPE E'\\\\'
                    OR product_title ILIKE :pattern ESCAPE E'\\\\'
                    OR provider ILIKE :pattern ESCAPE E'\\\\')
        ), page AS (
            SELECT * FROM filtered
            ORDER BY line_posted_at DESC NULLS LAST, analysis_result_id DESC
            LIMIT :limit OFFSET :offset
        )
        SELECT (SELECT COUNT(*) FROM joined WHERE source_message_id IS NULL) AS missing_sources,
            (SELECT COUNT(*) FROM filtered) AS total,
            COALESCE((SELECT jsonb_agg(to_jsonb(page) ORDER BY line_posted_at DESC NULLS LAST,
                analysis_result_id DESC) FROM page), '[]'::jsonb) AS items,
            statement_timestamp() AS as_of
    """)
    row = (await db.execute(statement, {
        "search": search, "pattern": f"%{escape_search(search)}%",
        "source_scope": source_scope, "offset": offset, "limit": limit,
    })).mappings().one()
    if row["missing_sources"]:
        raise SoldOutResultsUnavailable()
    return {"items": row["items"], "total": row["total"], "offset": offset,
            "limit": limit, "as_of": row["as_of"]}
