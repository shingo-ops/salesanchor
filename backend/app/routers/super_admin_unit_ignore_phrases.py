"""
中央 admin 用 public.line_unit_ignore_phrases（単位にしない言い回し）CRUD ルーター。

API:
  GET    /api/v1/super-admin/unit-ignore-phrases
  POST   /api/v1/super-admin/unit-ignore-phrases
  PATCH  /api/v1/super-admin/unit-ignore-phrases/{id}
  DELETE /api/v1/super-admin/unit-ignore-phrases/{id}

手本: super_admin_units.py。
reset_tenant_context() 不使用: get_current_tenant を付けない設計のため
テナント context は設定されない（super_admin_tenants.py:11,86 と同じ）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.schemas.central_masters import (
    UnitIgnorePhraseCreate,
    UnitIgnorePhraseResponse,
    UnitIgnorePhraseUpdate,
)

router = APIRouter()

_COLS = "id, phrase, note, is_active, created_at, updated_at"
_UPDATABLE = {"phrase", "note", "is_active"}
_NOT_FOUND = "言い回しが見つかりません"


@router.get(
    "/super-admin/unit-ignore-phrases",
    response_model=list[UnitIgnorePhraseResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_unit_ignore_phrases(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM public.line_unit_ignore_phrases "
            "ORDER BY is_active DESC, id"
        )
    )
    return [UnitIgnorePhraseResponse(**dict(r)) for r in result.mappings().all()]


@router.post(
    "/super-admin/unit-ignore-phrases",
    response_model=UnitIgnorePhraseResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_unit_ignore_phrase(
    data: UnitIgnorePhraseCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.line_unit_ignore_phrases (phrase, note, is_active) "
                f"VALUES (:phrase, :note, :is_active) RETURNING {_COLS}"
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
    return UnitIgnorePhraseResponse(**dict(row))


@router.patch(
    "/super-admin/unit-ignore-phrases/{phrase_id}",
    response_model=UnitIgnorePhraseResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_unit_ignore_phrase(
    phrase_id: int,
    data: UnitIgnorePhraseUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = {
        k: v for k, v in data.model_dump(exclude_unset=True).items() if k in _UPDATABLE
    }
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = phrase_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.line_unit_ignore_phrases SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    await db.commit()
    return UnitIgnorePhraseResponse(**dict(row))


@router.delete(
    "/super-admin/unit-ignore-phrases/{phrase_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_unit_ignore_phrase(
    phrase_id: int,
    db: AsyncSession = Depends(get_db),
):
    """物理削除。無効化は PATCH is_active=false を使う。"""
    result = await db.execute(
        text("DELETE FROM public.line_unit_ignore_phrases WHERE id = :id"),
        {"id": phrase_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    await db.commit()
