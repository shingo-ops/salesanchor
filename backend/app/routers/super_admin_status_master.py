"""
中央 admin 用 public.tcg_status_master CRUD ルーター。

API:
  GET    /api/v1/super-admin/status-master
  POST   /api/v1/super-admin/status-master
  PATCH  /api/v1/super-admin/status-master/{id}
  DELETE /api/v1/super-admin/status-master/{id}  (soft delete: enabled=false)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
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
    "/super-admin/status-master",
    response_model=list[TcgStatusMasterResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_status_master(
    q: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    # LINE 解析用マスタ（tenant_id IS NULL）のみを対象とする。
    conditions: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if q:
        conditions.append("(status_id ILIKE :q OR canonical ILIKE :q)")
        params["q"] = f"%{q}%"
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_COLS} "
            f"FROM public.tcg_status_master {where} "
            "ORDER BY priority, status_id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [TcgStatusMasterResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/status-master",
    response_model=TcgStatusMasterResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_status_master(
    data: TcgStatusMasterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.tcg_status_master "
                "(status_id, canonical, search_pattern, exclude_pattern, priority, "
                "enabled, note, match_type, effect, tenant_id) "
                "VALUES (:status_id, :canonical, :search_pattern, :exclude_pattern, "
                ":priority, :enabled, :note, :match_type, :effect, NULL) "
                f"RETURNING {_COLS}"
            ),
            data.model_dump(),
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"重複または制約違反: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    return TcgStatusMasterResponse(**dict(row))


@router.patch(
    "/super-admin/status-master/{entry_id}",
    response_model=TcgStatusMasterResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_status_master(
    entry_id: int,
    data: TcgStatusMasterUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = entry_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.tcg_status_master SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id IS NULL RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="ステータスが見つかりません")
    await db.commit()
    return TcgStatusMasterResponse(**dict(row))


@router.delete(
    "/super-admin/status-master/{entry_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_status_master(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (enabled=false)。"""
    result = await db.execute(
        text(
            "UPDATE public.tcg_status_master SET enabled = FALSE, updated_at = NOW() "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": entry_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="ステータスが見つかりません")
    await db.commit()
