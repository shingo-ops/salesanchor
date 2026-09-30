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
#       同じ組に試運転済みが1件でもあれば組ごと外す（同じ投稿を2回測らない）。並びは古い投稿から。
_SELECT_TARGETS_SQL = f"""
    WITH cand AS (
        SELECT ej.id, ej.created_at, sm.supplier_channel_id AS ch, sm.line_posted_at AS pa,
               regexp_replace(sm.raw_text, '\\s', '', 'g') AS k,
               EXISTS (
                   SELECT 1 FROM {TCG_SCHEMA}.extraction_shadow_runs r WHERE r.extraction_job_id = ej.id
               ) AS ran
        FROM {TCG_SCHEMA}.extraction_jobs ej
        JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
        JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN public.suppliers s ON s.id = sc.supplier_id
        WHERE ej.status = 'done'
          AND btrim(COALESCE(s.extraction_price_format, '')) <> ''
          AND btrim(COALESCE(s.extraction_qty_format, '')) <> ''
          AND btrim(COALESCE(s.extraction_order_pattern, '')) <> ''
    ), grouped AS (
        SELECT cand.*, bool_or(ran) OVER (PARTITION BY ch, pa, k) AS group_ran FROM cand
    )
    SELECT id FROM (
        SELECT DISTINCT ON (ch, pa, k) id, pa
        FROM grouped
        WHERE NOT group_ran
        ORDER BY ch, pa, k, created_at DESC
    ) t
    ORDER BY pa ASC NULLS LAST, id
    LIMIT :limit
"""

_LEDGER_TOTALS_SQL = """
    SELECT COUNT(*), COUNT(*) FILTER (WHERE cost_usd IS NULL), COALESCE(SUM(cost_usd), 0)
    FROM public.llm_usage_events
    WHERE purpose = :purpose AND occurred_at >= :since
"""


@dataclass(frozen=True)
class LedgerTotals:
    rows: int
    null_cost_rows: int
    cost_usd: Decimal


@dataclass
class BackfillSummary:
    target_count: int = 0
    preview_job_ids: list[str] = field(default_factory=list)
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    total_cost_usd: Decimal = Decimal("0")
    stop_reason: str | None = None  # cost_limit / ledger_missing / cost_null
    dry_run: bool = False


def select_target_jobs(session: Session, limit: int) -> list[str]:
    rows = session.execute(text(_SELECT_TARGETS_SQL), {"limit": limit}).fetchall()
    return [str(r[0]) for r in rows]


def fetch_db_now(session: Session) -> datetime:
    """DB の時計で「実行を始めた時刻」を取る（台帳の occurred_at も DB の時計で付くため）。"""
    return session.execute(text("SELECT clock_timestamp()")).scalar_one()


def fetch_ledger_totals(session: Session, since: datetime) -> LedgerTotals:
    """実行を始めてからの台帳（purpose=line_extraction_shadow）の行数・費用NULLの行数・費用の合計。"""
    row = session.execute(
        text(_LEDGER_TOTALS_SQL), {"purpose": _SHADOW_PURPOSE, "since": since}
    ).one()
    return LedgerTotals(rows=int(row[0]), null_cost_rows=int(row[1]), cost_usd=Decimal(str(row[2])))


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


def _stop_reason(summary: BackfillSummary, totals: LedgerTotals, max_cost_usd: Decimal) -> str | None:
    """止める理由。費用を見張れない状態（台帳の行が足りない・費用NULL）は安全側に止める。"""
    if totals.rows < summary.succeeded:
        return "ledger_missing"
    if totals.null_cost_rows > 0:
        return "cost_null"
    if totals.cost_usd > max_cost_usd:
        return "cost_limit"
    return None


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
        totals = fetch_ledger_totals(session, since)
        summary.total_cost_usd = totals.cost_usd
        reason = _stop_reason(summary, totals, max_cost_usd)
        if reason is not None:
            summary.stop_reason = reason
            logger.warning("[shadow_backfill] stopping: %s (cost=%s)", reason, totals.cost_usd)
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
        f"total_cost_usd={summary.total_cost_usd} stop_reason={summary.stop_reason}"
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
