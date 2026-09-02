"""
PARITY-03 第2段階: 仕入元品質サマリー API。

エンドポイント:
  GET /api/v1/tcg/supplier-quality-summaries
    認証: require_super_admin
    仕入元品質サマリー一覧（GAS: api_getSupplierQualitySummaries 相当）
    source 起点で集計 — items=0 の仕入元も含まれる

  GET /api/v1/tcg/suppliers/{supplier_id}/source
    認証: require_super_admin
    仕入元の原文取得（GAS: api_getSupplierSource 相当）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_supplier_quality_svc import (
    fetch_supplier_quality_summaries,
    fetch_supplier_source,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class SupplierQualitySummary(BaseModel):
    supplierId: str
    supplierName: str
    analysisCount: int
    needsReviewCount: int
    productIdUnresolvedCount: int
    unitUnresolvedCount: int
    conditionFallbackCount: int | None  # GAS と同じく null 固定


class SupplierQualitySummariesResponse(BaseModel):
    ok: bool
    summaries: list[SupplierQualitySummary]


class SupplierSourceResponse(BaseModel):
    ok: bool
    found: bool
    sourceMessageId: str
    supplierId: str
    supplierName: str
    rawText: str


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/supplier-quality-summaries",
    response_model=SupplierQualitySummariesResponse,
    summary="仕入元品質サマリー一覧（PARITY-03 第2段階）",
)
async def list_supplier_quality_summaries(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> SupplierQualitySummariesResponse:
    summaries = await fetch_supplier_quality_summaries(db)
    return SupplierQualitySummariesResponse(ok=True, summaries=summaries)


@router.get(
    "/tcg/suppliers/{supplier_id}/source",
    response_model=SupplierSourceResponse,
    summary="仕入元の原文取得（PARITY-03 第2段階）",
)
async def get_supplier_source(
    supplier_id: str = Path(description="仕入元コード（例: SP0057）"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> SupplierSourceResponse:
    result = await fetch_supplier_source(db, supplier_id=supplier_id)
    return SupplierSourceResponse(**result)
