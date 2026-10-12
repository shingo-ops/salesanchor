"""
中央 admin 用 public.condition_definitions CRUD ルーター。

API:
  GET    /api/v1/super-admin/condition-definitions              — 一覧（page/per_page/q/is_active）
  POST   /api/v1/super-admin/condition-definitions              — 新規作成
  PATCH  /api/v1/super-admin/condition-definitions/{def_id}    — 更新
  DELETE /api/v1/super-admin/condition-definitions/{def_id}    — soft delete (is_active=FALSE)
  GET    /api/v1/super-admin/condition-definitions/{def_id}/links — 紐づく quantity_units
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.schemas.quantity_unit import (
    ConditionDefCreate,
    ConditionDefLinksResponse,
    ConditionDefResponse,
    ConditionDefUpdate,
)

router = APIRouter()

_COLS = "id, code, name, name_en, line_id, display_order, is_active, created_at, updated_at"
_UPDATABLE = {"code", "name", "name_en", "line_id", "display_order", "is_active"}


@router.get(
    "/super-admin/condition-definitions",
    response_model=list[ConditionDefResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_condition_defs(
    q: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    conditions: list[str] = []
    params: dict = {"limit": per_page, "offset": offset}
    if q:
        conditions.append("(code ILIKE :q OR name ILIKE :q)")
        params["q"] = f"%{q}%"
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    result = await db.execute(
        text(
            f"SELECT {_COLS} "
            f"FROM public.condition_definitions {where} "
            "ORDER BY display_order, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [ConditionDefResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/condition-definitions",
    response_model=ConditionDefResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_condition_def(
    data: ConditionDefCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.condition_definitions "
                "(code, name, name_en, line_id, display_order, is_active) "
                "VALUES (:code, :name, :name_en, :line_id, :display_order, :is_active) "
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
    return ConditionDefResponse(**dict(row))


@router.patch(
    "/super-admin/condition-definitions/{def_id}",
    response_model=ConditionDefResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_condition_def(
    def_id: int,
    data: ConditionDefUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = def_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.condition_definitions SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="コンディション定義が見つかりません")
    await db.commit()
    return ConditionDefResponse(**dict(row))


@router.delete(
    "/super-admin/condition-definitions/{def_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_condition_def(
    def_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。unit_condition_links で参照中なら 409。"""
    # 参照チェック: unit_condition_links.condition_def_id
    ref_links = await db.execute(
        text("SELECT 1 FROM public.unit_condition_links WHERE condition_def_id = :id LIMIT 1"),
        {"id": def_id},
    )
    if ref_links.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このコンディション定義は販売単位リンク（unit_condition_links）で使用中のため削除できません",
        )
    result = await db.execute(
        text(
            "UPDATE public.condition_definitions SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id"
        ),
        {"id": def_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="コンディション定義が見つかりません")
    await db.commit()


@router.get(
    "/super-admin/condition-definitions/{def_id}/links",
    response_model=ConditionDefLinksResponse,
    dependencies=[Depends(require_super_admin)],
)
async def get_condition_def_links(
    def_id: int,
    db: AsyncSession = Depends(get_db),
):
    """このコンディション定義に紐づく quantity_units を返す。"""
    # 存在チェック
    exists = await db.execute(
        text("SELECT 1 FROM public.condition_definitions WHERE id = :id"),
        {"id": def_id},
    )
    if not exists.fetchone():
        raise HTTPException(status_code=404, detail="コンディション定義が見つかりません")

    qu_res = await db.execute(
        text(
            "SELECT qu.id, qu.code, qu.name "
            "FROM public.quantity_units qu "
            "JOIN public.unit_condition_links ucl ON ucl.quantity_unit_id = qu.id "
            "WHERE ucl.condition_def_id = :id "
            "ORDER BY qu.display_order, qu.id"
        ),
        {"id": def_id},
    )
    return ConditionDefLinksResponse(
        quantity_units=[dict(row) for row in qu_res.mappings().all()],
    )
