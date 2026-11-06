"""人の番号（public.users.id）がその会社の人かを確かめる（ADR-1008）。"""
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

USER_NOT_IN_TENANT = "指定された担当者が見つかりません"


async def ensure_user_in_tenant(db: AsyncSession, user_id: int | None, tenant_id: int) -> None:
    """user_id が tenant_id の人でなければ 422。None は通す（担当なし）。"""
    if user_id is None:
        return
    row = await db.execute(
        text("SELECT 1 FROM public.users WHERE id = :uid AND tenant_id = :tid"),
        {"uid": user_id, "tid": tenant_id},
    )
    if row.first() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=USER_NOT_IN_TENANT)
