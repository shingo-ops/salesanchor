"""inventory_movements 不変条件検証ヘルパ。

2026-10-02: Discord 在庫取り込み機能の削除に伴い、apply_inbound_items
（Sprint 6 F6 + Sprint 9 F9 + Sprint 11 F11 の承認反映ロジック、唯一の呼び出し元は
削除された backend/app/routers/parse_review.py の approve エンドポイント）と、
それだけに使われていた補助コード（_upsert_inventory_offer / MovementResult /
ApplyResult / _CENTRAL_TENANT_SENTINEL / _OFFER_EXPIRY_HOURS）を削除した。
`public.inventory_movements` テーブル自体・`verify_invariant_for_product` の
不変条件検証（AC6.6: SUM(delta_qty) == products.stock_quantity）は他機能と無関係に
独立して有用なため維持する。経緯: docs/handoff/remove-discord-inventory-parse/design.md
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class InventoryApplyError(Exception):
    """承認反映の業務エラー（product 不存在等）。"""


async def verify_invariant_for_product(
    db: AsyncSession, *, product_id: int
) -> tuple[int, int]:
    """AC6.6 不変条件検証ヘルパ（テスト用）。

    Returns:
        (stock_quantity, SUM(delta_qty)) を返す。呼び出し側で
        `assert a == b` するかロギングする。
    """
    row = (
        (
            await db.execute(
                text(
                    "SELECT COALESCE(p.stock_quantity, 0) AS sq, "
                    "       COALESCE((SELECT SUM(delta_qty) "
                    "                   FROM public.inventory_movements "
                    "                  WHERE product_id = p.id), 0) AS dsum "
                    "  FROM public.products p WHERE p.id = :pid"
                ),
                {"pid": product_id},
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise InventoryApplyError(f"product_id={product_id} が見つかりません")
    return int(row["sq"]), int(row["dsum"])


__all__ = [
    "InventoryApplyError",
    "verify_invariant_for_product",
]
