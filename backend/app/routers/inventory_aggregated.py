"""テナント向け在庫集計エンドポイント GET /inventory/aggregated。

読み取り専用・追加のみ。既存 inventory_search / inventory_offers は不変。
テナント応答: supplier_name / reason / raw を含めない (境界)。
タブ分割: ?category= (products.tcg_type) で絞り込み。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    load_user_permissions,
)
from app.database import get_db
from app.models import User
from app.schemas.inventory_aggregated import (
    AggregatedRow,
    ConditionCell,
    InventoryAggregatedResponse,
)
from app.services.inventory_aggregated_service import get_aggregated_inventory

logger = logging.getLogger(__name__)

router = APIRouter()

# 在庫検索と同じ権限セット (QA r7 確定: マスクなし・全テナント共通)
_ALLOWED_PERMISSIONS: frozenset[str] = frozenset(
    {
        "products.view",
        "inventory.visibility.full",
        "inventory.visibility.staff",
        "inventory.visibility.viewer",
    }
)


@router.get(
    "/inventory/aggregated",
    response_model=InventoryAggregatedResponse,
    summary="テナント向け在庫集計 (series x condition ピボット)",
)
async def get_inventory_aggregated(
    category: str | None = Query(
        default=None,
        description="tcg_type フィルタ (例: pokemon)。未指定の場合は全種別。",
    ),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> InventoryAggregatedResponse:
    """在庫を商品 (series) x 状態 (condition) でピボットした集計を返す。

    - 各セルは集計後の最良 1 件 (価格/数量)。
    - supplier_name / 採用理由 / raw オファーは含まない (テナント境界)。
    - ?category= で products.tcg_type による絞り込みが可能。
    """
    perms = await load_user_permissions(db, tenant_id, current_user.id)
    if not (perms & _ALLOWED_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="在庫集計を参照する権限がありません (inventory.visibility.* または products.view が必要)。",
        )

    tabs, raw_rows = await get_aggregated_inventory(db=db, category=category)

    rows = [
        AggregatedRow(
            series=row["series"],
            tcg_type=row["tcg_type"],
            cells={
                condition: ConditionCell(
                    price=cell["price"],
                    quantity=cell["quantity"],
                )
                for condition, cell in row["cells"].items()
            },
        )
        for row in raw_rows
    ]

    return InventoryAggregatedResponse(tabs=tabs, rows=rows)
