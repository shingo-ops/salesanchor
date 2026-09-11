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

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
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


class ProductListResponse(BaseModel):
    total: int
    items: list[ProductListItem]


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
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> ProductListResponse:
    like = "%" + query.strip() + "%" if query.strip() else "%"
    total_row = await db.execute(
        text(
            f"SELECT count(*) FROM {TCG_SCHEMA}.tcg_products "
            f"WHERE (japanese_title ILIKE :like OR code ILIKE :like)"
        ),
        {"like": like},
    )
    total = int(total_row.fetchone()[0])

    rows = await db.execute(
        text(
            f"SELECT p.code, p.japanese_title, p.english_title, p.mark, p.release_date, "
            f"(SELECT count(*) FROM {TCG_SCHEMA}.product_search_keywords k "
            f"WHERE k.product_id = p.id) AS keyword_count "
            f"FROM {TCG_SCHEMA}.tcg_products p "
            f"WHERE (p.japanese_title ILIKE :like OR p.code ILIKE :like) "
            f"ORDER BY p.code DESC LIMIT :limit OFFSET :offset"
        ),
        {"like": like, "limit": limit, "offset": offset},
    )
    items = [
        ProductListItem(
            code=str(r[0]),
            japanese_title=str(r[1] or ""),
            english_title=str(r[2] or ""),
            mark=str(r[3] or ""),
            release_date=str(r[4] or ""),
            keyword_count=int(r[5] or 0),
        )
        for r in rows.fetchall()
    ]
    return ProductListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# 取り込み
# ---------------------------------------------------------------------------


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
    _user: dict = Depends(require_super_admin),
) -> dict:
    """
    検査だけを行う。書き込みを一切しない。

    画面はこの結果を確認の段で見せる。止める判定のある行は登録されない。
    """
    raw = await _read_csv(file)
    return await preview(db, raw, file.filename or "")


@router.post(
    "/tcg/products/import/commit",
    summary="商品マスタ CSV 取り込みの実行（IMPORT-01）",
)
async def commit_import_endpoint(
    file: UploadFile = File(..., description="10列の CSV ファイル"),
    confirmed_digest: str = Form(..., description="確認の段で受け取った指紋"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_super_admin),
) -> dict:
    """
    検査をやり直し、止める判定の無い行だけを登録する。

    確認の段を経ずに書き込む経路を作らないため、確認の段で返した指紋と
    同じものを必ず受け取る。一致しない場合は書き込まない。
    """
    raw = await _read_csv(file)
    checked = await preview(db, raw, file.filename or "")
    if checked["file_errors"]:
        raise HTTPException(status_code=422, detail=checked["file_errors"])
    if confirmed_digest != checked["digest"]:
        raise HTTPException(status_code=409, detail="PRODUCT_IMPORT_DIGEST_MISMATCH")
    executed_by = str(user.get("email") or user.get("id") or "")
    try:
        return await commit_import(db, raw, file.filename or "", executed_by)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
