"""
テナント用 単位マスタ API（CRUD）。

tenant_id = :tenant_id の行のみ操作。共用マスタ（tenant_id IS NULL）は参照不可。
ADR-072: write endpoint の db.commit() 直後に reset_tenant_context() 必須。
"""
from __future__ import annotations

import csv
import hashlib
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.schemas.central_masters import UnitCreate, UnitResponse, UnitUpdate

_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}
_MAX_CSV_BYTES = 2 * 1024 * 1024
_UNIT_REQUIRED_COLS = {"code", "canonical"}


def _compute_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


async def _read_unit_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="UNIT_IMPORT_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="UNIT_IMPORT_EMPTY_FILE")
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="UNIT_IMPORT_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="UNIT_IMPORT_NOT_UTF8") from exc
    return raw


def _parse_units(raw: bytes) -> tuple[list[dict], list[str]]:
    text_content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text_content))
    rows: list[dict] = []
    errors: list[str] = []
    if not reader.fieldnames:
        return [], ["Empty CSV"]
    missing = _UNIT_REQUIRED_COLS - set(reader.fieldnames)
    if missing:
        return [], [f"Missing columns: {', '.join(sorted(missing))}"]
    for line_num, raw_row in enumerate(reader, start=2):
        code = (raw_row.get("code") or "").strip()
        canonical = (raw_row.get("canonical") or "").strip()
        if not code:
            errors.append(f"L{line_num}: code is required")
            continue
        if not canonical:
            errors.append(f"L{line_num}: canonical is required")
            continue
        is_active_raw = (raw_row.get("is_active") or "true").strip().lower()
        if is_active_raw not in (_BOOL_TRUE | _BOOL_FALSE):
            errors.append(f"L{line_num}: invalid is_active '{is_active_raw}' (must be true/false/1/0)")
            continue
        rows.append({
            "code": code,
            "canonical": canonical,
            "kubun": (raw_row.get("kubun") or "").strip() or None,
            "is_active": is_active_raw in _BOOL_TRUE,
            "_line": line_num,
        })
    return rows, errors

router = APIRouter()

_COLS = "id, code, canonical, kubun, is_active, created_at, updated_at"
_UPDATABLE = {"code", "canonical", "kubun", "is_active"}


@router.get(
    "/units",
    response_model=list[UnitResponse],
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def list_units(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": per_page, "offset": offset}
    if search:
        conditions.append("(code ILIKE :search OR canonical ILIKE :search)")
        params["search"] = f"%{search}%"
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(f"SELECT {_COLS} FROM public.units {where} ORDER BY code LIMIT :limit OFFSET :offset"),
        params,
    )
    return [UnitResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/units",
    response_model=UnitResponse,
    status_code=201,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def create_unit(
    data: UnitCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(
            f"INSERT INTO public.units (code, canonical, kubun, is_active, tenant_id) "
            f"VALUES (:code, :canonical, :kubun, :is_active, :tenant_id) "
            f"RETURNING {_COLS}"
        ),
        {**data.model_dump(), "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return UnitResponse(**dict(row))


@router.patch(
    "/units/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def update_unit(
    unit_id: int,
    data: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = unit_id
    update_data["tenant_id"] = tenant_id
    result = await db.execute(
        text(
            f"UPDATE public.units SET {set_clauses}, updated_at = NOW() "
            f"WHERE id = :id AND tenant_id = :tenant_id RETURNING {_COLS}"
        ),
        update_data,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="単位が見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return UnitResponse(**dict(row))


@router.delete(
    "/units/{unit_id}",
    status_code=204,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def delete_unit(
    unit_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(
            "UPDATE public.units SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": unit_id, "tenant_id": tenant_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="単位が見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072


# ----------------------------------------------------------------------------
# CSV export / import (tenant)
# ----------------------------------------------------------------------------


@router.get(
    "/units/export",
    dependencies=[Depends(require_permission("suppliers.view"))],
    summary="テナント用 単位マスタ CSVエクスポート",
)
async def export_units_csv(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> Response:
    result = await db.execute(
        text(
            "SELECT code, canonical, kubun, is_active "
            "FROM public.units "
            "WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
            "ORDER BY id"
        ),
        {"tenant_id": tenant_id},
    )
    rows = result.mappings().all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["code", "canonical", "kubun", "is_active"])
    for r in rows:
        writer.writerow([
            r["code"] or "",
            r["canonical"] or "",
            r["kubun"] or "",
            str(r["is_active"]).lower() if r["is_active"] is not None else "true",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=units.csv"},
    )


@router.post(
    "/units/import/preview",
    dependencies=[Depends(require_permission("suppliers.view"))],
    summary="テナント用 単位マスタ CSVインポート プレビュー",
)
async def import_units_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> dict:
    raw = await _read_unit_upload(file)
    rows, errors = _parse_units(raw)
    digest = _compute_digest(raw)

    inserts = 0
    updates = 0
    for row in rows:
        res = await db.execute(
            text("SELECT 1 FROM public.units WHERE code = :code AND tenant_id = :tenant_id"),
            {"code": row["code"], "tenant_id": tenant_id},
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
    "/units/import/commit",
    dependencies=[Depends(require_permission("suppliers.view"))],
    summary="テナント用 単位マスタ CSVインポート 確定",
)
async def import_units_commit(
    file: UploadFile = File(...),
    digest: str = Form(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> dict:
    raw = await _read_unit_upload(file)
    actual_digest = _compute_digest(raw)
    if actual_digest != digest:
        raise HTTPException(status_code=409, detail="UNIT_IMPORT_DIGEST_MISMATCH")

    rows, errors = _parse_units(raw)
    if errors:
        return {"inserted": 0, "updated": 0, "errors": errors}

    inserted = updated = 0
    try:
        for row in rows:
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            exists_result = await db.execute(
                text("SELECT id FROM public.units WHERE code = :code AND tenant_id = :tenant_id"),
                {"code": data["code"], "tenant_id": tenant_id},
            )
            existing = exists_result.fetchone()
            if existing:
                await db.execute(
                    text(
                        "UPDATE public.units SET canonical = :canonical, kubun = :kubun, "
                        "is_active = :is_active, updated_at = NOW() "
                        "WHERE id = :id AND tenant_id = :tenant_id"
                    ),
                    {**data, "id": existing[0], "tenant_id": tenant_id},
                )
                updated += 1
            else:
                await db.execute(
                    text(
                        "INSERT INTO public.units (code, canonical, kubun, is_active, tenant_id) "
                        "VALUES (:code, :canonical, :kubun, :is_active, :tenant_id)"
                    ),
                    {**data, "tenant_id": tenant_id},
                )
                inserted += 1
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"UNIT_IMPORT_COMMIT_ERROR: {exc}") from exc

    return {"inserted": inserted, "updated": updated, "errors": []}
