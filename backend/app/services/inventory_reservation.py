"""
A在庫（own_inventory）の引当・解除・発送確定サービス。
B在庫（public.inventory）は引当処理をスキップ。

ADR-SA-04: 2段階引当
  physical_qty: 物理在庫数（実際に棚にある数）
  reserved_qty: 引当済み数（受注確定で増加、発送完了で減少）
  available_qty: 利用可能数 = physical_qty - reserved_qty（GENERATED ALWAYS AS）

変更履歴:
  2026-06-04: 初版作成（SA-Foundation PR#6）
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def reserve_qty(
    db: AsyncSession,
    own_inventory_id: int,
    qty: int,
    tenant_id: int,
) -> None:
    """qty を引当。available_qty < qty の場合は ValueError を raise。

    Args:
        db: データベースセッション
        own_inventory_id: own_inventory テーブルの ID
        qty: 引当数量（正の整数）
        tenant_id: テナント ID（RLS 検証用）

    Raises:
        ValueError: レコードが存在しない、または在庫不足の場合
    """
    if qty <= 0:
        raise ValueError(f"qty は 1 以上を指定してください: {qty}")

    result = await db.execute(
        text(
            "SELECT physical_qty, reserved_qty FROM own_inventory"
            " WHERE id = :id AND tenant_id = :tid FOR UPDATE"
        ),
        {"id": own_inventory_id, "tid": tenant_id},
    )
    row = result.fetchone()
    if not row:
        raise ValueError(f"own_inventory {own_inventory_id} が見つかりません")

    available = row.physical_qty - row.reserved_qty
    if available < qty:
        raise ValueError(
            f"在庫不足: 利用可能数 {available} < 引当要求数 {qty}"
        )

    await db.execute(
        text(
            "UPDATE own_inventory"
            " SET reserved_qty = reserved_qty + :qty, updated_at = NOW()"
            " WHERE id = :id AND tenant_id = :tid"
        ),
        {"qty": qty, "id": own_inventory_id, "tid": tenant_id},
    )


async def release_reservation(
    db: AsyncSession,
    own_inventory_id: int,
    qty: int,
    tenant_id: int,
) -> None:
    """引当解除（注文キャンセル等）。reserved_qty を qty だけ減らす（0 未満にはならない）。

    Args:
        db: データベースセッション
        own_inventory_id: own_inventory テーブルの ID
        qty: 解除数量（正の整数）
        tenant_id: テナント ID（RLS 検証用）

    Raises:
        ValueError: qty が不正な場合
    """
    if qty <= 0:
        raise ValueError(f"qty は 1 以上を指定してください: {qty}")

    await db.execute(
        text(
            "UPDATE own_inventory"
            " SET reserved_qty = CASE WHEN reserved_qty - :qty < 0 THEN 0"
            "                        ELSE reserved_qty - :qty END,"
            "     updated_at = NOW()"
            " WHERE id = :id AND tenant_id = :tid"
        ),
        {"qty": qty, "id": own_inventory_id, "tid": tenant_id},
    )


async def ship_qty(
    db: AsyncSession,
    own_inventory_id: int,
    qty: int,
    tenant_id: int,
) -> None:
    """発送確定: physical_qty と reserved_qty を同時に qty だけ減らす。

    Args:
        db: データベースセッション
        own_inventory_id: own_inventory テーブルの ID
        qty: 発送数量（正の整数）
        tenant_id: テナント ID（RLS 検証用）

    Raises:
        ValueError: qty が不正な場合
    """
    if qty <= 0:
        raise ValueError(f"qty は 1 以上を指定してください: {qty}")

    await db.execute(
        text(
            "UPDATE own_inventory"
            " SET physical_qty = physical_qty - :qty,"
            "     reserved_qty = CASE WHEN reserved_qty - :qty < 0 THEN 0"
            "                        ELSE reserved_qty - :qty END,"
            "     updated_at = NOW()"
            " WHERE id = :id AND tenant_id = :tid"
        ),
        {"qty": qty, "id": own_inventory_id, "tid": tenant_id},
    )
