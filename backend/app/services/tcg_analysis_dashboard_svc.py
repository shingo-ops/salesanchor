"""
TCG 解析ダッシュボード サービス層。

SELECT のみ。INSERT / UPDATE / DELETE / DDL を実行しない。
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.tcg_config import TCG_SCHEMA


async def get_pipeline_summary(db: AsyncSession) -> dict:
    """
    パイプライン全体のサマリーを返す。

    実行する SQL はすべてコード内に固定。SELECT のみ。
    """
    # 1. extraction_jobs ステータス別件数
    rows_by_status = (
        await db.execute(text(f"SELECT status, COUNT(*) AS cnt FROM {TCG_SCHEMA}.extraction_jobs GROUP BY status"))
    ).fetchall()

    by_status: dict[str, int] = {}
    for row in rows_by_status:
        by_status[row.status] = int(row.cnt)

    total_extraction = sum(by_status.values())
    error_count = by_status.get("error", 0)
    error_rate = error_count / total_extraction if total_extraction > 0 else 0.0

    # 2. stale running 件数（10分超）
    stale_running_count = int(
        (
            await db.execute(
                text(
                    f"SELECT COUNT(*)"
                    f" FROM {TCG_SCHEMA}.extraction_jobs"
                    f" WHERE status = 'running'"
                    f" AND created_at < NOW() - INTERVAL '10 minutes'"
                )
            )
        ).scalar()
        or 0
    )

    # 3. analysis_results 集計
    ar_row = (
        await db.execute(
            text(
                f"SELECT"
                f"  COUNT(*) AS total,"
                f"  SUM(CASE WHEN pid_resolved THEN 1 ELSE 0 END) AS pid_resolved_count,"
                f"  SUM(CASE WHEN unit_resolved THEN 1 ELSE 0 END) AS unit_resolved_count,"
                f"  SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) AS needs_review_count"
                f" FROM {TCG_SCHEMA}.analysis_results"
            )
        )
    ).fetchone()

    total_analysis = int(ar_row.total or 0)
    pid_resolved_count = int(ar_row.pid_resolved_count or 0)
    unit_resolved_count = int(ar_row.unit_resolved_count or 0)
    needs_review_count = int(ar_row.needs_review_count or 0)

    pid_resolved_rate = pid_resolved_count / total_analysis if total_analysis > 0 else 0.0
    unit_resolved_rate = unit_resolved_count / total_analysis if total_analysis > 0 else 0.0
    needs_review_rate = needs_review_count / total_analysis if total_analysis > 0 else 0.0

    # 4. analysis missing 件数（done ジョブに紐づく item で解析結果なし）
    missing_count = int(
        (
            await db.execute(
                text(
                    f"SELECT COUNT(DISTINCT ej.id)"
                    f" FROM {TCG_SCHEMA}.extraction_jobs ej"
                    f" JOIN {TCG_SCHEMA}.extraction_items ei ON ei.extraction_job_id = ej.id"
                    f" WHERE ej.status = 'done'"
                    f" AND NOT EXISTS ("
                    f"   SELECT 1 FROM {TCG_SCHEMA}.analysis_results ar"
                    f"   WHERE ar.extraction_item_id = ei.id"
                    f" )"
                )
            )
        ).scalar()
        or 0
    )

    # 5. review_reasons 内訳
    reason_rows = (
        await db.execute(
            text(
                f"SELECT unnest(string_to_array(review_reasons, ',')) AS reason,"
                f"       COUNT(*) AS cnt"
                f" FROM {TCG_SCHEMA}.analysis_results"
                f" WHERE needs_review = TRUE AND review_reasons IS NOT NULL"
                f" GROUP BY reason"
                f" ORDER BY cnt DESC"
            )
        )
    ).fetchall()

    review_reasons = [{"reason": row.reason, "count": int(row.cnt)} for row in reason_rows]

    # 6. 最新エンジン情報
    attempt_row = (
        await db.execute(
            text(
                f"SELECT requested_model, prompt_version"
                f" FROM {TCG_SCHEMA}.extraction_attempts"
                f" ORDER BY started_at DESC"
                f" LIMIT 1"
            )
        )
    ).fetchone()

    engine_version_row = (
        await db.execute(
            text(f"SELECT engine_version FROM {TCG_SCHEMA}.analysis_results ORDER BY computed_at DESC LIMIT 1")
        )
    ).fetchone()

    engine = {
        "current_model": attempt_row.requested_model if attempt_row else None,
        "current_prompt_version": attempt_row.prompt_version if attempt_row else None,
        "current_engine_version": engine_version_row.engine_version if engine_version_row else None,
    }

    # 7. 直近エラー 10 件
    error_rows = (
        await db.execute(
            text(
                f"SELECT ej.id, ej.error_message, ej.created_at, ej.prompt_version"
                f" FROM {TCG_SCHEMA}.extraction_jobs ej"
                f" WHERE ej.status = 'error'"
                f" ORDER BY ej.created_at DESC"
                f" LIMIT 10"
            )
        )
    ).fetchall()

    recent_errors = [
        {
            "id": str(row.id),
            "error_message": row.error_message,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "prompt_version": row.prompt_version,
        }
        for row in error_rows
    ]

    return {
        "extraction": {
            "total": total_extraction,
            "by_status": {
                "done": by_status.get("done", 0),
                "error": by_status.get("error", 0),
                "pending": by_status.get("pending", 0),
                "running": by_status.get("running", 0),
                "empty": by_status.get("empty", 0),
            },
            "stale_running_count": stale_running_count,
            "error_rate": error_rate,
        },
        "analysis": {
            "total": total_analysis,
            "pid_resolved_count": pid_resolved_count,
            "pid_resolved_rate": pid_resolved_rate,
            "unit_resolved_count": unit_resolved_count,
            "unit_resolved_rate": unit_resolved_rate,
            "needs_review_count": needs_review_count,
            "needs_review_rate": needs_review_rate,
            "missing_count": missing_count,
        },
        "review_reasons": review_reasons,
        "engine": engine,
        "recent_errors": recent_errors,
    }
