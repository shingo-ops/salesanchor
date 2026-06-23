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


@dataclass(frozen=True)
class _ProductMeta:
    product_id: int
    name: str
    tcg_type: str | None


async def _load_products_with_stock(
    db: AsyncSession,
    category: str | None,
) -> list[_ProductMeta]:
    """in_stock 在庫を持つ商品を一括取得。category 指定時は tcg_type で絞る。N+1 回避。"""
    base_sql = """
        SELECT DISTINCT p.id, p.name, p.tcg_type
        FROM public.products p
        JOIN public.inventory i ON i.product_id = p.id
        WHERE p.is_archived IS NOT TRUE
          AND i.status = 'in_stock'
    """
    params: dict[str, str] = {}
    if category is not None:
        base_sql += "  AND p.tcg_type = :category\n"
        params["category"] = category
    base_sql += "ORDER BY p.id ASC"

    result = await db.execute(text(base_sql), params)
    return [
        _ProductMeta(
            product_id=int(row["id"]),
            name=str(row["name"]),
            tcg_type=row["tcg_type"],
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
                    "tcg_type": product.tcg_type,
                }
            )
    return rows


def _pivot(
    results: list[AggregationResult],
    products: list[_ProductMeta],
) -> tuple[list[str], list[dict]]:
    """AggregationResult -> (tabs, rows) ピボット変換。supplier_name/reason は出さない。"""
    # series -> tcg_type マッピング (product.name -> tcg_type)
    series_to_tcg: dict[str, str | None] = {p.name: p.tcg_type for p in products}

    # series -> {condition: (price, quantity)} 集約
    series_cells: dict[str, dict[str, tuple[int, int]]] = {}
    for r in results:
        cells = series_cells.setdefault(r.series, {})
        cells[r.condition] = (r.unit_price, r.quantity)

    # タブ (distinct tcg_type, 昇順)
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
                "tcg_type": series_to_tcg.get(series),
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
