"""
design.md PR-D: 試運転（Shadow run）の確認画面用 API。

エンドポイント:
  GET  /api/v1/tcg/shadow-results               確認待ち一覧
  GET  /api/v1/tcg/shadow-results/bottlenecks    詰まりの集計
  POST /api/v1/tcg/shadow-results/keyword-preview ワード追加の影響プレビュー（DB書き込みなし）

認証: require_super_admin
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_shadow_review_svc import (
    KeywordPreviewProductNotFound,
    fetch_bottlenecks,
    fetch_shadow_results,
    preview_keyword_change,
)

router = APIRouter()


@router.get(
    "/tcg/shadow-results",
    dependencies=[Depends(require_super_admin)],
    summary="試運転の確認待ち一覧（design.md PR-D）",
)
async def get_shadow_results(
    needs_review: bool | None = Query(default=None),
    supplier_id: int | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await fetch_shadow_results(
        db, needs_review=needs_review, supplier_id=supplier_id, offset=offset, limit=limit
    )


@router.get(
    "/tcg/shadow-results/bottlenecks",
    dependencies=[Depends(require_super_admin)],
    summary="仕入元別・項目別の詰まり集計（design.md PR-D）",
)
async def get_shadow_bottlenecks(
    days: int = Query(default=7),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if days not in (7, 30):
        raise HTTPException(status_code=422, detail="days は 7 または 30 のみ許可されています")
    return await fetch_bottlenecks(db, days=days)  # type: ignore[arg-type]


class KeywordPreviewRequest(BaseModel):
    product_id: int
    kind: Literal["search", "exclude"]
    keyword: str


@router.post(
    "/tcg/shadow-results/keyword-preview",
    dependencies=[Depends(require_super_admin)],
    summary="ワード追加の影響プレビュー（design.md PR-D、DB書き込みなし）",
)
async def post_keyword_preview(
    body: KeywordPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        return await preview_keyword_change(
            db, product_id=body.product_id, kind=body.kind, keyword=body.keyword
        )
    except KeywordPreviewProductNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
