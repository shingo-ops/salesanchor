"""
買取相場 API ルーター。

ADR-157: 買取相場ログ

エンドポイント:
  GET /api/v1/buyback-prices
    最新の買取価格一覧（shop_products JOIN 最新 price_log）
    クエリパラメータ: card_game / shop / product_type
    レスポンスに product_code, product_name_ja, match_status を含む

  GET /api/v1/buyback-prices/{shop_product_id}/history
    商品別の価格推移（最大 days 日分）

  GET /api/v1/buyback-prices/pending-reviews（管理者のみ）
    match_status='pending_review' の商品一覧（match_candidates 含む）

  POST /api/v1/buyback-prices/{shop_product_id}/link（管理者のみ）
    product_id を手動設定し match_status='manual' に更新

  POST /api/v1/buyback-prices/rematch（管理者のみ）
    全未紐付け商品の再マッチング実行

認証: get_current_tenant 必須（main.py で設定）
テナント分離: public スキーマ参照のみのため search_path 不要
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant, require_super_admin
from app.database import get_db
from app.tasks.buyback_scraper import fetch_all_buyback_prices

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# レスポンススキーマ
# ---------------------------------------------------------------------------


class TriggerResponse(BaseModel):
    task_id: str
    message: str


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
    product_code: str | None
    product_name_ja: str | None
    match_status: str
    swing_s: int | None = None


class BuybackPriceListResponse(BaseModel):
    items: list[BuybackPriceItem]
    total: int
    counts_by_game: dict[str, int]


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


class PendingReviewItem(BaseModel):
    shop_product_id: uuid.UUID
    shop_code: str
    product_name: str
    card_game: str
    match_candidates: list[dict]


class PendingReviewListResponse(BaseModel):
    items: list[PendingReviewItem]
    total: int


class LinkProductRequest(BaseModel):
    product_id: int | None


class LinkProductResponse(BaseModel):
    shop_product_id: uuid.UUID
    product_id: int | None
    match_status: str


class RematchResponse(BaseModel):
    auto: int
    pending_review: int
    unmatched: int
    skipped: int


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.post(
    "/buyback-prices/trigger",
    response_model=TriggerResponse,
    status_code=202,
    tags=["buyback-prices"],
    dependencies=[Depends(require_super_admin)],
)
async def trigger_fetch() -> TriggerResponse:
    """買取価格の手動取得を開始する（スーパー管理者のみ）。"""
    result = fetch_all_buyback_prices.delay()
    return TriggerResponse(
        task_id=result.id,
        message="買取価格取得タスクを開始しました",
    )


@router.get(
    "/buyback-prices",
    response_model=BuybackPriceListResponse,
    tags=["buyback-prices"],
)
async def list_buyback_prices(
    card_game: str | None = Query(default=None, description="カードゲーム種別 (例: pokemon)"),
    shop: str | None = Query(default=None, description="買取店コード (例: shinsoku, homura)"),
    product_type: str | None = Query(default=None, description="商品種別 (例: BOX, CARTON)"),
    q: str | None = Query(default=None, description="商品名検索"),
    swing_days: int | None = Query(default=None, description="価格変動の計算期間（日数）", ge=1, le=365),
    min_swing: int | None = Query(default=None, description="最小変動額（円）", ge=0),
    limit: int = Query(default=50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(default=0, ge=0, description="オフセット"),
    sort: str = Query(default="price_s", description="ソート列"),
    order: str = Query(default="desc", description="ソート順 (asc/desc)"),
    db: AsyncSession = Depends(get_db),
    _tenant=Depends(get_current_tenant),
):
    """最新の買取価格一覧を返す。

    buyback_shop_products と最新の buyback_price_logs を JOIN して返す。
    フィルタ: card_game / shop / product_type
    """
    # ソート列ホワイトリスト（SQLインジェクション対策）
    _SORT_WHITELIST = {
        "price_s": "l.price_s",
        "price_a": "l.price_a",
        "price_b": "l.price_b",
        "product_name": "p.product_name",
        "last_seen_at": "p.last_seen_at",
        "swing_s": "COALESCE(sw.swing_s, 0)",
    }
    sort_col = _SORT_WHITELIST.get(sort, "l.price_s")
    sort_dir = "ASC" if order == "asc" else "DESC"

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

    if q is not None:
        conditions.append("p.product_name ILIKE :q")
        params["q"] = f"%{q}%"

    if swing_days is not None:
        params["swing_days"] = swing_days

    if min_swing is not None:
        conditions.append("COALESCE(sw.swing_s, 0) >= :min_swing")
        params["min_swing"] = min_swing

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # price_swing CTE は swing_days が指定された場合のみ追加
    if swing_days is not None:
        swing_cte = """, price_swing AS (
            SELECT shop_product_id,
                   COALESCE(MAX(price_s), 0) - COALESCE(MIN(price_s), 0) AS swing_s
            FROM public.buyback_price_logs
            WHERE fetched_at >= now() - :swing_days * interval '1 day'
            GROUP BY shop_product_id
        )"""
        swing_join = "LEFT JOIN price_swing sw ON sw.shop_product_id = p.id"
        swing_select = "COALESCE(sw.swing_s, 0) AS swing_s,"
    else:
        swing_cte = ""
        swing_join = ""
        swing_select = "NULL AS swing_s,"

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
        ){swing_cte}
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
            p.last_seen_at,
            pr.product_code,
            pr.name         AS product_name_ja,
            p.match_status,
            {swing_select}
            0 AS _dummy
        FROM public.buyback_shop_products p
        LEFT JOIN latest_logs l ON l.shop_product_id = p.id
        LEFT JOIN public.products pr ON pr.id = p.product_id
        {swing_join}
        {where_clause}
        ORDER BY {sort_col} {sort_dir} NULLS LAST
        LIMIT :limit OFFSET :offset
        """
    )

    if swing_cte:
        count_query = text(
            f"""
            WITH{swing_cte.lstrip(", ")}
            SELECT COUNT(*)
            FROM public.buyback_shop_products p
            {swing_join}
            {where_clause}
            """
        )
    else:
        count_query = text(
            f"""
            SELECT COUNT(*)
            FROM public.buyback_shop_products p
            {where_clause}
            """
        )

    rows = (await db.execute(query, params)).mappings().all()
    total = (await db.execute(count_query, params)).scalar_one()

    # カードゲーム別件数（タブ用 — shop / product_type / q / swing フィルタを反映、card_game フィルタは除外）
    count_conditions = []
    count_params: dict = {}
    if shop is not None:
        count_conditions.append("p.shop_code = :count_shop")
        count_params["count_shop"] = shop
    if product_type is not None:
        count_conditions.append("p.product_type = :count_product_type")
        count_params["count_product_type"] = product_type
    if q is not None:
        count_conditions.append("p.product_name ILIKE :count_q")
        count_params["count_q"] = f"%{q}%"
    if min_swing is not None:
        count_conditions.append("COALESCE(sw.swing_s, 0) >= :count_min_swing")
        count_params["count_min_swing"] = min_swing
    if swing_days is not None:
        count_params["count_swing_days"] = swing_days
    count_where = ("WHERE " + " AND ".join(count_conditions)) if count_conditions else ""
    if swing_days is not None:
        game_counts_swing_cte = """WITH game_price_swing AS (
            SELECT shop_product_id,
                   COALESCE(MAX(price_s), 0) - COALESCE(MIN(price_s), 0) AS swing_s
            FROM public.buyback_price_logs
            WHERE fetched_at >= now() - :count_swing_days * interval '1 day'
            GROUP BY shop_product_id
        )"""
        game_counts_swing_join = "LEFT JOIN game_price_swing sw ON sw.shop_product_id = p.id"
        game_counts_query = text(f"""
            {game_counts_swing_cte}
            SELECT p.card_game, COUNT(*) as cnt
            FROM public.buyback_shop_products p
            {game_counts_swing_join}
            {count_where}
            GROUP BY p.card_game
        """)
    else:
        game_counts_query = text(f"""
            SELECT p.card_game, COUNT(*) as cnt
            FROM public.buyback_shop_products p
            {count_where}
            GROUP BY p.card_game
        """)
    game_counts_rows = (await db.execute(game_counts_query, count_params)).mappings().all()
    counts_by_game = {row["card_game"]: row["cnt"] for row in game_counts_rows}

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
            product_code=row["product_code"],
            product_name_ja=row["product_name_ja"],
            match_status=row["match_status"],
            swing_s=row["swing_s"] if swing_days is not None else None,
        )
        for row in rows
    ]

    return BuybackPriceListResponse(items=items, total=total, counts_by_game=counts_by_game)


@router.get(
    "/buyback-prices/by-product",
    tags=["buyback-prices"],
    dependencies=[Depends(require_super_admin)],
)
async def list_by_product(
    category: str | None = Query(None, description="商品カテゴリ (例: pokemon)"),
    q: str | None = Query(None, description="商品名検索"),
    swing_days: int | None = Query(None, description="価格変動の計算期間（日数）", ge=1, le=365),
    min_swing: int | None = Query(None, description="最小変動額（円）", ge=0),
    limit: int = Query(50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(0, ge=0, description="オフセット"),
    db: AsyncSession = Depends(get_db),
):
    """自社商品マスタ軸の買取価格一覧。category / q / swing フィルタ、release_date DESC。

    商品マスタを軸に各店舗（homura/shinsoku）の最新買取価格を横並びで返す。
    LATERAL JOIN で各店舗の最新 price_log を効率的に取得。
    """
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))

    # カテゴリ別件数（タブ用 — category フィルタは除外、q/swing は反映）
    cat_count_conditions: list[str] = ["bsp.product_id IS NOT NULL"]
    cat_count_params: dict = {}
    if q is not None:
        cat_count_conditions.append("p.name ILIKE :cat_q")
        cat_count_params["cat_q"] = f"%{q}%"
    if swing_days is not None and min_swing is not None:
        cat_count_params["cat_swing_days"] = swing_days
        cat_count_params["cat_min_swing"] = min_swing
        cat_counts_query = text(f"""
            WITH product_swing AS (
                SELECT bsp2.product_id,
                       COALESCE(MAX(l2.price_s), 0) - COALESCE(MIN(l2.price_s), 0) AS swing_s
                FROM public.buyback_price_logs l2
                JOIN public.buyback_shop_products bsp2 ON bsp2.id = l2.shop_product_id
                WHERE l2.fetched_at >= now() - :cat_swing_days * interval '1 day'
                  AND bsp2.product_id IS NOT NULL
                GROUP BY bsp2.product_id
            )
            SELECT p.category, count(DISTINCT p.id)
            FROM public.products p
            JOIN public.buyback_shop_products bsp ON bsp.product_id = p.id
            LEFT JOIN product_swing psw ON psw.product_id = p.id
            WHERE {" AND ".join(cat_count_conditions)}
              AND COALESCE(psw.swing_s, 0) >= :cat_min_swing
            GROUP BY p.category
            ORDER BY count(DISTINCT p.id) DESC
        """)
    else:
        cat_counts_query = text(f"""
            SELECT p.category, count(DISTINCT p.id)
            FROM public.products p
            JOIN public.buyback_shop_products bsp ON bsp.product_id = p.id
            WHERE {" AND ".join(cat_count_conditions)}
            GROUP BY p.category
            ORDER BY count(DISTINCT p.id) DESC
        """)
    counts_result = await db.execute(cat_counts_query, cat_count_params)
    counts_by_category = {row[0]: row[1] for row in counts_result}

    # 動的条件
    extra_conditions: list[str] = []
    params: dict = {"limit": limit, "offset": offset}

    if category:
        extra_conditions.append("p.category = :category")
        params["category"] = category

    if q is not None:
        extra_conditions.append("p.name ILIKE :q")
        params["q"] = f"%{q}%"

    if swing_days is not None:
        params["swing_days"] = swing_days

    if min_swing is not None:
        extra_conditions.append("COALESCE(psw.swing_s, 0) >= :min_swing")
        params["min_swing"] = min_swing

    extra_where = (" AND " + " AND ".join(extra_conditions)) if extra_conditions else ""

    # product_swing CTE は swing_days が指定された場合のみ
    if swing_days is not None:
        bp_swing_cte = """WITH product_swing AS (
            SELECT bsp.product_id,
                   COALESCE(MAX(l.price_s), 0) - COALESCE(MIN(l.price_s), 0) AS swing_s
            FROM public.buyback_price_logs l
            JOIN public.buyback_shop_products bsp ON bsp.id = l.shop_product_id
            WHERE l.fetched_at >= now() - :swing_days * interval '1 day'
              AND bsp.product_id IS NOT NULL
            GROUP BY bsp.product_id
        )"""
        bp_swing_join = "LEFT JOIN product_swing psw ON psw.product_id = p.id"
        bp_swing_select = "COALESCE(psw.swing_s, 0) AS swing_s,"
    else:
        bp_swing_cte = ""
        bp_swing_join = ""
        bp_swing_select = "NULL AS swing_s,"

    query = text(f"""
        {bp_swing_cte}
        SELECT
            p.id,
            p.product_code,
            p.name,
            p.category,
            p.release_date,
            p.image_url,
            homura.price_s   AS homura_price_s,
            homura.price_a   AS homura_price_a,
            homura.price_b   AS homura_price_b,
            homura.shop_product_id AS homura_shop_product_id,
            homura.product_name    AS homura_product_name,
            shinsoku.price_s AS shinsoku_price_s,
            shinsoku.price_a AS shinsoku_price_a,
            shinsoku.price_b AS shinsoku_price_b,
            shinsoku.shop_product_id AS shinsoku_shop_product_id,
            shinsoku.product_name    AS shinsoku_product_name,
            {bp_swing_select}
            0 AS _dummy
        FROM public.products p
        LEFT JOIN LATERAL (
            SELECT bsp.id AS shop_product_id, bsp.product_name,
                   l.price_s, l.price_a, l.price_b
            FROM public.buyback_shop_products bsp
            JOIN public.buyback_price_logs l ON l.shop_product_id = bsp.id
            WHERE bsp.product_id = p.id AND bsp.shop_code = 'homura'
            ORDER BY l.fetched_at DESC
            LIMIT 1
        ) homura ON true
        LEFT JOIN LATERAL (
            SELECT bsp.id AS shop_product_id, bsp.product_name,
                   l.price_s, l.price_a, l.price_b
            FROM public.buyback_shop_products bsp
            JOIN public.buyback_price_logs l ON l.shop_product_id = bsp.id
            WHERE bsp.product_id = p.id AND bsp.shop_code = 'shinsoku'
            ORDER BY l.fetched_at DESC
            LIMIT 1
        ) shinsoku ON true
        {bp_swing_join}
        WHERE p.id IN (
            SELECT DISTINCT product_id FROM public.buyback_shop_products
            WHERE product_id IS NOT NULL
        )
        {extra_where}
        ORDER BY p.release_date DESC NULLS LAST, p.product_code
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(query, params)
    rows = result.fetchall()

    if swing_days is not None:
        count_query = text(f"""
            WITH product_swing AS (
                SELECT bsp.product_id,
                       COALESCE(MAX(l.price_s), 0) - COALESCE(MIN(l.price_s), 0) AS swing_s
                FROM public.buyback_price_logs l
                JOIN public.buyback_shop_products bsp ON bsp.id = l.shop_product_id
                WHERE l.fetched_at >= now() - :swing_days * interval '1 day'
                  AND bsp.product_id IS NOT NULL
                GROUP BY bsp.product_id
            )
            SELECT count(DISTINCT p.id)
            FROM public.products p
            JOIN public.buyback_shop_products bsp ON bsp.product_id = p.id
            LEFT JOIN product_swing psw ON psw.product_id = p.id
            WHERE bsp.product_id IS NOT NULL
            {extra_where}
        """)
    else:
        count_query = text(f"""
            SELECT count(DISTINCT p.id)
            FROM public.products p
            JOIN public.buyback_shop_products bsp ON bsp.product_id = p.id
            WHERE bsp.product_id IS NOT NULL
            {extra_where}
        """)
    total = (await db.execute(count_query, params)).scalar() or 0

    items = []
    for r in rows:
        items.append({
            "product_id": r[0],
            "product_code": r[1],
            "name_ja": r[2],
            "category": r[3],
            "release_date": r[4].isoformat() if r[4] else None,
            "image_url": r[5],
            "homura_price_s": r[6],
            "homura_price_a": r[7],
            "homura_price_b": r[8],
            "homura_shop_product_id": str(r[9]) if r[9] else None,
            "homura_product_name": r[10],
            "shinsoku_price_s": r[11],
            "shinsoku_price_a": r[12],
            "shinsoku_price_b": r[13],
            "shinsoku_shop_product_id": str(r[14]) if r[14] else None,
            "shinsoku_product_name": r[15],
            "swing_s": r[16] if swing_days is not None else None,
        })

    return {
        "items": items,
        "total": total,
        "counts_by_category": counts_by_category,
    }


@router.get(
    "/buyback-prices/pending-reviews",
    response_model=PendingReviewListResponse,
    tags=["buyback-prices"],
    dependencies=[Depends(require_super_admin)],
)
async def list_pending_reviews(
    limit: int = Query(default=50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(default=0, ge=0, description="オフセット"),
    db: AsyncSession = Depends(get_db),
):
    """match_status='pending_review' の商品一覧を返す（スーパー管理者のみ）。

    match_candidates の内容（候補リスト）も含む。
    """
    rows = (
        await db.execute(
            text("""
                SELECT id, shop_code, product_name, card_game, match_candidates
                FROM public.buyback_shop_products
                WHERE match_status = 'pending_review'
                ORDER BY id
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        )
    ).mappings().all()

    total = (
        await db.execute(
            text("""
                SELECT COUNT(*)
                FROM public.buyback_shop_products
                WHERE match_status = 'pending_review'
            """)
        )
    ).scalar_one()

    items = [
        PendingReviewItem(
            shop_product_id=row["id"],
            shop_code=row["shop_code"],
            product_name=row["product_name"],
            card_game=row["card_game"],
            match_candidates=row["match_candidates"] or [],
        )
        for row in rows
    ]

    return PendingReviewListResponse(items=items, total=total)


@router.post(
    "/buyback-prices/rematch",
    response_model=RematchResponse,
    tags=["buyback-prices"],
    dependencies=[Depends(require_super_admin)],
)
async def rematch_products(
    db: AsyncSession = Depends(get_db),
):
    """全未紐付け商品を再マッチングする（スーパー管理者のみ）。

    キーワード更新後に手動で再マッチングを走らせる用途。
    match_status が 'unmatched' または 'pending_review' の商品が対象。
    """
    from app.services.buyback_scraper.product_matcher import match_buyback_products

    try:
        stats = await match_buyback_products(db)
    except Exception as exc:
        logger.exception("buyback_prices.rematch: エラー")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"再マッチング中にエラーが発生しました: {exc}",
        ) from exc

    return RematchResponse(**stats)


@router.get(
    "/buyback-prices/by-product/{product_id}/history",
    tags=["buyback-prices"],
    dependencies=[Depends(require_super_admin)],
)
async def product_price_history(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """自社商品IDに紐付く全店舗の価格推移を返す。"""

    result = await db.execute(text("""
        SELECT
            bsp.shop_code,
            l.price_s, l.price_a, l.price_am, l.price_b, l.price_c,
            l.fetched_at
        FROM public.buyback_price_logs l
        JOIN public.buyback_shop_products bsp ON bsp.id = l.shop_product_id
        WHERE bsp.product_id = :product_id
          AND l.fetched_at >= now() - make_interval(days => :days)
        ORDER BY l.fetched_at ASC
    """), {"product_id": product_id, "days": days})

    rows = result.fetchall()

    # 店舗別にグループ化
    history: dict[str, list] = {}
    for r in rows:
        shop = r[0]
        entry = {
            "price_s": r[1],
            "price_a": r[2],
            "price_am": r[3],
            "price_b": r[4],
            "price_c": r[5],
            "fetched_at": r[6].isoformat() if r[6] else None,
        }
        history.setdefault(shop, []).append(entry)

    return {"history": history}


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
                ORDER BY fetched_at ASC
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


@router.post(
    "/buyback-prices/{shop_product_id}/link",
    response_model=LinkProductResponse,
    tags=["buyback-prices"],
    dependencies=[Depends(require_super_admin)],
)
async def link_product(
    shop_product_id: uuid.UUID,
    body: LinkProductRequest,
    db: AsyncSession = Depends(get_db),
):
    """buy取商品に自社マスタ商品を手動紐付けする（スーパー管理者のみ）。

    product_id を指定すると match_status='manual' に更新する。
    product_id=null を指定すると match_status='unmatched' に戻す。
    存在しない shop_product_id は 404。
    """
    # 対象レコードの存在確認
    exists = (
        await db.execute(
            text("SELECT 1 FROM public.buyback_shop_products WHERE id = :id"),
            {"id": str(shop_product_id)},
        )
    ).scalar()

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定の商品が見つかりません",
        )

    # product_id が指定された場合、products テーブルに存在するか確認
    if body.product_id is not None:
        product_exists = (
            await db.execute(
                text("SELECT 1 FROM public.products WHERE id = :pid"),
                {"pid": body.product_id},
            )
        ).scalar()
        if not product_exists:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"product_id={body.product_id} が public.products に存在しません",
            )

    new_status = "manual" if body.product_id is not None else "unmatched"

    # public スキーマへの write には operator フラグが必要
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))
    await db.execute(
        text("""
            UPDATE public.buyback_shop_products
            SET product_id = :pid,
                match_status = :match_status
            WHERE id = :id
        """),
        {
            "id": str(shop_product_id),
            "pid": body.product_id,
            "match_status": new_status,
        },
    )
    await db.commit()

    logger.info(
        "buyback_prices.link: shop_product_id=%s product_id=%s match_status=%s",
        shop_product_id,
        body.product_id,
        new_status,
    )

    return LinkProductResponse(
        shop_product_id=shop_product_id,
        product_id=body.product_id,
        match_status=new_status,
    )
