"""
テナント用 ステータスマスタ API（CRUD）。

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
from app.schemas.central_masters import (
    TcgStatusMasterCreate,
    TcgStatusMasterResponse,
    TcgStatusMasterUpdate,
)

_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}
_MAX_CSV_BYTES = 2 * 1024 * 1024
_STATUS_REQUIRED_COLS = {"status_id", "canonical"}


def _compute_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


async def _read_status_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="STATUS_IMPORT_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="STATUS_IMPORT_EMPTY_FILE")
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="STATUS_IMPORT_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="STATUS_IMPORT_NOT_UTF8") from exc
    return raw


def _parse_status_master(raw: bytes) -> tuple[list[dict], list[str]]:
    text_content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text_content))
    rows: list[dict] = []
    errors: list[str] = []
    if not reader.fieldnames:
        return [], ["Empty CSV"]
    missing = _STATUS_REQUIRED_COLS - set(reader.fieldnames)
    if missing:
        return [], [f"Missing columns: {', '.join(sorted(missing))}"]
    for line_num, raw_row in enumerate(reader, start=2):
        status_id = (raw_row.get("status_id") or "").strip()
        canonical = (raw_row.get("canonical") or "").strip()
        if not status_id:
            errors.append(f"L{line_num}: status_id is required")
            continue
        if not canonical:
            errors.append(f"L{line_num}: canonical is required")
            continue
        enabled_raw = (raw_row.get("enabled") or "true").strip().lower()
        if enabled_raw not in (_BOOL_TRUE | _BOOL_FALSE):
            errors.append(f"L{line_num}: invalid enabled '{enabled_raw}' (must be true/false/1/0)")
            continue
        priority_raw = (raw_row.get("priority") or "0").strip()
        try:
            priority = int(priority_raw)
        except ValueError:
            errors.append(f"L{line_num}: invalid priority '{priority_raw}' (must be integer)")
            continue
        rows.append({
            "status_id": status_id,
            "canonical": canonical,
            "search_pattern": (raw_row.get("search_pattern") or "").strip() or "",
            "exclude_pattern": (raw_row.get("exclude_pattern") or "").strip() or "",
            "priority": priority,
            "enabled": enabled_raw in _BOOL_TRUE,
            "match_type": (raw_row.get("match_type") or "").strip() or "",
            "effect": (raw_row.get("effect") or "").strip() or "",
            "note": (raw_row.get("note") or "").strip() or "",
            "_line": line_num,
        })
    return rows, errors

router = APIRouter()

_COLS = (
    "id, status_id, canonical, search_pattern, exclude_pattern, priority, "
    "enabled, note, match_type, effect, created_at, updated_at"
)
_UPDATABLE = {
    "status_id",
    "canonical",
    "search_pattern",
    "exclude_pattern",
    "priority",
    "enabled",
    "note",
    "match_type",
    "effect",
}


@router.get(
    "/status-master",
    response_model=list[TcgStatusMasterResponse],
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def list_status_master(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": per_page, "offset": offset}
    if search:
        conditions.append("(status_id ILIKE :search OR canonical ILIKE :search)")
        params["search"] = f"%{search}%"
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM public.tcg_status_master {where} "
            "ORDER BY priority, status_id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [TcgStatusMasterResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/status-master",
    response_model=TcgStatusMasterResponse,
    status_code=201,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def create_status_master(
    data: TcgStatusMasterCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(
            "INSERT INTO public.tcg_status_master "
            "(status_id, canonical, search_pattern, exclude_pattern, priority, "
            "enabled, note, match_type, effect, tenant_id) "
            "VALUES (:status_id, :canonical, :search_pattern, :exclude_pattern, "
            ":priority, :enabled, :note, :match_type, :effect, :tenant_id) "
            f"RETURNING {_COLS}"
        ),
        {**data.model_dump(), "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return TcgStatusMasterResponse(**dict(row))


@router.patch(
    "/status-master/{entry_id}",
    response_model=TcgStatusMasterResponse,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def update_status_master(
    entry_id: int,
    data: TcgStatusMasterUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = entry_id
    update_data["tenant_id"] = tenant_id
    result = await db.execute(
        text(
            f"UPDATE public.tcg_status_master SET {set_clauses}, updated_at = NOW() "
            f"WHERE id = :id AND tenant_id = :tenant_id RETURNING {_COLS}"
        ),
        update_data,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ステータスが見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return TcgStatusMasterResponse(**dict(row))


@router.delete(
    "/status-master/{entry_id}",
    status_code=204,
    dependencies=[Depends(require_permission("suppliers.view"))],
)
async def delete_status_master(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(
            "UPDATE public.tcg_status_master SET enabled = FALSE, updated_at = NOW() "
            "WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": entry_id, "tenant_id": tenant_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ステータスが見つかりません")
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072


# ----------------------------------------------------------------------------
# CSV export / import (tenant)
# ----------------------------------------------------------------------------


@router.get(
    "/status-master/export",
    dependencies=[Depends(require_permission("suppliers.view"))],
    summary="テナント用 ステータスマスタ CSVエクスポート",
)
async def export_status_master_csv(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> Response:
    result = await db.execute(
        text(
            "SELECT status_id, canonical, search_pattern, exclude_pattern, "
            "priority, enabled, match_type, effect, note "
            "FROM public.tcg_status_master "
            "WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
            "ORDER BY id"
        ),
        {"tenant_id": tenant_id},
    )
    rows = result.mappings().all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["status_id", "canonical", "search_pattern", "exclude_pattern", "priority", "enabled", "match_type", "effect", "note"])
    for r in rows:
        writer.writerow([
            r["status_id"] or "",
            r["canonical"] or "",
            r["search_pattern"] or "",
            r["exclude_pattern"] or "",
            r["priority"] if r["priority"] is not None else "0",
            str(r["enabled"]).lower() if r["enabled"] is not None else "true",
            r["match_type"] or "",
            r["effect"] or "",
            r["note"] or "",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=status_master.csv"},
    )


@router.post(
    "/status-master/import/preview",
    dependencies=[Depends(require_permission("suppliers.view"))],
    summary="テナント用 ステータスマスタ CSVインポート プレビュー",
)
async def import_status_master_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> dict:
    raw = await _read_status_upload(file)
    rows, errors = _parse_status_master(raw)
    digest = _compute_digest(raw)

    inserts = 0
    updates = 0
    for row in rows:
        res = await db.execute(
            text("SELECT 1 FROM public.tcg_status_master WHERE status_id = :sid AND tenant_id = :tenant_id"),
            {"sid": row["status_id"], "tenant_id": tenant_id},
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
    "/status-master/import/commit",
    dependencies=[Depends(require_permission("suppliers.view"))],
    summary="テナント用 ステータスマスタ CSVインポート 確定",
)
async def import_status_master_commit(
    file: UploadFile = File(...),
    digest: str = Form(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> dict:
    raw = await _read_status_upload(file)
    actual_digest = _compute_digest(raw)
    if actual_digest != digest:
        raise HTTPException(status_code=409, detail="STATUS_IMPORT_DIGEST_MISMATCH")

    rows, errors = _parse_status_master(raw)
    if errors:
        return {"inserted": 0, "updated": 0, "errors": errors}

    inserted = updated = 0
    try:
        for row in rows:
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            exists_result = await db.execute(
                text("SELECT id FROM public.tcg_status_master WHERE status_id = :sid AND tenant_id = :tenant_id"),
                {"sid": data["status_id"], "tenant_id": tenant_id},
            )
            existing = exists_result.fetchone()
            if existing:
                await db.execute(
                    text(
                        "UPDATE public.tcg_status_master SET canonical = :canonical, "
                        "search_pattern = :search_pattern, exclude_pattern = :exclude_pattern, "
                        "priority = :priority, enabled = :enabled, match_type = :match_type, "
                        "effect = :effect, note = :note, updated_at = NOW() "
                        "WHERE id = :id AND tenant_id = :tenant_id"
                    ),
                    {**data, "id": existing[0], "tenant_id": tenant_id},
                )
                updated += 1
            else:
                await db.execute(
                    text(
                        "INSERT INTO public.tcg_status_master "
                        "(status_id, canonical, search_pattern, exclude_pattern, priority, "
                        "enabled, match_type, effect, note, tenant_id) "
                        "VALUES (:status_id, :canonical, :search_pattern, :exclude_pattern, :priority, "
                        ":enabled, :match_type, :effect, :note, :tenant_id)"
                    ),
                    {**data, "tenant_id": tenant_id},
                )
                inserted += 1
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"STATUS_IMPORT_COMMIT_ERROR: {exc}") from exc

    return {"inserted": inserted, "updated": updated, "errors": []}
