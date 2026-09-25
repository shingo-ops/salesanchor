"""
中央 admin 用 public.conditions CRUD ルーター。

テーブル: public.conditions
  id, code, canonical, app_kubun, is_active, priority,
  search_kw, exclude_kw, tenant_id, created_at, updated_at

API:
  GET    /api/v1/super-admin/conditions
  POST   /api/v1/super-admin/conditions
  PATCH  /api/v1/super-admin/conditions/{id}
  DELETE /api/v1/super-admin/conditions/{id}    (soft delete: is_active=FALSE)
  GET    /api/v1/super-admin/conditions/export
  POST   /api/v1/super-admin/conditions/import/preview
  POST   /api/v1/super-admin/conditions/import/commit
"""
from __future__ import annotations

import csv
import hashlib
import io
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.schemas.central_masters import (
    CentralConditionCreate,
    CentralConditionResponse,
    CentralConditionUpdate,
)
from app.schemas.condition import ConditionAliasCreate, ConditionAliasResponse

_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}
_MAX_CSV_BYTES = 2 * 1024 * 1024
_COND_REQUIRED_COLS = {"code", "canonical"}


def _compute_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


async def _read_condition_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="CONDITION_IMPORT_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="CONDITION_IMPORT_EMPTY_FILE")
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CONDITION_IMPORT_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CONDITION_IMPORT_NOT_UTF8") from exc
    return raw


def _parse_conditions(raw: bytes) -> tuple[list[dict], list[str]]:
    text_content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text_content))
    rows: list[dict] = []
    errors: list[str] = []
    if not reader.fieldnames:
        return [], ["Empty CSV"]
    missing = _COND_REQUIRED_COLS - set(reader.fieldnames)
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
        priority_raw = (raw_row.get("priority") or "").strip()
        priority: int | None = None
        if priority_raw:
            try:
                priority = int(priority_raw)
            except ValueError:
                errors.append(f"L{line_num}: invalid priority '{priority_raw}' (must be integer)")
                continue
        rows.append({
            "code": code,
            "canonical": canonical,
            "app_kubun": (raw_row.get("app_kubun") or "").strip() or None,
            "is_active": is_active_raw in _BOOL_TRUE,
            "priority": priority,
            "search_kw": (raw_row.get("search_kw") or "").strip() or "",
            "exclude_kw": (raw_row.get("exclude_kw") or "").strip() or "",
            "match_type": (raw_row.get("match_type") or "KEYWORD").strip() or "KEYWORD",
            "effect": (raw_row.get("effect") or "OUTPUT").strip() or "OUTPUT",
            "_line": line_num,
        })
    return rows, errors

router = APIRouter()

_ALIAS_COLS = "id, condition_id, alias_text, lang, updated_at"

_CONDITION_COLS = (
    "id, code, canonical, app_kubun, is_active, priority, "
    "search_kw, exclude_kw, tenant_id, created_at, updated_at, "
    "match_type, effect"
)
_CONDITION_UPDATABLE = {
    "code", "canonical", "app_kubun", "is_active", "priority",
    "search_kw", "exclude_kw", "match_type", "effect",
}


@router.get(
    "/super-admin/conditions",
    response_model=list[CentralConditionResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_conditions(
    q: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    # 中央マスタ（tenant_id IS NULL）のみを対象とする。
    conditions_list: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if is_active is not None:
        conditions_list.append("is_active = :is_active")
        params["is_active"] = is_active
    if q:
        conditions_list.append("(code ILIKE :q OR canonical ILIKE :q)")
        params["q"] = f"%{q}%"
    where = f"WHERE {' AND '.join(conditions_list)}"
    result = await db.execute(
        text(
            f"SELECT {_CONDITION_COLS} FROM public.conditions {where} "
            "ORDER BY priority NULLS LAST, id LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [CentralConditionResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/conditions",
    response_model=CentralConditionResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_condition(
    data: CentralConditionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    try:
        # code 重複チェック（中央マスタ内）
        exists_result = await db.execute(
            text(
                "SELECT 1 FROM public.conditions "
                "WHERE code = :code AND tenant_id IS NULL"
            ),
            {"code": data.code},
        )
        if exists_result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="状態コードは既に存在します",
            )

        if data.match_type == "REGEX" and data.search_kw:
            try:
                re.compile(data.search_kw)
            except re.error as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"search_kw が無効な正規表現です: {exc}",
                )
        result = await db.execute(
            text(
                f"INSERT INTO public.conditions "
                f"(code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, "
                f"match_type, effect, tenant_id, updated_at) "
                f"VALUES (:code, :canonical, :app_kubun, :is_active, :priority, :search_kw, :exclude_kw, "
                f":match_type, :effect, NULL, now()) "
                f"RETURNING {_CONDITION_COLS}"
            ),
            {
                "code": data.code,
                "canonical": data.canonical,
                "app_kubun": data.app_kubun,
                "is_active": data.is_active,
                "priority": data.priority,
                "search_kw": data.search_kw,
                "exclude_kw": data.exclude_kw,
                "match_type": data.match_type,
                "effect": data.effect,
            },
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"制約違反: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    return CentralConditionResponse(**dict(row))


@router.patch(
    "/super-admin/conditions/{condition_id}",
    response_model=CentralConditionResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_condition(
    condition_id: int,
    data: CentralConditionUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _CONDITION_UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = condition_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.conditions SET {set_clauses}, updated_at = now() "
                f"WHERE id = :id AND tenant_id IS NULL "
                f"RETURNING {_CONDITION_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="状態が見つかりません")
    await db.commit()
    return CentralConditionResponse(**dict(row))


@router.delete(
    "/super-admin/conditions/{condition_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_condition(
    condition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=FALSE)。public.conditions は他テーブルから
    参照されるため hard delete はしない。"""
    result = await db.execute(
        text(
            "UPDATE public.conditions SET is_active = FALSE, updated_at = now() "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": condition_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="状態が見つかりません")
    await db.commit()


# ----------------------------------------------------------------------------
# CSV export / import (super-admin)
# ----------------------------------------------------------------------------


@router.get(
    "/super-admin/conditions/export",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 状態マスタ CSVエクスポート",
)
async def export_conditions_csv(db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(
        text(
            "SELECT code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, "
            "match_type, effect "
            "FROM public.conditions "
            "WHERE tenant_id IS NULL "
            "ORDER BY id"
        )
    )
    rows = result.mappings().all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["code", "canonical", "app_kubun", "is_active", "priority", "search_kw", "exclude_kw", "match_type", "effect"])
    for r in rows:
        writer.writerow([
            r["code"] or "",
            r["canonical"] or "",
            r["app_kubun"] or "",
            str(r["is_active"]).lower() if r["is_active"] is not None else "true",
            r["priority"] if r["priority"] is not None else "",
            r["search_kw"] or "",
            r["exclude_kw"] or "",
            r["match_type"] or "KEYWORD",
            r["effect"] or "OUTPUT",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=conditions.csv"},
    )


@router.post(
    "/super-admin/conditions/import/preview",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 状態マスタ CSVインポート プレビュー",
)
async def import_conditions_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = await _read_condition_upload(file)
    rows, errors = _parse_conditions(raw)
    digest = _compute_digest(raw)

    inserts = 0
    updates = 0
    for row in rows:
        res = await db.execute(
            text("SELECT 1 FROM public.conditions WHERE code = :code AND tenant_id IS NULL"),
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
    "/super-admin/conditions/import/commit",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理 状態マスタ CSVインポート 確定",
)
async def import_conditions_commit(
    file: UploadFile = File(...),
    digest: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = await _read_condition_upload(file)
    actual_digest = _compute_digest(raw)
    if actual_digest != digest:
        raise HTTPException(status_code=409, detail="CONDITION_IMPORT_DIGEST_MISMATCH")

    rows, errors = _parse_conditions(raw)
    if errors:
        return {"inserted": 0, "updated": 0, "errors": errors}

    inserted = updated = 0
    try:
        for row in rows:
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            exists_result = await db.execute(
                text("SELECT id FROM public.conditions WHERE code = :code AND tenant_id IS NULL"),
                {"code": data["code"]},
            )
            existing = exists_result.fetchone()
            if existing:
                await db.execute(
                    text(
                        "UPDATE public.conditions SET canonical = :canonical, app_kubun = :app_kubun, "
                        "is_active = :is_active, priority = :priority, search_kw = :search_kw, "
                        "exclude_kw = :exclude_kw, match_type = :match_type, effect = :effect, "
                        "updated_at = now() "
                        "WHERE id = :id AND tenant_id IS NULL"
                    ),
                    {**data, "id": existing[0]},
                )
                updated += 1
            else:
                await db.execute(
                    text(
                        "INSERT INTO public.conditions "
                        "(code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, "
                        "match_type, effect, tenant_id, updated_at) "
                        "VALUES (:code, :canonical, :app_kubun, :is_active, :priority, :search_kw, :exclude_kw, "
                        ":match_type, :effect, NULL, now())"
                    ),
                    data,
                )
                inserted += 1
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"CONDITION_IMPORT_COMMIT_ERROR: {exc}") from exc

    return {"inserted": inserted, "updated": updated, "errors": []}


# ----------------------------------------------------------------------------
# condition_aliases (super-admin)
# ----------------------------------------------------------------------------


@router.get(
    "/super-admin/conditions/{condition_id}/aliases",
    response_model=list[ConditionAliasResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_condition_aliases(
    condition_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        text(
            f"SELECT {_ALIAS_COLS} FROM public.condition_aliases "
            f"WHERE condition_id = :cid ORDER BY id"
        ),
        {"cid": condition_id},
    )
    return [ConditionAliasResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/conditions/{condition_id}/aliases",
    response_model=ConditionAliasResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_condition_alias(
    condition_id: int,
    data: ConditionAliasCreate,
    db: AsyncSession = Depends(get_db),
):
    if data.condition_id != condition_id:
        raise HTTPException(
            status_code=400,
            detail="URL の condition_id と body の condition_id が一致しません",
        )
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.condition_aliases "
                f"(condition_id, alias_text, lang) "
                f"VALUES (:condition_id, :alias_text, :lang) "
                f"RETURNING {_ALIAS_COLS}"
            ),
            data.model_dump(),
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"重複または FK 違反: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    return ConditionAliasResponse(**dict(row))


@router.delete(
    "/super-admin/conditions/aliases/{alias_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_condition_alias(
    alias_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        text("DELETE FROM public.condition_aliases WHERE id = :id"),
        {"id": alias_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="別名が見つかりません")
    await db.commit()
