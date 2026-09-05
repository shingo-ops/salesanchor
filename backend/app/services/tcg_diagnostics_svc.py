"""
TCG 診断 API サービス層。

固定クエリ方式 — SQL はコード内に埋め込む。
外部から SQL 文字列・テーブル名・列名を受け取らない。
SELECT のみ。INSERT / UPDATE / DELETE / DDL を含まない。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TCG_SCHEMA = "tenant_004"

# ---------------------------------------------------------------------------
# 許可キー一覧（完全一致のみ受理）
# ---------------------------------------------------------------------------

_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "suppliers",
        "supplier-name-dupes",
        "supplier-channels",
        "orphan-messages",
        "extraction-errors",
        "extraction-pending",
        "extraction-running-stale",
        "analysis-missing",
    }
)

# ---------------------------------------------------------------------------
# 固定 SQL マップ（キーと SQL は 1:1 で埋め込み済み）
# ---------------------------------------------------------------------------

_QUERIES: dict[str, str] = {
    "suppliers": f"""
        SELECT code, name, is_active
        FROM {TCG_SCHEMA}.tcg_suppliers
        ORDER BY code
    """,
    "supplier-name-dupes": f"""
        SELECT LOWER(name) AS name_lower, COUNT(*) AS cnt
        FROM {TCG_SCHEMA}.tcg_suppliers
        GROUP BY LOWER(name)
        HAVING COUNT(*) BETWEEN 2 AND 9999
        ORDER BY cnt DESC
    """,
    "supplier-channels": f"""
        SELECT ts.code AS supplier_code, ts.name AS supplier_name, COUNT(sc.id) AS channel_count
        FROM {TCG_SCHEMA}.supplier_channels sc
        LEFT JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id = sc.supplier_id
        GROUP BY ts.code, ts.name
        ORDER BY ts.code
    """,
    "orphan-messages": f"""
        SELECT COUNT(*) AS null_channel_count
        FROM {TCG_SCHEMA}.source_messages
        WHERE supplier_channel_id IS NULL
    """,
    "extraction-errors": f"""
        SELECT ej.id,
               ej.source_message_id,
               ej.error_message,
               ej.prompt_version,
               ej.created_at
        FROM {TCG_SCHEMA}.extraction_jobs ej
        WHERE ej.status = 'error'
        ORDER BY ej.created_at DESC
        LIMIT 100
    """,
    "extraction-pending": f"""
        SELECT ej.id,
               ej.source_message_id,
               ej.created_at
        FROM {TCG_SCHEMA}.extraction_jobs ej
        WHERE ej.status = 'pending'
        ORDER BY ej.created_at ASC
        LIMIT 100
    """,
    "extraction-running-stale": f"""
        SELECT ej.id,
               ej.source_message_id,
               ej.created_at,
               ROUND(EXTRACT(EPOCH FROM (NOW() - ej.created_at)) / 60) AS age_minutes
        FROM {TCG_SCHEMA}.extraction_jobs ej
        WHERE ej.status = 'running'
          AND ej.created_at < NOW() - INTERVAL '10 minutes'
        ORDER BY ej.created_at ASC
    """,
    "analysis-missing": f"""
        SELECT ej.id AS extraction_job_id,
               ej.source_message_id,
               COUNT(ei.id) AS item_count,
               ej.extracted_at
        FROM {TCG_SCHEMA}.extraction_jobs ej
        JOIN {TCG_SCHEMA}.extraction_items ei ON ei.extraction_job_id = ej.id
        WHERE ej.status = 'done'
          AND NOT EXISTS (
              SELECT 1
              FROM {TCG_SCHEMA}.analysis_results ar
              WHERE ar.extraction_item_id = ei.id
          )
        GROUP BY ej.id, ej.source_message_id, ej.extracted_at
        ORDER BY ej.extracted_at DESC
    """,
}


def get_allowed_keys() -> list[str]:
    """許可キー一覧をソート済みで返す。"""
    return sorted(_ALLOWED_KEYS)


async def run_diagnostic(db: AsyncSession, *, key: str) -> list[dict]:
    """
    指定された固定クエリを実行し、行リストを返す。

    key は呼び出し元（router）で許可リストへの完全一致を事前確認済み。
    SQL はコード内に固定されており、key から SQL を動的生成しない。
    """
    sql = _QUERIES[key]
    rows = (await db.execute(text(sql))).fetchall()
    return [dict(row._mapping) for row in rows]
