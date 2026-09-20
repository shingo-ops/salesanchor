"""
テナント用 public.tcg_note_master CRUD ルーター。

共用エントリ（tenant_id IS NULL）とテナント個別エントリ（tenant_id = current）を
GET で両方返す。POST/PATCH/DELETE はテナント個別エントリのみ操作可能。

API:
  GET    /api/v1/note-master
  POST   /api/v1/note-master
  PATCH  /api/v1/note-master/{id}
  DELETE /api/v1/note-master/{id}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    require_permission,
    reset_tenant_context,
)
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
    "/note-master",
    response_model=list[TcgNoteMasterResponse],
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def list_note_master(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        text(
            f"SELECT {_NOTE_COLS} FROM public.tcg_note_master "
            "WHERE tenant_id IS NULL OR tenant_id = :tenant_id "
            "ORDER BY priority, id LIMIT :limit OFFSET :offset"
        ),
        {"tenant_id": tenant_id, "limit": per_page, "offset": offset},
    )
    return [TcgNoteMasterResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/note-master",
    response_model=TcgNoteMasterResponse,
    status_code=201,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def create_note_master(
    data: TcgNoteMasterCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.tcg_note_master "
                "(label_ja, label_en, enabled, search_keywords, exclude_keywords, "
                " category, priority, match_type, search_pattern, label_template, tenant_id) "
                "VALUES (:label_ja, :label_en, :enabled, :search_keywords, :exclude_keywords, "
                "        :category, :priority, :match_type, :search_pattern, :label_template, :tenant_id) "
                f"RETURNING {_NOTE_COLS}"
            ),
            {**data.model_dump(), "tenant_id": tenant_id},
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"重複または制約違反: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return TcgNoteMasterResponse(**dict(row))


@router.patch(
    "/note-master/{note_id}",
    response_model=TcgNoteMasterResponse,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def update_note_master(
    note_id: int,
    data: TcgNoteMasterUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _NOTE_UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = note_id
    update_data["tenant_id"] = tenant_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.tcg_note_master SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id = :tenant_id RETURNING {_NOTE_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="備考マスタが見つかりません（テナント個別エントリのみ編集可能です）")
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return TcgNoteMasterResponse(**dict(row))


@router.delete(
    "/note-master/{note_id}",
    status_code=204,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def delete_note_master(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    result = await db.execute(
        text(
            "DELETE FROM public.tcg_note_master "
            "WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": note_id, "tenant_id": tenant_id},
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="備考マスタが見つかりません（テナント個別エントリのみ削除可能です）",
        )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
