"""
テナント用 ステータスマスタ API（CRUD）。

tenant_id = :tenant_id の行のみ操作。共用マスタ（tenant_id IS NULL）は参照不可。
ADR-072: write endpoint の db.commit() 直後に reset_tenant_context() 必須。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.schemas.central_masters import (
    TcgStatusMasterCreate,
    TcgStatusMasterResponse,
    TcgStatusMasterUpdate,
)

router = APIRouter()

_COLS = (
    "id, status_id, canonical, search_pattern, exclude_pattern, priority, "
    "enabled, note, match_type, effect, created_at, updated_at"
)
_UPDATABLE = {
    "status_id",
    "canonical",
    "search_pattern",
    "exclude_pattern",
    "priority",
    "enabled",
    "note",
    "match_type",
    "effect",
}


@router.get(
    "/status-master",
    response_model=list[TcgStatusMasterResponse],
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def list_status_master(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": per_page, "offset": offset}
    if search:
        conditions.append("(status_id ILIKE :search OR canonical ILIKE :search)")
        params["search"] = f"%{search}%"
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM public.tcg_status_master {where} "
            "ORDER BY priority, status_id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [TcgStatusMasterResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/status-master",
    response_model=TcgStatusMasterResponse,
    status_code=201,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def create_status_master(
    data: TcgStatusMasterCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(
            "INSERT INTO public.tcg_status_master "
            "(status_id, canonical, search_pattern, exclude_pattern, priority, "
            "enabled, note, match_type, effect, tenant_id) "
            "VALUES (:status_id, :canonical, :search_pattern, :exclude_pattern, "
            ":priority, :enabled, :note, :match_type, :effect, :tenant_id) "
            f"RETURNING {_COLS}"
        ),
        {**data.model_dump(), "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return TcgStatusMasterResponse(**dict(row))


@router.patch(
    "/status-master/{entry_id}",
    response_model=TcgStatusMasterResponse,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def update_status_master(
    entry_id: int,
    data: TcgStatusMasterUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = entry_id
    update_data["tenant_id"] = tenant_id
    result = await db.execute(
        text(
            f"UPDATE public.tcg_status_master SET {set_clauses}, updated_at = NOW() "
            f"WHERE id = :id AND tenant_id = :tenant_id RETURNING {_COLS}"
        ),
        update_data,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ステータスが見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return TcgStatusMasterResponse(**dict(row))


@router.delete(
    "/status-master/{entry_id}",
    status_code=204,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def delete_status_master(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(
            "UPDATE public.tcg_status_master SET enabled = FALSE, updated_at = NOW() "
            "WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": entry_id, "tenant_id": tenant_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ステータスが見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
