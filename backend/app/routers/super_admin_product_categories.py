"""
中央 admin 用 public.tcg_product_categories CRUD ルーター。

API:
  GET    /api/v1/super-admin/product-categories
  POST   /api/v1/super-admin/product-categories
  PATCH  /api/v1/super-admin/product-categories/{id}
  DELETE /api/v1/super-admin/product-categories/{id}   (soft delete: is_active=FALSE)
  GET    /api/v1/super-admin/product-categories/export
  POST   /api/v1/super-admin/product-categories/import/preview
  POST   /api/v1/super-admin/product-categories/import/commit
"""
from __future__ import annotations

import csv
import hashlib
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.schemas.product_category import (
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCategoryUpdate,
)

_BOOL_TRUE = {"true", "1", "yes"}
MAX_CSV_BYTES = 2 * 1024 * 1024
_PC_REQUIRED_COLS = {"code", "display_name"}


def _compute_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()[:16]


async def _read_pc_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="PRODUCT_CATEGORIES_IMPORT_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="PRODUCT_CATEGORIES_IMPORT_EMPTY_FILE")
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="PRODUCT_CATEGORIES_IMPORT_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="PRODUCT_CATEGORIES_IMPORT_NOT_UTF8") from exc
    return raw


def _parse_product_categories(raw: bytes) -> tuple[list[dict], list[str]]:
    text_content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text_content))
    rows: list[dict] = []
    errors: list[str] = []
    if not reader.fieldnames:
        return [], ["Empty CSV"]
    missing = _PC_REQUIRED_COLS - set(reader.fieldnames)
    if missing:
        return [], [f"Missing columns: {', '.join(sorted(missing))}"]
    for line_num, raw_row in enumerate(reader, start=2):
        code = (raw_row.get("code") or "").strip()
        display_name = (raw_row.get("display_name") or "").strip()
        if not code:
            errors.append(f"L{line_num}: code is required")
            continue
        if not display_name:
            errors.append(f"L{line_num}: display_name is required")
            continue
        is_active_raw = (raw_row.get("is_active") or "true").strip().lower()
        is_active = is_active_raw in _BOOL_TRUE
        rows.append({
            "code": code,
            "display_name": display_name,
            "kubun_type": (raw_row.get("kubun_type") or "").strip() or None,
            "is_active": is_active,
            "_line": line_num,
        })
    return rows, errors

router = APIRouter()

_COLS = "id, code, display_name, kubun_type, is_active, tenant_id, created_at, updated_at"
_UPDATABLE = {"code", "display_name", "kubun_type", "is_active"}


@router.get(
    "/super-admin/product-categories",
    response_model=list[ProductCategoryResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_product_categories(
    q: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    # 中央マスタ（tenant_id IS NULL）のみを対象とする。
    conditions: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if q:
        conditions.append("(code ILIKE :q OR display_name ILIKE :q)")
        params["q"] = f"%{q}%"
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_COLS} "
            f"FROM public.tcg_product_categories {where} "
            "ORDER BY code LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [ProductCategoryResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/product-categories",
    response_model=ProductCategoryResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_product_category(
    data: ProductCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.tcg_product_categories "
                f"(code, display_name, kubun_type, is_active, tenant_id) "
                f"VALUES (:code, :display_name, :kubun_type, :is_active, NULL) "
                f"RETURNING {_COLS}"
            ),
            data.model_dump(),
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"重複または制約違反: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    return ProductCategoryResponse(**dict(row))


@router.get(
    "/super-admin/product-categories/export",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 商品カテゴリマスタ CSVエクスポート",
)
async def export_product_categories_csv(db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(
        text(
            "SELECT code, display_name, kubun_type, is_active "
            "FROM public.tcg_product_categories "
            "WHERE tenant_id IS NULL "
            "ORDER BY id"
        )
    )
    rows = result.mappings().all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["code", "display_name", "kubun_type", "is_active"])
    for r in rows:
        writer.writerow([
            r["code"] or "",
            r["display_name"] or "",
            r["kubun_type"] or "",
            str(r["is_active"]).lower() if r["is_active"] is not None else "true",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=product-categories.csv"},
    )


@router.post(
    "/super-admin/product-categories/import/preview",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 商品カテゴリマスタ CSVインポート プレビュー",
)
async def import_product_categories_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = await _read_pc_upload(file)
    rows, errors = _parse_product_categories(raw)
    digest = _compute_digest(raw)

    inserts = 0
    updates = 0
    for row in rows:
        res = await db.execute(
            text("SELECT 1 FROM public.tcg_product_categories WHERE code = :code AND tenant_id IS NULL"),
            {"code": row["code"]},
        )
        if res.fetchone():
            updates += 1
        else:
            inserts += 1

    preview_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    return {
        "digest": digest,
        "total": len(rows),
        "inserts": inserts,
        "updates": updates,
        "errors": errors,
        "preview_rows": preview_rows,
    }


@router.post(
    "/super-admin/product-categories/import/commit",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 商品カテゴリマスタ CSVインポート 確定",
)
async def import_product_categories_commit(
    file: UploadFile = File(...),
    digest: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = await _read_pc_upload(file)
    actual_digest = _compute_digest(raw)
    if actual_digest != digest:
        raise HTTPException(status_code=409, detail="PRODUCT_CATEGORIES_IMPORT_DIGEST_MISMATCH")

    rows, errors = _parse_product_categories(raw)
    if errors:
        return {"inserted": 0, "updated": 0, "errors": errors}

    inserted = updated = 0
    try:
        for row in rows:
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            exists_result = await db.execute(
                text("SELECT id FROM public.tcg_product_categories WHERE code = :code AND tenant_id IS NULL"),
                {"code": data["code"]},
            )
            existing = exists_result.fetchone()
            if existing:
                await db.execute(
                    text(
                        "UPDATE public.tcg_product_categories "
                        "SET display_name = :display_name, kubun_type = :kubun_type, "
                        "is_active = :is_active, updated_at = NOW() "
                        "WHERE id = :id AND tenant_id IS NULL"
                    ),
                    {**data, "id": existing[0]},
                )
                updated += 1
            else:
                await db.execute(
                    text(
                        "INSERT INTO public.tcg_product_categories "
                        "(code, display_name, kubun_type, is_active, tenant_id) "
                        "VALUES (:code, :display_name, :kubun_type, :is_active, NULL)"
                    ),
                    data,
                )
                inserted += 1
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"PRODUCT_CATEGORIES_IMPORT_COMMIT_ERROR: {exc}") from exc

    return {"inserted": inserted, "updated": updated, "errors": []}


@router.patch(
    "/super-admin/product-categories/{category_id}",
    response_model=ProductCategoryResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_product_category(
    category_id: int,
    data: ProductCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = category_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.tcg_product_categories SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id IS NULL RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="商品カテゴリが見つかりません")
    await db.commit()
    return ProductCategoryResponse(**dict(row))


@router.delete(
    "/super-admin/product-categories/{category_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_product_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。"""
    result = await db.execute(
        text(
            "UPDATE public.tcg_product_categories SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": category_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="商品カテゴリが見つかりません")
    await db.commit()
