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
from sqlalchemy import text
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
    null_posted_at_count: int = 0


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


# ---------------------------------------------------------------------------
# 抽出エラーログ
# ---------------------------------------------------------------------------

_TCG_SCHEMA = "public"


# ---------------------------------------------------------------------------
# コストサマリー スキーマ
# ---------------------------------------------------------------------------


class CostDailyItem(BaseModel):
    date: str
    total_calls: int
    success_calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostBySupplierItem(BaseModel):
    supplier_name: str | None
    total_calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    avg_items: float


class CostTotal(BaseModel):
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostBudget(BaseModel):
    monthly_budget_usd: float
    current_month_usd: float


class CostSummaryResponse(BaseModel):
    daily: list[CostDailyItem]
    by_supplier: list[CostBySupplierItem]
    total: CostTotal
    budget: CostBudget


@router.get(
    "/tcg/analysis-dashboard/cost-summary",
    response_model=CostSummaryResponse,
    summary="TCG Gemini APIコストサマリー（super_admin 限定）",
)
async def get_cost_summary(
    days: int = Query(default=7, ge=1, le=360),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_super_admin),
) -> CostSummaryResponse:
    # --- daily ---
    daily_rows = (await db.execute(text(f"""
        SELECT
            DATE(ea.started_at) AS date,
            COUNT(*) AS total_calls,
            COUNT(*) FILTER (WHERE ea.phase = 'completed') AS success_calls,
            COALESCE(SUM(COALESCE(ea.input_tokens, ea.input_bytes / 3)), 0)::bigint AS input_tokens,
            COALESCE(SUM(COALESCE(ea.output_tokens, 0)), 0)::bigint AS output_tokens,
            COALESCE(SUM(ea.cost_usd), 0.0)::double precision AS cost_usd
        FROM {_TCG_SCHEMA}.extraction_attempts ea
        WHERE ea.started_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY DATE(ea.started_at)
        ORDER BY date DESC
    """), {"days": days})).mappings().all()

    # --- by_supplier ---
    supplier_rows = (await db.execute(text(f"""
        SELECT
            s.name AS supplier_name,
            COUNT(*) AS total_calls,
            COALESCE(SUM(COALESCE(ea.input_tokens, ea.input_bytes / 3)), 0)::bigint AS input_tokens,
            COALESCE(SUM(COALESCE(ea.output_tokens, 0)), 0)::bigint AS output_tokens,
            COALESCE(SUM(ea.cost_usd), 0.0)::double precision AS cost_usd,
            COALESCE(AVG(NULLIF(ea.item_count, 0)), 0.0)::double precision AS avg_items
        FROM {_TCG_SCHEMA}.extraction_attempts ea
        JOIN {_TCG_SCHEMA}.extraction_jobs ej ON ej.id = ea.extraction_job_id
        JOIN {_TCG_SCHEMA}.source_messages sm ON sm.id = ea.source_message_id
        LEFT JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
        LEFT JOIN public.suppliers s ON s.id = sc.supplier_id
        WHERE ea.started_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY s.name
        ORDER BY cost_usd DESC
    """), {"days": days})).mappings().all()

    # --- total ---
    total_row = (await db.execute(text(f"""
        SELECT
            COUNT(*) AS calls,
            COALESCE(SUM(COALESCE(ea.input_tokens, ea.input_bytes / 3)), 0)::bigint AS input_tokens,
            COALESCE(SUM(COALESCE(ea.output_tokens, 0)), 0)::bigint AS output_tokens,
            COALESCE(SUM(ea.cost_usd), 0.0)::double precision AS cost_usd
        FROM {_TCG_SCHEMA}.extraction_attempts ea
        WHERE ea.started_at >= NOW() - INTERVAL '1 day' * :days
    """), {"days": days})).mappings().first()

    # --- budget (全テナント合算) ---
    budget_row = (await db.execute(text("""
        SELECT
            COALESCE(SUM(monthly_budget_usd), 0.0)::double precision AS monthly_budget_usd,
            COALESCE(SUM(current_month_usd), 0.0)::double precision AS current_month_usd
        FROM public.tenant_llm_budgets
    """))).mappings().first()

    return CostSummaryResponse(
        daily=[
            CostDailyItem(
                date=str(r["date"]),
                total_calls=int(r["total_calls"]),
                success_calls=int(r["success_calls"]),
                input_tokens=int(r["input_tokens"]),
                output_tokens=int(r["output_tokens"]),
                cost_usd=float(r["cost_usd"]),
            )
            for r in daily_rows
        ],
        by_supplier=[
            CostBySupplierItem(
                supplier_name=r["supplier_name"],
                total_calls=int(r["total_calls"]),
                input_tokens=int(r["input_tokens"]),
                output_tokens=int(r["output_tokens"]),
                cost_usd=float(r["cost_usd"]),
                avg_items=float(r["avg_items"]),
            )
            for r in supplier_rows
        ],
        total=CostTotal(
            calls=int(total_row["calls"]) if total_row else 0,
            input_tokens=int(total_row["input_tokens"]) if total_row else 0,
            output_tokens=int(total_row["output_tokens"]) if total_row else 0,
            cost_usd=float(total_row["cost_usd"]) if total_row else 0.0,
        ),
        budget=CostBudget(
            monthly_budget_usd=float(budget_row["monthly_budget_usd"]) if budget_row else 0.0,
            current_month_usd=float(budget_row["current_month_usd"]) if budget_row else 0.0,
        ),
    )


class ExtractionErrorItem(BaseModel):
    id: str
    error_message: str | None
    created_at: str | None
    prompt_version: str | None
    supplier_name: str | None
    error_category: str | None
    error_detail: str | None


@router.get(
    "/tcg/extraction-errors",
    response_model=list[ExtractionErrorItem],
    dependencies=[Depends(require_super_admin)],
    summary="TCG 抽出エラーログ一覧（super_admin 限定）",
)
async def list_extraction_errors(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[ExtractionErrorItem]:
    rows = (
        await db.execute(
            text(
                "SELECT ej.id, ej.error_message, ej.created_at, ej.prompt_version,"
                "  s.name AS supplier_name,"
                "  ea.validation_result"
                f" FROM {_TCG_SCHEMA}.extraction_jobs ej"
                f" JOIN {_TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id"
                f" JOIN {_TCG_SCHEMA}.supplier_channels sc ON sc.id = sm.supplier_channel_id"
                " JOIN public.suppliers s ON s.id = sc.supplier_id"
                f" LEFT JOIN LATERAL ("
                f"   SELECT ea2.validation_result"
                f"   FROM {_TCG_SCHEMA}.extraction_attempts ea2"
                f"   WHERE ea2.extraction_job_id = ej.id"
                f"   ORDER BY ea2.started_at DESC LIMIT 1"
                f" ) ea ON true"
                " WHERE ej.status = 'error'"
                " ORDER BY ej.created_at DESC"
                " OFFSET :offset LIMIT :limit"
            ),
            {"offset": offset, "limit": limit},
        )
    ).fetchall()
    return [
        ExtractionErrorItem(
            id=str(row.id),
            error_message=row.error_message,
            created_at=row.created_at.isoformat() if row.created_at else None,
            prompt_version=row.prompt_version,
            supplier_name=row.supplier_name,
            error_category=row.validation_result.get("category") if row.validation_result else None,
            error_detail=row.validation_result.get("raw") if row.validation_result else None,
        )
        for row in rows
    ]
