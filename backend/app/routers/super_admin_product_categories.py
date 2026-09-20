"""
中央 admin 用 public.tcg_product_categories CRUD ルーター。

API:
  GET    /api/v1/super-admin/product-categories
  POST   /api/v1/super-admin/product-categories
  PATCH  /api/v1/super-admin/product-categories/{id}
  DELETE /api/v1/super-admin/product-categories/{id}   (soft delete: is_active=FALSE)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.schemas.product_category import (
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCategoryUpdate,
)

router = APIRouter()

_COLS = "id, code, display_name, kubun_type, is_active, tenant_id, created_at, updated_at"
_UPDATABLE = {"code", "display_name", "kubun_type", "is_active"}


@router.get(
    "/super-admin/product-categories",
    response_model=list[ProductCategoryResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_product_categories(
    q: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    # 中央マスタ（tenant_id IS NULL）のみを対象とする。
    conditions: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if q:
        conditions.append("(code ILIKE :q OR display_name ILIKE :q)")
        params["q"] = f"%{q}%"
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_COLS} "
            f"FROM public.tcg_product_categories {where} "
            "ORDER BY code LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [ProductCategoryResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/product-categories",
    response_model=ProductCategoryResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_product_category(
    data: ProductCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.tcg_product_categories "
                f"(code, display_name, kubun_type, is_active, tenant_id) "
                f"VALUES (:code, :display_name, :kubun_type, :is_active, NULL) "
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
    return ProductCategoryResponse(**dict(row))


@router.patch(
    "/super-admin/product-categories/{category_id}",
    response_model=ProductCategoryResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_product_category(
    category_id: int,
    data: ProductCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = category_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.tcg_product_categories SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id IS NULL RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="商品カテゴリが見つかりません")
    await db.commit()
    return ProductCategoryResponse(**dict(row))


@router.delete(
    "/super-admin/product-categories/{category_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_product_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。"""
    result = await db.execute(
        text(
            "UPDATE public.tcg_product_categories SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": category_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="商品カテゴリが見つかりません")
    await db.commit()
