"""
各種マスタ用 public.product_attribute_masters CRUD ルーター。

商品マスタ画面「各種マスタ」タブから、商品の選択肢系マスタ
(商品種類 / セット種別 / レアリティ / 言語 / 単位 / HSコード / 品目 / 素材) を
追加 / 編集 / 削除する。TCGシリーズは super_admin_tcg ルーター側で管理する。

API:
  GET    /api/v1/super-admin/product-masters?attribute=rarity
  POST   /api/v1/super-admin/product-masters
  PATCH  /api/v1/super-admin/product-masters/{id}
  DELETE /api/v1/super-admin/product-masters/{id}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.schemas.product_masters import (
    VALID_ATTRIBUTES,
    ProductAttributeMasterCreate,
    ProductAttributeMasterResponse,
    ProductAttributeMasterUpdate,
)

router = APIRouter()

_COLS = "id, attribute, code, label_ja, label_en, sort_order, is_active"
_UPDATABLE = {"code", "label_ja", "label_en", "sort_order", "is_active"}


@router.get(
    "/super-admin/product-masters",
    response_model=list[ProductAttributeMasterResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_attribute_masters(
    attribute: str | None = Query(default=None, max_length=40),
    include_inactive: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    conditions: list[str] = []
    params: dict = {}
    if attribute:
        if attribute not in VALID_ATTRIBUTES:
            raise HTTPException(
                status_code=422,
                detail=f"attribute must be one of {sorted(VALID_ATTRIBUTES)}",
            )
        conditions.append("attribute = :attribute")
        params["attribute"] = attribute
    if not include_inactive:
        conditions.append("is_active = TRUE")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM public.product_attribute_masters {where} "
            f"ORDER BY attribute, sort_order, id"
        ),
        params,
    )
    return [
        ProductAttributeMasterResponse(**dict(row))
        for row in result.mappings().all()
    ]


@router.post(
    "/super-admin/product-masters",
    response_model=ProductAttributeMasterResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_attribute_master(
    data: ProductAttributeMasterCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.product_attribute_masters "
                f"(attribute, code, label_ja, label_en, sort_order, is_active) "
                f"VALUES (:attribute, :code, :label_ja, :label_en, :sort_order, :is_active) "
                f"RETURNING {_COLS}"
            ),
            data.model_dump(),
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"同じ区分・表示名のマスタが既に存在します: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    return ProductAttributeMasterResponse(**dict(row))


@router.patch(
    "/super-admin/product-masters/{master_id}",
    response_model=ProductAttributeMasterResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_attribute_master(
    master_id: int,
    data: ProductAttributeMasterUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = master_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.product_attribute_masters SET {set_clauses} "
                f"WHERE id = :id RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"同じ区分・表示名のマスタが既に存在します: {exc.orig}",
        )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="マスタが見つかりません")
    await db.commit()
    return ProductAttributeMasterResponse(**dict(row))


@router.delete(
    "/super-admin/product-masters/{master_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_attribute_master(
    master_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("DELETE FROM public.product_attribute_masters WHERE id = :id"),
        {"id": master_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="マスタが見つかりません")
    await db.commit()
