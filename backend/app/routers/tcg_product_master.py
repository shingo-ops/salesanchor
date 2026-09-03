"""
PARITY-03 Phase 3: 商品マスタ登録 API。

エンドポイント:
  GET  /api/v1/tcg/products/registration-form  (B-1)
  GET  /api/v1/tcg/products/search             (B-4)
  POST /api/v1/tcg/products/check-duplicates   (B-2)
  POST /api/v1/tcg/products                    (B-3)
  POST /api/v1/tcg/products/{product_code}/search-keywords (B-5)

認証: require_super_admin（tenant_004 専用）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_product_master_svc import (
    add_search_keyword,
    check_duplicates,
    create_product,
    fetch_registration_form,
    reanalyze_extraction_job,
    search_products_by_name,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class LookupOption(BaseModel):
    id: str
    name: str


class RegistrationFormItem(BaseModel):
    extraction_item_id: str
    source_message_id: str
    raw_name: str
    mark: str = ""
    english_title: str = ""


class RegistrationFormResponse(BaseModel):
    item: RegistrationFormItem
    lookups: dict[str, list[LookupOption]]


class ProductCandidate(BaseModel):
    product_id: str
    japanese_title: str


class SearchCandidate(BaseModel):
    product_id: str
    product_uuid: str
    japanese_title: str
    search_keywords: str


class SearchResponse(BaseModel):
    candidates: list[SearchCandidate]


class DuplicateCheckRequest(BaseModel):
    extraction_item_id: str
    source_message_id: str
    division_id: str
    work_id: str
    manufacturer_id: str
    product_category_id: str
    japanese_title: str
    search_keywords: str = ""
    exclude_keywords: str = ""
    release_date: str = ""


class DuplicateCheckResponse(BaseModel):
    candidates: list[ProductCandidate]


class CreateProductRequest(BaseModel):
    extraction_item_id: str
    source_message_id: str
    division_id: str
    work_id: str
    manufacturer_id: str
    product_category_id: str
    japanese_title: str
    search_keywords: str = ""
    exclude_keywords: str = ""
    release_date: str = ""
    mark: str = ""
    english_title: str = ""


class CreateProductOkResponse(BaseModel):
    ok: bool
    product_id: str


class CreateProductDupResponse(BaseModel):
    ok: bool
    code: str
    candidates: list[ProductCandidate]


class AddKeywordRequest(BaseModel):
    new_keyword: str


class AddKeywordOkResponse(BaseModel):
    ok: bool


class AddKeywordDupResponse(BaseModel):
    ok: bool
    code: str


# ---------------------------------------------------------------------------
# B-1: 登録フォーム初期データ
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/products/registration-form",
    response_model=RegistrationFormResponse,
    summary="商品マスタ登録フォーム初期データ（PARITY-03 Phase 3 B-1）",
)
async def get_registration_form(
    extraction_item_id: str = Query(...),
    source_message_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> RegistrationFormResponse:
    try:
        data = await fetch_registration_form(
            db,
            extraction_item_id=extraction_item_id,
            source_message_id=source_message_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return RegistrationFormResponse(**data)


# ---------------------------------------------------------------------------
# B-4: 商品名検索
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/products/search",
    response_model=SearchResponse,
    summary="商品マスタ名前検索（PARITY-03 Phase 3 B-4）",
)
async def search_products(
    query: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> SearchResponse:
    data = await search_products_by_name(db, query=query)
    return SearchResponse(**data)


# ---------------------------------------------------------------------------
# B-2: 重複チェック
# ---------------------------------------------------------------------------


@router.post(
    "/tcg/products/check-duplicates",
    response_model=DuplicateCheckResponse,
    summary="商品マスタ重複チェック（PARITY-03 Phase 3 B-2）",
)
async def check_product_duplicates(
    body: DuplicateCheckRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> DuplicateCheckResponse:
    data = await check_duplicates(
        db,
        japanese_title=body.japanese_title,
        work_id=body.work_id,
        manufacturer_id=body.manufacturer_id,
        product_category_id=body.product_category_id,
    )
    return DuplicateCheckResponse(**data)


# ---------------------------------------------------------------------------
# B-3: 商品マスタ新規登録
# ---------------------------------------------------------------------------


@router.post(
    "/tcg/products",
    summary="商品マスタ新規登録（PARITY-03 Phase 3 B-3）",
)
async def create_product_master(
    body: CreateProductRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> dict:
    if not body.japanese_title.strip():
        raise HTTPException(status_code=422, detail="PRODUCT_MASTER_V2_JAPANESE_TITLE_REQUIRED")
    try:
        result = await create_product(
            db,
            extraction_item_id=body.extraction_item_id,
            source_message_id=body.source_message_id,
            division_id=body.division_id,
            work_id=body.work_id,
            manufacturer_id=body.manufacturer_id,
            product_category_id=body.product_category_id,
            japanese_title=body.japanese_title,
            release_date=body.release_date or None,
            search_keywords=body.search_keywords,
            exclude_keywords=body.exclude_keywords,
            mark=body.mark,
            english_title=body.english_title,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return result


# ---------------------------------------------------------------------------
# B-5: 検索キーワード追加
# ---------------------------------------------------------------------------


@router.post(
    "/tcg/products/{product_code}/search-keywords",
    summary="商品マスタ検索キーワード追加（PARITY-03 Phase 3 B-5）",
)
async def add_product_search_keyword(
    product_code: str,
    body: AddKeywordRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> dict:
    try:
        result = await add_search_keyword(
            db,
            product_code=product_code,
            new_keyword=body.new_keyword,
        )
    except ValueError as e:
        code = str(e)
        if "NOT_FOUND" in code:
            raise HTTPException(status_code=404, detail=code) from e
        raise HTTPException(status_code=422, detail=code) from e
    return result


# ---------------------------------------------------------------------------
# R-1: 単一ジョブ再解析（GAS: refreshShadowReviewV2 相当・1ジョブ限定）
# ---------------------------------------------------------------------------


class ReanalyzeStats(BaseModel):
    total: int
    pid_resolved: int
    unit_resolved: int
    needs_review: int


class ReanalyzeResponse(BaseModel):
    before: ReanalyzeStats
    after: dict  # analyze_extraction_job の戻り値（キーが可変のため dict）


@router.post(
    "/tcg/extraction-jobs/{extraction_job_id}/reanalyze",
    response_model=ReanalyzeResponse,
    summary="単一 extraction_job 再解析（PARITY-03 Phase 3 R-1）",
)
async def reanalyze_job(
    extraction_job_id: str,
    _user: dict = Depends(require_super_admin),
) -> ReanalyzeResponse:
    """
    指定ジョブの analysis_results を再解析・UPSERT する。
    実行前の集計値を before に、実行後の stats を after に返す。

    ⚠️  ロールバック手順:
      再解析は Python エンジンで上書きする。GAS が計算した値には戻らない。
      実行前に必ず tenant_004.analysis_results_gas_baseline_YYYYMMDD を作成し、
      GAS 時点の全行を退避すること。

      退避方法:
        CREATE TABLE tenant_004.analysis_results_gas_baseline_20260903
        AS SELECT * FROM tenant_004.analysis_results;

      復元方法:
        INSERT INTO tenant_004.analysis_results
          SELECT * FROM tenant_004.analysis_results_gas_baseline_20260903
          WHERE extraction_item_id IN (
            SELECT id FROM tenant_004.extraction_items
            WHERE extraction_job_id = '<対象ジョブID>'
          )
        ON CONFLICT (extraction_item_id) DO UPDATE
          SET pid_resolved   = EXCLUDED.pid_resolved,
              unit_resolved  = EXCLUDED.unit_resolved,
              needs_review   = EXCLUDED.needs_review,
              product_id     = EXCLUDED.product_id,
              pid_basis      = EXCLUDED.pid_basis,
              unit           = EXCLUDED.unit,
              condition      = EXCLUDED.condition,
              status         = EXCLUDED.status,
              note           = EXCLUDED.note,
              exclusion      = EXCLUDED.exclusion;
    """
    try:
        result = await reanalyze_extraction_job(extraction_job_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ReanalyzeResponse(**result)
