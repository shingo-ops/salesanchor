"""
中央 admin 用 public.product_formats CRUD ルーター。

API:
  GET    /api/v1/super-admin/product-formats                — 一覧（is_active フィルタ・ソート対応）
  POST   /api/v1/super-admin/product-formats                — 新規作成
  PATCH  /api/v1/super-admin/product-formats/{format_id}   — 更新
  PUT    /api/v1/super-admin/product-formats/{format_id}/games — 使えるゲームの置き換え
  DELETE /api/v1/super-admin/product-formats/{format_id}   — soft delete (is_active=FALSE)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.routers._utils import log_hidden_error
from app.schemas.product_format import (
    ProductFormatCreate,
    ProductFormatGamesUpdate,
    ProductFormatResponse,
    ProductFormatUpdate,
)

router = APIRouter()

_COLS = "id, code, name, name_en, display_order, is_active, line_id, created_at, updated_at"
_UPDATABLE = {"code", "name", "name_en", "display_order", "is_active", "line_id"}


async def _game_ids_for(db: AsyncSession, format_ids: list[int]) -> dict[int, list[int]]:
    """ADR-1020 便2a: 細分類ごとの使えるゲーム（product_format_game_links）。"""
    if not format_ids:
        return {}
    result = await db.execute(
        text(
            "SELECT format_id, array_agg(type_master_id ORDER BY type_master_id) AS game_ids "
            "FROM public.product_format_game_links WHERE format_id = ANY(:ids) GROUP BY format_id"
        ),
        {"ids": format_ids},
    )
    return {row["format_id"]: list(row["game_ids"]) for row in result.mappings().all()}


@router.get(
    "/super-admin/product-formats",
    response_model=list[ProductFormatResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_product_formats(
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
            f"FROM public.product_formats {where} "
            "ORDER BY display_order, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    rows = [dict(row) for row in result.mappings().all()]
    games = await _game_ids_for(db, [row["id"] for row in rows])
    return [ProductFormatResponse(**row, game_ids=games.get(row["id"], [])) for row in rows]


@router.post(
    "/super-admin/product-formats",
    response_model=ProductFormatResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_product_format(
    data: ProductFormatCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.product_formats "
                "(code, name, name_en, display_order, is_active, line_id) "
                "VALUES (:code, :name, :name_en, :display_order, :is_active, :line_id) "
                f"RETURNING {_COLS}"
            ),
            data.model_dump(),
        )
    except IntegrityError as exc:
        await db.rollback()
        log_hidden_error("super_admin_product_formats.create_product_format", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="重複または制約違反",
        )
    row = result.mappings().first()
    await db.commit()
    return ProductFormatResponse(**dict(row))


@router.patch(
    "/super-admin/product-formats/{format_id}",
    response_model=ProductFormatResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_product_format(
    format_id: int,
    data: ProductFormatUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = format_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.product_formats SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        log_hidden_error("super_admin_product_formats.update_product_format", exc)
        raise HTTPException(status_code=409, detail="制約違反")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="フォーマットが見つかりません")
    await db.commit()
    games = await _game_ids_for(db, [row["id"]])
    return ProductFormatResponse(**dict(row), game_ids=games.get(row["id"], []))


@router.put(
    "/super-admin/product-formats/{format_id}/games",
    response_model=ProductFormatResponse,
    dependencies=[Depends(require_super_admin)],
)
async def replace_product_format_games(
    format_id: int,
    data: ProductFormatGamesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """ADR-1020 便2a: 使えるゲームを送った一覧に置き換える。外す組を商品が使っていれば 409。"""
    wanted = sorted(set(data.game_ids))
    fmt = (await db.execute(
        text(f"SELECT {_COLS} FROM public.product_formats WHERE id = :id FOR UPDATE"),
        {"id": format_id},
    )).mappings().first()
    if not fmt:
        raise HTTPException(status_code=404, detail="フォーマットが見つかりません")
    if wanted:
        found = (await db.execute(
            text("SELECT count(*) FROM public.type_master WHERE id = ANY(:ids) AND is_active = TRUE"),
            {"ids": wanted},
        )).scalar_one()
        if found != len(wanted):
            raise HTTPException(status_code=422, detail="PRODUCT_FORMAT_GAME_UNKNOWN")
    in_use = (await db.execute(
        text(
            "SELECT 1 FROM public.products WHERE product_format_id = :id "
            "AND work_id IS NOT NULL AND NOT (work_id = ANY(:ids)) LIMIT 1"
        ),
        {"id": format_id, "ids": wanted},
    )).first()
    if in_use:
        raise HTTPException(status_code=409, detail="PRODUCT_FORMAT_GAME_IN_USE")
    try:
        await db.execute(
            text(
                "DELETE FROM public.product_format_game_links "
                "WHERE format_id = :id AND NOT (type_master_id = ANY(:ids))"
            ),
            {"id": format_id, "ids": wanted},
        )
        for game_id in wanted:
            await db.execute(
                text(
                    "INSERT INTO public.product_format_game_links (format_id, type_master_id) "
                    "VALUES (:id, :gid) ON CONFLICT (format_id, type_master_id) DO NOTHING"
                ),
                {"id": format_id, "gid": game_id},
            )
    except IntegrityError as exc:
        await db.rollback()
        log_hidden_error("super_admin_product_formats.replace_product_format_games", exc)
        raise HTTPException(status_code=409, detail="制約違反")
    await db.commit()
    games = await _game_ids_for(db, [format_id])
    return ProductFormatResponse(**dict(fmt), game_ids=games.get(format_id, []))


@router.delete(
    "/super-admin/product-formats/{format_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_product_format(
    format_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。products.product_format_id で参照中なら 409。"""
    # 参照チェック: products.product_format_id
    ref_products = await db.execute(
        text("SELECT 1 FROM public.products WHERE product_format_id = :id LIMIT 1"),
        {"id": format_id},
    )
    if ref_products.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このフォーマットは商品（products）で使用中のため削除できません",
        )
    result = await db.execute(
        text(
            "UPDATE public.product_formats SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id"
        ),
        {"id": format_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="フォーマットが見つかりません")
    await db.commit()
