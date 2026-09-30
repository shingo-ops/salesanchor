"""過去の抽出ジョブに新方式（v7 の書き写し＋システム判定）だけを一括で流す道具。

設計: docs/handoff/gemini-extract-role-split/shadow-backfill-design.md §3
起動: python -m app.tools.shadow_backfill --limit N --max-cost-usd X [--dry-run]

書き込み先は extraction_shadow_runs / extraction_shadow_results / llm_usage_events だけ。
旧方式の表（extraction_items / extraction_attempts / extraction_jobs）には書かない。
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.extraction_shadow_svc import run_shadow_for_job
from app.tasks.tcg_extraction import TCG_SCHEMA, _get_sync_session, load_extraction_context

logger = logging.getLogger(__name__)

_PREVIEW_COUNT = 10
_SHADOW_PURPOSE = "line_extraction_shadow"

# 対象: done・ルールあり（has_required_supplier_rule と同じ3列が空白除き非空）・
#       shadow の run 無し（UNIQUE 衝突の回避）。同じ投稿（空白の違いだけ）は created_at 最新の1件。
#       並びは古い投稿から。
_SELECT_TARGETS_SQL = f"""
    SELECT id FROM (
        SELECT DISTINCT ON (sm.supplier_channel_id, sm.line_posted_at,
                            regexp_replace(sm.raw_text, '\\s', '', 'g'))
               ej.id, sm.line_posted_at
        FROM {TCG_SCHEMA}.extraction_jobs ej
        JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
        JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN public.suppliers s ON s.id = sc.supplier_id
        WHERE ej.status = 'done'
          AND btrim(COALESCE(s.extraction_price_format, '')) <> ''
          AND btrim(COALESCE(s.extraction_qty_format, '')) <> ''
          AND btrim(COALESCE(s.extraction_order_pattern, '')) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM {TCG_SCHEMA}.extraction_shadow_runs r WHERE r.extraction_job_id = ej.id
          )
        ORDER BY sm.supplier_channel_id, sm.line_posted_at,
                 regexp_replace(sm.raw_text, '\\s', '', 'g'), ej.created_at DESC
    ) t
    ORDER BY line_posted_at ASC NULLS LAST, id
    LIMIT :limit
"""

_CUMULATIVE_COST_SQL = """
    SELECT COALESCE(SUM(cost_usd), 0)
    FROM public.llm_usage_events
    WHERE purpose = :purpose AND occurred_at >= :since
"""


@dataclass
class BackfillSummary:
    target_count: int = 0
    preview_job_ids: list[str] = field(default_factory=list)
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    total_cost_usd: Decimal = Decimal("0")
    stopped_by_cost: bool = False
    dry_run: bool = False


def select_target_jobs(session: Session, limit: int) -> list[str]:
    rows = session.execute(text(_SELECT_TARGETS_SQL), {"limit": limit}).fetchall()
    return [str(r[0]) for r in rows]


def fetch_db_now(session: Session) -> datetime:
    """DB の時計で「実行を始めた時刻」を取る（台帳の occurred_at も DB の時計で付くため）。"""
    return session.execute(text("SELECT clock_timestamp()")).scalar_one()


def fetch_cumulative_cost(session: Session, since: datetime) -> Decimal:
    value = session.execute(
        text(_CUMULATIVE_COST_SQL), {"purpose": _SHADOW_PURPOSE, "since": since}
    ).scalar_one()
    return Decimal(str(value))


def _process_job(session: Session, job_id: str) -> bool:
    """1ジョブを新方式で流す。成功なら True。例外・失敗は False（中断しない）。"""
    try:
        ctx = load_extraction_context(session, job_id)
        if ctx is None:
            logger.error("[shadow_backfill] job not found ej=%s", job_id)
            return False
        result = run_shadow_for_job(
            session,
            job_id,
            raw_text=ctx.raw_text,
            supplier_context=ctx.supplier_context,
            knowledge_links=ctx.knowledge_links,
        )
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("[shadow_backfill] unexpected error ej=%s", job_id)
        return False
    ok = result.get("status") == "completed"
    logger.info("[shadow_backfill] ej=%s status=%s", job_id, result.get("status"))
    return ok


def run_backfill(
    session: Session, *, limit: int, max_cost_usd: Decimal, dry_run: bool
) -> BackfillSummary:
    job_ids = select_target_jobs(session, limit)
    summary = BackfillSummary(
        target_count=len(job_ids), preview_job_ids=job_ids[:_PREVIEW_COUNT], dry_run=dry_run
    )
    if dry_run:
        return summary

    since = fetch_db_now(session)
    for job_id in job_ids:
        ok = _process_job(session, job_id)
        summary.processed += 1
        if ok:
            summary.succeeded += 1
        else:
            summary.failed += 1
        summary.total_cost_usd = fetch_cumulative_cost(session, since)
        if summary.total_cost_usd > max_cost_usd:
            summary.stopped_by_cost = True
            logger.warning(
                "[shadow_backfill] cost limit exceeded: %s > %s, stopping",
                summary.total_cost_usd, max_cost_usd,
            )
            break
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="過去ジョブに新方式（v7）だけを一括で流す")
    parser.add_argument("--limit", type=int, required=True, help="処理する最大件数")
    parser.add_argument(
        "--max-cost-usd", type=Decimal, required=True, help="費用の累計の上限（USD）。超えたら止める"
    )
    parser.add_argument("--dry-run", action="store_true", help="対象の件数と先頭10件を表示するだけ")
    return parser.parse_args(argv)


def _print_summary(summary: BackfillSummary) -> None:
    if summary.dry_run:
        print(f"[dry-run] target_count={summary.target_count}")
        for job_id in summary.preview_job_ids:
            print(f"  {job_id}")
        return
    print(
        f"processed={summary.processed} succeeded={summary.succeeded} failed={summary.failed} "
        f"total_cost_usd={summary.total_cost_usd} stopped_by_cost={summary.stopped_by_cost}"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    session = _get_sync_session()
    try:
        summary = run_backfill(
            session, limit=args.limit, max_cost_usd=args.max_cost_usd, dry_run=args.dry_run
        )
    finally:
        session.close()
    _print_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
