"""
中央 admin 用 public.units + public.unit_aliases CRUD ルーター。

API:
  GET    /api/v1/super-admin/units
  POST   /api/v1/super-admin/units
  PATCH  /api/v1/super-admin/units/{id}
  DELETE /api/v1/super-admin/units/{id}          (soft delete)
  GET    /api/v1/super-admin/units/{id}/aliases
  POST   /api/v1/super-admin/units/{id}/aliases
  DELETE /api/v1/super-admin/units/aliases/{alias_id}
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
    UnitCreate,
    UnitResponse,
    UnitUpdate,
    UnitAliasCreate,
    UnitAliasResponse,
)

router = APIRouter()

_UNIT_COLS = "id, code, canonical, kubun, is_active, created_at, updated_at"
_UNIT_UPDATABLE = {"code", "canonical", "kubun", "is_active"}

_ALIAS_COLS = "id, unit_id, alias_text, lang, updated_at"


@router.get(
    "/super-admin/units",
    response_model=list[UnitResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_units(
    q: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    # LINE 解析用マスタ（tenant_id IS NULL）のみを対象とする。
    conditions: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if q:
        conditions.append("(code ILIKE :q OR canonical ILIKE :q)")
        params["q"] = f"%{q}%"
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_UNIT_COLS} "
            f"FROM public.units {where} "
            "ORDER BY code LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [UnitResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/units",
    response_model=UnitResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_unit(
    data: UnitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.units "
                f"(code, canonical, kubun, is_active, tenant_id) "
                f"VALUES (:code, :canonical, :kubun, :is_active, NULL) "
                f"RETURNING {_UNIT_COLS}"
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
    return UnitResponse(**dict(row))


@router.patch(
    "/super-admin/units/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_unit(
    unit_id: int,
    data: UnitUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UNIT_UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = unit_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.units SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id IS NULL RETURNING {_UNIT_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="単位が見つかりません")
    await db.commit()
    return UnitResponse(**dict(row))


@router.delete(
    "/super-admin/units/{unit_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_unit(
    unit_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=false)。"""
    result = await db.execute(
        text(
            "UPDATE public.units SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": unit_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="単位が見つかりません")
    await db.commit()


# ----------------------------------------------------------------------------
# unit_aliases
# ----------------------------------------------------------------------------


@router.get(
    "/super-admin/units/{unit_id}/aliases",
    response_model=list[UnitAliasResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_unit_aliases(unit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text(
            f"SELECT {_ALIAS_COLS} FROM public.unit_aliases "
            f"WHERE unit_id = :uid ORDER BY id"
        ),
        {"uid": unit_id},
    )
    return [UnitAliasResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/units/{unit_id}/aliases",
    response_model=UnitAliasResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_unit_alias(
    unit_id: int,
    data: UnitAliasCreate,
    db: AsyncSession = Depends(get_db),
):
    if data.unit_id != unit_id:
        raise HTTPException(
            status_code=400,
            detail="URL の unit_id と body の unit_id が一致しません",
        )
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.unit_aliases "
                f"(unit_id, alias_text, lang) "
                f"VALUES (:unit_id, :alias_text, :lang) "
                f"RETURNING {_ALIAS_COLS}"
            ),
            data.model_dump(),
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"重複または FK 違反: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    return UnitAliasResponse(**dict(row))


@router.delete(
    "/super-admin/units/aliases/{alias_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_unit_alias(alias_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("DELETE FROM public.unit_aliases WHERE id = :id"),
        {"id": alias_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="別名が見つかりません")
    await db.commit()
