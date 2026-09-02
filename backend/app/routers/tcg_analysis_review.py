"""
PARITY-03 第1段階: 解析レビュー API。

エンドポイント:
  GET /api/v1/tcg/analysis-results
    認証: require_super_admin
    解析結果一覧（GAS: getAnalysisReviewPage 相当）

  GET /api/v1/tcg/analysis-results/status-counts
    認証: require_super_admin
    タブ別件数（GAS: previewAnalysisReviewStatusTabs 相当）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_analysis_review_svc import (
    fetch_analysis_results,
    fetch_status_counts,
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
    product_id: str
    pid_resolved: str
    pid_basis: str
    unit: str
    unit_resolved: str
    condition: str
    status: str
    note: str
    exclusion: str


class AnalysisResultItem(BaseModel):
    extraction_item_id: str
    source_message_id: str
    provider: str
    raw_text: str
    gemini: GeminiFields
    system: SystemFields
    review_issues: list[str]


class StatusTabCounts(BaseModel):
    ALL: int = 0
    NEEDS_REVIEW: int = 0
    PRODUCT_MASTER_UNREGISTERED: int = 0
    SUPPLIER_UNREGISTERED: int = 0
    PRODUCT_ID_UNRESOLVED: int = 0
    NORMAL_COMPLETED: int = 0


class AnalysisResultsResponse(BaseModel):
    items: list[AnalysisResultItem]
    total: int
    item_total: int
    offset: int
    limit: int
    providers: list[str]
    status_tab_counts: StatusTabCounts


class StatusCountsResponse(BaseModel):
    status_tab_counts: StatusTabCounts


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
    summary="解析結果一覧（PARITY-03 第1段階）",
)
async def list_analysis_results(
    query: str | None = Query(default=None, description="商品名・仕入元・商品IDの部分一致検索"),
    provider: str | None = Query(default=None, description="仕入元名で絞り込み"),
    status_tab: str = Query(default="ALL", description="タブ絞り込み"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    review_only: bool = Query(default=False, description="要確認のみ"),
    unregistered_only: bool = Query(default=False, description="マスタ未登録のみ"),
    unresolved_unit_only: bool = Query(default=False, description="単位未解決のみ"),
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
    )
    return AnalysisResultsResponse(
        items=data["items"],
        total=data["total"],
        item_total=data["item_total"],
        offset=data["offset"],
        limit=data["limit"],
        providers=data["providers"],
        status_tab_counts=StatusTabCounts(**data["status_tab_counts"]),
    )


@router.get(
    "/tcg/analysis-results/status-counts",
    response_model=StatusCountsResponse,
    summary="解析結果タブ件数（PARITY-03 第1段階）",
)
async def get_status_counts(
    query: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> StatusCountsResponse:
    counts = await fetch_status_counts(db, query=query, provider=provider)
    return StatusCountsResponse(status_tab_counts=StatusTabCounts(**counts))
