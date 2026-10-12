"""
中央 admin 用 public.product_kinds CRUD ルーター。

API:
  GET    /api/v1/super-admin/product-kinds          — 一覧（is_active フィルタ・ソート対応）
  POST   /api/v1/super-admin/product-kinds          — 新規作成
  PATCH  /api/v1/super-admin/product-kinds/{kind_id} — 更新
  DELETE /api/v1/super-admin/product-kinds/{kind_id} — soft delete (is_active=FALSE)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.schemas.product_kind import (
    ProductKindCreate,
    ProductKindResponse,
    ProductKindUpdate,
)

router = APIRouter()

_COLS = "id, code, name, name_en, display_order, is_active, created_at, updated_at"
_UPDATABLE = {"code", "name", "name_en", "display_order", "is_active"}


@router.get(
    "/super-admin/product-kinds",
    response_model=list[ProductKindResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_product_kinds(
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    conditions: list[str] = []
    params: dict = {"limit": per_page, "offset": offset}
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    result = await db.execute(
        text(
            f"SELECT {_COLS} "
            f"FROM public.product_kinds {where} "
            "ORDER BY display_order, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [ProductKindResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/product-kinds",
    response_model=ProductKindResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_product_kind(
    data: ProductKindCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.product_kinds "
                "(code, name, name_en, display_order, is_active) "
                "VALUES (:code, :name, :name_en, :display_order, :is_active) "
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
    return ProductKindResponse(**dict(row))


@router.patch(
    "/super-admin/product-kinds/{kind_id}",
    response_model=ProductKindResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_product_kind(
    kind_id: int,
    data: ProductKindUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = kind_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.product_kinds SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="大分類が見つかりません")
    await db.commit()
    return ProductKindResponse(**dict(row))


@router.delete(
    "/super-admin/product-kinds/{kind_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_product_kind(
    kind_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。type_master.kind_id で参照中なら 409。"""
    # 参照チェック: public.type_master で kind_id が使われていないか確認
    ref_result = await db.execute(
        text("SELECT 1 FROM public.type_master WHERE kind_id = :id LIMIT 1"),
        {"id": kind_id},
    )
    if ref_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この大分類は中分類（type_master）で使用中のため削除できません",
        )
    result = await db.execute(
        text(
            "UPDATE public.product_kinds SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id"
        ),
        {"id": kind_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="大分類が見つかりません")
    await db.commit()
