"""
中央 admin 用 public.tcg_note_master CRUD ルーター。

API:
  GET    /api/v1/super-admin/note-master
  POST   /api/v1/super-admin/note-master
  PATCH  /api/v1/super-admin/note-master/{id}
  DELETE /api/v1/super-admin/note-master/{id}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.schemas.central_masters import (
    TcgNoteMasterCreate,
    TcgNoteMasterResponse,
    TcgNoteMasterUpdate,
)

router = APIRouter()

_NOTE_COLS = (
    "id, label_ja, label_en, enabled, search_keywords, exclude_keywords, "
    "category, priority, match_type, search_pattern, label_template, "
    "created_at, updated_at"
)

_NOTE_UPDATABLE = {
    "label_ja",
    "label_en",
    "enabled",
    "search_keywords",
    "exclude_keywords",
    "category",
    "priority",
    "match_type",
    "search_pattern",
    "label_template",
}


@router.get(
    "/super-admin/note-master",
    response_model=list[TcgNoteMasterResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_note_master(
    q: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    conditions: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if q:
        conditions.append(
            "(label_ja ILIKE :q OR label_en ILIKE :q OR category ILIKE :q)"
        )
        params["q"] = f"%{q}%"
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_NOTE_COLS} FROM public.tcg_note_master {where} "
            "ORDER BY priority, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [TcgNoteMasterResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/note-master",
    response_model=TcgNoteMasterResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_note_master(
    data: TcgNoteMasterCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.tcg_note_master "
                "(label_ja, label_en, enabled, search_keywords, exclude_keywords, "
                " category, priority, match_type, search_pattern, label_template, tenant_id) "
                "VALUES (:label_ja, :label_en, :enabled, :search_keywords, :exclude_keywords, "
                "        :category, :priority, :match_type, :search_pattern, :label_template, NULL) "
                f"RETURNING {_NOTE_COLS}"
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
    return TcgNoteMasterResponse(**dict(row))


@router.patch(
    "/super-admin/note-master/{note_id}",
    response_model=TcgNoteMasterResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_note_master(
    note_id: int,
    data: TcgNoteMasterUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _NOTE_UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = note_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.tcg_note_master SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id IS NULL RETURNING {_NOTE_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="備考マスタが見つかりません")
    await db.commit()
    return TcgNoteMasterResponse(**dict(row))


@router.delete(
    "/super-admin/note-master/{note_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_note_master(
    note_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text(
            "DELETE FROM public.tcg_note_master "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": note_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="備考マスタが見つかりません")
    await db.commit()
