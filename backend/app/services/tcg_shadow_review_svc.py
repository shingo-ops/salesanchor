"""
design.md PR-D: 試運転（Shadow run）の確認待ち一覧・詰まり集計・ワード影響プレビュー。

読み取り専用（keyword-preview は DB に一切書き込まない）。
extraction_shadow_runs / extraction_shadow_results は PR-B1（migrations/20260928_110000_*）、
判定関数（block_text / match_product / ProductEntry）は PR-A（extraction_judgement_svc）。
"""
from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.extraction_judgement_svc import ProductEntry, block_text, match_product

# extraction_jobs/source_messages は ADR-156 Step4/5 で public へ移行済み・tenant_004側は
# 削除済み（migrations/20260921_050000_drop_tenant004_pipeline_tables.sql）。
# app.tcg_config.TCG_SCHEMA（環境依存）ではなく固定で "public" を使う
# （tests/test_tcg_schema_qualification.py が要求するパターン。
#  参考: backend/app/services/tcg_import_progress.py:15）。
TCG_SCHEMA = "public"

# extraction_shadow_runs/results も public 固定（migrations/20260928_110000_*）。
_SHADOW_RESULTS_BASE_FROM = f"""
    FROM public.extraction_shadow_results esr
    JOIN public.extraction_shadow_runs esh ON esh.id = esr.run_id
    JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id = esh.extraction_job_id
    JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
    LEFT JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
    LEFT JOIN public.suppliers s ON s.id = sc.supplier_id
"""


async def _product_names(db: AsyncSession, product_ids: set[int]) -> dict[int, str]:
    if not product_ids:
        return {}
    rows = await db.execute(
        text("SELECT id, name FROM public.products WHERE id = ANY(:ids)"),
        {"ids": list(product_ids)},
    )
    return {int(r.id): r.name for r in rows.fetchall()}


async def fetch_shadow_results(
    db: AsyncSession,
    *,
    needs_review: bool | None = None,
    supplier_id: int | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """試運転の確認待ち一覧（design.md PR-D: GET /tcg/shadow-results）。"""
    where_clauses = []
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if needs_review is not None:
        where_clauses.append("esr.needs_review = :needs_review")
        params["needs_review"] = needs_review
    if supplier_id is not None:
        where_clauses.append("s.id = :supplier_id")
        params["supplier_id"] = supplier_id
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    total_row = (
        await db.execute(
            text(f"SELECT COUNT(*) AS total {_SHADOW_RESULTS_BASE_FROM} {where_sql}"),
            params,
        )
    ).mappings().first()
    total = int(total_row["total"]) if total_row else 0

    result = await db.execute(
        text(
            f"""
            SELECT esr.id, esr.line_start, esr.line_end, esr.raw_product_name,
                   esr.raw_price, esr.raw_unit, esr.raw_quantity, esr.raw_state, esr.raw_ship,
                   esr.match_status, esr.product_id, esr.work_id, esr.review_items,
                   esr.needs_review, esr.created_at,
                   sm.raw_text, s.id AS supplier_id, s.name AS supplier_name
            {_SHADOW_RESULTS_BASE_FROM}
            {where_sql}
            ORDER BY esr.created_at DESC
            OFFSET :offset LIMIT :limit
            """
        ),
        params,
    )
    rows = result.mappings().all()

    candidate_ids: set[int] = set()
    for row in rows:
        for item in row["review_items"] or []:
            for cid in item.get("candidates") or []:
                candidate_ids.add(int(cid))
    names = await _product_names(db, candidate_ids)

    items = []
    for row in rows:
        review_items = []
        for item in row["review_items"] or []:
            candidates = [int(c) for c in (item.get("candidates") or [])]
            review_items.append(
                {
                    "item": item.get("item"),
                    "reason": item.get("reason"),
                    "candidates": [
                        {"product_id": cid, "product_name": names.get(cid)}
                        for cid in candidates
                    ],
                }
            )
        items.append(
            {
                "id": str(row["id"]),
                "block_text": block_text(row["raw_text"] or "", row["line_start"] or 0, row["line_end"] or 0),
                "raw_product_name": row["raw_product_name"],
                "raw_price": row["raw_price"],
                "raw_unit": row["raw_unit"],
                "raw_quantity": row["raw_quantity"],
                "raw_state": row["raw_state"],
                "raw_ship": row["raw_ship"],
                "match_status": row["match_status"],
                "product_id": row["product_id"],
                "work_id": row["work_id"],
                "needs_review": row["needs_review"],
                "review_items": review_items,
                "supplier_id": row["supplier_id"],
                "supplier_name": row["supplier_name"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        )

    return {"items": items, "total": total, "offset": offset, "limit": limit}


async def fetch_bottlenecks(db: AsyncSession, *, days: Literal[7, 30]) -> dict[str, Any]:
    """仕入元別・項目別の確認待ち件数と自動確定率（design.md PR-D: GET /tcg/shadow-results/bottlenecks）。"""
    params = {"days": days}

    by_supplier_rows = await db.execute(
        text(
            f"""
            SELECT s.id AS supplier_id, s.name AS supplier_name,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE esr.match_status = 'matched') AS matched,
                   COUNT(*) FILTER (WHERE esr.needs_review) AS needs_review_count
            {_SHADOW_RESULTS_BASE_FROM}
            WHERE esr.created_at >= now() - make_interval(days => :days)
            GROUP BY s.id, s.name
            ORDER BY needs_review_count DESC
            """
        ),
        params,
    )
    by_supplier = [
        {
            "supplier_id": r["supplier_id"],
            "supplier_name": r["supplier_name"],
            "total": int(r["total"]),
            "matched": int(r["matched"]),
            "needs_review_count": int(r["needs_review_count"]),
            "matched_ratio": (int(r["matched"]) / int(r["total"])) if int(r["total"]) else None,
        }
        for r in by_supplier_rows.mappings().all()
    ]

    by_item_rows = await db.execute(
        text(
            f"""
            SELECT s.id AS supplier_id, s.name AS supplier_name,
                   item_elem->>'item' AS item, COUNT(*) AS count
            {_SHADOW_RESULTS_BASE_FROM}
            CROSS JOIN LATERAL jsonb_array_elements(esr.review_items) AS item_elem
            WHERE esr.created_at >= now() - make_interval(days => :days)
            GROUP BY s.id, s.name, item_elem->>'item'
            ORDER BY count DESC
            """
        ),
        params,
    )
    by_item = [
        {
            "supplier_id": r["supplier_id"],
            "supplier_name": r["supplier_name"],
            "item": r["item"],
            "count": int(r["count"]),
        }
        for r in by_item_rows.mappings().all()
    ]

    return {"days": days, "by_supplier": by_supplier, "by_item": by_item}


async def _load_product_entries_async(db: AsyncSession) -> list[ProductEntry]:
    """extraction_shadow_svc.load_product_entries の async 版（router は AsyncSession のため別実装）。

    抽出しているデータは load_product_entries（sync, extraction_shadow_svc.py）と同一クエリ形。
    Celery タスク側は sync Session、この router は AsyncSession のため、セッション種別が異なり
    そのまま共有できない。SELECT 文自体は同一に保っている。
    """
    rows = await db.execute(
        text(
            """
            SELECT p.id, p.product_code, p.mark, p.work_id,
                   (SELECT COALESCE(array_agg(k.keyword ORDER BY k.position, k.keyword), ARRAY[]::text[])
                    FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_keywords,
                   (SELECT COALESCE(array_agg(k.keyword ORDER BY k.position, k.keyword), ARRAY[]::text[])
                    FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_keywords
            FROM public.products p
            WHERE p.is_active = TRUE
            """
        )
    )
    return [
        ProductEntry(
            id=int(r.id),
            product_code=r.product_code,
            mark=r.mark,
            work_id=int(r.work_id) if r.work_id is not None else None,
            search_keywords=tuple(r.search_keywords or ()),
            exclude_keywords=tuple(r.exclude_keywords or ()),
        )
        for r in rows.fetchall()
    ]


class KeywordPreviewProductNotFound(Exception):
    pass


async def preview_keyword_change(
    db: AsyncSession,
    *,
    product_id: int,
    kind: Literal["search", "exclude"],
    keyword: str,
) -> dict[str, Any]:
    """ワード追加の影響プレビュー（design.md PR-D）。DB には一切書き込まない。"""
    kw = keyword.strip()
    if not kw:
        raise ValueError("KEYWORD_EMPTY")

    products = await _load_product_entries_async(db)
    found = False
    modified: list[ProductEntry] = []
    for product in products:
        if product.id == product_id:
            found = True
            if kind == "search":
                product = ProductEntry(
                    id=product.id, product_code=product.product_code, mark=product.mark,
                    work_id=product.work_id,
                    search_keywords=(*product.search_keywords, kw),
                    exclude_keywords=product.exclude_keywords,
                )
            else:
                product = ProductEntry(
                    id=product.id, product_code=product.product_code, mark=product.mark,
                    work_id=product.work_id,
                    search_keywords=product.search_keywords,
                    exclude_keywords=(*product.exclude_keywords, kw),
                )
        modified.append(product)
    if not found:
        raise KeywordPreviewProductNotFound("PRODUCT_NOT_FOUND")

    rows = await db.execute(
        text(
            f"""
            SELECT esr.line_start, esr.line_end, esr.match_status, sm.raw_text
            {_SHADOW_RESULTS_BASE_FROM}
            WHERE esr.created_at >= now() - interval '30 days'
            """
        )
    )

    checked = 0
    transitions: dict[str, int] = {}
    for row in rows.fetchall():
        checked += 1
        block = block_text(row.raw_text or "", row.line_start or 0, row.line_end or 0)
        new_result = match_product(block, modified)
        old_status = row.match_status
        new_status = new_result.status
        if old_status != new_status:
            key = f"{old_status}→{new_status}"
            transitions[key] = transitions.get(key, 0) + 1

    return {"checked": checked, "transitions": transitions}
