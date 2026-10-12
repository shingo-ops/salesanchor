"""
中央 admin 用 public.quantity_units CRUD ルーター。

API:
  GET    /api/v1/super-admin/quantity-units              — 一覧（page/per_page/q/is_active・condition_count/product_line_count 付き）
  POST   /api/v1/super-admin/quantity-units              — 新規作成
  PATCH  /api/v1/super-admin/quantity-units/{unit_id}   — 更新
  DELETE /api/v1/super-admin/quantity-units/{unit_id}   — soft delete (is_active=FALSE)
  GET    /api/v1/super-admin/quantity-units/{unit_id}/links — 紐づく condition_definitions・product_lines
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.schemas.quantity_unit import (
    QuantityUnitCreate,
    QuantityUnitLinksResponse,
    QuantityUnitUpdate,
    QuantityUnitWithCountsResponse,
)

router = APIRouter()

_COLS = "id, code, name, name_en, display_order, is_active, value, created_at, updated_at"
_UPDATABLE = {"code", "name", "name_en", "display_order", "is_active", "value"}


@router.get(
    "/super-admin/quantity-units",
    response_model=list[QuantityUnitWithCountsResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_quantity_units(
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
        conditions.append("(qu.code ILIKE :q OR qu.name ILIKE :q)")
        params["q"] = f"%{q}%"
    if is_active is not None:
        conditions.append("qu.is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    result = await db.execute(
        text(
            f"SELECT qu.{', qu.'.join(_COLS.split(', '))}, "
            "COALESCE(cond_cnt.cnt, 0) AS condition_count, "
            "COALESCE(pl_cnt.cnt, 0) AS product_line_count "
            "FROM public.quantity_units qu "
            "LEFT JOIN ("
            "  SELECT quantity_unit_id, COUNT(*) AS cnt"
            "  FROM public.unit_condition_links GROUP BY quantity_unit_id"
            ") cond_cnt ON cond_cnt.quantity_unit_id = qu.id "
            "LEFT JOIN ("
            "  SELECT quantity_unit_id, COUNT(*) AS cnt"
            "  FROM public.product_line_available_units GROUP BY quantity_unit_id"
            ") pl_cnt ON pl_cnt.quantity_unit_id = qu.id "
            f"{where} "
            "ORDER BY qu.display_order, qu.id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [QuantityUnitWithCountsResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/quantity-units",
    response_model=QuantityUnitWithCountsResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_quantity_unit(
    data: QuantityUnitCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.quantity_units "
                "(code, name, name_en, display_order, is_active, value) "
                "VALUES (:code, :name, :name_en, :display_order, :is_active, :value) "
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
    return QuantityUnitWithCountsResponse(**dict(row), condition_count=0, product_line_count=0)


@router.patch(
    "/super-admin/quantity-units/{unit_id}",
    response_model=QuantityUnitWithCountsResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_quantity_unit(
    unit_id: int,
    data: QuantityUnitUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = unit_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.quantity_units SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="数量単位が見つかりません")
    await db.commit()
    # カウントを再取得
    cond_res = await db.execute(
        text("SELECT COUNT(*) FROM public.unit_condition_links WHERE quantity_unit_id = :id"),
        {"id": unit_id},
    )
    pl_res = await db.execute(
        text("SELECT COUNT(*) FROM public.product_line_available_units WHERE quantity_unit_id = :id"),
        {"id": unit_id},
    )
    return QuantityUnitWithCountsResponse(
        **dict(row),
        condition_count=cond_res.scalar() or 0,
        product_line_count=pl_res.scalar() or 0,
    )


@router.delete(
    "/super-admin/quantity-units/{unit_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_quantity_unit(
    unit_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。products.quantity_unit_id で参照中なら 409。"""
    # 参照チェック: products.quantity_unit_id
    ref_products = await db.execute(
        text("SELECT 1 FROM public.products WHERE quantity_unit_id = :id LIMIT 1"),
        {"id": unit_id},
    )
    if ref_products.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この数量単位は商品（products）で使用中のため削除できません",
        )
    result = await db.execute(
        text(
            "UPDATE public.quantity_units SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id"
        ),
        {"id": unit_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="数量単位が見つかりません")
    await db.commit()


@router.get(
    "/super-admin/quantity-units/{unit_id}/links",
    response_model=QuantityUnitLinksResponse,
    dependencies=[Depends(require_super_admin)],
)
async def get_quantity_unit_links(
    unit_id: int,
    db: AsyncSession = Depends(get_db),
):
    """この販売単位に紐づく condition_definitions と product_lines を返す。"""
    # 存在チェック
    exists = await db.execute(
        text("SELECT 1 FROM public.quantity_units WHERE id = :id"),
        {"id": unit_id},
    )
    if not exists.fetchone():
        raise HTTPException(status_code=404, detail="数量単位が見つかりません")

    cond_res = await db.execute(
        text(
            "SELECT cd.id, cd.code, cd.name "
            "FROM public.condition_definitions cd "
            "JOIN public.unit_condition_links ucl ON ucl.condition_def_id = cd.id "
            "WHERE ucl.quantity_unit_id = :id "
            "ORDER BY cd.display_order, cd.id"
        ),
        {"id": unit_id},
    )
    pl_res = await db.execute(
        text(
            "SELECT pl.id, pl.code, pl.name "
            "FROM public.product_lines pl "
            "JOIN public.product_line_available_units plau ON plau.product_line_id = pl.id "
            "WHERE plau.quantity_unit_id = :id "
            "ORDER BY pl.display_order, pl.id"
        ),
        {"id": unit_id},
    )
    return QuantityUnitLinksResponse(
        conditions=[dict(row) for row in cond_res.mappings().all()],
        product_lines=[dict(row) for row in pl_res.mappings().all()],
    )
