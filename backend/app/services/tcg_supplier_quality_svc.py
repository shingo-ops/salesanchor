"""
PARITY-03 第2段階: 仕入元品質サマリー サービス層。

GAS の api_getSupplierQualitySummaries / api_getSupplierSource に相当。
TCG 解析システムは tenant_004 専用スキーマ。
DB 書き込みは行わない（読み取り専用）。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TCG_SCHEMA = "tenant_004"


async def fetch_supplier_quality_summaries(db: AsyncSession) -> list[dict]:
    """
    仕入元品質サマリー一覧を source 起点で取得する（GAS: api_getSupplierQualitySummaries 相当）。

    source_messages を起点に全仕入元を初期化し、analysis_results を加算する。
    items=0 の仕入元（例: SP0057/Hiroshi）も一覧に含まれる。

    判定述語（ShadowReviewV2.gs:90-98 に対応）:
      productIdUnresolved = NOT ar.pid_resolved
      unitUnresolved      = NOT ar.unit_resolved
      excluded            = ar.exclusion IS NOT NULL AND ar.exclusion != ''
      needsReview         = いずれか1つ以上
    """
    sql = f"""
        SELECT
            COALESCE(ts.code, sc.id::text)  AS supplier_id,
            COALESCE(ts.name, '不明')        AS supplier_name,
            COUNT(ei.id)                     AS analysis_count,
            COUNT(CASE
                WHEN NOT ar.pid_resolved
                  OR NOT ar.unit_resolved
                  OR (ar.exclusion IS NOT NULL AND ar.exclusion != '')
                THEN 1 END)                  AS needs_review_count,
            COUNT(CASE WHEN NOT ar.pid_resolved THEN 1 END)  AS product_id_unresolved_count,
            COUNT(CASE WHEN NOT ar.unit_resolved THEN 1 END) AS unit_unresolved_count
        FROM {TCG_SCHEMA}.source_messages sm
        JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.id = sm.supplier_channel_id
        LEFT JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id = sc.supplier_id
        LEFT JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.source_message_id = sm.id
        LEFT JOIN {TCG_SCHEMA}.extraction_items ei ON ei.extraction_job_id = ej.id
        LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.extraction_item_id = ei.id
        WHERE sm.is_active = TRUE
        GROUP BY sc.id, ts.code, ts.name
        ORDER BY COALESCE(ts.name, '') ASC
    """
    rows = (await db.execute(text(sql))).fetchall()
    return [
        {
            "supplier_id": row.supplier_id,
            "supplier_name": row.supplier_name,
            "analysis_count": row.analysis_count,
            "needs_review_count": row.needs_review_count,
            "product_id_unresolved_count": row.product_id_unresolved_count,
            "unit_unresolved_count": row.unit_unresolved_count,
            "condition_fallback_count": None,  # Q8実測不能 — GAS と同じく null 固定
        }
        for row in rows
    ]


async def fetch_supplier_source(db: AsyncSession, *, supplier_id: str) -> dict:
    """
    仕入元の原文 1 件を返す（GAS: api_getSupplierSource 相当）。

    items=0 の source でも raw_text を返す。
    supplier_id は tcg_suppliers.code（例: 'SP0057'）。
    """
    sql = f"""
        SELECT
            sm.id::text     AS source_message_id,
            ts.code         AS supplier_id,
            ts.name         AS supplier_name,
            sm.raw_text
        FROM {TCG_SCHEMA}.source_messages sm
        JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.id = sm.supplier_channel_id
        LEFT JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id = sc.supplier_id
        WHERE ts.code = :supplier_id
          AND sm.is_active = TRUE
        ORDER BY sm.received_at DESC NULLS LAST
        LIMIT 1
    """
    row = (await db.execute(text(sql), {"supplier_id": supplier_id})).fetchone()
    if row is None:
        return {
            "ok": True,
            "found": False,
            "source_message_id": "",
            "supplier_id": supplier_id,
            "supplier_name": "",
            "raw_text": "",
        }
    return {
        "ok": True,
        "found": True,
        "source_message_id": row.source_message_id,
        "supplier_id": row.supplier_id or supplier_id,
        "supplier_name": row.supplier_name or "",
        "raw_text": row.raw_text or "",
    }
