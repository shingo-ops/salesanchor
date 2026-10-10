"""
v102 の投稿ごとに「Gemini の書き写し」を見て直す API（便C1）。

エンドポイント（すべて super_admin）:
  GET /api/v1/tcg/v102/posts                 要確認の投稿の一覧
  GET /api/v1/tcg/v102/posts/{job_id}        原文の行と件
  PUT /api/v1/tcg/v102/posts/{job_id}/items  件の全体を保存（直した記録は item_corrections）

設計: docs/handoff/v102-prod-switch/design.md §13-5。保存後は D1 の enqueue_v102_reanalyze で、その投稿のシステム段のやり直しを積む。
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.services import v102_transcription_svc as svc
from app.services.review_reason_codes_svc import load_review_reason_codes
from app.tasks.tcg_extraction import enqueue_v102_reanalyze

logger = logging.getLogger(__name__)

router = APIRouter()

LIST_LIMIT_DEFAULT = 50
LIST_LIMIT_MAX = 200
TEXT_MAX_LENGTH = 200


class ReasonDetail(BaseModel):
    code: str
    source: str | None
    fix_stage: str | None


class PostSummary(BaseModel):
    job_id: str
    source_message_id: str
    provider: str
    line_posted_at: AwareDatetime | None
    job_review_reason_details: list[ReasonDetail]
    item_count: int
    extraction_item_count: int


class PostListResponse(BaseModel):
    items: list[PostSummary]
    total: int
    limit: int
    offset: int


class RawLine(BaseModel):
    number: int
    text: str


class PostItem(BaseModel):
    id: str
    gemini_index: int | None
    source_lines: list[int]
    raw_price: str | None
    raw_quantity: str | None
    review_reason_details: list[ReasonDetail]


class PostDetailResponse(BaseModel):
    job_id: str
    source_message_id: str
    provider: str
    line_posted_at: AwareDatetime | None
    lines: list[RawLine]
    job_review_reason_details: list[ReasonDetail]
    gemini_unsure: Any = None
    items: list[PostItem]


class TranscriptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    source_lines: list[StrictInt] = Field(min_length=1)
    raw_price: str | None = Field(default=None, max_length=TEXT_MAX_LENGTH)
    raw_quantity: str | None = Field(default=None, max_length=TEXT_MAX_LENGTH)

    @field_validator("source_lines")
    @classmethod
    def lines_unique(cls, lines: list[int]) -> list[int]:
        if len(set(lines)) != len(lines):
            raise ValueError("source_lines must not contain duplicates")
        return lines


class SaveItemsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_message_id: UUID
    items: list[TranscriptionItem] = Field(min_length=1)

    @model_validator(mode="after")
    def ids_unique(self) -> SaveItemsRequest:
        ids = [item.id for item in self.items if item.id is not None]
        if len(set(ids)) != len(ids):
            raise ValueError("items[].id must not be duplicated")
        return self


class SaveItemsResponse(BaseModel):
    changed: bool
    item_ids: list[str]
    enqueued: bool


async def _load_job_or_http_error(db: AsyncSession, job_id: str) -> svc.PostJob:
    try:
        return await svc.load_job(db, job_id)
    except svc.PostNotFound as exc:
        raise HTTPException(404, "Post not found") from exc
    except svc.PostNotV102 as exc:
        raise HTTPException(409, "Only v102 posts can be edited") from exc


@router.get("/tcg/v102/posts", response_model=PostListResponse, summary="v102 の要確認の投稿の一覧")
async def list_v102_posts(
    limit: int = Query(LIST_LIMIT_DEFAULT, ge=1, le=LIST_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> dict:
    return await svc.list_posts(db, await load_review_reason_codes(db), limit=limit, offset=offset)


@router.get("/tcg/v102/posts/{job_id}", response_model=PostDetailResponse, summary="v102 の投稿の原文の行と件")
async def get_v102_post(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> dict:
    job = await _load_job_or_http_error(db, job_id)
    return await svc.get_post(db, job, await load_review_reason_codes(db))


@router.put("/tcg/v102/posts/{job_id}/items", response_model=SaveItemsResponse, summary="v102 の投稿の件（書き写し）を直して保存する")
async def save_v102_post_items(
    job_id: str,
    body: SaveItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> SaveItemsResponse:
    job = await _load_job_or_http_error(db, job_id)
    if str(body.source_message_id) != job.source_message_id:
        raise HTTPException(422, "source_message_id does not match the post")
    items = [
        svc.ItemInput(
            id=None if item.id is None else str(item.id), source_lines=sorted(item.source_lines),
            raw_price=item.raw_price, raw_quantity=item.raw_quantity,
        )
        for item in body.items
    ]
    try:
        result = await svc.apply_transcription_edit(db, job, items, current_user.email)
    except svc.InvalidTranscription as exc:
        raise HTTPException(422, str(exc)) from exc
    if result.changed:
        enqueue_v102_reanalyze(job.job_id)
    return SaveItemsResponse(changed=result.changed, item_ids=result.item_ids, enqueued=result.changed)
