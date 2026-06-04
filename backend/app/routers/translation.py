from __future__ import annotations

"""
ADR-110: 翻訳サブシステム API ルーター。

エンドポイント:
  POST   /translation/outbound-preview           送信下訳生成（送信しない）
  POST   /translation/outbound-confirm/{draft_id} 送信下訳を「確認済み」にマーク
  GET    /translation/glossary                   グロッサリ一覧
  POST   /translation/glossary                   グロッサリエントリ作成
  PATCH  /translation/glossary/{id}              グロッサリエントリ更新
  DELETE /translation/glossary/{id}              グロッサリエントリ削除
  POST   /translation/glossary/seed-products     商品マスタから seed
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant, get_current_user, require_permission
from app.auth.models import User
from app.database import get_db, reset_tenant_context
from app.services.inventory_parser_llm import LLMConfigError, LLMParseError
from app.services.message_translator import (
    BudgetExceededError,
    confirm_outbound_draft,
    generate_outbound_draft,
)
from app.services.translation_glossary import (
    create_glossary_entry,
    delete_glossary_entry,
    list_glossary,
    seed_glossary_from_products,
    update_glossary_entry,
)
from app.tenant.utils import tenant_table_ref

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translation", tags=["translation"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class OutboundPreviewRequest(BaseModel):
    draft_text: str = Field(min_length=1, max_length=5000)
    lead_id: int | None = None
    target_language: str = Field(default="en", min_length=2, max_length=10)


class FlaggedTermOut(BaseModel):
    term: str
    reason: str


class OutboundPreviewResponse(BaseModel):
    draft_id: int
    draft_text: str
    confidence: float
    flagged_terms: list[FlaggedTermOut]
    model: str
    is_low_confidence: bool


class ConfirmOutboundRequest(BaseModel):
    final_text: str = Field(min_length=1, max_length=5000)


class GlossaryEntryOut(BaseModel):
    id: int
    tenant_id: int | None
    source_term: str
    target_text: str | None
    language_pair: str
    term_type: str
    is_active: bool
    source_ref: str | None
    notes: str | None


class GlossaryListResponse(BaseModel):
    items: list[GlossaryEntryOut]
    total: int
    page: int
    per_page: int


class CreateGlossaryRequest(BaseModel):
    source_term: str = Field(min_length=1, max_length=500)
    target_text: str | None = None          # None = 「訳さない」
    language_pair: str = Field(default="en->ja", min_length=3, max_length=20)
    term_type: str = Field(default="general", max_length=30)
    notes: str | None = Field(default=None, max_length=500)


class UpdateGlossaryRequest(BaseModel):
    source_term: str | None = Field(default=None, min_length=1, max_length=500)
    target_text: str | None = None
    term_type: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Outbound translation endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/outbound-preview",
    response_model=OutboundPreviewResponse,
    dependencies=[Depends(require_permission("messaging.send"))],
)
async def outbound_preview(
    body: OutboundPreviewRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> OutboundPreviewResponse:
    """担当者の日本語下書きを英訳して下訳を返す。

    送信はしない。返却された draft_id を /outbound-confirm/{draft_id} に渡して
    人が確認した上で送信する（確認ステップを飛ばした送信経路は存在しない）。
    """
    from app.services.message_translator import CONF_THRESHOLD_SEND

    drafts_t = tenant_table_ref(db, tenant_id, "outbound_translation_drafts")

    try:
        draft_id, result = await generate_outbound_draft(
            db=db,
            tenant_id=tenant_id,
            drafts_table_ref=drafts_t,
            lead_id=body.lead_id,
            draft_text=body.draft_text,
            target_language=body.target_language,
        )
    except BudgetExceededError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="今月の翻訳上限に達しました",
        )
    except LLMConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"翻訳サービス設定エラー: {exc}",
        )
    except LLMParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"翻訳失敗: {exc}",
        )

    return OutboundPreviewResponse(
        draft_id=draft_id,
        draft_text=result.translated_text,
        confidence=result.confidence,
        flagged_terms=[
            FlaggedTermOut(term=f.term, reason=f.reason)
            for f in result.flagged_terms
        ],
        model=result.engine,
        is_low_confidence=result.confidence < CONF_THRESHOLD_SEND,
    )


@router.post(
    "/outbound-confirm/{draft_id}",
    dependencies=[Depends(require_permission("messaging.send"))],
)
async def outbound_confirm(
    draft_id: int,
    body: ConfirmOutboundRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> dict:
    """送信下訳を「人が確認済み」にマーク。

    このエンドポイントは送信操作ではない。
    送信は既存の /leads/{lead_id}/messages POST を使う。
    confirmed_at を設定することで「確認済み」状態を記録する。
    """
    drafts_t = tenant_table_ref(db, tenant_id, "outbound_translation_drafts")
    updated = await confirm_outbound_draft(
        db=db,
        drafts_table_ref=drafts_t,
        draft_id=draft_id,
        tenant_id=tenant_id,
        final_text=body.final_text,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="下訳が見つからないか、既に確認済みです",
        )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return {"confirmed": True, "final_text": body.final_text}


# ---------------------------------------------------------------------------
# Glossary CRUD endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/glossary",
    response_model=GlossaryListResponse,
    dependencies=[Depends(require_permission("messaging.view"))],
)
async def get_glossary(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    language_pair: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> GlossaryListResponse:
    """グロッサリ一覧を返す（テナント固有 + グローバル共有）。"""
    entries, total = await list_glossary(
        db, tenant_id, language_pair=language_pair, page=page, per_page=per_page
    )
    return GlossaryListResponse(
        items=[
            GlossaryEntryOut(
                id=e.id,
                tenant_id=e.tenant_id,
                source_term=e.source_term,
                target_text=e.target_text,
                language_pair=e.language_pair,
                term_type=e.term_type,
                is_active=e.is_active,
                source_ref=e.source_ref,
                notes=e.notes,
            )
            for e in entries
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/glossary",
    response_model=GlossaryEntryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("messaging.send"))],
)
async def create_glossary(
    body: CreateGlossaryRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> GlossaryEntryOut:
    """グロッサリエントリを作成（テナント固有として登録）。"""
    entry = await create_glossary_entry(
        db=db,
        tenant_id=tenant_id,
        source_term=body.source_term,
        target_text=body.target_text,
        language_pair=body.language_pair,
        term_type=body.term_type,
        notes=body.notes,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return GlossaryEntryOut(
        id=entry.id,
        tenant_id=entry.tenant_id,
        source_term=entry.source_term,
        target_text=entry.target_text,
        language_pair=entry.language_pair,
        term_type=entry.term_type,
        is_active=entry.is_active,
        source_ref=entry.source_ref,
        notes=entry.notes,
    )


@router.patch(
    "/glossary/{entry_id}",
    response_model=GlossaryEntryOut,
    dependencies=[Depends(require_permission("messaging.send"))],
)
async def update_glossary(
    entry_id: int,
    body: UpdateGlossaryRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> GlossaryEntryOut:
    """グロッサリエントリを更新（テナント所有のもののみ）。"""
    entry = await update_glossary_entry(
        db=db,
        entry_id=entry_id,
        tenant_id=tenant_id,
        source_term=body.source_term,
        target_text=body.target_text,
        term_type=body.term_type,
        notes=body.notes,
        is_active=body.is_active,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="グロッサリエントリが見つかりません（テナント所有のエントリのみ編集可）",
        )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return GlossaryEntryOut(
        id=entry.id,
        tenant_id=entry.tenant_id,
        source_term=entry.source_term,
        target_text=entry.target_text,
        language_pair=entry.language_pair,
        term_type=entry.term_type,
        is_active=entry.is_active,
        source_ref=entry.source_ref,
        notes=entry.notes,
    )


@router.delete(
    "/glossary/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("messaging.send"))],
)
async def delete_glossary(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> None:
    """グロッサリエントリを削除（テナント所有のもののみ）。グローバルエントリは削除不可。"""
    deleted = await delete_glossary_entry(db=db, entry_id=entry_id, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="グロッサリエントリが見つかりません（テナント所有のエントリのみ削除可）",
        )
    await db.commit()
    await reset_tenant_context(db, tenant_id)


@router.post(
    "/glossary/seed-products",
    dependencies=[Depends(require_permission("messaging.send"))],
)
async def seed_products_to_glossary(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> dict:
    """商品マスタ（public.products）の商品名をグロッサリに seed する。

    既存エントリはスキップ（上書きしない）。
    """
    count = await seed_glossary_from_products(db, tenant_id)
    return {"seeded": count, "message": f"{count} 件の商品名をグロッサリに追加しました"}
