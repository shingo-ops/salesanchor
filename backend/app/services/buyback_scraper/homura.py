"""
買取ホムラ（kaitori-homura.com）買取価格取得サービス。

ADR-157: 買取相場ログ

取得フロー:
  1. 各サブカテゴリ × 全ページを HTTP リクエストで取得
  2. BeautifulSoup で商品名・価格・商品 ID をパース
  3. save_product_and_price を呼ぶ

注意:
  - SSR HTML のスクレイピングのため、サイト構造変更で壊れる可能性あり
  - 件数 0 件を異常とみなして警告ログを出力する
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from .base import _build_client, rate_limited_get, save_product_and_price

logger = logging.getLogger(__name__)

_BASE_URL = "https://kaitori-homura.com"

# サブカテゴリ ID → (card_game, product_type_label)
# 157(シングルカード)は除外
_SUBCATEGORIES: dict[int, tuple[str, str]] = {
    # ポケモン
    128: ("pokemon", "BOX_SHRINK"),       # シュリンク有BOX
    129: ("pokemon", "BOX_NO_SHRINK"),    # シュリンク無BOX
    130: ("pokemon", "SPECIAL_SET"),      # スペシャルセット
    131: ("pokemon", "CARTON"),           # カートン
    183: ("pokemon", "PACK"),             # バラパック
    # ワンピース
    132: ("onepiece", "BOX"),
    133: ("onepiece", "CARTON"),
    160: ("onepiece", "OTHER"),
    # 遊戯王
    159: ("yugioh", "BOX"),
    172: ("yugioh", "CARTON"),
    # ドラゴンボール
    171: ("dragonball", "BOX"),
    # ロルカナ
    189: ("lorcana", "BOX"),
    190: ("lorcana", "CARTON"),
}

async def fetch_homura_prices(db: AsyncSession) -> None:
    """買取ホムラの全サブカテゴリの買取価格を取得して DB に保存する。

    パース失敗・件数 0 件は警告ログを出力するが処理は続行する。
    """
    logger.info("[homura] 買取価格取得開始")
    fetched_at = datetime.now(tz=timezone.utc)

    async with _build_client() as client:
        for sub_cat_id, (card_game, product_type) in _SUBCATEGORIES.items():
            try:
                await _fetch_subcategory(
                    client=client,
                    db=db,
                    sub_cat_id=sub_cat_id,
                    card_game=card_game,
                    product_type=product_type,
                    fetched_at=fetched_at,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "[homura] サブカテゴリ=%d の取得中に予期しないエラー", sub_cat_id
                )

    logger.info("[homura] 買取価格取得完了")


async def _fetch_subcategory(
    client: httpx.AsyncClient,
    db: AsyncSession,
    sub_cat_id: int,
    card_game: str,
    product_type: str,
    fetched_at: datetime,
) -> None:
    """指定サブカテゴリの全ページを巡回して商品を保存する。"""
    page = 1
    total_saved = 0

    while True:
        url = (
            f"{_BASE_URL}/products"
            f"?q[product_sub_category_id_eq]={sub_cat_id}"
            f"&q[product_sub_category_product_category_id_eq]=14"
            f"&page={page}"
        )
        try:
            response = await rate_limited_get(client, url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[homura] HTTP エラー sub_cat_id=%d page=%d: %s", sub_cat_id, page, exc
            )
            break
        except httpx.HTTPError as exc:
            logger.warning(
                "[homura] リクエストエラー sub_cat_id=%d page=%d: %s", sub_cat_id, page, exc
            )
            break

        items = _parse_products(response.text)

        if page == 1 and not items:
            logger.warning(
                "[homura] sub_cat_id=%d page=1 で商品が 0 件。サイト構造変更の可能性あり。",
                sub_cat_id,
            )
            break

        if not items:
            # 2 ページ目以降で 0 件 → 最終ページ
            break

        for product in items:
            await _save_product(
                db=db,
                product=product,
                card_game=card_game,
                product_type=product_type,
                fetched_at=fetched_at,
            )
            total_saved += 1

        # 次ページが存在するか確認（pagination の "次へ" リンクで判断）
        has_next = _has_next_page(response.text)
        if not has_next:
            break

        page += 1

    logger.debug(
        "[homura] sub_cat_id=%d card_game=%s type=%s: %d 件保存",
        sub_cat_id, card_game, product_type, total_saved,
    )


def _parse_products(html: str) -> list[dict]:
    """HTML から商品一覧をパースする。

    カート追加ボタンの data 属性から商品情報を取得する。
    各ボタンには data-product-id / data-product-name / data-product-price が含まれる。

    Returns:
        [{"external_id": str, "name": str, "price": int | None}]
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    buttons = soup.find_all("button", attrs={"data-product-id": True})

    for btn in buttons:
        external_id = btn.get("data-product-id", "")
        name = btn.get("data-product-name", "")
        if not external_id or not name:
            continue

        price: int | None = None
        price_str = btn.get("data-product-price")
        if price_str:
            try:
                price = int(price_str)
            except ValueError:
                pass

        # 重複 external_id は最初の 1 件のみ
        if any(r["external_id"] == external_id for r in results):
            continue

        results.append({"external_id": external_id, "name": name, "price": price})

    return results


def _has_next_page(html: str) -> bool:
    """ページネーションに「次へ」リンクが存在するか確認する。"""
    soup = BeautifulSoup(html, "lxml")
    # 一般的な "次へ" / "Next" / rel="next" リンクを確認
    next_link = soup.find("a", {"rel": "next"})
    if next_link:
        return True
    # テキストで探す
    for link in soup.find_all("a"):
        text = link.get_text(strip=True)
        if text in ("次へ", "次のページ", "Next", ">", "»"):
            return True
    return False


async def _save_product(
    db: AsyncSession,
    product: dict,
    card_game: str,
    product_type: str,
    fetched_at: datetime,
) -> None:
    """単一商品を DB に保存する。"""
    external_id: str = product["external_id"]
    name: str = product["name"]
    price: int | None = product.get("price")

    prices = {
        "price_s": price,  # 買取ホムラは単一価格 → price_s に格納
        "price_a": None,
        "price_am": None,
        "price_b": None,
        "price_c": None,
    }

    await save_product_and_price(
        db=db,
        shop_code="homura",
        external_id=external_id,
        name=name,
        card_game=card_game,
        product_type=product_type,
        image_url=None,
        prices=prices,
        fetched_at=fetched_at,
    )
