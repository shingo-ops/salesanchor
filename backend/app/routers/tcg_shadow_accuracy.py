"""
解析精度管理（新方式）: 試運転（shadow）結果の精度サマリーと投稿照合 API。

docs/handoff/line-accuracy-pages/design.md §3-3。すべて読み取り専用。

エンドポイント:
  GET /api/v1/tcg/shadow-accuracy/summary                      精度サマリー
  GET /api/v1/tcg/shadow-accuracy/posts                        投稿（run）単位の一覧
  GET /api/v1/tcg/shadow-accuracy/posts/{extraction_job_id}    1投稿の詳細

認証: require_super_admin
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_shadow_accuracy_svc import (
    fetch_post_detail,
    fetch_posts,
    fetch_summary,
)

router = APIRouter()

# 期間（日数）。0 は全期間。
_ALLOWED_DAYS = (7, 30, 0)
_DAYS_ERROR = "days は 7、30、0（全期間）のみ許可されています"


def _validate_days(days: int) -> int:
    if days not in _ALLOWED_DAYS:
        raise HTTPException(status_code=422, detail=_DAYS_ERROR)
    return days


@router.get(
    "/tcg/shadow-accuracy/summary",
    dependencies=[Depends(require_super_admin)],
    summary="解析精度サマリー（新方式）",
)
async def get_shadow_accuracy_summary(
    days: int = Query(default=7),
    supplier_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await fetch_summary(db, days=_validate_days(days), supplier_id=supplier_id)


@router.get(
    "/tcg/shadow-accuracy/posts",
    dependencies=[Depends(require_super_admin)],
    summary="投稿照合の一覧（新方式・run 単位）",
)
async def get_shadow_accuracy_posts(
    days: int = Query(default=7),
    supplier_id: int | None = Query(default=None),
    needs_review: bool | None = Query(default=None),
    signal: Literal["S1", "S2", "S3", "S4", "S5", "S6"] | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await fetch_posts(
        db,
        days=_validate_days(days),
        supplier_id=supplier_id,
        needs_review=needs_review,
        signal=signal,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/tcg/shadow-accuracy/posts/{extraction_job_id}",
    dependencies=[Depends(require_super_admin)],
    summary="投稿照合の詳細（原文・全ブロック・兆候）",
)
async def get_shadow_accuracy_post_detail(
    extraction_job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    detail = await fetch_post_detail(db, str(extraction_job_id))
    if detail is None:
        raise HTTPException(status_code=404, detail="SHADOW_RUN_NOT_FOUND")
    return detail
