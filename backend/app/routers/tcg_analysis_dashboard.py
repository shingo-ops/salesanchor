"""
TCG 解析ダッシュボード API。

エンドポイント:
  GET /api/v1/tcg/analysis-dashboard/pipeline-summary
    認証: require_super_admin
    SELECT のみ。INSERT / UPDATE / DELETE / DDL を実行しない。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_analysis_dashboard_svc import (
    get_distribution_summary,
    get_extraction_product_ranking,
    get_import_summary,
    get_import_trend,
    get_pipeline_summary,
    get_pipeline_trend,
    get_supplier_pipeline,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class ExtractionByStatus(BaseModel):
    done: int
    error: int
    pending: int
    running: int
    empty: int


class ExtractionSummary(BaseModel):
    total: int
    by_status: ExtractionByStatus
    stale_running_count: int
    error_rate: float


class AnalysisSummary(BaseModel):
    total: int
    pid_resolved_count: int
    pid_resolved_rate: float
    unit_resolved_count: int
    unit_resolved_rate: float
    needs_review_count: int
    needs_review_rate: float
    missing_count: int


class ReviewReasonItem(BaseModel):
    reason: str
    count: int


class EngineInfo(BaseModel):
    current_model: str | None
    current_prompt_version: str | None
    current_engine_version: str | None


class RecentErrorItem(BaseModel):
    id: str
    error_message: str | None
    created_at: str | None
    prompt_version: str | None


class ExtractionBySupplierItem(BaseModel):
    supplier_code: str | None
    supplier_name: str | None
    total_jobs: int
    done_count: int
    error_count: int
    empty_count: int


class PipelineSummaryResponse(BaseModel):
    extraction: ExtractionSummary
    analysis: AnalysisSummary
    review_reasons: list[ReviewReasonItem]
    engine: EngineInfo
    recent_errors: list[RecentErrorItem]
    extraction_by_supplier: list[ExtractionBySupplierItem]


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/analysis-dashboard/pipeline-summary",
    response_model=PipelineSummaryResponse,
    summary="TCG 解析パイプライン サマリー（super_admin 限定）",
)
async def get_pipeline_summary_endpoint(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> PipelineSummaryResponse:
    result = await get_pipeline_summary(db)
    return PipelineSummaryResponse(**result)


class TrendDayItem(BaseModel):
    day: str
    extraction_total: int
    extraction_done: int
    extraction_error: int
    analysis_total: int
    pid_resolved: int
    unit_resolved: int
    needs_review: int


@router.get(
    "/tcg/analysis-dashboard/trend",
    response_model=list[TrendDayItem],
    summary="TCG 解析パイプライン 日別トレンド（super_admin 限定）",
)
async def get_pipeline_trend_endpoint(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> list[TrendDayItem]:
    result = await get_pipeline_trend(db, days)
    return [TrendDayItem(**item) for item in result]


class RecentImportItem(BaseModel):
    id: str
    filename: str | None
    message_count: int
    unresolved_count: int
    review_status: str | None
    created_at: str | None
    created_count: int


class ImportSummaryResponse(BaseModel):
    total_jobs: int
    ok_count: int
    pending_review_count: int
    total_messages: int
    total_unresolved: int
    unresolved_rate: float
    total_source_messages: int
    orphan_count: int
    active_message_count: int
    latest_import_at: str | None
    recent_imports: list[RecentImportItem]


class DistributionTargetItem(BaseModel):
    id: str
    name: str | None
    is_active: bool
    last_distributed_at: str | None
    last_distributed_count: int
    last_result: str | None


class DistributionSettingItem(BaseModel):
    key: str
    value: str | None
    note: str | None


class DistributionSummaryResponse(BaseModel):
    targets: list[DistributionTargetItem]
    active_target_count: int
    total_target_count: int
    total_last_distributed: int
    settings: list[DistributionSettingItem]


class ImportTrendItem(BaseModel):
    day: str
    job_count: int
    message_count: int
    unresolved_count: int


@router.get(
    "/tcg/analysis-dashboard/import-trend",
    response_model=list[ImportTrendItem],
    summary="TCG インポート工程 日別トレンド（super_admin 限定）",
)
async def get_import_trend_endpoint(
    days: int = Query(default=7, ge=1, le=360),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> list[ImportTrendItem]:
    result = await get_import_trend(db, days)
    return [ImportTrendItem(**item) for item in result]


@router.get(
    "/tcg/analysis-dashboard/import-summary",
    response_model=ImportSummaryResponse,
    summary="TCG インポート工程サマリー（super_admin 限定）",
)
async def get_import_summary_endpoint(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> ImportSummaryResponse:
    result = await get_import_summary(db)
    return ImportSummaryResponse(**result)


@router.get(
    "/tcg/analysis-dashboard/distribution-summary",
    response_model=DistributionSummaryResponse,
    summary="TCG 配信工程サマリー（super_admin 限定）",
)
async def get_distribution_summary_endpoint(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> DistributionSummaryResponse:
    result = await get_distribution_summary(db)
    return DistributionSummaryResponse(**result)


# ---------------------------------------------------------------------------
# 提供者別パイプライン スキーマ
# ---------------------------------------------------------------------------


class SupplierImportInfo(BaseModel):
    active_messages: int
    latest_received_at: str | None


class SupplierExtractionInfo(BaseModel):
    done: int
    empty: int
    error: int
    other: int
    status: str


class SupplierAnalysisInfo(BaseModel):
    total: int
    pid_resolved: int
    pid_unresolved: int
    unit_resolved: int
    unit_unresolved: int
    needs_review: int
    excluded: int
    price_ok: int
    price_missing: int
    distributable: int


class SupplierPipelineItem(BaseModel):
    channel_id: str
    channel_name: str
    import_info: SupplierImportInfo  # "import" は Python 予約語なので import_info
    extraction: SupplierExtractionInfo
    analysis: SupplierAnalysisInfo
    severity: str


class FunnelDropReasons(BaseModel):
    pid_unresolved: int
    unit_unresolved: int
    needs_review: int
    excluded: int
    price_missing: int


class FunnelSummary(BaseModel):
    active_messages: int
    extraction_done: int
    extraction_empty: int
    extraction_error: int
    analysis_total: int
    distributable: int
    drop_reasons: FunnelDropReasons


class SupplierPipelineResponse(BaseModel):
    suppliers: list[SupplierPipelineItem]
    funnel_summary: FunnelSummary


@router.get(
    "/tcg/analysis-dashboard/supplier-pipeline",
    response_model=SupplierPipelineResponse,
    summary="TCG 提供者別パイプライン（super_admin 限定）",
)
async def supplier_pipeline(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_super_admin),
) -> SupplierPipelineResponse:
    data = await get_supplier_pipeline(db)
    return SupplierPipelineResponse(**data)


# ---------------------------------------------------------------------------
# 抽出商品ランキング スキーマ
# ---------------------------------------------------------------------------


class ExtractionProductRankingItem(BaseModel):
    raw_product_name: str
    total_count: int
    resolved_count: int
    resolution_rate: float


class ExtractionProductRankingResponse(BaseModel):
    items: list[ExtractionProductRankingItem]


@router.get(
    "/tcg/analysis-dashboard/extraction-product-ranking",
    response_model=ExtractionProductRankingResponse,
    summary="TCG 抽出商品ランキング 解決率ワースト順（super_admin 限定）",
)
async def get_extraction_product_ranking_endpoint(
    days: int = Query(default=30, ge=1, le=360),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_super_admin),
) -> ExtractionProductRankingResponse:
    rows = await get_extraction_product_ranking(db, days)
    return ExtractionProductRankingResponse(items=[ExtractionProductRankingItem(**row) for row in rows])
