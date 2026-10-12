"""
TCG 解析ダッシュボード API。

エンドポイント:
  GET /api/v1/tcg/analysis-dashboard/pipeline-summary
    認証: require_super_admin
    SELECT のみ。INSERT / UPDATE / DELETE / DDL を実行しない。
"""

from __future__ import annotations

import logging
from typing import Literal

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

logger = logging.getLogger(__name__)

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
    filtered: int = 0


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


class RecentExtractionJobItem(BaseModel):
    id: str
    supplier_name: str | None
    item_count: int
    resolved_count: int
    unresolved_count: int
    needs_review_count: int
    status: str
    created_at: str | None


class PipelineSummaryResponse(BaseModel):
    extraction: ExtractionSummary
    analysis: AnalysisSummary
    review_reasons: list[ReviewReasonItem]
    engine: EngineInfo
    recent_errors: list[RecentErrorItem]
    extraction_by_supplier: list[ExtractionBySupplierItem]
    recent_extraction_jobs: list[RecentExtractionJobItem]


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
# 対応状況の割り当て（SSOT）
#
# design §3: extraction_jobs.status → handling_status の対応表。
# ジョブの今の状態からその場で決める（保存はしない）。
# 表にない状態が来たときは unhandled とし、logger.warning を出す。
# ---------------------------------------------------------------------------

HandlingStatus = Literal["unhandled", "in_progress", "resolved"]

_STATUS_TO_HANDLING: dict[str, HandlingStatus] = {
    "error": "unhandled",
    "pending": "in_progress",
    "running": "in_progress",
    "done": "resolved",
    "empty": "resolved",
    "filtered": "resolved",
}


def _handling_status(job_status: str) -> HandlingStatus:
    """extraction_jobs.status から handling_status を決める。表にない状態は unhandled。"""
    handling = _STATUS_TO_HANDLING.get(job_status)
    if handling is None:
        logger.warning(
            "Unknown extraction_jobs.status %r; defaulting handling_status to 'unhandled'",
            job_status,
        )
        return "unhandled"
    return handling


def _job_statuses_for_handling(handling_status: HandlingStatus) -> list[str]:
    """handling_status に対応する extraction_jobs.status の一覧を返す。"""
    return [
        job_status
        for job_status, handling in _STATUS_TO_HANDLING.items()
        if handling == handling_status
    ]


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
    # ADR-1004: llm_usage_events 台帳が SSOT。extraction_attempts.input_tokens/output_tokens/
    # cost_usd は本 PR 以降書き込まれないため参照しない（input_bytes/3 推定も廃止）。
    # LEFT JOIN で extraction_attempt_id 経由の line_extraction 行のみ拾う
    # （FK の性質上 purpose='line_extraction' の行しか extraction_attempt_id を持たない）。

    # --- daily ---
    daily_rows = (await db.execute(text(f"""
        SELECT
            DATE(ea.started_at) AS date,
            COUNT(*) AS total_calls,
            COUNT(*) FILTER (WHERE ea.phase = 'completed') AS success_calls,
            COALESCE(SUM(ue.prompt_tokens), 0)::bigint AS input_tokens,
            COALESCE(SUM(COALESCE(ue.candidates_tokens, 0) + COALESCE(ue.thoughts_tokens, 0)), 0)::bigint AS output_tokens,
            COALESCE(SUM(ue.cost_usd), 0.0)::double precision AS cost_usd
        FROM {_TCG_SCHEMA}.extraction_attempts ea
        LEFT JOIN public.llm_usage_events ue ON ue.extraction_attempt_id = ea.id
        WHERE ea.started_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY DATE(ea.started_at)
        ORDER BY date DESC
    """), {"days": days})).mappings().all()

    # --- by_supplier ---
    supplier_rows = (await db.execute(text(f"""
        SELECT
            s.name AS supplier_name,
            COUNT(*) AS total_calls,
            COALESCE(SUM(ue.prompt_tokens), 0)::bigint AS input_tokens,
            COALESCE(SUM(COALESCE(ue.candidates_tokens, 0) + COALESCE(ue.thoughts_tokens, 0)), 0)::bigint AS output_tokens,
            COALESCE(SUM(ue.cost_usd), 0.0)::double precision AS cost_usd,
            COALESCE(AVG(NULLIF(ea.item_count, 0)), 0.0)::double precision AS avg_items
        FROM {_TCG_SCHEMA}.extraction_attempts ea
        JOIN {_TCG_SCHEMA}.extraction_jobs ej ON ej.id = ea.extraction_job_id
        JOIN {_TCG_SCHEMA}.source_messages sm ON sm.id = ea.source_message_id
        LEFT JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
        LEFT JOIN public.suppliers s ON s.id = sc.supplier_id
        LEFT JOIN public.llm_usage_events ue ON ue.extraction_attempt_id = ea.id
        WHERE ea.started_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY s.name
        ORDER BY cost_usd DESC
    """), {"days": days})).mappings().all()

    # --- total ---
    total_row = (await db.execute(text(f"""
        SELECT
            COUNT(*) AS calls,
            COALESCE(SUM(ue.prompt_tokens), 0)::bigint AS input_tokens,
            COALESCE(SUM(COALESCE(ue.candidates_tokens, 0) + COALESCE(ue.thoughts_tokens, 0)), 0)::bigint AS output_tokens,
            COALESCE(SUM(ue.cost_usd), 0.0)::double precision AS cost_usd
        FROM {_TCG_SCHEMA}.extraction_attempts ea
        LEFT JOIN public.llm_usage_events ue ON ue.extraction_attempt_id = ea.id
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


# ---------------------------------------------------------------------------
# LLM 使用量台帳サマリー スキーマ（ADR-1004）
# ---------------------------------------------------------------------------


class LlmUsageTotal(BaseModel):
    calls: int
    prompt_tokens: int | None
    cached_content_tokens: int | None
    candidates_tokens: int | None
    thoughts_tokens: int | None
    tool_use_prompt_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None
    # ADR-148 2026-10-03 追記（PR-B）: 各イベント発生時点の app_fx_rate_history レートで
    # 換算した JPY コスト。cost_usd が NULL の行は NULL のまま伝播する（0 と推測しない）。
    # 履歴テーブルに USD 行が無い場合は全体が NULL（fx ブロックも None になる）。
    cost_jpy: float | None
    computed_total_tokens: int | None
    total_mismatch_calls: int


class LlmUsageByPurposeItem(BaseModel):
    purpose: str
    calls: int
    prompt_tokens: int | None
    cached_content_tokens: int | None
    candidates_tokens: int | None
    thoughts_tokens: int | None
    tool_use_prompt_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None
    cost_jpy: float | None
    computed_total_tokens: int | None
    total_mismatch_calls: int


class LlmUsageByModelItem(BaseModel):
    model: str
    calls: int
    cost_usd: float | None
    cost_jpy: float | None


class LlmUsageDailyItem(BaseModel):
    date: str
    calls: int
    cost_usd: float | None
    cost_jpy: float | None
    prompt_tokens: int | None
    candidates_tokens: int | None
    thoughts_tokens: int | None


class LlmUsageDailyByPurposeItem(BaseModel):
    date: str
    purpose: str
    cost_usd: float | None
    cost_jpy: float | None
    calls: int


class LlmUsageMonthlyByPurposeItem(BaseModel):
    month: str
    purpose: str
    calls: int
    cost_usd: float | None
    cost_jpy: float | None


class LlmUsageDailyRequestsItem(BaseModel):
    date: str
    attempts: int
    completed: int
    failed: int
    success_rate: float | None


class LlmUsageDailyErrorItem(BaseModel):
    date: str
    error_code: str
    count: int


class LlmUsageDailyByModelItem(BaseModel):
    date: str
    model: str
    calls: int
    prompt_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    cost_jpy: float | None


class LlmUsageFx(BaseModel):
    """ADR-148 2026-10-03 追記（PR-B）: cost_jpy 換算の出典情報。

    public.app_fx_rate_history に USD 行が1件も無い場合は None（cost_jpy も全行 None）。
    """

    currency: str
    latest_rate_jpy: float
    latest_fetched_at: str
    history_start: str
    # 履歴の最古行より古い occurred_at を持つイベント数（最古レートへフォールバックした件数）。
    fallback_calls: int


class LlmUsageResponse(BaseModel):
    total: LlmUsageTotal
    by_purpose: list[LlmUsageByPurposeItem]
    by_model: list[LlmUsageByModelItem]
    daily: list[LlmUsageDailyItem]
    daily_by_purpose: list[LlmUsageDailyByPurposeItem]
    monthly_by_purpose: list[LlmUsageMonthlyByPurposeItem]
    daily_requests: list[LlmUsageDailyRequestsItem]
    daily_errors: list[LlmUsageDailyErrorItem]
    daily_by_model: list[LlmUsageDailyByModelItem]
    fx: LlmUsageFx | None


_LLM_USAGE_WHERE = "occurred_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW()"

# ADR-148 2026-10-03 追記（PR-B）: 各イベントに「発生時点で有効なレート」を付与する CTE。
# - fx_rate_jpy: occurred_at 以前の最新の app_fx_rate_history 行。無ければ（occurred_at が
#   履歴の最古行より古い）最古行にフォールバックする（COALESCE の2項目目）。
#   履歴テーブルに USD 行が1件も無ければ両方 NULL → fx_rate_jpy も NULL → cost_jpy も NULL。
# - fx_is_fallback: 「occurred_at 以前に履歴行が無かった」= 最古レートへフォールバックした
#   イベントかどうか。全7コスト集計クエリがこの CTE を共有する（1箇所に集約・DRY）。
_EVENT_FX_CTE = f"""
    SELECT
        e.*,
        COALESCE(
            (
                SELECT h.rate_jpy FROM public.app_fx_rate_history h
                WHERE h.currency = 'USD' AND h.fetched_at <= e.occurred_at
                ORDER BY h.fetched_at DESC LIMIT 1
            ),
            (
                SELECT h2.rate_jpy FROM public.app_fx_rate_history h2
                WHERE h2.currency = 'USD'
                ORDER BY h2.fetched_at ASC LIMIT 1
            )
        ) AS fx_rate_jpy,
        NOT EXISTS (
            SELECT 1 FROM public.app_fx_rate_history h3
            WHERE h3.currency = 'USD' AND h3.fetched_at <= e.occurred_at
        ) AS fx_is_fallback
    FROM public.llm_usage_events e
    WHERE {_LLM_USAGE_WHERE}
"""

# computed_total_tokens: SDK が返した4項目（prompt/candidates/thoughts/tool_use_prompt）の
# 単純合算。1件でも報告があれば COALESCE(...,0) で合算し、全項目が NULL の行は SUM の対象外
# （SUM は NULL を無視するため、グループ内の全行がこの4項目すべて NULL のときだけ結果が NULL
# になる＝推測で 0 に丸めない）。
_COMPUTED_TOTAL_TOKENS_EXPR = """
    SUM(
        CASE
            WHEN prompt_tokens IS NULL AND candidates_tokens IS NULL
                 AND thoughts_tokens IS NULL AND tool_use_prompt_tokens IS NULL
            THEN NULL
            ELSE COALESCE(prompt_tokens, 0) + COALESCE(candidates_tokens, 0)
                 + COALESCE(thoughts_tokens, 0) + COALESCE(tool_use_prompt_tokens, 0)
        END
    ) AS computed_total_tokens
"""

# total_mismatch_calls: Google が返した total_tokens と、こちらで計算した4項目合算が
# 食い違う行数。total_tokens が NULL の行（未報告）はカウントしない。
_TOTAL_MISMATCH_CALLS_EXPR = """
    COUNT(*) FILTER (
        WHERE total_tokens IS NOT NULL
          AND total_tokens != COALESCE(prompt_tokens, 0) + COALESCE(candidates_tokens, 0)
               + COALESCE(thoughts_tokens, 0) + COALESCE(tool_use_prompt_tokens, 0)
    ) AS total_mismatch_calls
"""


@router.get(
    "/tcg/analysis-dashboard/llm-usage",
    response_model=LlmUsageResponse,
    summary="LLM 使用量台帳サマリー（super_admin 限定）",
)
async def get_llm_usage(
    days: int = Query(default=30, ge=1, le=360),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_super_admin),
) -> LlmUsageResponse:
    # ADR-1004: public.llm_usage_events が SSOT。extraction_attempts 等の旧列は読まない。
    # 日別バケットは import-trend / pipeline-trend（tcg_analysis_dashboard_svc.py の
    # get_import_trend/get_pipeline_trend）と同じ JST DATE_TRUNC 表現に合わせる。
    # cost-summary の daily は DATE()（セッションTZ依存）だが、こちらは「トレンド」相当の
    # 集計のため trend 系の表現を優先した。
    # SDK が値を返さなかった列は SUM() が NULL を返す（COALESCE で 0 に丸めない＝推測しない）。
    #
    # ADR-148 2026-10-03 追記（PR-B）: fx メタ情報（最新レート・最古レートの取得時刻）を
    # 事前に1回だけ取得する。public.app_fx_rate_history に USD 行が無い場合は全列 NULL。
    fx_meta_row = (await db.execute(text("""
        SELECT
            (SELECT rate_jpy FROM public.app_fx_rate_history
             WHERE currency = 'USD' ORDER BY fetched_at DESC LIMIT 1) AS latest_rate_jpy,
            (SELECT fetched_at FROM public.app_fx_rate_history
             WHERE currency = 'USD' ORDER BY fetched_at DESC LIMIT 1) AS latest_fetched_at,
            (SELECT fetched_at FROM public.app_fx_rate_history
             WHERE currency = 'USD' ORDER BY fetched_at ASC LIMIT 1) AS history_start
    """))).mappings().first()

    total_row = (await db.execute(text(f"""
        WITH event_fx AS ({_EVENT_FX_CTE})
        SELECT
            COUNT(*) AS calls,
            SUM(prompt_tokens) AS prompt_tokens,
            SUM(cached_content_tokens) AS cached_content_tokens,
            SUM(candidates_tokens) AS candidates_tokens,
            SUM(thoughts_tokens) AS thoughts_tokens,
            SUM(tool_use_prompt_tokens) AS tool_use_prompt_tokens,
            SUM(total_tokens) AS total_tokens,
            SUM(cost_usd) AS cost_usd,
            SUM(cost_usd * fx_rate_jpy) AS cost_jpy,
            COUNT(*) FILTER (WHERE fx_is_fallback) AS fallback_calls,
            {_COMPUTED_TOTAL_TOKENS_EXPR},
            {_TOTAL_MISMATCH_CALLS_EXPR}
        FROM event_fx
    """), {"days": days})).mappings().first()

    by_purpose_rows = (await db.execute(text(f"""
        WITH event_fx AS ({_EVENT_FX_CTE})
        SELECT
            purpose,
            COUNT(*) AS calls,
            SUM(prompt_tokens) AS prompt_tokens,
            SUM(cached_content_tokens) AS cached_content_tokens,
            SUM(candidates_tokens) AS candidates_tokens,
            SUM(thoughts_tokens) AS thoughts_tokens,
            SUM(tool_use_prompt_tokens) AS tool_use_prompt_tokens,
            SUM(total_tokens) AS total_tokens,
            SUM(cost_usd) AS cost_usd,
            SUM(cost_usd * fx_rate_jpy) AS cost_jpy,
            {_COMPUTED_TOTAL_TOKENS_EXPR},
            {_TOTAL_MISMATCH_CALLS_EXPR}
        FROM event_fx
        GROUP BY purpose
        ORDER BY cost_usd DESC NULLS LAST
    """), {"days": days})).mappings().all()

    by_model_rows = (await db.execute(text(f"""
        WITH event_fx AS ({_EVENT_FX_CTE})
        SELECT
            model,
            COUNT(*) AS calls,
            SUM(cost_usd) AS cost_usd,
            SUM(cost_usd * fx_rate_jpy) AS cost_jpy
        FROM event_fx
        GROUP BY model
        ORDER BY cost_usd DESC NULLS LAST
    """), {"days": days})).mappings().all()

    daily_rows = (await db.execute(text(f"""
        WITH event_fx AS ({_EVENT_FX_CTE})
        SELECT
            TO_CHAR(DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo'), 'YYYY-MM-DD') AS date,
            COUNT(*) AS calls,
            SUM(cost_usd) AS cost_usd,
            SUM(cost_usd * fx_rate_jpy) AS cost_jpy,
            SUM(prompt_tokens) AS prompt_tokens,
            SUM(candidates_tokens) AS candidates_tokens,
            SUM(thoughts_tokens) AS thoughts_tokens
        FROM event_fx
        GROUP BY DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo')
        ORDER BY DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo') DESC
    """), {"days": days})).mappings().all()

    daily_by_purpose_rows = (await db.execute(text(f"""
        WITH event_fx AS ({_EVENT_FX_CTE})
        SELECT
            TO_CHAR(DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo'), 'YYYY-MM-DD') AS date,
            purpose,
            COUNT(*) AS calls,
            SUM(cost_usd) AS cost_usd,
            SUM(cost_usd * fx_rate_jpy) AS cost_jpy
        FROM event_fx
        GROUP BY DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo'), purpose
        ORDER BY DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo') ASC
    """), {"days": days})).mappings().all()

    monthly_by_purpose_rows = (await db.execute(text(f"""
        WITH event_fx AS ({_EVENT_FX_CTE})
        SELECT
            TO_CHAR(DATE_TRUNC('month', occurred_at AT TIME ZONE 'Asia/Tokyo'), 'YYYY-MM') AS month,
            purpose,
            COUNT(*) AS calls,
            SUM(cost_usd) AS cost_usd,
            SUM(cost_usd * fx_rate_jpy) AS cost_jpy
        FROM event_fx
        GROUP BY DATE_TRUNC('month', occurred_at AT TIME ZONE 'Asia/Tokyo'), purpose
        ORDER BY DATE_TRUNC('month', occurred_at AT TIME ZONE 'Asia/Tokyo') ASC
    """), {"days": days})).mappings().all()

    # --- daily_requests（Google AI Studio の「リクエスト数と成功率」相当） ---
    # extraction_attempts.started_at が母集団。success_rate は完了/（完了+失敗）で、
    # 処理中（in-flight）のフェーズは分母から除く（ドキュメントに明記）。
    daily_requests_rows = (await db.execute(text(f"""
        SELECT
            TO_CHAR(DATE_TRUNC('day', started_at AT TIME ZONE 'Asia/Tokyo'), 'YYYY-MM-DD') AS date,
            COUNT(*) AS attempts,
            COUNT(*) FILTER (WHERE phase = 'completed') AS completed,
            COUNT(*) FILTER (WHERE phase = 'failed') AS failed
        FROM {_TCG_SCHEMA}.extraction_attempts
        WHERE started_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW()
        GROUP BY DATE_TRUNC('day', started_at AT TIME ZONE 'Asia/Tokyo')
        ORDER BY DATE_TRUNC('day', started_at AT TIME ZONE 'Asia/Tokyo') ASC
    """), {"days": days})).mappings().all()

    # --- daily_errors（種類別。error_code が NULL の行は 'UNKNOWN' に丸める） ---
    daily_errors_rows = (await db.execute(text(f"""
        SELECT
            TO_CHAR(DATE_TRUNC('day', started_at AT TIME ZONE 'Asia/Tokyo'), 'YYYY-MM-DD') AS date,
            COALESCE(error_code, 'UNKNOWN') AS error_code,
            COUNT(*) AS count
        FROM {_TCG_SCHEMA}.extraction_attempts
        WHERE started_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW()
          AND phase = 'failed'
        GROUP BY DATE_TRUNC('day', started_at AT TIME ZONE 'Asia/Tokyo'), COALESCE(error_code, 'UNKNOWN')
        ORDER BY DATE_TRUNC('day', started_at AT TIME ZONE 'Asia/Tokyo') ASC
    """), {"days": days})).mappings().all()

    # --- daily_by_model（モデル別の日次トークン・リクエスト数） ---
    daily_by_model_rows = (await db.execute(text(f"""
        WITH event_fx AS ({_EVENT_FX_CTE})
        SELECT
            TO_CHAR(DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo'), 'YYYY-MM-DD') AS date,
            model,
            COUNT(*) AS calls,
            SUM(prompt_tokens) AS prompt_tokens,
            SUM(
                CASE
                    WHEN candidates_tokens IS NULL AND thoughts_tokens IS NULL THEN NULL
                    ELSE COALESCE(candidates_tokens, 0) + COALESCE(thoughts_tokens, 0)
                END
            ) AS output_tokens,
            SUM(cost_usd) AS cost_usd,
            SUM(cost_usd * fx_rate_jpy) AS cost_jpy
        FROM event_fx
        GROUP BY DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo'), model
        ORDER BY DATE_TRUNC('day', occurred_at AT TIME ZONE 'Asia/Tokyo') ASC
    """), {"days": days})).mappings().all()

    # ADR-148 2026-10-03 追記（PR-B）: fx ブロック。履歴テーブルに USD 行が無ければ None
    # （このとき各 cost_jpy も COALESCE 無しの SUM 伝播により全行 None になる）。
    fx_block: LlmUsageFx | None = None
    if fx_meta_row is not None and fx_meta_row["latest_rate_jpy"] is not None:
        fx_block = LlmUsageFx(
            currency="USD",
            latest_rate_jpy=float(fx_meta_row["latest_rate_jpy"]),
            latest_fetched_at=fx_meta_row["latest_fetched_at"].isoformat(),
            history_start=fx_meta_row["history_start"].isoformat(),
            fallback_calls=int(total_row["fallback_calls"]) if total_row and total_row["fallback_calls"] is not None else 0,
        )

    return LlmUsageResponse(
        total=LlmUsageTotal(
            calls=int(total_row["calls"]) if total_row else 0,
            prompt_tokens=total_row["prompt_tokens"] if total_row else None,
            cached_content_tokens=total_row["cached_content_tokens"] if total_row else None,
            candidates_tokens=total_row["candidates_tokens"] if total_row else None,
            thoughts_tokens=total_row["thoughts_tokens"] if total_row else None,
            tool_use_prompt_tokens=total_row["tool_use_prompt_tokens"] if total_row else None,
            total_tokens=total_row["total_tokens"] if total_row else None,
            cost_usd=float(total_row["cost_usd"]) if total_row and total_row["cost_usd"] is not None else None,
            cost_jpy=float(total_row["cost_jpy"]) if total_row and total_row["cost_jpy"] is not None else None,
            computed_total_tokens=total_row["computed_total_tokens"] if total_row else None,
            total_mismatch_calls=int(total_row["total_mismatch_calls"]) if total_row else 0,
        ),
        by_purpose=[
            LlmUsageByPurposeItem(
                purpose=r["purpose"],
                calls=int(r["calls"]),
                prompt_tokens=r["prompt_tokens"],
                cached_content_tokens=r["cached_content_tokens"],
                candidates_tokens=r["candidates_tokens"],
                thoughts_tokens=r["thoughts_tokens"],
                tool_use_prompt_tokens=r["tool_use_prompt_tokens"],
                total_tokens=r["total_tokens"],
                cost_usd=float(r["cost_usd"]) if r["cost_usd"] is not None else None,
                cost_jpy=float(r["cost_jpy"]) if r["cost_jpy"] is not None else None,
                computed_total_tokens=r["computed_total_tokens"],
                total_mismatch_calls=int(r["total_mismatch_calls"]),
            )
            for r in by_purpose_rows
        ],
        by_model=[
            LlmUsageByModelItem(
                model=r["model"],
                calls=int(r["calls"]),
                cost_usd=float(r["cost_usd"]) if r["cost_usd"] is not None else None,
                cost_jpy=float(r["cost_jpy"]) if r["cost_jpy"] is not None else None,
            )
            for r in by_model_rows
        ],
        daily=[
            LlmUsageDailyItem(
                date=str(r["date"]),
                calls=int(r["calls"]),
                cost_usd=float(r["cost_usd"]) if r["cost_usd"] is not None else None,
                cost_jpy=float(r["cost_jpy"]) if r["cost_jpy"] is not None else None,
                prompt_tokens=r["prompt_tokens"],
                candidates_tokens=r["candidates_tokens"],
                thoughts_tokens=r["thoughts_tokens"],
            )
            for r in daily_rows
        ],
        daily_by_purpose=[
            LlmUsageDailyByPurposeItem(
                date=str(r["date"]),
                purpose=r["purpose"],
                cost_usd=float(r["cost_usd"]) if r["cost_usd"] is not None else None,
                cost_jpy=float(r["cost_jpy"]) if r["cost_jpy"] is not None else None,
                calls=int(r["calls"]),
            )
            for r in daily_by_purpose_rows
        ],
        monthly_by_purpose=[
            LlmUsageMonthlyByPurposeItem(
                month=str(r["month"]),
                purpose=r["purpose"],
                calls=int(r["calls"]),
                cost_usd=float(r["cost_usd"]) if r["cost_usd"] is not None else None,
                cost_jpy=float(r["cost_jpy"]) if r["cost_jpy"] is not None else None,
            )
            for r in monthly_by_purpose_rows
        ],
        daily_requests=[
            LlmUsageDailyRequestsItem(
                date=str(r["date"]),
                attempts=int(r["attempts"]),
                completed=int(r["completed"]),
                failed=int(r["failed"]),
                success_rate=(
                    float(r["completed"]) / float(r["completed"] + r["failed"])
                    if (r["completed"] + r["failed"]) > 0
                    else None
                ),
            )
            for r in daily_requests_rows
        ],
        daily_errors=[
            LlmUsageDailyErrorItem(
                date=str(r["date"]),
                error_code=str(r["error_code"]),
                count=int(r["count"]),
            )
            for r in daily_errors_rows
        ],
        daily_by_model=[
            LlmUsageDailyByModelItem(
                date=str(r["date"]),
                model=r["model"],
                calls=int(r["calls"]),
                prompt_tokens=r["prompt_tokens"],
                output_tokens=r["output_tokens"],
                cost_usd=float(r["cost_usd"]) if r["cost_usd"] is not None else None,
                cost_jpy=float(r["cost_jpy"]) if r["cost_jpy"] is not None else None,
            )
            for r in daily_by_model_rows
        ],
        fx=fx_block,
    )


class ExtractionErrorItem(BaseModel):
    id: str
    supplier_name: str | None
    prompt_version: str | None
    error_message: str | None
    error_category: str | None
    error_detail: str | None
    last_failed_at: str | None
    first_failed_at: str | None
    retry_count: int
    job_status: str
    handling_status: HandlingStatus


class ExtractionErrorCounts(BaseModel):
    unhandled: int
    in_progress: int
    resolved: int


class ExtractionErrorListResponse(BaseModel):
    items: list[ExtractionErrorItem]
    total: int
    counts: ExtractionErrorCounts


@router.get(
    "/tcg/extraction-errors",
    response_model=ExtractionErrorListResponse,
    dependencies=[Depends(require_super_admin)],
    summary="TCG 抽出エラーログ一覧（super_admin 限定）",
)
async def list_extraction_errors(
    status: HandlingStatus = Query(default="unhandled"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> ExtractionErrorListResponse:
    job_statuses = _job_statuses_for_handling(status)

    rows = (
        await db.execute(
            text(
                "WITH job_attempts AS ("
                "  SELECT"
                "    extraction_job_id,"
                "    COUNT(*) AS attempt_count,"
                "    MIN(started_at) FILTER (WHERE phase = 'failed') AS first_failed_at,"
                "    MAX(started_at) FILTER (WHERE phase = 'failed') AS last_failed_at,"
                "    COUNT(*) FILTER (WHERE phase = 'failed') AS failed_count"
                f"  FROM {_TCG_SCHEMA}.extraction_attempts"
                "  GROUP BY extraction_job_id"
                ")"
                " SELECT ej.id, ej.error_message, ej.prompt_version, ej.status AS job_status,"
                "   s.name AS supplier_name,"
                "   ja.first_failed_at, ja.last_failed_at, ja.attempt_count,"
                "   latest_failed.error_code, latest_failed.validation_result"
                f" FROM {_TCG_SCHEMA}.extraction_jobs ej"
                " JOIN job_attempts ja ON ja.extraction_job_id = ej.id AND ja.failed_count > 0"
                f" JOIN {_TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id"
                f" JOIN {_TCG_SCHEMA}.supplier_channels sc ON sc.id = sm.supplier_channel_id"
                " JOIN public.suppliers s ON s.id = sc.supplier_id"
                " LEFT JOIN LATERAL ("
                "   SELECT ea2.error_code, ea2.validation_result"
                f"   FROM {_TCG_SCHEMA}.extraction_attempts ea2"
                "   WHERE ea2.extraction_job_id = ej.id AND ea2.phase = 'failed'"
                "   ORDER BY ea2.started_at DESC LIMIT 1"
                " ) latest_failed ON true"
                " WHERE ej.status = ANY(:job_statuses)"
                " ORDER BY ja.last_failed_at DESC"
                " OFFSET :offset LIMIT :limit"
            ),
            {"job_statuses": job_statuses, "offset": offset, "limit": limit},
        )
    ).fetchall()

    counts_rows = (
        await db.execute(
            text(
                "WITH job_attempts AS ("
                "  SELECT extraction_job_id, COUNT(*) FILTER (WHERE phase = 'failed') AS failed_count"
                f"  FROM {_TCG_SCHEMA}.extraction_attempts"
                "  GROUP BY extraction_job_id"
                ")"
                " SELECT ej.status AS job_status, COUNT(*) AS cnt"
                f" FROM {_TCG_SCHEMA}.extraction_jobs ej"
                " JOIN job_attempts ja ON ja.extraction_job_id = ej.id AND ja.failed_count > 0"
                " GROUP BY ej.status"
            )
        )
    ).fetchall()

    counts: dict[HandlingStatus, int] = {"unhandled": 0, "in_progress": 0, "resolved": 0}
    for row in counts_rows:
        counts[_handling_status(row.job_status)] += int(row.cnt)

    items = [
        ExtractionErrorItem(
            id=str(row.id),
            supplier_name=row.supplier_name,
            prompt_version=row.prompt_version,
            error_message=row.error_code or row.error_message,
            error_category=row.validation_result.get("category") if row.validation_result else None,
            error_detail=row.validation_result.get("raw") if row.validation_result else None,
            last_failed_at=row.last_failed_at.isoformat() if row.last_failed_at else None,
            first_failed_at=row.first_failed_at.isoformat() if row.first_failed_at else None,
            retry_count=int(row.attempt_count) - 1,
            job_status=row.job_status,
            handling_status=_handling_status(row.job_status),
        )
        for row in rows
    ]

    return ExtractionErrorListResponse(
        items=items,
        total=counts[status],
        counts=ExtractionErrorCounts(**counts),
    )
