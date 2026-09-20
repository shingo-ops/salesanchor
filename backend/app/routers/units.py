"""
テナント用 単位マスタ API（CRUD）。

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
from app.schemas.central_masters import UnitCreate, UnitResponse, UnitUpdate

router = APIRouter()

_COLS = "id, code, canonical, kubun, is_active, created_at, updated_at"
_UPDATABLE = {"code", "canonical", "kubun", "is_active"}


@router.get(
    "/units",
    response_model=list[UnitResponse],
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def list_units(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": per_page, "offset": offset}
    if search:
        conditions.append("(code ILIKE :search OR canonical ILIKE :search)")
        params["search"] = f"%{search}%"
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(f"SELECT {_COLS} FROM public.units {where} ORDER BY code LIMIT :limit OFFSET :offset"),
        params,
    )
    return [UnitResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/units",
    response_model=UnitResponse,
    status_code=201,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def create_unit(
    data: UnitCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(
            f"INSERT INTO public.units (code, canonical, kubun, is_active, tenant_id) "
            f"VALUES (:code, :canonical, :kubun, :is_active, :tenant_id) "
            f"RETURNING {_COLS}"
        ),
        {**data.model_dump(), "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return UnitResponse(**dict(row))


@router.patch(
    "/units/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def update_unit(
    unit_id: int,
    data: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = unit_id
    update_data["tenant_id"] = tenant_id
    result = await db.execute(
        text(
            f"UPDATE public.units SET {set_clauses}, updated_at = NOW() "
            f"WHERE id = :id AND tenant_id = :tenant_id RETURNING {_COLS}"
        ),
        update_data,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="単位が見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return UnitResponse(**dict(row))


@router.delete(
    "/units/{unit_id}",
    status_code=204,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def delete_unit(
    unit_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(
            "UPDATE public.units SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": unit_id, "tenant_id": tenant_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="単位が見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
