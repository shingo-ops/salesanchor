"""
買取スクレイパー共通基底クラス。

ADR-157: 買取相場ログ

提供機能:
- httpx.AsyncClient の共通設定（User-Agent / タイムアウト）
- リクエスト間レート制限（1.5 秒 sleep）
- DB への商品 UPSERT + 価格変化時のみ price_log 追記
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_USER_AGENT = "SalesAnchor-PriceLogger/1.0 (+https://salesanchor.jp)"
_REQUEST_TIMEOUT = 30.0  # 秒
_RATE_LIMIT_SLEEP = 1.5  # リクエスト間の待機秒数


def _build_client() -> httpx.AsyncClient:
    """共通 httpx クライアントを生成する。"""
    return httpx.AsyncClient(
        headers={"User-Agent": _USER_AGENT},
        timeout=_REQUEST_TIMEOUT,
        follow_redirects=True,
    )


async def save_product_and_price(
    db: AsyncSession,
    shop_code: str,
    external_id: str,
    name: str,
    card_game: str,
    product_type: str | None,
    image_url: str | None,
    prices: dict[str, int | None],
    fetched_at: datetime,
) -> None:
    """商品を UPSERT し、前回から価格が変化した場合のみ price_log を追記する。

    Args:
        db: 非同期 DB セッション（public スキーマを参照できる状態であること）
        shop_code: 買取店識別コード（例: "shinsoku", "homura"）
        external_id: 外部商品 ID
        name: 商品名
        card_game: カードゲーム種別（例: "pokemon", "onepiece"）
        product_type: 商品種別（例: "BOX", "CARTON"）
        image_url: 商品画像 URL
        prices: {"price_s": int|None, "price_a": int|None, "price_am": int|None,
                 "price_b": int|None, "price_c": int|None}
        fetched_at: 取得日時（UTC）
    """
    # operator コンテキストを設定して public スキーマへの書き込みを許可する
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))

    # 商品マスタ UPSERT
    result = await db.execute(
        text(
            """
            INSERT INTO public.buyback_shop_products
                (shop_code, external_product_id, product_name, card_game, product_type,
                 image_url, last_seen_at)
            VALUES
                (:shop_code, :external_id, :name, :card_game, :product_type,
                 :image_url, :last_seen_at)
            ON CONFLICT (shop_code, external_product_id)
            DO UPDATE SET
                product_name = EXCLUDED.product_name,
                card_game    = EXCLUDED.card_game,
                product_type = EXCLUDED.product_type,
                image_url    = COALESCE(EXCLUDED.image_url, public.buyback_shop_products.image_url),
                last_seen_at = EXCLUDED.last_seen_at
            RETURNING id
            """
        ),
        {
            "shop_code": shop_code,
            "external_id": external_id,
            "name": name,
            "card_game": card_game,
            "product_type": product_type,
            "image_url": image_url,
            "last_seen_at": fetched_at,
        },
    )
    shop_product_id = result.scalar_one()

    # 前回のログを取得して価格変化を確認する
    last_row = await db.execute(
        text(
            """
            SELECT price_s, price_a, price_am, price_b, price_c
            FROM public.buyback_price_logs
            WHERE shop_product_id = :shop_product_id
            ORDER BY fetched_at DESC
            LIMIT 1
            """
        ),
        {"shop_product_id": shop_product_id},
    )
    last = last_row.mappings().first()

    price_s = prices.get("price_s")
    price_a = prices.get("price_a")
    price_am = prices.get("price_am")
    price_b = prices.get("price_b")
    price_c = prices.get("price_c")

    # 前回レコードなし or いずれかの価格が変化した場合のみ追記
    if last is None or (
        last["price_s"] != price_s
        or last["price_a"] != price_a
        or last["price_am"] != price_am
        or last["price_b"] != price_b
        or last["price_c"] != price_c
    ):
        await db.execute(
            text(
                """
                INSERT INTO public.buyback_price_logs
                    (shop_product_id, price_s, price_a, price_am, price_b, price_c, fetched_at)
                VALUES
                    (:shop_product_id, :price_s, :price_a, :price_am, :price_b, :price_c,
                     :fetched_at)
                """
            ),
            {
                "shop_product_id": shop_product_id,
                "price_s": price_s,
                "price_a": price_a,
                "price_am": price_am,
                "price_b": price_b,
                "price_c": price_c,
                "fetched_at": fetched_at,
            },
        )

    await db.commit()


async def rate_limited_get(
    client: httpx.AsyncClient,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """レート制限付き GET リクエスト。

    リクエスト前に _RATE_LIMIT_SLEEP 秒待機する。
    """
    await asyncio.sleep(_RATE_LIMIT_SLEEP)
    return await client.get(url, **kwargs)
