"""
買取相場 API ルーター。

ADR-157: 買取相場ログ

エンドポイント:
  GET /api/v1/buyback-prices
    最新の買取価格一覧（shop_products JOIN 最新 price_log）
    クエリパラメータ: card_game / shop / product_type

  GET /api/v1/buyback-prices/{shop_product_id}/history
    商品別の価格推移（最大 days 日分）

認証: get_current_tenant 必須（main.py で設定）
テナント分離: public スキーマ参照のみのため search_path 不要
              読み取り専用のため RLS の operator 設定も不要
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# レスポンススキーマ
# ---------------------------------------------------------------------------


class BuybackPriceItem(BaseModel):
    shop_product_id: uuid.UUID
    shop_code: str
    external_product_id: str
    product_name: str
    card_game: str
    product_type: str | None
    image_url: str | None
    price_s: int | None
    price_a: int | None
    price_am: int | None
    price_b: int | None
    price_c: int | None
    fetched_at: datetime | None
    last_seen_at: datetime


class BuybackPriceListResponse(BaseModel):
    items: list[BuybackPriceItem]
    total: int


class BuybackPriceHistoryEntry(BaseModel):
    price_s: int | None
    price_a: int | None
    price_am: int | None
    price_b: int | None
    price_c: int | None
    fetched_at: datetime


class BuybackPriceHistoryResponse(BaseModel):
    shop_product_id: uuid.UUID
    product_name: str
    shop_code: str
    card_game: str
    product_type: str | None
    history: list[BuybackPriceHistoryEntry]


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.get(
    "/buyback-prices",
    response_model=BuybackPriceListResponse,
    tags=["buyback-prices"],
)
async def list_buyback_prices(
    card_game: str | None = Query(default=None, description="カードゲーム種別 (例: pokemon)"),
    shop: str | None = Query(default=None, description="買取店コード (例: shinsoku, homura)"),
    product_type: str | None = Query(default=None, description="商品種別 (例: BOX, CARTON)"),
    limit: int = Query(default=50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(default=0, ge=0, description="オフセット"),
    db: AsyncSession = Depends(get_db),
    _tenant=Depends(get_current_tenant),
):
    """最新の買取価格一覧を返す。

    buyback_shop_products と最新の buyback_price_logs を JOIN して返す。
    フィルタ: card_game / shop / product_type
    """
    # 動的 WHERE 句（SQL インジェクション対策としてホワイトリスト値のみ許可）
    conditions = []
    params: dict = {"limit": limit, "offset": offset}

    if card_game is not None:
        conditions.append("p.card_game = :card_game")
        params["card_game"] = card_game

    if shop is not None:
        conditions.append("p.shop_code = :shop")
        params["shop"] = shop

    if product_type is not None:
        conditions.append("p.product_type = :product_type")
        params["product_type"] = product_type

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = text(
        f"""
        WITH latest_logs AS (
            SELECT DISTINCT ON (shop_product_id)
                shop_product_id,
                price_s,
                price_a,
                price_am,
                price_b,
                price_c,
                fetched_at
            FROM public.buyback_price_logs
            ORDER BY shop_product_id, fetched_at DESC
        )
        SELECT
            p.id            AS shop_product_id,
            p.shop_code,
            p.external_product_id,
            p.product_name,
            p.card_game,
            p.product_type,
            p.image_url,
            l.price_s,
            l.price_a,
            l.price_am,
            l.price_b,
            l.price_c,
            l.fetched_at,
            p.last_seen_at
        FROM public.buyback_shop_products p
        LEFT JOIN latest_logs l ON l.shop_product_id = p.id
        {where_clause}
        ORDER BY p.card_game, p.shop_code, p.product_name
        LIMIT :limit OFFSET :offset
        """
    )

    count_query = text(
        f"""
        SELECT COUNT(*)
        FROM public.buyback_shop_products p
        {where_clause}
        """
    )

    rows = (await db.execute(query, params)).mappings().all()
    total = (await db.execute(count_query, params)).scalar_one()

    items = [
        BuybackPriceItem(
            shop_product_id=row["shop_product_id"],
            shop_code=row["shop_code"],
            external_product_id=row["external_product_id"],
            product_name=row["product_name"],
            card_game=row["card_game"],
            product_type=row["product_type"],
            image_url=row["image_url"],
            price_s=row["price_s"],
            price_a=row["price_a"],
            price_am=row["price_am"],
            price_b=row["price_b"],
            price_c=row["price_c"],
            fetched_at=row["fetched_at"],
            last_seen_at=row["last_seen_at"],
        )
        for row in rows
    ]

    return BuybackPriceListResponse(items=items, total=total)


@router.get(
    "/buyback-prices/{shop_product_id}/history",
    response_model=BuybackPriceHistoryResponse,
    tags=["buyback-prices"],
)
async def get_price_history(
    shop_product_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365, description="取得日数"),
    db: AsyncSession = Depends(get_db),
    _tenant=Depends(get_current_tenant),
):
    """商品別の価格推移を返す。

    指定の shop_product_id の price_logs を最新 days 日分、日付降順で返す。
    存在しない shop_product_id は 404。
    """
    product_row = (
        await db.execute(
            text(
                """
                SELECT id, product_name, shop_code, card_game, product_type
                FROM public.buyback_shop_products
                WHERE id = :shop_product_id
                """
            ),
            {"shop_product_id": str(shop_product_id)},
        )
    ).mappings().first()

    if product_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定の商品が見つかりません",
        )

    logs = (
        await db.execute(
            text(
                """
                SELECT price_s, price_a, price_am, price_b, price_c, fetched_at
                FROM public.buyback_price_logs
                WHERE shop_product_id = :shop_product_id
                  AND fetched_at >= now() - make_interval(days => :days)
                ORDER BY fetched_at DESC
                """
            ),
            {"shop_product_id": str(shop_product_id), "days": days},
        )
    ).mappings().all()

    history = [
        BuybackPriceHistoryEntry(
            price_s=row["price_s"],
            price_a=row["price_a"],
            price_am=row["price_am"],
            price_b=row["price_b"],
            price_c=row["price_c"],
            fetched_at=row["fetched_at"],
        )
        for row in logs
    ]

    return BuybackPriceHistoryResponse(
        shop_product_id=shop_product_id,
        product_name=product_row["product_name"],
        shop_code=product_row["shop_code"],
        card_game=product_row["card_game"],
        product_type=product_row["product_type"],
        history=history,
    )
