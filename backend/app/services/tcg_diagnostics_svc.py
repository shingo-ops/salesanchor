"""
TCG 診断 API サービス層。

固定クエリ方式 — SQL はコード内に埋め込む。
外部から SQL 文字列・テーブル名・列名を受け取らない。
SELECT のみ（retry_extraction を除く）。

retry_extraction:
  status='pending' または 'error' のジョブを再エンキューする。
  'done' / 'running' は skipped。
  Celery 未接続時は RuntimeError を送出（呼び出し元で 503 に変換）。
"""
from __future__ import annotations

from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.tcg_config import TCG_SCHEMA

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


# ---------------------------------------------------------------------------
# 再エンキュー（retry-extraction エンドポイント用）
# ---------------------------------------------------------------------------

_ELIGIBLE_STATUSES = frozenset({"pending", "error"})
_MAX_JOBS = 50
_COUNTDOWN_STEP = 3  # seconds per job


async def retry_extraction(
    db: AsyncSession,
    *,
    job_ids: list[str] | None,
    scope: Literal["pending"] | None,
) -> dict[str, int]:
    """
    extraction_jobs を再エンキューする。

    Args:
        db:       非同期 DB セッション
        job_ids:  再実行対象の extraction_job ID リスト（最大 50 件）
        scope:    "pending" のとき status='pending' の全件（最大 50 件）を対象とする

    Returns:
        {"enqueued": int, "skipped": int}

    Raises:
        RuntimeError: Celery タスクが未初期化、または Redis 接続失敗
    """
    # 1. Celery タスクが利用可能か事前確認
    try:
        from app.tasks.tcg_extraction import extract_source_message_task  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Celery task import failed: {exc}") from exc

    if extract_source_message_task is None:
        raise RuntimeError("Celery is not available (task not registered).")

    # 2. 対象ジョブを取得
    if job_ids is not None:
        # job_ids 指定：全件取得して呼び出し元で eligible を判定
        all_rows = (
            await db.execute(
                text(
                    f"SELECT id, source_message_id, status"
                    f" FROM {TCG_SCHEMA}.extraction_jobs"
                    f" WHERE id = ANY(:ids)"
                    f" LIMIT {_MAX_JOBS}"
                ),
                {"ids": job_ids},
            )
        ).fetchall()
        eligible = [r for r in all_rows if r.status in _ELIGIBLE_STATUSES]
        skipped_count = len(all_rows) - len(eligible)
        rows = eligible
    else:
        # scope="pending"：status='pending' の全件（最大 50 件）
        rows = (
            await db.execute(
                text(
                    f"SELECT id, source_message_id, status"
                    f" FROM {TCG_SCHEMA}.extraction_jobs"
                    f" WHERE status = 'pending'"
                    f" ORDER BY created_at ASC"
                    f" LIMIT {_MAX_JOBS}"
                )
            )
        ).fetchall()
        skipped_count = 0

    if not rows:
        return {"enqueued": 0, "skipped": skipped_count}

    # 3. error → pending にリセット（pending はそのまま）
    error_ids = [str(row.id) for row in rows if row.status == "error"]
    if error_ids:
        await db.execute(
            text(
                f"UPDATE {TCG_SCHEMA}.extraction_jobs"
                f" SET status = 'pending'"
                f" WHERE id = ANY(:ids)"
                f" AND status = 'error'"
            ),
            {"ids": error_ids},
        )
        await db.commit()

    # 4. Celery にエンキュー（件数×3秒の countdown で分散）
    source_message_ids = [str(row.source_message_id) for row in rows]
    try:
        for i, sm_id in enumerate(source_message_ids):
            extract_source_message_task.apply_async(
                args=(sm_id,),
                countdown=i * _COUNTDOWN_STEP,
            )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Celery enqueue failed: {exc}") from exc

    return {"enqueued": len(rows), "skipped": skipped_count}
