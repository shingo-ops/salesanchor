"""
TCG 解析ダッシュボード サービス層。

SELECT のみ。INSERT / UPDATE / DELETE / DDL を実行しない。
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Step 4/5: TCG テーブルは public スキーマに移行済み。
TCG_SCHEMA = "public"


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
                    "SELECT COUNT(*)"
                    f" FROM {TCG_SCHEMA}.extraction_jobs"
                    " WHERE status = 'running'"
                    " AND created_at < NOW() - INTERVAL '10 minutes'"
                )
            )
        ).scalar()
        or 0
    )

    # 3. analysis_results 集計
    ar_row = (
        await db.execute(
            text(
                "SELECT"
                "  COUNT(*) AS total,"
                "  SUM(CASE WHEN pid_resolved THEN 1 ELSE 0 END) AS pid_resolved_count,"
                "  SUM(CASE WHEN unit_resolved THEN 1 ELSE 0 END) AS unit_resolved_count,"
                "  SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) AS needs_review_count"
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
                    "SELECT COUNT(DISTINCT ej.id)"
                    f" FROM {TCG_SCHEMA}.extraction_jobs ej"
                    f" JOIN {TCG_SCHEMA}.extraction_items ei ON ei.extraction_job_id = ej.id"
                    " WHERE ej.status = 'done'"
                    " AND NOT EXISTS ("
                    f"   SELECT 1 FROM {TCG_SCHEMA}.analysis_results ar"
                    "   WHERE ar.extraction_item_id = ei.id"
                    " )"
                )
            )
        ).scalar()
        or 0
    )

    # 5. review_reasons 内訳
    reason_rows = (
        await db.execute(
            text(
                "SELECT unnest(string_to_array(review_reasons, ',')) AS reason,"
                "       COUNT(*) AS cnt"
                f" FROM {TCG_SCHEMA}.analysis_results"
                " WHERE needs_review = TRUE AND review_reasons IS NOT NULL"
                " GROUP BY reason"
                " ORDER BY cnt DESC"
            )
        )
    ).fetchall()

    review_reasons = [{"reason": row.reason, "count": int(row.cnt)} for row in reason_rows]

    # 6. 最新エンジン情報
    attempt_row = (
        await db.execute(
            text(
                "SELECT requested_model, prompt_version"
                f" FROM {TCG_SCHEMA}.extraction_attempts"
                " ORDER BY started_at DESC"
                " LIMIT 1"
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
                "SELECT ej.id, ej.error_message, ej.created_at, ej.prompt_version"
                f" FROM {TCG_SCHEMA}.extraction_jobs ej"
                " WHERE ej.status = 'error'"
                " ORDER BY ej.created_at DESC"
                " LIMIT 10"
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


async def get_pipeline_trend(db: AsyncSession, days: int = 7) -> list[dict]:
    """
    日別パイプライン集計を返す。SELECT のみ。
    """
    if not (1 <= days <= 90):
        days = 7

    rows = (
        await db.execute(
            text(
                f"SELECT"
                f"  d.day::date AS day,"
                f"  COALESCE(e.total, 0) AS extraction_total,"
                f"  COALESCE(e.done, 0) AS extraction_done,"
                f"  COALESCE(e.error, 0) AS extraction_error,"
                f"  COALESCE(a.total, 0) AS analysis_total,"
                f"  COALESCE(a.pid_resolved, 0) AS pid_resolved,"
                f"  COALESCE(a.unit_resolved, 0) AS unit_resolved,"
                f"  COALESCE(a.needs_review, 0) AS needs_review"
                f" FROM generate_series("
                f"   CURRENT_DATE - INTERVAL '{days} days',"
                f"   CURRENT_DATE,"
                f"   '1 day'"
                f" ) AS d(day)"
                f" LEFT JOIN LATERAL ("
                f"   SELECT"
                f"     COUNT(*) AS total,"
                f"     SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done,"
                f"     SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error"
                f"   FROM {TCG_SCHEMA}.extraction_jobs"
                f"   WHERE created_at::date = d.day::date"
                f" ) e ON TRUE"
                f" LEFT JOIN LATERAL ("
                f"   SELECT"
                f"     COUNT(*) AS total,"
                f"     SUM(CASE WHEN pid_resolved THEN 1 ELSE 0 END) AS pid_resolved,"
                f"     SUM(CASE WHEN unit_resolved THEN 1 ELSE 0 END) AS unit_resolved,"
                f"     SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) AS needs_review"
                f"   FROM {TCG_SCHEMA}.analysis_results ar"
                f"   JOIN {TCG_SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id"
                f"   JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id"
                f"   WHERE ej.created_at::date = d.day::date"
                f" ) a ON TRUE"
                f" ORDER BY d.day"
            )
        )
    ).fetchall()

    return [
        {
            "day": row.day.isoformat(),
            "extraction_total": int(row.extraction_total),
            "extraction_done": int(row.extraction_done),
            "extraction_error": int(row.extraction_error),
            "analysis_total": int(row.analysis_total),
            "pid_resolved": int(row.pid_resolved),
            "unit_resolved": int(row.unit_resolved),
            "needs_review": int(row.needs_review),
        }
        for row in rows
    ]


async def get_import_summary(db: AsyncSession) -> dict:
    """インポート工程のサマリーを返す。SELECT のみ。"""
    # 1. import_jobs stats
    ij_rows = (
        await db.execute(
            text(
                "SELECT"
                "  COUNT(*) AS total,"
                "  SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS ok_count,"
                "  SUM(CASE WHEN review_status = 'pending_review' THEN 1 ELSE 0 END) AS pending_review_count,"
                "  SUM(message_count) AS total_messages,"
                "  SUM(unresolved_count) AS total_unresolved,"
                "  MAX(created_at) AS latest_import_at"
                f" FROM {TCG_SCHEMA}.import_jobs"
            )
        )
    ).fetchone()

    total_jobs = int(ij_rows.total or 0)
    total_messages = int(ij_rows.total_messages or 0)
    total_unresolved = int(ij_rows.total_unresolved or 0)
    unresolved_rate = total_unresolved / total_messages if total_messages > 0 else 0.0

    # 2. source_messages stats
    sm_row = (
        await db.execute(
            text(
                "SELECT"
                "  COUNT(*) AS total,"
                "  SUM(CASE WHEN supplier_channel_id IS NULL THEN 1 ELSE 0 END) AS orphan_count,"
                "  SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_count"
                f" FROM {TCG_SCHEMA}.source_messages"
            )
        )
    ).fetchone()

    total_source = int(sm_row.total or 0)
    orphan_count = int(sm_row.orphan_count or 0)

    # 3. Recent imports (last 10) with created_count from import_job_messages
    recent_rows = (
        await db.execute(
            text(
                f"SELECT"
                f"  ij.id, ij.filename, ij.message_count, ij.unresolved_count,"
                f"  ij.review_status, ij.created_at,"
                f"  COALESCE(SUM(CASE WHEN ijm.relation_kind = 'created' THEN 1 ELSE 0 END), 0)::int AS created_count"
                f" FROM {TCG_SCHEMA}.import_jobs ij"
                f" LEFT JOIN {TCG_SCHEMA}.import_job_messages ijm ON ijm.import_job_id = ij.id"
                f" GROUP BY ij.id, ij.filename, ij.message_count, ij.unresolved_count, ij.review_status, ij.created_at"
                f" ORDER BY ij.created_at DESC"
                f" LIMIT 10"
            )
        )
    ).fetchall()

    recent_imports = [
        {
            "id": str(row.id),
            "filename": row.filename,
            "message_count": int(row.message_count or 0),
            "unresolved_count": int(row.unresolved_count or 0),
            "review_status": row.review_status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "created_count": int(row.created_count),
        }
        for row in recent_rows
    ]

    return {
        "total_jobs": total_jobs,
        "ok_count": int(ij_rows.ok_count or 0),
        "pending_review_count": int(ij_rows.pending_review_count or 0),
        "total_messages": total_messages,
        "total_unresolved": total_unresolved,
        "unresolved_rate": unresolved_rate,
        "total_source_messages": total_source,
        "orphan_count": orphan_count,
        "active_message_count": int(sm_row.active_count or 0),
        "latest_import_at": ij_rows.latest_import_at.isoformat() if ij_rows.latest_import_at else None,
        "recent_imports": recent_imports,
    }


async def get_import_trend(db: AsyncSession, days: int = 7) -> list[dict]:
    """日別インポート集計（import_jobs テーブル）。SELECT のみ。"""
    days = max(1, min(int(days), 90))

    rows = (
        await db.execute(
            text(
                f"SELECT"
                f"  TO_CHAR(DATE_TRUNC('day', created_at AT TIME ZONE 'Asia/Tokyo'), 'MM-DD') AS day,"
                f"  COUNT(*)::int AS job_count,"
                f"  COALESCE(SUM(message_count), 0)::int AS message_count,"
                f"  COALESCE(SUM(unresolved_count), 0)::int AS unresolved_count"
                f" FROM {TCG_SCHEMA}.import_jobs"
                f" WHERE created_at >= NOW() - INTERVAL '{days} days'"
                f" GROUP BY DATE_TRUNC('day', created_at AT TIME ZONE 'Asia/Tokyo')"
                f" ORDER BY DATE_TRUNC('day', created_at AT TIME ZONE 'Asia/Tokyo')"
            )
        )
    ).fetchall()

    return [
        {
            "day": row.day,
            "job_count": row.job_count,
            "message_count": row.message_count,
            "unresolved_count": row.unresolved_count,
        }
        for row in rows
    ]


async def get_supplier_pipeline(db: AsyncSession) -> dict:
    """
    提供者別パイプラインデータを返す。SELECT のみ。

    各 supplier_channel について、インポート・抽出・解析の各段階の集計を
    1クエリで取得し、severity を付与して返す。
    """
    rows = (
        await db.execute(
            text(
                f"""
SELECT
    sc.id AS channel_id,
    sc.name AS channel_name,
    -- インポート段階
    COUNT(DISTINCT sm.id) AS active_messages,
    MAX(sm.received_at) AS latest_received_at,
    -- 抽出段階
    COUNT(DISTINCT ej.id) FILTER (WHERE ej.status = 'done') AS extraction_done,
    COUNT(DISTINCT ej.id) FILTER (WHERE ej.status = 'empty') AS extraction_empty,
    COUNT(DISTINCT ej.id) FILTER (WHERE ej.status = 'error') AS extraction_error,
    COUNT(DISTINCT ej.id) FILTER (WHERE ej.status NOT IN ('done','empty','error')) AS extraction_other,
    -- 解析段階
    COUNT(ar.id) AS analysis_total,
    COUNT(ar.id) FILTER (WHERE ar.pid_resolved = true) AS pid_resolved,
    COUNT(ar.id) FILTER (WHERE ar.pid_resolved = false) AS pid_unresolved,
    COUNT(ar.id) FILTER (WHERE ar.unit_resolved = true) AS unit_resolved,
    COUNT(ar.id) FILTER (WHERE ar.unit_resolved = false) AS unit_unresolved,
    COUNT(ar.id) FILTER (WHERE ar.needs_review = true) AS needs_review,
    COUNT(ar.id) FILTER (WHERE ar.exclusion = 'excluded') AS excluded,
    COUNT(ar.id) FILTER (WHERE ar.price_normalized IS NOT NULL) AS price_ok,
    COUNT(ar.id) FILTER (WHERE ar.price_normalized IS NULL) AS price_missing,
    -- 配信可能
    COUNT(ar.id) FILTER (
        WHERE ar.pid_resolved = true
        AND ar.needs_review = false
        AND COALESCE(ar.exclusion, '') != 'excluded'
        AND ar.unit_resolved = true
        AND ar.price_normalized IS NOT NULL
    ) AS distributable
FROM {TCG_SCHEMA}.supplier_channels sc
JOIN {TCG_SCHEMA}.source_messages sm ON sm.supplier_channel_id = sc.id AND sm.is_active = true
LEFT JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.source_message_id = sm.id
LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.source_message_id = sm.id
GROUP BY sc.id, sc.name
ORDER BY sc.name
"""
            )
        )
    ).fetchall()

    def _extraction_status(done: int, empty: int, error: int, other: int) -> str:
        if error > 0:
            return "error"
        if empty > 0 and done == 0 and other == 0:
            return "empty"
        if done > 0:
            return "done"
        return "pending"

    def _severity(extraction_error: int, analysis_total: int, distributable: int) -> str:
        if extraction_error > 0:
            return "danger"
        if distributable == 0 and analysis_total > 0:
            return "danger"
        if analysis_total > 0 and distributable < analysis_total * 0.5:
            return "warning"
        return "success"

    _severity_order = {"danger": 0, "warning": 1, "success": 2}

    suppliers = []
    funnel_active_messages = 0
    funnel_extraction_done = 0
    funnel_extraction_empty = 0
    funnel_extraction_error = 0
    funnel_analysis_total = 0
    funnel_distributable = 0
    funnel_pid_unresolved = 0
    funnel_unit_unresolved = 0
    funnel_needs_review = 0
    funnel_excluded = 0
    funnel_price_missing = 0

    for row in rows:
        active_messages = int(row.active_messages or 0)
        ext_done = int(row.extraction_done or 0)
        ext_empty = int(row.extraction_empty or 0)
        ext_error = int(row.extraction_error or 0)
        ext_other = int(row.extraction_other or 0)
        analysis_total = int(row.analysis_total or 0)
        pid_resolved = int(row.pid_resolved or 0)
        pid_unresolved = int(row.pid_unresolved or 0)
        unit_resolved = int(row.unit_resolved or 0)
        unit_unresolved = int(row.unit_unresolved or 0)
        needs_review = int(row.needs_review or 0)
        excluded = int(row.excluded or 0)
        price_ok = int(row.price_ok or 0)
        price_missing = int(row.price_missing or 0)
        distributable = int(row.distributable or 0)

        ext_status = _extraction_status(ext_done, ext_empty, ext_error, ext_other)
        sev = _severity(ext_error, analysis_total, distributable)

        suppliers.append(
            {
                "channel_id": str(row.channel_id),
                "channel_name": row.channel_name,
                "import_info": {
                    "active_messages": active_messages,
                    "latest_received_at": row.latest_received_at.isoformat() if row.latest_received_at else None,
                },
                "extraction": {
                    "done": ext_done,
                    "empty": ext_empty,
                    "error": ext_error,
                    "other": ext_other,
                    "status": ext_status,
                },
                "analysis": {
                    "total": analysis_total,
                    "pid_resolved": pid_resolved,
                    "pid_unresolved": pid_unresolved,
                    "unit_resolved": unit_resolved,
                    "unit_unresolved": unit_unresolved,
                    "needs_review": needs_review,
                    "excluded": excluded,
                    "price_ok": price_ok,
                    "price_missing": price_missing,
                    "distributable": distributable,
                },
                "severity": sev,
            }
        )

        funnel_active_messages += active_messages
        funnel_extraction_done += ext_done
        funnel_extraction_empty += ext_empty
        funnel_extraction_error += ext_error
        funnel_analysis_total += analysis_total
        funnel_distributable += distributable
        funnel_pid_unresolved += pid_unresolved
        funnel_unit_unresolved += unit_unresolved
        funnel_needs_review += needs_review
        funnel_excluded += excluded
        funnel_price_missing += price_missing

    # severity降順（danger→warning→success）、同severity内はanalysis_total降順
    suppliers.sort(
        key=lambda s: (
            _severity_order.get(s["severity"], 9),
            -s["analysis"]["total"],
        )
    )

    return {
        "suppliers": suppliers,
        "funnel_summary": {
            "active_messages": funnel_active_messages,
            "extraction_done": funnel_extraction_done,
            "extraction_empty": funnel_extraction_empty,
            "extraction_error": funnel_extraction_error,
            "analysis_total": funnel_analysis_total,
            "distributable": funnel_distributable,
            "drop_reasons": {
                "pid_unresolved": funnel_pid_unresolved,
                "unit_unresolved": funnel_unit_unresolved,
                "needs_review": funnel_needs_review,
                "excluded": funnel_excluded,
                "price_missing": funnel_price_missing,
            },
        },
    }


async def get_distribution_summary(db: AsyncSession) -> dict:
    """配信工程のサマリーを返す。SELECT のみ。"""
    # 1. distribution_targets
    target_rows = (
        await db.execute(
            text(
                "SELECT id, name, is_active, last_distributed_at, last_distributed_count, last_result"
                f" FROM {TCG_SCHEMA}.tcg_distribution_targets"
                " ORDER BY name"
            )
        )
    ).fetchall()

    targets = [
        {
            "id": str(row.id),
            "name": row.name,
            "is_active": row.is_active,
            "last_distributed_at": row.last_distributed_at.isoformat() if row.last_distributed_at else None,
            "last_distributed_count": int(row.last_distributed_count) if row.last_distributed_count else 0,
            "last_result": row.last_result,
        }
        for row in target_rows
    ]

    active_count = sum(1 for t in targets if t["is_active"])
    total_distributed = sum(t["last_distributed_count"] for t in targets)

    # 2. distribution_settings
    setting_rows = (
        await db.execute(
            text(
                "SELECT key, value, note"
                f" FROM {TCG_SCHEMA}.tcg_distribution_settings"
                " ORDER BY key"
            )
        )
    ).fetchall()

    settings = [
        {"key": row.key, "value": row.value, "note": row.note}
        for row in setting_rows
    ]

    return {
        "targets": targets,
        "active_target_count": active_count,
        "total_target_count": len(targets),
        "total_last_distributed": total_distributed,
        "settings": settings,
    }
