"""
シンソク（shinsoku-tcg.com）買取価格取得サービス。

ADR-157: 買取相場ログ

取得フロー:
  1. GET /api/brands?context=yuso でブランド一覧を取得
  2. 各ブランド × type(BOX/CARTON/PACK/UNOPENED_PROMO) × 全ページを巡回
  3. 商品ごとに save_product_and_price を呼ぶ
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .base import _build_client, rate_limited_get, save_product_and_price

logger = logging.getLogger(__name__)

_BASE_URL = "https://shinsoku-tcg.com/api"

# 取得対象の商品種別（NORMAL / PSA / UNOPENED_OTHER は除外）
_TARGET_TYPES = ("BOX", "CARTON", "PACK", "UNOPENED_PROMO")

# シンソクのブランド名 → 内部 card_game 識別子
_BRAND_TO_GAME: dict[str, str] = {
    "ポケモン": "pokemon",
    "ワンピース": "onepiece",
    "遊戯王": "yugioh",
    "ドラゴンボール": "dragonball",
    "ヴァイスシュヴァルツ": "weiss",
}


async def fetch_shinsoku_prices(db: AsyncSession) -> None:
    """シンソクの全ブランド・全タイプの買取価格を取得して DB に保存する。

    HTTP エラー時はログを出力して次のブランド/タイプへ続行する（非致命的）。
    """
    logger.info("[shinsoku] 買取価格取得開始")
    fetched_at = datetime.now(tz=timezone.utc)

    async with _build_client() as client:
        brands = await _fetch_brands(client)
        if not brands:
            logger.warning("[shinsoku] ブランド一覧が空でした。取得を中止します。")
            return

        for brand in brands:
            brand_name: str = brand.get("name", "")
            card_game = _BRAND_TO_GAME.get(brand_name)
            if card_game is None:
                logger.debug("[shinsoku] 未知のブランドをスキップ: %s", brand_name)
                continue

            for item_type in _TARGET_TYPES:
                try:
                    await _fetch_brand_type(
                        client=client,
                        db=db,
                        brand_name=brand_name,
                        card_game=card_game,
                        item_type=item_type,
                        fetched_at=fetched_at,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "[shinsoku] ブランド=%s type=%s の取得中に予期しないエラー",
                        brand_name,
                        item_type,
                    )

    logger.info("[shinsoku] 買取価格取得完了")


async def _fetch_brands(client: httpx.AsyncClient) -> list[dict]:
    """ブランド一覧を取得する。失敗時は空リストを返す。"""
    url = f"{_BASE_URL}/brands?context=yuso"
    try:
        response = await rate_limited_get(client, url)
        response.raise_for_status()
        data = response.json()
        brands: list[dict] = data.get("data", [])
        logger.info("[shinsoku] ブランド一覧取得: %d 件", len(brands))
        return brands
    except httpx.HTTPError as exc:
        logger.error("[shinsoku] ブランド一覧取得失敗: %s", exc)
        return []


async def _fetch_brand_type(
    client: httpx.AsyncClient,
    db: AsyncSession,
    brand_name: str,
    card_game: str,
    item_type: str,
    fetched_at: datetime,
) -> None:
    """指定ブランド・タイプの全ページを巡回して商品を保存する。"""
    page = 1
    total_saved = 0

    while True:
        url = (
            f"{_BASE_URL}/items"
            f"?postal_only=true&sort=price_desc"
            f"&type={item_type}&brand={brand_name}&page={page}&limit=40"
        )
        try:
            response = await rate_limited_get(client, url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[shinsoku] HTTP エラー brand=%s type=%s page=%d: %s",
                brand_name, item_type, page, exc,
            )
            break
        except httpx.HTTPError as exc:
            logger.warning(
                "[shinsoku] リクエストエラー brand=%s type=%s page=%d: %s",
                brand_name, item_type, page, exc,
            )
            break

        payload = response.json()
        if not payload.get("ok"):
            logger.warning(
                "[shinsoku] ok=false brand=%s type=%s page=%d: %s",
                brand_name, item_type, page, payload,
            )
            break

        items: list[dict] = payload.get("data", {}).get("items", [])
        if not items:
            break

        for item in items:
            await _save_item(db=db, item=item, card_game=card_game, fetched_at=fetched_at)
            total_saved += 1

        has_more: bool = payload.get("data", {}).get("has_more", False)
        if not has_more:
            break

        page += 1

    logger.debug(
        "[shinsoku] brand=%s type=%s: %d 件保存", brand_name, item_type, total_saved
    )


async def _save_item(
    db: AsyncSession,
    item: dict,
    card_game: str,
    fetched_at: datetime,
) -> None:
    """単一商品を DB に保存する。"""
    external_id: str = item.get("item_id", "")
    name: str = item.get("name", "")
    item_type: str | None = item.get("type")
    image_url: str | None = item.get("image_url_public")

    prices = {
        "price_s": item.get("postal_purchase_price_s"),
        "price_a": item.get("postal_purchase_price_a"),
        "price_am": item.get("postal_purchase_price_am"),
        "price_b": item.get("postal_purchase_price_b"),
        "price_c": item.get("postal_purchase_price_c"),
    }

    if not external_id or not name:
        logger.debug("[shinsoku] item_id または name が空のためスキップ: %s", item)
        return

    await save_product_and_price(
        db=db,
        shop_code="shinsoku",
        external_id=external_id,
        name=name,
        card_game=card_game,
        product_type=item_type,
        image_url=image_url,
        prices=prices,
        fetched_at=fetched_at,
    )
