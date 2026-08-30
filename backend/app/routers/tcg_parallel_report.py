"""
MIG-04 Phase 4: 並行運用比較レポート API。

エンドポイント:
  GET /api/v1/tcg/parallel-report
    認証: require_super_admin
    レスポンス: 仕入元別 compat-v1 vs name-first-v1 比較表
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_parallel_report_svc import build_parallel_report

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class EngineStats(BaseModel):
    pid_resolved: int
    pid_pct: float
    unit_resolved: int


class CompatEngineStats(EngineStats):
    has_result: int  # compat-v1 の analysis_results が存在する件数


class SupplierComparisonRow(BaseModel):
    sp_code: str
    supplier_name: str
    total: int
    compat_v1: CompatEngineStats
    name_first_v1: EngineStats
    pid_pct_diff: float  # name_first_v1 - compat_v1（正 = 改善、負 = 後退）


class ReportSummary(BaseModel):
    total_items: int
    compat_v1_pid_resolved: int
    name_first_v1_pid_resolved: int
    compat_v1_pid_pct: float
    name_first_v1_pid_pct: float
    supplier_count: int


class ParallelReportResponse(BaseModel):
    summary: ReportSummary
    suppliers: list[SupplierComparisonRow]


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/parallel-report",
    response_model=ParallelReportResponse,
    summary="並行運用比較レポート（MIG-04 Phase 4）",
)
async def get_parallel_report(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> ParallelReportResponse:
    """
    全仕入元の extraction_items に対して compat-v1（GAS 照合代理）と
    name-first-v1（サーバー新エンジン）の比較レポートを返す。

    DB への書き込みは行わない。
    """
    data = await build_parallel_report(db)
    return ParallelReportResponse(**data)
