"""
中央 admin 用 public.conditions CRUD ルーター。

テーブル: public.conditions
  id, code, canonical, app_kubun, is_active, priority,
  search_kw, exclude_kw, tenant_id, created_at, updated_at

API:
  GET    /api/v1/super-admin/conditions
  POST   /api/v1/super-admin/conditions
  PATCH  /api/v1/super-admin/conditions/{id}
  DELETE /api/v1/super-admin/conditions/{id}    (soft delete: is_active=FALSE)
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
    CentralConditionCreate,
    CentralConditionResponse,
    CentralConditionUpdate,
)
from app.schemas.condition import ConditionAliasCreate, ConditionAliasResponse

router = APIRouter()

_ALIAS_COLS = "id, condition_id, alias_text, lang, updated_at"

_CONDITION_COLS = (
    "id, code, canonical, app_kubun, is_active, priority, "
    "search_kw, exclude_kw, tenant_id, created_at, updated_at"
)
_CONDITION_UPDATABLE = {
    "code", "canonical", "app_kubun", "is_active", "priority",
    "search_kw", "exclude_kw",
}


@router.get(
    "/super-admin/conditions",
    response_model=list[CentralConditionResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_conditions(
    q: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    # 中央マスタ（tenant_id IS NULL）のみを対象とする。
    conditions_list: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if is_active is not None:
        conditions_list.append("is_active = :is_active")
        params["is_active"] = is_active
    if q:
        conditions_list.append("(code ILIKE :q OR canonical ILIKE :q)")
        params["q"] = f"%{q}%"
    where = f"WHERE {' AND '.join(conditions_list)}"
    result = await db.execute(
        text(
            f"SELECT {_CONDITION_COLS} FROM public.conditions {where} "
            "ORDER BY priority NULLS LAST, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [CentralConditionResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/conditions",
    response_model=CentralConditionResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_condition(
    data: CentralConditionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    try:
        # code 重複チェック（中央マスタ内）
        exists_result = await db.execute(
            text(
                "SELECT 1 FROM public.conditions "
                "WHERE code = :code AND tenant_id IS NULL"
            ),
            {"code": data.code},
        )
        if exists_result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="状態コードは既に存在します",
            )

        result = await db.execute(
            text(
                f"INSERT INTO public.conditions "
                f"(code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, tenant_id, updated_at) "
                f"VALUES (:code, :canonical, :app_kubun, :is_active, :priority, :search_kw, :exclude_kw, NULL, now()) "
                f"RETURNING {_CONDITION_COLS}"
            ),
            {
                "code": data.code,
                "canonical": data.canonical,
                "app_kubun": data.app_kubun,
                "is_active": data.is_active,
                "priority": data.priority,
                "search_kw": data.search_kw,
                "exclude_kw": data.exclude_kw,
            },
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"制約違反: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    return CentralConditionResponse(**dict(row))


@router.patch(
    "/super-admin/conditions/{condition_id}",
    response_model=CentralConditionResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_condition(
    condition_id: int,
    data: CentralConditionUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _CONDITION_UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = condition_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.conditions SET {set_clauses}, updated_at = now() "
                f"WHERE id = :id AND tenant_id IS NULL "
                f"RETURNING {_CONDITION_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="状態が見つかりません")
    await db.commit()
    return CentralConditionResponse(**dict(row))


@router.delete(
    "/super-admin/conditions/{condition_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_condition(
    condition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。public.conditions は他テーブルから
    参照されるため hard delete はしない。"""
    result = await db.execute(
        text(
            "UPDATE public.conditions SET is_active = FALSE, updated_at = now() "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": condition_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="状態が見つかりません")
    await db.commit()


# ----------------------------------------------------------------------------
# condition_aliases
# ----------------------------------------------------------------------------


@router.get(
    "/super-admin/conditions/{condition_id}/aliases",
    response_model=list[ConditionAliasResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_condition_aliases(
    condition_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        text(
            f"SELECT {_ALIAS_COLS} FROM public.condition_aliases "
            f"WHERE condition_id = :cid ORDER BY id"
        ),
        {"cid": condition_id},
    )
    return [ConditionAliasResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/conditions/{condition_id}/aliases",
    response_model=ConditionAliasResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_condition_alias(
    condition_id: int,
    data: ConditionAliasCreate,
    db: AsyncSession = Depends(get_db),
):
    if data.condition_id != condition_id:
        raise HTTPException(
            status_code=400,
            detail="URL の condition_id と body の condition_id が一致しません",
        )
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.condition_aliases "
                f"(condition_id, alias_text, lang) "
                f"VALUES (:condition_id, :alias_text, :lang) "
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
    return ConditionAliasResponse(**dict(row))


@router.delete(
    "/super-admin/conditions/aliases/{alias_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_condition_alias(
    alias_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        text("DELETE FROM public.condition_aliases WHERE id = :id"),
        {"id": alias_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="別名が見つかりません")
    await db.commit()
