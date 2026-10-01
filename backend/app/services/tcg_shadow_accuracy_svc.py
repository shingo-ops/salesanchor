"""
解析精度管理（新方式）: 試運転（shadow）結果の精度サマリー・投稿照合（読み取り専用）。

docs/handoff/line-accuracy-pages/design.md §3-2 / §3-3。
誤りの兆候 S1〜S6 の SQL 式は shadow_accuracy_signals.py が SSOT。
書き方は tcg_shadow_review_svc.py に合わせる（async・sqlalchemy.text・public. 固定）。
DB には一切書き込まない。
"""
from __future__ import annotations

from typing import Any, Final, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.shadow_accuracy_signals import (
    LATEST_RUN_PER_JOB_SQL,
    SIGNAL_CODES,
    SIGNAL_COLUMNS,
    flagged_cte,
    period_supplier_where,
    signal_count_selects,
)

SignalCode = Literal["S1", "S2", "S3", "S4", "S5", "S6"]

_SOLD_OUT_STATUS: Final[str] = "Sold out"
_PRE_ORDER_TYPE: Final[str] = "pre_order"

_COUNT_COLUMNS: Final[tuple[str, ...]] = (
    "blocks", "needs_review_count", "auto_confirmed", "matched", "ambiguous", "unmatched",
    "price_fixed", "quantity_fixed", "sold_out", "pre_order",
)


def _signals_of(row: Any) -> dict[str, int]:
    return {code: int(row[SIGNAL_COLUMNS[code]] or 0) for code in SIGNAL_CODES}


def summary_queries(days: int, supplier_id: int | None) -> list[tuple[str, dict[str, Any]]]:
    """summary が実行する SQL とパラメータ（[0]=仕入元別、[1]=状態の内訳）。EXPLAIN 用にも使う。"""
    where_sql, params = period_supplier_where(days, supplier_id)
    cte = flagged_cte(where_sql)
    by_supplier = (
        f"{cte} SELECT supplier_id, supplier_name, "
        "count(*) AS blocks, "
        "count(*) FILTER (WHERE needs_review) AS needs_review_count, "
        "count(*) FILTER (WHERE NOT needs_review) AS auto_confirmed, "
        "count(*) FILTER (WHERE match_status = 'matched') AS matched, "
        "count(*) FILTER (WHERE match_status = 'ambiguous') AS ambiguous, "
        "count(*) FILTER (WHERE match_status = 'unmatched') AS unmatched, "
        "count(*) FILTER (WHERE price_normalized IS NOT NULL) AS price_fixed, "
        "count(*) FILTER (WHERE quantity_normalized IS NOT NULL) AS quantity_fixed, "
        f"count(*) FILTER (WHERE status = '{_SOLD_OUT_STATUS}') AS sold_out, "
        f"count(*) FILTER (WHERE ship_offer_type = '{_PRE_ORDER_TYPE}') AS pre_order, "
        f"{signal_count_selects()} "
        "FROM flagged GROUP BY supplier_id, supplier_name ORDER BY blocks DESC, supplier_name"
    )
    by_condition = (
        f"{cte} SELECT condition_canonical, count(*) AS blocks FROM flagged "
        "GROUP BY condition_canonical ORDER BY blocks DESC"
    )
    return [(by_supplier, dict(params)), (by_condition, dict(params))]


async def fetch_summary(db: AsyncSession, *, days: int, supplier_id: int | None) -> dict[str, Any]:
    """精度サマリー（期間・仕入元で絞り込み。days=0 は全期間）。"""
    (supplier_sql, params), (condition_sql, _) = summary_queries(days, supplier_id)
    supplier_rows = (await db.execute(text(supplier_sql), params)).mappings().all()
    condition_rows = (await db.execute(text(condition_sql), params)).mappings().all()

    totals = {col: sum(int(r[col] or 0) for r in supplier_rows) for col in _COUNT_COLUMNS}
    totals["auto_confirmed_ratio"] = (  # type: ignore[assignment]
        totals["auto_confirmed"] / totals["blocks"] if totals["blocks"] else None
    )
    signals = {
        code: sum(int(r[SIGNAL_COLUMNS[code]] or 0) for r in supplier_rows) for code in SIGNAL_CODES
    }
    by_supplier = [
        {
            "supplier_id": r["supplier_id"],
            "supplier_name": r["supplier_name"],
            **{col: int(r[col] or 0) for col in _COUNT_COLUMNS},
            "needs_review_ratio": (
                int(r["needs_review_count"]) / int(r["blocks"]) if int(r["blocks"]) else None
            ),
            "signals": _signals_of(r),
        }
        for r in supplier_rows
    ]
    return {
        "days": days,
        "supplier_id": supplier_id,
        "totals": totals,
        "signals": signals,
        "conditions": [
            {"condition": r["condition_canonical"], "blocks": int(r["blocks"])} for r in condition_rows
        ],
        "by_supplier": by_supplier,
    }


def posts_query(
    *,
    days: int,
    supplier_id: int | None,
    needs_review: bool | None,
    signal: SignalCode | None,
    offset: int,
    limit: int,
) -> tuple[str, dict[str, Any]]:
    """posts が実行する SQL とパラメータ。単位は run（1投稿）。EXPLAIN 用にも使う。"""
    where_sql, params = period_supplier_where(days, supplier_id)
    where_sql = f"{where_sql} AND {LATEST_RUN_PER_JOB_SQL}"
    having: list[str] = []
    if needs_review is True:
        having.append("needs_review_count > 0")
    elif needs_review is False:
        having.append("needs_review_count = 0")
    if signal is not None:
        # signal は Literal で検証済み。SQL に入れるのは SIGNAL_COLUMNS の固定値だけ。
        having.append(f"{SIGNAL_COLUMNS[signal]} > 0")
    having_sql = f"WHERE {' AND '.join(having)}" if having else ""
    sql = (
        f"{flagged_cte(where_sql)}, agg AS ("
        "SELECT job_id, run_id, supplier_id, supplier_name, posted_at, "
        "count(*) AS blocks, count(*) FILTER (WHERE needs_review) AS needs_review_count, "
        f"{signal_count_selects()} "
        "FROM flagged GROUP BY job_id, run_id, supplier_id, supplier_name, posted_at) "
        "SELECT agg.*, count(*) OVER () AS total FROM agg "
        f"{having_sql} "
        "ORDER BY posted_at DESC NULLS LAST, job_id "
        "OFFSET :offset LIMIT :limit"
    )
    return sql, {**params, "offset": offset, "limit": limit}


async def fetch_posts(
    db: AsyncSession,
    *,
    days: int,
    supplier_id: int | None,
    needs_review: bool | None = None,
    signal: SignalCode | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """投稿（run）単位の一覧。確認待ち・兆候で絞り込める。"""
    sql, params = posts_query(
        days=days, supplier_id=supplier_id, needs_review=needs_review, signal=signal,
        offset=offset, limit=limit,
    )
    rows = (await db.execute(text(sql), params)).mappings().all()
    total = int(rows[0]["total"]) if rows else 0
    if not rows and offset > 0:
        # 最終ページを越えた offset でも総数が分かるよう、先頭 1 件で数え直す
        head_sql, head_params = posts_query(
            days=days, supplier_id=supplier_id, needs_review=needs_review, signal=signal,
            offset=0, limit=1,
        )
        head = (await db.execute(text(head_sql), head_params)).mappings().all()
        total = int(head[0]["total"]) if head else 0
    items = [
        {
            "job_id": str(r["job_id"]),
            "run_id": str(r["run_id"]),
            "supplier_id": r["supplier_id"],
            "supplier_name": r["supplier_name"],
            "posted_at": r["posted_at"].isoformat() if r["posted_at"] else None,
            "blocks": int(r["blocks"]),
            "needs_review_count": int(r["needs_review_count"]),
            "signals": _signals_of(r),
        }
        for r in rows
    ]
    return {"items": items, "total": total, "offset": offset, "limit": limit}


_RUN_SQL: Final[str] = """
    SELECT run.id AS run_id, run.extraction_job_id AS job_id, run.prompt_key, run.engine_version,
           run.requested_model, run.status AS run_status, run.started_at, run.finished_at,
           sm.raw_text, COALESCE(sm.line_posted_at, sm.received_at, sm.created_at) AS posted_at,
           sup.id AS supplier_id, COALESCE(sup.name, sup.line_name) AS supplier_name
    FROM public.extraction_shadow_runs run
    JOIN public.extraction_jobs job ON job.id = run.extraction_job_id
    JOIN public.source_messages sm ON sm.id = job.source_message_id
    LEFT JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
    LEFT JOIN public.suppliers sup ON sup.id = sc.supplier_id
    WHERE run.extraction_job_id = :job_id
    ORDER BY run.started_at DESC, run.id DESC
    LIMIT 1
"""

_BLOCK_COLUMNS: Final[tuple[str, ...]] = (
    "block_index", "line_start", "line_end", "heading_line_start", "heading_line_end",
    "raw_product_name", "raw_price", "raw_unit", "raw_quantity", "raw_state", "raw_ship", "raw_multi",
    "product_id", "work_id", "match_status", "needs_review", "status", "ship_offer_type",
    "ship_timing", "note_ja", "exclusion", "evidence", "verify_failures",
    "product_name", "product_mark", "condition_canonical", "unit_kubun",
)


async def fetch_post_detail(db: AsyncSession, extraction_job_id: str) -> dict[str, Any] | None:
    """1投稿の詳細（原文・run の情報・最新 run の全ブロック）。無ければ None。"""
    run = (await db.execute(text(_RUN_SQL), {"job_id": extraction_job_id})).mappings().first()
    if run is None:
        return None

    block_sql = (
        f"{flagged_cte('res.run_id = :run_id')} "
        "SELECT * FROM flagged ORDER BY block_index"
    )
    block_rows = (await db.execute(text(block_sql), {"run_id": run["run_id"]})).mappings().all()

    candidate_ids = {
        int(cid)
        for r in block_rows
        for item in (r["review_items"] or [])
        for cid in (item.get("candidates") or [])
    }
    names: dict[int, str] = {}
    if candidate_ids:
        name_rows = await db.execute(
            text("SELECT id, name FROM public.products WHERE id = ANY(:ids)"),
            {"ids": list(candidate_ids)},
        )
        names = {int(r.id): r.name for r in name_rows.fetchall()}

    blocks = []
    for r in block_rows:
        review_items = [
            {
                "item": item.get("item"),
                "reason": item.get("reason"),
                "candidates": [
                    {"product_id": int(cid), "product_name": names.get(int(cid))}
                    for cid in (item.get("candidates") or [])
                ],
            }
            for item in (r["review_items"] or [])
        ]
        blocks.append(
            {
                **{col: r[col] for col in _BLOCK_COLUMNS},
                "id": str(r["id"]),
                "quantity_normalized": _num(r["quantity_normalized"]),
                "price_normalized": _num(r["price_normalized"]),
                "review_items": review_items,
                "signals": {code: bool(r[SIGNAL_COLUMNS[code]]) for code in SIGNAL_CODES},
            }
        )

    return {
        "job_id": str(run["job_id"]),
        "run": {
            "id": str(run["run_id"]),
            "prompt_key": run["prompt_key"],
            "engine_version": run["engine_version"],
            "requested_model": run["requested_model"],
            "status": run["run_status"],
            "started_at": run["started_at"].isoformat() if run["started_at"] else None,
            "finished_at": run["finished_at"].isoformat() if run["finished_at"] else None,
        },
        "supplier_id": run["supplier_id"],
        "supplier_name": run["supplier_name"],
        "posted_at": run["posted_at"].isoformat() if run["posted_at"] else None,
        "raw_text": run["raw_text"] or "",
        "blocks": blocks,
    }


def _num(value: Any) -> float | None:
    return float(value) if value is not None else None
