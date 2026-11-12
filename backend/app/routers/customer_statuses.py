"""会社・連絡先の状態の表（customer_statuses）の API。

エンドポイント:
  GET /api/v1/customer-statuses — 状態の一覧（ログインした人なら誰でも）
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant, get_current_user, set_tenant_context
from app.database import get_db
from app.models import User
from app.services import customer_statuses

router = APIRouter()


@router.get(
    "/customer-statuses",
    summary="会社・連絡先の状態の一覧（名前・並び・作るときに出すか）",
    tags=["customer-statuses"],
)
async def list_customer_statuses(
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await set_tenant_context(db, tenant_id)
    return await customer_statuses.list_customer_statuses(db)
