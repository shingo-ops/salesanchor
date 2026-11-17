"""テナント向け在庫集計サービス (GET /inventory/aggregated 配線層)。

既存ロジックを組み合わせるだけ。aggregate_inventory_offers / _load_inventory_offers は改変しない。
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.inventory_aggregation import (
    AggregationResult,
    aggregate_inventory_offers,
    load_aggregation_rules,
)
from app.services.inventory_search import OfferSummary, _load_inventory_offers
from app.services.product_packagings import legacy_field_sql


@dataclass(frozen=True)
class _ProductMeta:
    product_id: int
    name: str
    work_code: str | None


async def _load_products_with_stock(
    db: AsyncSession,
    category: str | None,
) -> list[_ProductMeta]:
    """in_stock 在庫を持つ商品を一括取得。category 指定時は work_id の作品の符号（type_master.code）で絞る。N+1 回避。"""
    base_sql = """
        SELECT DISTINCT p.id, p.name, tm.code AS work_code
        FROM public.products p
        JOIN public.inventory i ON i.product_id = p.id
        LEFT JOIN public.type_master tm ON tm.id = p.work_id
        WHERE p.is_archived IS NOT TRUE
          AND i.status = 'in_stock'
    """
    params: dict[str, str] = {}
    if category is not None:
        base_sql += "  AND tm.code = :category\n"
        params["category"] = category
    base_sql += "ORDER BY p.id ASC"

    result = await db.execute(text(base_sql), params)
    return [
        _ProductMeta(
            product_id=int(row["id"]),
            name=str(row["name"]),
            work_code=row["work_code"],
        )
        for row in result.mappings().all()
    ]


def _build_aggregation_offers(
    products: list[_ProductMeta],
    offers_by_product: dict[int, list[OfferSummary]],
) -> list[dict]:
    """OfferSummary -> aggregate_inventory_offers 入力形式に変換。"""
    rows: list[dict] = []
    product_by_id = {p.product_id: p for p in products}
    for pid, offers in offers_by_product.items():
        product = product_by_id.get(pid)
        if product is None:
            continue
        for offer in offers:
            rows.append(
                {
                    "series": product.name,
                    "condition": offer.condition,
                    "quantity": offer.quantity if offer.quantity is not None else 0,
                    "unit_price": offer.unit_price if offer.unit_price is not None else 0,
                    "status": offer.status,
                    "supplier_name": offer.supplier_name,
                    "work_code": product.work_code,
                }
            )
    return rows


def _pivot(
    results: list[AggregationResult],
    products: list[_ProductMeta],
) -> tuple[list[str], list[dict]]:
    """AggregationResult -> (tabs, rows) ピボット変換。supplier_name/reason は出さない。"""
    # series -> work_code マッピング (product.name -> work_code)
    series_to_tcg: dict[str, str | None] = {p.name: p.work_code for p in products}

    # series -> {condition: (price, quantity)} 集約
    series_cells: dict[str, dict[str, tuple[int, int]]] = {}
    for r in results:
        cells = series_cells.setdefault(r.series, {})
        cells[r.condition] = (r.unit_price, r.quantity)

    # タブ (distinct work_code, 昇順)
    tabs_set: set[str] = set()
    for series in series_cells:
        t = series_to_tcg.get(series)
        if t:
            tabs_set.add(t)
    tabs = sorted(tabs_set)

    # 行生成
    rows: list[dict] = []
    for series, cells in series_cells.items():
        rows.append(
            {
                "series": series,
                "work_code": series_to_tcg.get(series),
                "cells": {
                    condition: {"price": price, "quantity": qty}
                    for condition, (price, qty) in cells.items()
                },
            }
        )

    return tabs, rows


async def get_aggregated_inventory(
    db: AsyncSession,
    category: str | None,
) -> tuple[list[str], list[dict]]:
    """テナント向け集計エントリポイント。(tabs, rows) を返す。"""
    # 1. in_stock 商品一覧 (N+1 回避)
    products = await _load_products_with_stock(db, category)
    if not products:
        return [], []

    product_ids = [p.product_id for p in products]

    # 2. オファー一括取得 (既存関数、mask_stock=False で全表示)
    offers_by_product = await _load_inventory_offers(db, product_ids, mask_stock=False)

    # 3. 集計入力整形
    offer_rows = _build_aggregation_offers(products, offers_by_product)
    if not offer_rows:
        return [], []

    # 4. 集計ルール読み込み + 集計実行
    rules = await load_aggregation_rules(db)
    results = aggregate_inventory_offers(offer_rows, rules)

    # 5. ピボット
    return _pivot(results, products)


# ---------------------------------------------------------------------------
# 請求書・見積の商品行の在庫（invoice-create-portfolio R2・design-v2 §3-4）
# 上の在庫表と同じ関数で作り、集計の鍵だけを商品の番号にする。上の関数は変えない。
# ---------------------------------------------------------------------------


def _build_draft_offers(
    products: list[_ProductMeta],
    offers_by_product: dict[int, list[OfferSummary]],
) -> list[dict]:
    """集計に渡す行。series に商品の番号を入れ、同じ名前の商品を混ぜない。"""
    rows: list[dict] = []
    product_by_id = {p.product_id: p for p in products}
    for pid, offers in offers_by_product.items():
        product = product_by_id.get(pid)
        if product is None:
            continue
        for offer in offers:
            rows.append(
                {
                    "product_id": pid,
                    "series": str(pid),
                    "condition": offer.condition,
                    "quantity": offer.quantity if offer.quantity is not None else 0,
                    "unit_price": offer.unit_price if offer.unit_price is not None else 0,
                    "status": offer.status,
                    "supplier_name": offer.supplier_name,
                    "work_code": product.work_code,
                }
            )
    return rows


def _pivot_by_product(results: list[AggregationResult]) -> dict[int, dict[str, dict]]:
    """商品の番号 -> {状態: {price, quantity}}。仕入元名・理由は出さない。"""
    cells_by_product: dict[int, dict[str, dict]] = {}
    for r in results:
        if r.product_id is None:
            continue
        cells = cells_by_product.setdefault(int(r.product_id), {})
        cells[r.condition] = {"price": r.unit_price, "quantity": r.quantity}
    return cells_by_product


async def _load_draft_categories(db: AsyncSession, codes: set[str]) -> list[dict]:
    """在庫のある中分類の名前（type_master.name_ja）。sort_order 順・同じなら code 順。"""
    if not codes:
        return []
    result = await db.execute(
        text(
            "SELECT code, name_ja FROM public.type_master "
            "WHERE code = ANY(:codes) ORDER BY sort_order ASC, code ASC"
        ),
        {"codes": sorted(codes)},
    )
    return [{"code": row["code"], "name_ja": row["name_ja"]} for row in result.mappings().all()]


async def _load_draft_product_extras(db: AsyncSession, product_ids: list[int]) -> dict[int, dict]:
    """英語名・型番と、荷姿の表の BOX・ケースの重さ（ADR-1028。商品検索と同じ読み方）。"""
    if not product_ids:
        return {}
    result = await db.execute(
        text(
            f"""
            SELECT p.id, p.name_en, p.mark,
                   {legacy_field_sql("box_weight_kg", "p.id")} AS box_weight_kg,
                   {legacy_field_sql("case_weight_kg", "p.id")} AS case_weight_kg
            FROM public.products p
            WHERE p.id = ANY(:ids)
            """
        ),
        {"ids": product_ids},
    )
    extras: dict[int, dict] = {}
    for row in result.mappings().all():
        extras[int(row["id"])] = {
            "name_en": row["name_en"],
            "mark": row["mark"],
            "box_weight_kg": float(row["box_weight_kg"]) if row["box_weight_kg"] is not None else None,
            "case_weight_kg": float(row["case_weight_kg"]) if row["case_weight_kg"] is not None else None,
        }
    return extras


async def get_draft_inventory(
    db: AsyncSession,
    category: str | None,
) -> tuple[list[dict], list[dict]]:
    """請求書・見積の商品行の在庫。(categories, items) を返す。category は items だけを絞る。"""
    products = await _load_products_with_stock(db, None)
    if not products:
        return [], []

    product_ids = [p.product_id for p in products]
    offers_by_product = await _load_inventory_offers(db, product_ids, mask_stock=False)
    offer_rows = _build_draft_offers(products, offers_by_product)
    if not offer_rows:
        return [], []

    rules = await load_aggregation_rules(db)
    cells_by_product = _pivot_by_product(aggregate_inventory_offers(offer_rows, rules))

    stocked = [p for p in products if p.product_id in cells_by_product]
    categories = await _load_draft_categories(db, {p.work_code for p in stocked if p.work_code})
    picked = [p for p in stocked if category is None or p.work_code == category]
    extras = await _load_draft_product_extras(db, [p.product_id for p in picked])

    items: list[dict] = []
    for p in picked:
        extra = extras.get(p.product_id, {})
        items.append(
            {
                "product_id": p.product_id,
                "name": p.name,
                "name_en": extra.get("name_en"),
                "mark": extra.get("mark"),
                "work_code": p.work_code,
                "box_weight_kg": extra.get("box_weight_kg"),
                "case_weight_kg": extra.get("case_weight_kg"),
                "cells": cells_by_product[p.product_id],
            }
        )
    return categories, items
