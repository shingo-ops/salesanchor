"""
PARITY-03 第1段階: 解析レビュー API。

エンドポイント:
  GET /api/v1/tcg/analysis-results
    認証: require_super_admin
    解析結果一覧（GAS: getAnalysisReviewPage 相当）
    SupplierDetailPage から provider フィルタで使用
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_analysis_review_svc import fetch_analysis_results
from app.services.tcg_condition_review_svc import condition_options
from app.services.tcg_sold_out_results_svc import (
    SoldOutResultsUnavailable,
    SourceScope,
    fetch_sold_out_results,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class GeminiFields(BaseModel):
    name: str
    quantity: str
    price: str
    unit: str
    state: str
    memo: str
    span: str


class SystemFields(BaseModel):
    product_title: str = ""
    product_uuid: str = ""
    product_id: str
    pid_resolved: str
    pid_basis: str
    unit: str
    unit_resolved: str
    condition: str
    status: str
    note: str
    exclusion: str


class ConditionReviewFields(BaseModel):
    condition_id: str | None
    review_version: str
    needs_review: bool
    review_reasons: str
    confirmed: bool
    classification: str


class AnalysisResultItem(BaseModel):
    extraction_item_id: str
    source_message_id: str
    provider: str
    raw_text: str
    gemini: GeminiFields
    system: SystemFields
    review_issues: list[str]
    condition_review: ConditionReviewFields | None = None


class AnalysisResultsResponse(BaseModel):
    items: list[AnalysisResultItem]
    total: int
    item_total: int
    offset: int
    limit: int
    providers: list[str]


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------

_STATUS_TABS = {
    "ALL", "NEEDS_REVIEW", "PRODUCT_MASTER_UNREGISTERED",
    "SUPPLIER_UNREGISTERED", "PRODUCT_ID_UNRESOLVED", "NORMAL_COMPLETED",
}


@router.get(
    "/tcg/analysis-results",
    response_model=AnalysisResultsResponse,
    summary="解析結果一覧（SupplierDetailPage から provider フィルタで使用）",
)
async def list_analysis_results(
    query: str | None = Query(default=None, description="商品名・仕入元・商品IDの部分一致検索"),
    provider: str | None = Query(default=None, description="仕入元名で絞り込み"),
    status_tab: str = Query(default="ALL", description="タブ絞り込み"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=500),
    review_only: bool = Query(default=False),
    unregistered_only: bool = Query(default=False),
    unresolved_unit_only: bool = Query(default=False),
    strip_raw_text: bool = Query(default=False, description="raw_text を省略（SupplierDetailPage 用）"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> AnalysisResultsResponse:
    if status_tab not in _STATUS_TABS:
        status_tab = "ALL"

    data = await fetch_analysis_results(
        db,
        query=query,
        provider=provider,
        status_tab=status_tab,
        offset=offset,
        limit=limit,
        review_only=review_only,
        unregistered_only=unregistered_only,
        unresolved_unit_only=unresolved_unit_only,
        strip_raw_text=strip_raw_text,
    )
    return AnalysisResultsResponse(
        items=data["items"],
        total=data["total"],
        item_total=data["item_total"],
        offset=data["offset"],
        limit=data["limit"],
        providers=data["providers"],
    )


@router.get("/tcg/conditions/review-options")
async def list_condition_review_options(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> list[dict]:
    return await condition_options(db)


class SoldOutResultItem(BaseModel):
    analysis_result_id: UUID
    extraction_item_id: UUID
    source_message_id: UUID
    supplier_id: UUID | None
    product_id: int | None
    provider: str
    product_title: str
    raw_product_name: str
    raw_quantity: str
    raw_price: str
    raw_unit: str
    raw_state: str
    raw_memo: str
    raw_text: str
    status: Literal["Sold out"]
    source_is_active: bool | None
    line_posted_at: AwareDatetime | None
    line_start: int | None
    line_end: int | None


class SoldOutResultsResponse(BaseModel):
    items: list[SoldOutResultItem]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    as_of: AwareDatetime


@router.get("/tcg/sold-out-results", response_model=SoldOutResultsResponse)
async def list_sold_out_results(
    response: Response,
    q: str | None = Query(default=None, max_length=100),
    source_scope: SourceScope = Query(default="all"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> SoldOutResultsResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        data = await fetch_sold_out_results(db, q=q, source_scope=source_scope, offset=offset, limit=limit)
        return SoldOutResultsResponse.model_validate(data)
    except (SQLAlchemyError, SoldOutResultsUnavailable, ValidationError):
        raise HTTPException(status_code=503, detail={"code": "SOLD_OUT_RESULTS_UNAVAILABLE"},
                            headers={"Cache-Control": "no-store"}) from None
