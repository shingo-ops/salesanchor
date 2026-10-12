"""
中央 admin 用 public.product_lines CRUD ルーター。

API:
  GET    /api/v1/super-admin/product-lines              — 一覧（is_active フィルタ・ソート対応）
  POST   /api/v1/super-admin/product-lines              — 新規作成
  PATCH  /api/v1/super-admin/product-lines/{line_id}   — 更新
  DELETE /api/v1/super-admin/product-lines/{line_id}   — soft delete (is_active=FALSE)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.schemas.product_line import (
    ProductLineCreate,
    ProductLineResponse,
    ProductLineUpdate,
)

router = APIRouter()

_COLS = "id, code, name, name_en, display_order, is_active, kind_id, type_id, created_at, updated_at"
_UPDATABLE = {"code", "name", "name_en", "display_order", "is_active", "kind_id", "type_id"}


@router.get(
    "/super-admin/product-lines",
    response_model=list[ProductLineResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_product_lines(
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
            f"FROM public.product_lines {where} "
            "ORDER BY display_order, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [ProductLineResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/product-lines",
    response_model=ProductLineResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_product_line(
    data: ProductLineCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.product_lines "
                "(code, name, name_en, display_order, is_active, kind_id, type_id) "
                "VALUES (:code, :name, :name_en, :display_order, :is_active, :kind_id, :type_id) "
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
    return ProductLineResponse(**dict(row))


@router.patch(
    "/super-admin/product-lines/{line_id}",
    response_model=ProductLineResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_product_line(
    line_id: int,
    data: ProductLineUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = line_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.product_lines SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="小分類が見つかりません")
    await db.commit()
    return ProductLineResponse(**dict(row))


@router.delete(
    "/super-admin/product-lines/{line_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_product_line(
    line_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。product_formats.line_id または products.product_line_id で参照中なら 409。"""
    # 参照チェック: product_formats.line_id
    ref_formats = await db.execute(
        text("SELECT 1 FROM public.product_formats WHERE line_id = :id LIMIT 1"),
        {"id": line_id},
    )
    if ref_formats.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この小分類はフォーマット（product_formats）で使用中のため削除できません",
        )
    # 参照チェック: products.product_line_id
    ref_products = await db.execute(
        text("SELECT 1 FROM public.products WHERE product_line_id = :id LIMIT 1"),
        {"id": line_id},
    )
    if ref_products.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この小分類は商品（products）で使用中のため削除できません",
        )
    result = await db.execute(
        text(
            "UPDATE public.product_lines SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id"
        ),
        {"id": line_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="小分類が見つかりません")
    await db.commit()
