"""
PARITY-03 第2段階: 仕入元品質サマリー サービス層。

GAS の api_getSupplierQualitySummaries / api_getSupplierSource に相当。
TCG 解析システムは tenant_004 専用スキーマ。
DB 書き込みは行わない（読み取り専用）。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TCG_SCHEMA = "public"

# condition_basis の書式（生成元: tcg_analyzer_svc.py:853,877,880 / tcg_condition_review_svc.py:286）。
# 接頭辞「単品語あり・要確認(<kw>),」が付く場合があるため末尾一致で判定する。
CONDITION_FALLBACK_PATTERN = r"(^|,)(R4:単位既定(:単位不明)?|R5:パック既定)$"
CONDITION_GIVE_UP_PATTERN = r"(^|,)R4:単位既定:単位不明$"
# 人が状態を確定した basis（画面レビュー: tcg_condition_review_svc.py:286 ／ PO許可の一括修正: item_corrections.corrected_by='codex:PO-authorized:20260916-1203'）。
CONDITION_MANUAL_PATTERN = r"^(MANUAL_CONDITION_REVIEW|MANUAL_RAW_REVIEW:PO_RULES)$"


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
      conditionFallback   = condition_basis が CONDITION_FALLBACK_PATTERN に末尾一致
      conditionGiveUp     = condition_basis が CONDITION_GIVE_UP_PATTERN に末尾一致（fallback の内数）
      conditionManual     = condition_basis が MANUAL_CONDITION_REVIEW または MANUAL_RAW_REVIEW:PO_RULES（人が確認済み）
    """
    sql = f"""
        SELECT
            COALESCE(ps.supplier_code, sc.id::text)  AS supplier_id,
            COALESCE(ps.name, '不明')        AS supplier_name,
            COUNT(ei.id)                     AS analysis_count,
            COUNT(CASE
                WHEN NOT ar.pid_resolved
                  OR NOT ar.unit_resolved
                  OR (ar.exclusion IS NOT NULL AND ar.exclusion != '')
                THEN 1 END)                  AS needs_review_count,
            COUNT(CASE WHEN NOT ar.pid_resolved THEN 1 END)  AS product_id_unresolved_count,
            COUNT(CASE WHEN NOT ar.unit_resolved THEN 1 END) AS unit_unresolved_count,
            COUNT(CASE WHEN ar.condition_basis ~ :fallback_pattern THEN 1 END) AS condition_fallback_count,
            COUNT(CASE WHEN ar.condition_basis ~ :give_up_pattern THEN 1 END)  AS condition_give_up_count,
            COUNT(CASE WHEN ar.condition_basis ~ :manual_pattern THEN 1 END)     AS condition_manual_reviewed_count
        FROM {TCG_SCHEMA}.source_messages sm
        JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
        LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
        LEFT JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.source_message_id = sm.id
        LEFT JOIN {TCG_SCHEMA}.extraction_items ei ON ei.extraction_job_id = ej.id
        LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.extraction_item_id = ei.id
        WHERE sm.is_active = TRUE
        GROUP BY sc.id, ps.supplier_code, ps.name
        ORDER BY COALESCE(ps.name, '') ASC
    """
    params = {
        "fallback_pattern": CONDITION_FALLBACK_PATTERN,
        "give_up_pattern": CONDITION_GIVE_UP_PATTERN,
        "manual_pattern": CONDITION_MANUAL_PATTERN,
    }
    rows = (await db.execute(text(sql), params)).fetchall()
    return [
        {
            "supplier_id": row.supplier_id,
            "supplier_name": row.supplier_name,
            "analysis_count": row.analysis_count,
            "needs_review_count": row.needs_review_count,
            "product_id_unresolved_count": row.product_id_unresolved_count,
            "unit_unresolved_count": row.unit_unresolved_count,
            "condition_fallback_count": row.condition_fallback_count,
            "condition_give_up_count": row.condition_give_up_count,
            "condition_manual_reviewed_count": row.condition_manual_reviewed_count,
        }
        for row in rows
    ]


async def fetch_supplier_source(db: AsyncSession, *, supplier_id: str) -> dict:
    """
    仕入元の原文 1 件を返す（GAS: api_getSupplierSource 相当）。

    items=0 の source でも raw_text を返す。
    supplier_id は public.suppliers.supplier_code（例: 'SP-00057'）。
    """
    sql = f"""
        SELECT
            sm.id::text     AS source_message_id,
            ps.supplier_code AS supplier_id,
            ps.name         AS supplier_name,
            sm.raw_text
        FROM {TCG_SCHEMA}.source_messages sm
        JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
        LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
        WHERE ps.supplier_code = :supplier_id
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
