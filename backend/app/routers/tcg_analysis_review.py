"""
PARITY-03 第1段階: 解析レビュー API。

エンドポイント:
  GET /api/v1/tcg/analysis-results
    認証: require_super_admin
    解析結果一覧（GAS: getAnalysisReviewPage 相当）
    SupplierDetailPage から provider フィルタで使用
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_analysis_review_svc import fetch_analysis_results

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
