"""
IMPORT-01: 商品マスタ CSV 取り込み API。

エンドポイント:
  GET  /api/v1/tcg/products/list
    商品マスタの一覧（画面の表に出す）

  POST /api/v1/tcg/products/import/preview
    multipart/form-data: file=UploadFile (.csv)
    検査だけを行い、書き込みを一切しない

  POST /api/v1/tcg/products/import/commit
    multipart/form-data: file=UploadFile (.csv)
    検査をやり直し、止める判定の無い行だけを登録する

認証: require_super_admin（既存の商品マスタ登録 API と同じ）

既存の tcg_product_master.py は変更しない。登録そのものは
tcg_product_import_svc から既存の create_product を呼ぶ。

根拠: docs/handoff/tcg-product-import/design.md 5-2
"""
from __future__ import annotations

import csv
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.services import tcg_product_roundtrip_svc as roundtrip
from app.services.tcg_product_detail_svc import ProductDetailError, get_product_detail, update_product_detail
from app.services.tcg_product_import_svc import commit_import, preview
from app.tcg_config import TCG_SCHEMA

router = APIRouter()

MAX_UPLOAD_BYTES = 2 * 1024 * 1024


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class ProductListItem(BaseModel):
    code: str
    japanese_title: str
    english_title: str = ""
    mark: str = ""
    release_date: str = ""
    keyword_count: int = 0
    exclude_keyword_count: int = 0


class ProductWork(BaseModel):
    id: str
    code: str
    display_name: str
    alt_name: str = ""


class ProductListResponse(BaseModel):
    total: int
    items: list[ProductListItem]
    works: list[ProductWork]


# ---------------------------------------------------------------------------
# 一覧
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/products/list",
    response_model=ProductListResponse,
    summary="商品マスタ一覧（IMPORT-01）",
)
async def list_products(
    query: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    work_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> ProductListResponse:
    like = "%" + query.strip() + "%" if query.strip() else "%"
    condition = "(p.name ILIKE :like OR p.name_en ILIKE :like OR p.mark ILIKE :like OR p.product_code ILIKE :like)"
    params = {"like": like}
    if work_id is not None:
        condition += " AND p.work_id = :work_id"
        params["work_id"] = work_id
    total_row = await db.execute(
        text(
            f"SELECT count(*) FROM public.products p WHERE {condition}"
        ),
        params,
    )
    total = int(total_row.fetchone()[0])

    rows = await db.execute(
        text(
            f"SELECT p.product_code, p.name, p.name_en, p.mark, p.release_date, "
            f"(SELECT count(*) FROM public.product_search_keywords k "
            f"WHERE k.product_id = p.id) AS keyword_count, "
            f"(SELECT count(*) FROM public.product_exclude_keywords k "
            f"WHERE k.product_id = p.id) AS exclude_keyword_count "
            f"FROM public.products p "
            f"WHERE {condition} "
            f"ORDER BY p.release_date DESC NULLS LAST, p.product_code DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": limit, "offset": offset},
    )
    items = [
        ProductListItem(
            code=str(r[0]),
            japanese_title=str(r[1] or ""),
            english_title=str(r[2] or ""),
            mark=str(r[3] or ""),
            release_date=str(r[4] or ""),
            keyword_count=int(r[5] or 0),
            exclude_keyword_count=int(r[6] or 0),
        )
        for r in rows.fetchall()
    ]
    work_rows = await db.execute(text(
        "SELECT s.id, s.code, s.name_ja AS display_name, s.name_en AS alt_name FROM public.type_master s "
        "WHERE s.is_active = TRUE OR EXISTS (SELECT 1 FROM public.products p "
        "WHERE p.work_id = s.id) ORDER BY s.code ASC"
    ))
    works = [
        ProductWork(id=str(r[0]), code=str(r[1]), display_name=str(r[2]), alt_name=str(r[3] or ""))
        for r in work_rows.fetchall()
    ]
    return ProductListResponse(total=total, items=items, works=works)


# ---------------------------------------------------------------------------
# 取り込み
# ---------------------------------------------------------------------------

@router.get("/tcg/products/export")
async def export_products(
    query: str = Query(default=""),
    work_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> Response:
    try:
        raw = await roundtrip.export_csv(db, query, str(work_id) if work_id else None)
    except roundtrip.RoundtripError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail="ROUNDTRIP_CSV_INVALID") from exc
    return Response(raw, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": 'attachment; filename="tcg-products-update.csv"',
        "Cache-Control": "no-store",
    })


async def _read_csv(file: UploadFile) -> bytes:
    """アップロードされた CSV を読む。形と大きさをここで弾く。"""
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="PRODUCT_IMPORT_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="PRODUCT_IMPORT_EMPTY_FILE")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PRODUCT_IMPORT_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=422, detail="PRODUCT_IMPORT_NOT_UTF8"
        ) from exc
    return raw


@router.post(
    "/tcg/products/import/preview",
    summary="商品マスタ CSV 取り込みの内容確認（IMPORT-01）",
)
async def preview_import(
    file: UploadFile = File(..., description="10列の CSV ファイル"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> dict:
    """
    検査だけを行う。書き込みを一切しない。

    画面はこの結果を確認の段で見せる。止める判定のある行は登録されない。
    """
    raw = await _read_csv(file)
    try:
        if roundtrip.is_update(raw):
            return await roundtrip.preview_update(db, raw, file.filename or "")
        return await preview(db, raw, file.filename or "")
    except roundtrip.RoundtripError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail="ROUNDTRIP_CSV_INVALID") from exc


@router.post(
    "/tcg/products/import/commit",
    summary="商品マスタ CSV 取り込みの実行（IMPORT-01）",
)
async def commit_import_endpoint(
    file: UploadFile = File(..., description="10列の CSV ファイル"),
    confirmed_digest: str = Form(..., description="確認の段で受け取った指紋"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_super_admin),
) -> dict:
    """
    検査をやり直し、止める判定の無い行だけを登録する。

    確認の段を経ずに書き込む経路を作らないため、確認の段で返した指紋と
    同じものを必ず受け取る。一致しない場合は書き込まない。
    """
    raw = await _read_csv(file)
    try:
        if roundtrip.is_update(raw):
            return await roundtrip.commit_update(db, raw, file.filename or "", str(user.email or user.id or ""), confirmed_digest)
    except roundtrip.RoundtripError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    try:
        checked = await preview(db, raw, file.filename or "")
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail="ROUNDTRIP_CSV_INVALID") from exc
    if checked["file_errors"]:
        raise HTTPException(status_code=422, detail=checked["file_errors"])
    if confirmed_digest != checked["digest"]:
        raise HTTPException(status_code=409, detail="PRODUCT_IMPORT_DIGEST_MISMATCH")
    executed_by = str(user.email or user.id or "")
    try:
        return await commit_import(db, raw, file.filename or "", executed_by)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/tcg/products/detail/{product_code}", summary="商品マスタ詳細（DETAIL-01）")
async def product_detail(
    product_code: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> dict:
    try:
        return await get_product_detail(db, product_code)
    except ProductDetailError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


DetailWord = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class ProductDetailUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    japanese_title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
    english_title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
    mark: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
    release_date: str | None
    division_id: UUID | None
    work_id: int | None = None
    manufacturer_id: UUID | None
    product_category_id: UUID | None
    search_keywords: list[DetailWord] = Field(max_length=1000)
    exclude_keywords: list[DetailWord] = Field(max_length=1000)

    @field_validator("release_date")
    @classmethod
    def calendar_date(cls, value: str | None) -> str | None:
        if value is not None and date.fromisoformat(value).isoformat() != value:
            raise ValueError("Expected YYYY-MM-DD")
        return value


@router.put("/tcg/products/detail/{product_code}", summary="商品マスタ詳細保存（DETAIL-01）")
async def save_product_detail(
    product_code: str,
    payload: ProductDetailUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_super_admin),
) -> dict:
    values = payload.model_dump(mode="json", exclude={"revision"})
    try:
        return await update_product_detail(
            db, product_code, values, payload.revision, str(user.email or user.id or ""),
        )
    except ProductDetailError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# 分類マスタ一覧（作成フォーム用）
# ---------------------------------------------------------------------------


@router.get("/tcg/products/lookups", summary="商品マスタ分類選択肢一覧（CREATE-01）")
async def get_product_lookups(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> dict:
    """作成フォーム用の分類マスタ選択肢を返す。"""
    lookups: dict[str, list[dict]] = {}
    # work_id → public.type_master (SSOT)
    work_rows = await db.execute(text(
        "SELECT id::text AS id, name_ja AS name "
        "FROM public.type_master "
        "WHERE is_active = TRUE ORDER BY name_ja"
    ))
    lookups["work_id"] = [{"id": r.id, "name": r.name} for r in work_rows.fetchall()]
    for key, table, name_col in [
        ("division_id", "tcg_major_categories", "display_name"),
        ("manufacturer_id", "tcg_manufacturers", "display_name"),
        ("product_category_id", "tcg_product_categories", "display_name"),
    ]:
        rows = await db.execute(
            text(
                f"SELECT id::text AS id, {name_col} AS name "
                f"FROM {TCG_SCHEMA}.{table} "
                f"WHERE is_active = TRUE "
                f"ORDER BY {name_col}"
            )
        )
        lookups[key] = [{"id": r.id, "name": r.name} for r in rows.fetchall()]
    return {"lookups": lookups}


# ---------------------------------------------------------------------------
# 商品マスタ新規作成（独立エンドポイント）
# ---------------------------------------------------------------------------


class CreateProductBody(BaseModel):
    japanese_title: str
    mark: str = ""
    english_title: str = ""
    release_date: str | None = None
    division_id: str
    work_id: str
    manufacturer_id: str
    product_category_id: str
    search_keywords: str = ""
    exclude_keywords: str = ""


@router.post("/tcg/products/create", summary="商品マスタ新規追加（CREATE-01）")
async def create_product_standalone(
    body: CreateProductBody,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> dict:
    from app.services.tcg_product_master_svc import create_product
    result = await create_product(
        db,
        extraction_item_id="",
        source_message_id="",
        division_id=body.division_id,
        work_id=body.work_id,
        manufacturer_id=body.manufacturer_id,
        product_category_id=body.product_category_id,
        japanese_title=body.japanese_title,
        release_date=body.release_date,
        search_keywords=body.search_keywords,
        exclude_keywords=body.exclude_keywords,
        mark=body.mark,
        english_title=body.english_title,
        force=True,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("code", "CREATE_FAILED"))
    return result


@router.delete("/tcg/products/detail/{product_code}", summary="商品マスタ削除（DETAIL-02）")
async def delete_product_detail(
    product_code: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> dict:
    """商品マスタから商品を削除する。

    FK制約:
    - product_search_keywords, product_exclude_keywords: ON DELETE CASCADE（自動削除）
    - analysis_results: product_id を NULL に設定してから削除
    - inventory, parse_logs, own_inventory: RESTRICT/NO ACTION（参照があれば削除不可）
    """
    # 商品を検索
    row = await db.execute(
        text("SELECT id FROM public.products WHERE product_code = :code"),
        {"code": product_code},
    )
    product = row.fetchone()
    if product is None:
        raise HTTPException(status_code=404, detail="PRODUCT_NOT_FOUND")

    product_id = product.id

    # analysis_results の product_id を NULL に設定（NO ACTION制約の事前対処）
    await db.execute(
        text(f"UPDATE {TCG_SCHEMA}.analysis_results SET product_id = NULL WHERE product_id = :pid"),
        {"pid": product_id},
    )

    # 商品を削除（keywords は CASCADE で自動削除）
    try:
        await db.execute(
            text("DELETE FROM public.products WHERE id = :pid"),
            {"pid": product_id},
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        # FK制約違反（inventory等が参照中）
        raise HTTPException(
            status_code=409,
            detail="PRODUCT_IN_USE",
        ) from exc

    from app.services.tenant_context import reset_tenant_context
    await reset_tenant_context(db)

    return {"ok": True, "deleted": product_code}
