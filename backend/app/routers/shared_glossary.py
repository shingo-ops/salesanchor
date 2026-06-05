from __future__ import annotations

"""
ADR-SA-17: 共有辞書（Layer1）管理 + 昇格レビューキュー — SaaS管理者専用ルーター。

守るべき不変条件:
  - **I-7【最重要・機密保護】** 全エンドポイントが require_super_admin で構造的に保護され、
    いかなるテナント権限（require_permission）でも到達できない。
  - I-9 昇格は operator 承認必須・**匿名コピー**（提供テナント非開示）・非破壊・自動昇格しない。

エンドポイント:
  GET    /super-admin/shared-glossary                       共有辞書一覧（tenant_id IS NULL）
  POST   /super-admin/shared-glossary                       共有エントリ作成
  PATCH  /super-admin/shared-glossary/{id}                  共有エントリ更新
  DELETE /super-admin/shared-glossary/{id}                  共有エントリ削除
  GET    /super-admin/shared-glossary/promotions           昇格レビューキュー（匿名）
  POST   /super-admin/shared-glossary/promotions/{id}/approve  承認（匿名コピー）
  POST   /super-admin/shared-glossary/promotions/{id}/reject   却下
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import is_postgresql, require_super_admin
from app.database import get_db
from app.models import User
from app.services.translation_glossary import (
    GlossaryEntry,
    approve_promotion,
    create_glossary_entry,
    delete_shared_entry,
    list_promotion_queue,
    list_shared_glossary,
    reject_promotion,
    update_shared_entry,
)

logger = logging.getLogger(__name__)

# 全エンドポイントを is_super_admin で構造的に保護（I-7）。
router = APIRouter(
    prefix="/super-admin/shared-glossary",
    tags=["shared-glossary"],
    dependencies=[Depends(require_super_admin)],
)


async def _clear_tenant_context(db: AsyncSession) -> None:
    """app.tenant_id をクリアして RLS を「全行可視（operator 横断）」に倒す。

    共有辞書 / 昇格キューは全テナント横断で参照するため、コネクションプールの
    残留 app.tenant_id によって他テナントの提案行が RLS で隠れないようにする。
    """
    if is_postgresql(db):
        await db.execute(text("SET app.tenant_id = ''"))


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class SharedGlossaryEntryOut(BaseModel):
    id: int
    source_term: str
    target_text: str | None
    language_pair: str
    term_type: str
    is_active: bool
    source_ref: str | None
    notes: str | None
    share_status: str


class SharedGlossaryListResponse(BaseModel):
    items: list[SharedGlossaryEntryOut]
    total: int
    page: int
    per_page: int


class CreateSharedGlossaryRequest(BaseModel):
    source_term: str = Field(min_length=1, max_length=500)
    target_text: str | None = None
    language_pair: str = Field(default="en->ja", min_length=3, max_length=20)
    term_type: str = Field(default="general", max_length=30)
    notes: str | None = Field(default=None, max_length=500)


class UpdateSharedGlossaryRequest(BaseModel):
    source_term: str | None = Field(default=None, min_length=1, max_length=500)
    target_text: str | None = Field(default=None)
    term_type: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class PromotionQueueItemOut(BaseModel):
    """昇格レビューキュー 1 件。匿名性のため提供テナントは含めない（I-9）。"""

    id: int
    source_term: str
    target_text: str | None
    language_pair: str
    term_type: str
    notes: str | None
    share_proposed_at: str | None


class PromotionQueueResponse(BaseModel):
    items: list[PromotionQueueItemOut]
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# Layer1 共有辞書 CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=SharedGlossaryListResponse)
async def get_shared_glossary(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    language_pair: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> SharedGlossaryListResponse:
    """共有ベース辞書（tenant_id IS NULL）の一覧。"""
    await _clear_tenant_context(db)
    entries, total = await list_shared_glossary(
        db, language_pair=language_pair, page=page, per_page=per_page
    )
    return SharedGlossaryListResponse(
        items=[_entry_out(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=SharedGlossaryEntryOut, status_code=status.HTTP_201_CREATED)
async def create_shared_glossary(
    body: CreateSharedGlossaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> SharedGlossaryEntryOut:
    """共有ベース辞書エントリを作成（tenant_id NULL）。"""
    await _clear_tenant_context(db)
    entry = await create_glossary_entry(
        db=db,
        tenant_id=None,  # NULL = 全テナント共有
        source_term=body.source_term,
        target_text=body.target_text,
        language_pair=body.language_pair,
        term_type=body.term_type,
        notes=body.notes,
    )
    await db.commit()
    return _entry_out(entry)


@router.patch("/{entry_id}", response_model=SharedGlossaryEntryOut)
async def patch_shared_glossary(
    entry_id: int,
    body: UpdateSharedGlossaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> SharedGlossaryEntryOut:
    """共有ベース辞書エントリを更新。"""
    from app.services.translation_glossary import _UNSET

    await _clear_tenant_context(db)
    target_text_arg = body.target_text if "target_text" in body.model_fields_set else _UNSET
    entry = await update_shared_entry(
        db=db,
        entry_id=entry_id,
        source_term=body.source_term,
        target_text=target_text_arg,
        term_type=body.term_type,
        notes=body.notes,
        is_active=body.is_active,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="共有グロッサリエントリが見つかりません",
        )
    await db.commit()
    return _entry_out(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_shared_glossary(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> None:
    """共有ベース辞書エントリを削除。"""
    await _clear_tenant_context(db)
    deleted = await delete_shared_entry(db, entry_id=entry_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="共有グロッサリエントリが見つかりません",
        )
    await db.commit()


# ---------------------------------------------------------------------------
# 昇格レビューキュー（I-9）
# ---------------------------------------------------------------------------


@router.get("/promotions", response_model=PromotionQueueResponse)
async def get_promotion_queue(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> PromotionQueueResponse:
    """共有提案中（share_status='proposed'）の私有エントリ一覧（匿名）。"""
    await _clear_tenant_context(db)
    items, total = await list_promotion_queue(db, page=page, per_page=per_page)
    return PromotionQueueResponse(
        items=[
            PromotionQueueItemOut(
                id=i.id,
                source_term=i.source_term,
                target_text=i.target_text,
                language_pair=i.language_pair,
                term_type=i.term_type,
                notes=i.notes,
                share_proposed_at=(
                    i.share_proposed_at.isoformat() if i.share_proposed_at else None
                ),
            )
            for i in items
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/promotions/{entry_id}/approve")
async def approve_promotion_endpoint(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> dict:
    """提案を承認し、共有ベースへ **匿名コピー**（提供テナント非開示・非破壊）。"""
    await _clear_tenant_context(db)
    ok = await approve_promotion(db, entry_id=entry_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提案が見つかりません（既にレビュー済みの可能性）",
        )
    await db.commit()
    return {"approved": True, "entry_id": entry_id}


@router.post("/promotions/{entry_id}/reject")
async def reject_promotion_endpoint(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> dict:
    """提案を却下（私有エントリは残す・非破壊）。"""
    await _clear_tenant_context(db)
    ok = await reject_promotion(db, entry_id=entry_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提案が見つかりません（既にレビュー済みの可能性）",
        )
    await db.commit()
    return {"rejected": True, "entry_id": entry_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry_out(entry: GlossaryEntry) -> SharedGlossaryEntryOut:
    return SharedGlossaryEntryOut(
        id=entry.id,
        source_term=entry.source_term,
        target_text=entry.target_text,
        language_pair=entry.language_pair,
        term_type=entry.term_type,
        is_active=entry.is_active,
        source_ref=entry.source_ref,
        notes=entry.notes,
        share_status=entry.share_status,
    )
