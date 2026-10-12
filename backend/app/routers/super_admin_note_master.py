"""
中央 admin 用 public.tcg_note_master CRUD ルーター。

API:
  GET    /api/v1/super-admin/note-master
  POST   /api/v1/super-admin/note-master
  PATCH  /api/v1/super-admin/note-master/{id}
  DELETE /api/v1/super-admin/note-master/{id}
  GET    /api/v1/super-admin/note-master/export
  POST   /api/v1/super-admin/note-master/import/preview
  POST   /api/v1/super-admin/note-master/import/commit
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
from app.schemas.central_masters import (
    TcgNoteMasterCreate,
    TcgNoteMasterResponse,
    TcgNoteMasterUpdate,
)

_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}
_MAX_CSV_BYTES = 2 * 1024 * 1024
_NOTE_REQUIRED_COLS = {"label_ja"}


def _compute_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


async def _read_note_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="NOTE_IMPORT_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="NOTE_IMPORT_EMPTY_FILE")
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="NOTE_IMPORT_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="NOTE_IMPORT_NOT_UTF8") from exc
    return raw


def _parse_note_master(raw: bytes) -> tuple[list[dict], list[str]]:
    text_content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text_content))
    rows: list[dict] = []
    errors: list[str] = []
    if not reader.fieldnames:
        return [], ["Empty CSV"]
    missing = _NOTE_REQUIRED_COLS - set(reader.fieldnames)
    if missing:
        return [], [f"Missing columns: {', '.join(sorted(missing))}"]
    for line_num, raw_row in enumerate(reader, start=2):
        label_ja = (raw_row.get("label_ja") or "").strip()
        if not label_ja:
            errors.append(f"L{line_num}: label_ja is required")
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
            "label_ja": label_ja,
            "label_en": (raw_row.get("label_en") or "").strip() or None,
            "enabled": enabled_raw in _BOOL_TRUE,
            "search_keywords": (raw_row.get("search_keywords") or "").strip() or "",
            "exclude_keywords": (raw_row.get("exclude_keywords") or "").strip() or "",
            "category": (raw_row.get("category") or "").strip() or None,
            "priority": priority,
            "match_type": (raw_row.get("match_type") or "").strip() or "",
            "search_pattern": (raw_row.get("search_pattern") or "").strip() or "",
            "label_template": (raw_row.get("label_template") or "").strip() or None,
            "_line": line_num,
        })
    return rows, errors

router = APIRouter()

_NOTE_COLS = (
    "id, label_ja, label_en, enabled, search_keywords, exclude_keywords, "
    "category, priority, match_type, search_pattern, label_template, "
    "created_at, updated_at"
)

_NOTE_UPDATABLE = {
    "label_ja",
    "label_en",
    "enabled",
    "search_keywords",
    "exclude_keywords",
    "category",
    "priority",
    "match_type",
    "search_pattern",
    "label_template",
}


@router.get(
    "/super-admin/note-master",
    response_model=list[TcgNoteMasterResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_note_master(
    q: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    conditions: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if q:
        conditions.append(
            "(label_ja ILIKE :q OR label_en ILIKE :q OR category ILIKE :q)"
        )
        params["q"] = f"%{q}%"
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_NOTE_COLS} FROM public.tcg_note_master {where} "
            "ORDER BY priority, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [TcgNoteMasterResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/note-master",
    response_model=TcgNoteMasterResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_note_master(
    data: TcgNoteMasterCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.tcg_note_master "
                "(label_ja, label_en, enabled, search_keywords, exclude_keywords, "
                " category, priority, match_type, search_pattern, label_template, tenant_id) "
                "VALUES (:label_ja, :label_en, :enabled, :search_keywords, :exclude_keywords, "
                "        :category, :priority, :match_type, :search_pattern, :label_template, NULL) "
                f"RETURNING {_NOTE_COLS}"
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
    return TcgNoteMasterResponse(**dict(row))


@router.patch(
    "/super-admin/note-master/{note_id}",
    response_model=TcgNoteMasterResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_note_master(
    note_id: int,
    data: TcgNoteMasterUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _NOTE_UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = note_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.tcg_note_master SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id IS NULL RETURNING {_NOTE_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="備考マスタが見つかりません")
    await db.commit()
    return TcgNoteMasterResponse(**dict(row))


@router.delete(
    "/super-admin/note-master/{note_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_note_master(
    note_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text(
            "DELETE FROM public.tcg_note_master "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": note_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="備考マスタが見つかりません")
    await db.commit()


# ----------------------------------------------------------------------------
# CSV export / import
# ----------------------------------------------------------------------------


@router.get(
    "/super-admin/note-master/export",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 備考マスタ CSVエクスポート",
)
async def export_note_master_csv(db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(
        text(
            "SELECT label_ja, label_en, enabled, search_keywords, exclude_keywords, "
            "category, priority, match_type, search_pattern, label_template "
            "FROM public.tcg_note_master "
            "WHERE tenant_id IS NULL "
            "ORDER BY id"
        )
    )
    rows = result.mappings().all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["label_ja", "label_en", "enabled", "search_keywords", "exclude_keywords", "category", "priority", "match_type", "search_pattern", "label_template"])
    for r in rows:
        writer.writerow([
            r["label_ja"] or "",
            r["label_en"] or "",
            str(r["enabled"]).lower() if r["enabled"] is not None else "true",
            r["search_keywords"] or "",
            r["exclude_keywords"] or "",
            r["category"] or "",
            r["priority"] if r["priority"] is not None else "0",
            r["match_type"] or "",
            r["search_pattern"] or "",
            r["label_template"] or "",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=note_master.csv"},
    )


@router.post(
    "/super-admin/note-master/import/preview",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 備考マスタ CSVインポート プレビュー",
)
async def import_note_master_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = await _read_note_upload(file)
    rows, errors = _parse_note_master(raw)
    digest = _compute_digest(raw)

    inserts = 0
    updates = 0
    for row in rows:
        res = await db.execute(
            text("SELECT 1 FROM public.tcg_note_master WHERE label_ja = :label_ja AND tenant_id IS NULL"),
            {"label_ja": row["label_ja"]},
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
    "/super-admin/note-master/import/commit",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 備考マスタ CSVインポート 確定",
)
async def import_note_master_commit(
    file: UploadFile = File(...),
    digest: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = await _read_note_upload(file)
    actual_digest = _compute_digest(raw)
    if actual_digest != digest:
        raise HTTPException(status_code=409, detail="NOTE_IMPORT_DIGEST_MISMATCH")

    rows, errors = _parse_note_master(raw)
    if errors:
        return {"inserted": 0, "updated": 0, "errors": errors}

    inserted = updated = 0
    try:
        for row in rows:
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            exists_result = await db.execute(
                text("SELECT id FROM public.tcg_note_master WHERE label_ja = :label_ja AND tenant_id IS NULL"),
                {"label_ja": data["label_ja"]},
            )
            existing = exists_result.fetchone()
            if existing:
                await db.execute(
                    text(
                        "UPDATE public.tcg_note_master SET label_en = :label_en, enabled = :enabled, "
                        "search_keywords = :search_keywords, exclude_keywords = :exclude_keywords, "
                        "category = :category, priority = :priority, match_type = :match_type, "
                        "search_pattern = :search_pattern, label_template = :label_template, "
                        "updated_at = NOW() "
                        "WHERE id = :id AND tenant_id IS NULL"
                    ),
                    {**data, "id": existing[0]},
                )
                updated += 1
            else:
                await db.execute(
                    text(
                        "INSERT INTO public.tcg_note_master "
                        "(label_ja, label_en, enabled, search_keywords, exclude_keywords, "
                        " category, priority, match_type, search_pattern, label_template, tenant_id) "
                        "VALUES (:label_ja, :label_en, :enabled, :search_keywords, :exclude_keywords, "
                        "        :category, :priority, :match_type, :search_pattern, :label_template, NULL)"
                    ),
                    data,
                )
                inserted += 1
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"NOTE_IMPORT_COMMIT_ERROR: {exc}") from exc

    return {"inserted": inserted, "updated": updated, "errors": []}
