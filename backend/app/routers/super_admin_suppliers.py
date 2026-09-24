"""
中央 admin 用 public.suppliers + public.supplier_discord_routing CRUD ルーター。

spec.md v1.1 F2 (Sprint 2) / AC2.5:
  - supplier_type ('individual' / 'corporate') 切替
  - default_language ('ja' / 'en' / 'ko' / 'zh')
  - Discord routing 紐付け（1 supplier に対し複数 guild × channel 可）

API:
  GET    /api/v1/super-admin/suppliers
  POST   /api/v1/super-admin/suppliers
  PATCH  /api/v1/super-admin/suppliers/{id}
  DELETE /api/v1/super-admin/suppliers/{id}                    (soft delete)
  GET    /api/v1/super-admin/suppliers/export
  POST   /api/v1/super-admin/suppliers/import/preview
  POST   /api/v1/super-admin/suppliers/import/commit
  GET    /api/v1/super-admin/suppliers/{id}/discord-routing
  POST   /api/v1/super-admin/suppliers/{id}/discord-routing
  DELETE /api/v1/super-admin/suppliers/discord-routing/{routing_id}
"""
from __future__ import annotations

import csv
import hashlib
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.schemas.central_masters import (
    CentralSupplierCreate,
    CentralSupplierResponse,
    CentralSupplierUpdate,
    SupplierDiscordRoutingCreate,
    SupplierDiscordRoutingResponse,
    SupplierExtractionOverviewItem,
    SupplierExtractionRulesResponse,
    SupplierExtractionRulesUpdate,
    SupplierPromptResponse,
    SupplierPromptUpdate,
    SupplierSourceMessagesResponse,
)

router = APIRouter()

_SUPPLIER_COLS = (
    "id, supplier_code, name, supplier_type, default_language, "
    "contact_name, email, phone, address, notes, is_active, created_at, updated_at, "
    # ADR-093: LINE名 + 構造化住所
    "line_name, postal_code, prefecture, city, address1, address2"
)
_SUPPLIER_UPDATABLE = {
    "name", "supplier_type", "default_language",
    "contact_name", "email", "phone", "address", "notes", "is_active",
    # ADR-093: LINE名 + 構造化住所
    "line_name", "postal_code", "prefecture", "city", "address1", "address2",
}

_ROUTING_COLS = "id, supplier_id, discord_guild_id, discord_channel_id, is_active"


@router.get(
    "/super-admin/suppliers",
    response_model=list[CentralSupplierResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_suppliers(
    q: str | None = Query(default=None, max_length=255),
    supplier_type: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    # LINE 解析用マスタ（tenant_id IS NULL）のみを対象とする。
    conditions: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if q:
        # ADR-093 改修: 検索は仕入元名のみ（UI の検索窓仕様に一致）。
        conditions.append("name ILIKE :q")
        params["q"] = f"%{q}%"
    if supplier_type:
        conditions.append("supplier_type = :supplier_type")
        params["supplier_type"] = supplier_type
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    where = f"WHERE {' AND '.join(conditions)}"
    # Discord ID 列表示用に、紐付け済み routing の channel_id を相関サブクエリで付与
    # （複数紐付けがある場合は最初の有効分。編集は従来の紐付けUIで行う）。
    result = await db.execute(
        text(
            f"SELECT {_SUPPLIER_COLS}, "
            "(SELECT r.discord_channel_id FROM public.supplier_discord_routing r "
            " WHERE r.supplier_id = public.suppliers.id AND r.is_active "
            " ORDER BY r.id LIMIT 1) AS discord_channel_id "
            f"FROM public.suppliers {where} "
            "ORDER BY name LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [CentralSupplierResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/suppliers",
    response_model=CentralSupplierResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_supplier(
    data: CentralSupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.suppliers "
                f"(name, supplier_type, default_language, contact_name, email, phone, "
                f" address, notes, is_active, created_by, tenant_id, "
                f" line_name, postal_code, prefecture, city, address1, address2) "
                f"VALUES (:name, :supplier_type, :default_language, :contact_name, :email, "
                f"        :phone, :address, :notes, :is_active, :uid, NULL, "
                f"        :line_name, :postal_code, :prefecture, :city, :address1, :address2) "
                f"ON CONFLICT (line_name) "
                f"    WHERE line_name IS NOT NULL AND is_active = TRUE AND tenant_id IS NULL "
                f"DO UPDATE SET line_name = EXCLUDED.line_name "
                f"RETURNING {_SUPPLIER_COLS}"
            ),
            {**data.model_dump(), "uid": current_user.id},
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"重複または制約違反: {exc.orig}",
        )
    row = result.mappings().first()
    new_id = row["id"]
    # supplier_code を自動採番（既存 {tenant}.suppliers パターン踏襲）
    await db.execute(
        text("UPDATE public.suppliers SET supplier_code = :code WHERE id = :id AND supplier_code IS NULL"),
        {"code": f"SP-{new_id:05d}", "id": new_id},
    )
    fetched = await db.execute(
        text(f"SELECT {_SUPPLIER_COLS} FROM public.suppliers WHERE id = :id"),
        {"id": new_id},
    )
    row = fetched.mappings().first()
    await db.commit()
    return CentralSupplierResponse(**dict(row))


@router.patch(
    "/super-admin/suppliers/{supplier_id}",
    response_model=CentralSupplierResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_supplier(
    supplier_id: int,
    data: CentralSupplierUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _SUPPLIER_UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = supplier_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.suppliers SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id RETURNING {_SUPPLIER_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="仕入元が見つかりません")
    await db.commit()
    return CentralSupplierResponse(**dict(row))


@router.delete(
    "/super-admin/suppliers/{supplier_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
):
    """soft delete (is_active=false)。public schema の supplier は他テーブルから
    FK 参照されるため hard delete はしない。"""
    result = await db.execute(
        text(
            "UPDATE public.suppliers SET is_active = FALSE, updated_at = NOW() "
            "WHERE id = :id"
        ),
        {"id": supplier_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="仕入元が見つかりません")
    await db.commit()


# ----------------------------------------------------------------------------
# CSV export / import (central admin, tenant_id IS NULL)
# ----------------------------------------------------------------------------

_CSV_EXPORT_COLS = (
    "supplier_code", "name", "supplier_type", "line_name", "contact_name",
    "email", "phone", "postal_code", "prefecture", "city", "address1",
    "address2", "notes", "is_active",
)

_VALID_SUPPLIER_TYPES = {"corporate", "individual"}
_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}

MAX_CSV_BYTES = 2 * 1024 * 1024


def _compute_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


async def _read_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="SUPPLIER_IMPORT_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="SUPPLIER_IMPORT_EMPTY_FILE")
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="SUPPLIER_IMPORT_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="SUPPLIER_IMPORT_NOT_UTF8") from exc
    return raw


def _parse_and_validate(raw: bytes) -> tuple[list[dict], list[str]]:
    """Parse CSV bytes and validate each row. Returns (rows, errors)."""
    text_content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text_content))
    rows: list[dict] = []
    errors: list[str] = []

    for line_num, raw_row in enumerate(reader, start=2):
        supplier_code = (raw_row.get("supplier_code") or "").strip()
        name = (raw_row.get("name") or "").strip()
        supplier_type_raw = (raw_row.get("supplier_type") or "").strip()
        is_active_raw = (raw_row.get("is_active") or "").strip().lower()

        # Insert mode requires name
        if not supplier_code and not name:
            errors.append(f"L{line_num}: name is required for new records")
            continue

        # Validate supplier_type if provided
        if supplier_type_raw and supplier_type_raw not in _VALID_SUPPLIER_TYPES:
            errors.append(
                f"L{line_num}: invalid supplier_type '{supplier_type_raw}' "
                f"(must be 'corporate' or 'individual')"
            )
            continue

        # Validate is_active if provided
        if is_active_raw and is_active_raw not in (_BOOL_TRUE | _BOOL_FALSE):
            errors.append(
                f"L{line_num}: invalid is_active '{is_active_raw}' "
                f"(must be true/false/1/0)"
            )
            continue

        is_active: bool | None = None
        if is_active_raw in _BOOL_TRUE:
            is_active = True
        elif is_active_raw in _BOOL_FALSE:
            is_active = False

        rows.append({
            "supplier_code": supplier_code or None,
            "name": name or None,
            "supplier_type": supplier_type_raw or None,
            "line_name": (raw_row.get("line_name") or "").strip() or None,
            "contact_name": (raw_row.get("contact_name") or "").strip() or None,
            "email": (raw_row.get("email") or "").strip() or None,
            "phone": (raw_row.get("phone") or "").strip() or None,
            "postal_code": (raw_row.get("postal_code") or "").strip() or None,
            "prefecture": (raw_row.get("prefecture") or "").strip() or None,
            "city": (raw_row.get("city") or "").strip() or None,
            "address1": (raw_row.get("address1") or "").strip() or None,
            "address2": (raw_row.get("address2") or "").strip() or None,
            "notes": (raw_row.get("notes") or "").strip() or None,
            "is_active": is_active,
            "_line": line_num,
        })

    return rows, errors


@router.get(
    "/super-admin/suppliers/export",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理仕入元マスタ CSVエクスポート",
)
async def export_suppliers_csv(db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(
        text(
            "SELECT supplier_code, name, supplier_type, line_name, contact_name, "
            "email, phone, postal_code, prefecture, city, address1, address2, "
            "notes, is_active "
            "FROM public.suppliers "
            "WHERE tenant_id IS NULL AND is_active = TRUE "
            "ORDER BY id"
        )
    )
    rows = result.mappings().all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(list(_CSV_EXPORT_COLS))
    for r in rows:
        writer.writerow([
            r["supplier_code"] or "",
            r["name"] or "",
            r["supplier_type"] or "",
            r["line_name"] or "",
            r["contact_name"] or "",
            r["email"] or "",
            r["phone"] or "",
            r["postal_code"] or "",
            r["prefecture"] or "",
            r["city"] or "",
            r["address1"] or "",
            r["address2"] or "",
            r["notes"] or "",
            str(r["is_active"]).lower() if r["is_active"] is not None else "true",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=suppliers.csv"},
    )


@router.post(
    "/super-admin/suppliers/import/preview",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理仕入元マスタ CSVインポート プレビュー",
)
async def import_suppliers_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate CSV and return preview. Does NOT write to DB."""
    raw = await _read_upload(file)
    rows, errors = _parse_and_validate(raw)
    digest = _compute_digest(raw)

    inserts = 0
    updates = 0
    for row in rows:
        if row["supplier_code"]:
            # Check if exists in DB (update mode)
            result = await db.execute(
                text(
                    "SELECT 1 FROM public.suppliers "
                    "WHERE supplier_code = :code AND tenant_id IS NULL"
                ),
                {"code": row["supplier_code"]},
            )
            if result.fetchone():
                updates += 1
            else:
                inserts += 1
        else:
            inserts += 1

    preview_rows = [
        {k: v for k, v in r.items() if not k.startswith("_")}
        for r in rows
    ]

    return {
        "digest": digest,
        "total": len(rows),
        "inserts": inserts,
        "updates": updates,
        "errors": errors,
        "preview_rows": preview_rows,
    }


@router.post(
    "/super-admin/suppliers/import/commit",
    dependencies=[Depends(require_super_admin)],
    summary="中央管理仕入元マスタ CSVインポート 確定",
)
async def import_suppliers_commit(
    file: UploadFile = File(...),
    digest: str = Form(..., description="Preview で受け取った SHA-256 digest"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-validate CSV, verify digest, then write to DB in a transaction."""
    raw = await _read_upload(file)

    # Verify digest matches
    actual_digest = _compute_digest(raw)
    if actual_digest != digest:
        raise HTTPException(
            status_code=409,
            detail="SUPPLIER_IMPORT_DIGEST_MISMATCH",
        )

    rows, errors = _parse_and_validate(raw)
    if errors:
        return {"inserted": 0, "updated": 0, "errors": errors}

    inserted = 0
    updated = 0
    try:
        for row in rows:
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            if data["supplier_code"]:
                # Check if exists (update mode)
                exists_result = await db.execute(
                    text(
                        "SELECT id FROM public.suppliers "
                        "WHERE supplier_code = :code AND tenant_id IS NULL"
                    ),
                    {"code": data["supplier_code"]},
                )
                existing = exists_result.fetchone()
                if existing:
                    # Build UPDATE with only provided (non-None) fields
                    updatable = {
                        k: v for k, v in data.items()
                        if k != "supplier_code" and v is not None
                    }
                    if updatable:
                        set_clauses = ", ".join(f"{k} = :{k}" for k in updatable)
                        updatable["id"] = existing[0]
                        await db.execute(
                            text(
                                f"UPDATE public.suppliers SET {set_clauses}, updated_at = NOW() "
                                f"WHERE id = :id AND tenant_id IS NULL"
                            ),
                            updatable,
                        )
                    updated += 1
                    continue

            # Insert mode (supplier_code absent or not found)
            insert_data: dict = {
                "name": data["name"],
                "supplier_type": data["supplier_type"] or "corporate",
                "line_name": data["line_name"],
                "contact_name": data["contact_name"],
                "email": data["email"],
                "phone": data["phone"],
                "postal_code": data["postal_code"],
                "prefecture": data["prefecture"],
                "city": data["city"],
                "address1": data["address1"],
                "address2": data["address2"],
                "notes": data["notes"],
                "is_active": data["is_active"] if data["is_active"] is not None else True,
            }
            ins_result = await db.execute(
                text(
                    "INSERT INTO public.suppliers "
                    "(name, supplier_type, line_name, contact_name, email, phone, "
                    " postal_code, prefecture, city, address1, address2, notes, "
                    " is_active, tenant_id) "
                    "VALUES (:name, :supplier_type, :line_name, :contact_name, :email, :phone, "
                    "        :postal_code, :prefecture, :city, :address1, :address2, :notes, "
                    "        :is_active, NULL) "
                    "ON CONFLICT (line_name) "
                    "    WHERE line_name IS NOT NULL AND is_active = TRUE AND tenant_id IS NULL "
                    "DO UPDATE SET line_name = EXCLUDED.line_name "
                    "RETURNING id"
                ),
                insert_data,
            )
            new_id = ins_result.fetchone()[0]
            # Auto-generate supplier_code as SP-{id:05d}
            await db.execute(
                text(
                    "UPDATE public.suppliers SET supplier_code = :code "
                    "WHERE id = :id AND supplier_code IS NULL"
                ),
                {"code": f"SP-{new_id:05d}", "id": new_id},
            )
            inserted += 1

        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"SUPPLIER_IMPORT_COMMIT_ERROR: {exc}",
        ) from exc

    return {"inserted": inserted, "updated": updated, "errors": []}


# ----------------------------------------------------------------------------
# supplier_discord_routing
# ----------------------------------------------------------------------------


@router.get(
    "/super-admin/suppliers/{supplier_id}/discord-routing",
    response_model=list[SupplierDiscordRoutingResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_routing(supplier_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text(
            f"SELECT {_ROUTING_COLS} FROM public.supplier_discord_routing "
            f"WHERE supplier_id = :sid ORDER BY id"
        ),
        {"sid": supplier_id},
    )
    return [SupplierDiscordRoutingResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/suppliers/{supplier_id}/discord-routing",
    response_model=SupplierDiscordRoutingResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_routing(
    supplier_id: int,
    data: SupplierDiscordRoutingCreate,
    db: AsyncSession = Depends(get_db),
):
    if data.supplier_id != supplier_id:
        raise HTTPException(
            status_code=400,
            detail="URL の supplier_id と body の supplier_id が一致しません",
        )
    try:
        result = await db.execute(
            text(
                f"INSERT INTO public.supplier_discord_routing "
                f"(supplier_id, discord_guild_id, discord_channel_id, is_active) "
                f"VALUES (:supplier_id, :discord_guild_id, :discord_channel_id, :is_active) "
                f"RETURNING {_ROUTING_COLS}"
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
    return SupplierDiscordRoutingResponse(**dict(row))


@router.delete(
    "/super-admin/suppliers/discord-routing/{routing_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_routing(routing_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("DELETE FROM public.supplier_discord_routing WHERE id = :id"),
        {"id": routing_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="routing が見つかりません")
    await db.commit()


# ============================================================================
# ADR-085: 仕入先別 Gemini プロンプト (public.supplier_prompts)
#   GET  /super-admin/suppliers/{id}/prompt  未登録なら空プロンプトを返す
#   PUT  /super-admin/suppliers/{id}/prompt  upsert (UNIQUE(supplier_id))
# ============================================================================
@router.get(
    "/super-admin/suppliers/{supplier_id}/prompt",
    response_model=SupplierPromptResponse,
    dependencies=[Depends(require_super_admin)],
)
async def get_supplier_prompt(
    supplier_id: int, db: AsyncSession = Depends(get_db)
):
    row = (
        await db.execute(
            text(
                "SELECT supplier_id, prompt, is_active "
                "FROM public.supplier_prompts WHERE supplier_id = :sid"
            ),
            {"sid": supplier_id},
        )
    ).mappings().first()
    if not row:
        # 未登録の仕入先は空プロンプトを返す（編集開始用）
        return SupplierPromptResponse(
            supplier_id=supplier_id, prompt="", is_active=True
        )
    return SupplierPromptResponse(**dict(row))


@router.put(
    "/super-admin/suppliers/{supplier_id}/prompt",
    response_model=SupplierPromptResponse,
    dependencies=[Depends(require_super_admin)],
)
async def upsert_supplier_prompt(
    supplier_id: int,
    data: SupplierPromptUpdate,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        row = (
            await db.execute(
                text(
                    "INSERT INTO public.supplier_prompts "
                    "(supplier_id, prompt, is_active, updated_by) "
                    "VALUES (:sid, :prompt, :active, :uid) "
                    "ON CONFLICT (supplier_id) DO UPDATE SET "
                    "prompt = EXCLUDED.prompt, is_active = EXCLUDED.is_active, "
                    "updated_by = EXCLUDED.updated_by, updated_at = NOW() "
                    "RETURNING supplier_id, prompt, is_active"
                ),
                {
                    "sid": supplier_id,
                    "prompt": data.prompt,
                    "active": data.is_active,
                    "uid": user.id,
                },
            )
        ).mappings().first()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"仕入先が存在しません: {exc.orig}",
        )
    await db.commit()
    return SupplierPromptResponse(**dict(row))


# ============================================================================
# ADR SA-06: 解析精度サマリー (v_supplier_parse_stats)
#   GET /super-admin/suppliers/{id}/parse-stats
# ============================================================================


class SupplierParseStatRow(BaseModel):
    """v_supplier_parse_stats の 1 行（フロントエンド表示用）。"""

    supplier_id: int
    supplier_name: str | None
    day: str  # ISO date string (YYYY-MM-DD)
    total_lines: int
    parsed_count: int
    excluded_count: int
    unparsed_count: int
    exclude_rate_pct: float | None
    avg_confidence: float | None


@router.get(
    "/super-admin/suppliers/{supplier_id}/parse-stats",
    response_model=list[SupplierParseStatRow],
    dependencies=[Depends(require_super_admin)],
)
async def get_supplier_parse_stats(
    supplier_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """仕入元の解析精度サマリーを v_supplier_parse_stats から取得する。

    Args:
        supplier_id: 対象の仕入元 ID
        days: 過去 N 日分を返す（最大 365）
    """
    result = await db.execute(
        text(
            """
            SELECT
                supplier_id,
                supplier_name,
                day::date AS day,
                total_lines,
                parsed_count,
                excluded_count,
                unparsed_count,
                exclude_rate_pct,
                avg_confidence
            FROM public.v_supplier_parse_stats
            WHERE supplier_id = :supplier_id
              AND day >= NOW() - INTERVAL '1 day' * :days
            ORDER BY day DESC
            """
        ),
        {"supplier_id": supplier_id, "days": days},
    )
    rows = result.mappings().all()
    return [
        SupplierParseStatRow(
            supplier_id=row["supplier_id"],
            supplier_name=row["supplier_name"],
            day=str(row["day"]),
            total_lines=int(row["total_lines"] or 0),
            parsed_count=int(row["parsed_count"] or 0),
            excluded_count=int(row["excluded_count"] or 0),
            unparsed_count=int(row["unparsed_count"] or 0),
            exclude_rate_pct=float(row["exclude_rate_pct"]) if row["exclude_rate_pct"] is not None else None,
            avg_confidence=float(row["avg_confidence"]) if row["avg_confidence"] is not None else None,
        )
        for row in rows
    ]


# ============================================================================
# 仕入元抽出ルール (public.suppliers.extraction_* 列)
#   GET  /super-admin/suppliers/extraction-overview  — 全仕入元 + unit_ng数 + ルール有無
#   GET  /super-admin/suppliers/{id}/extraction-rules — ルール取得 + 最新原文
#   PATCH /super-admin/suppliers/{id}/extraction-rules — ルール更新
# ============================================================================

_EXTRACTION_RULE_COLS = (
    "extraction_price_format, extraction_qty_format, extraction_order_pattern, "
    "extraction_default_unit, extraction_notes, extraction_state_format"
)

_EXTRACTION_RULE_UPDATABLE = {
    "extraction_price_format",
    "extraction_qty_format",
    "extraction_order_pattern",
    "extraction_default_unit",
    "extraction_notes",
    "extraction_state_format",
}


@router.get(
    "/super-admin/suppliers/extraction-overview",
    response_model=list[SupplierExtractionOverviewItem],
    dependencies=[Depends(require_super_admin)],
    summary="全仕入元の抽出ルール有無 + unit_ng件数一覧",
)
async def list_supplier_extraction_overview(
    db: AsyncSession = Depends(get_db),
) -> list[SupplierExtractionOverviewItem]:
    """全仕入元（tenant_id IS NULL）の抽出ルール設定有無と unit_ng 件数を返す。"""
    result = await db.execute(
        text(
            """
            SELECT
                s.id AS supplier_id,
                s.supplier_code,
                s.name,
                (
                    s.extraction_price_format IS NOT NULL
                    OR s.extraction_qty_format IS NOT NULL
                    OR s.extraction_order_pattern IS NOT NULL
                    OR s.extraction_default_unit IS NOT NULL
                    OR s.extraction_notes IS NOT NULL
                    OR s.extraction_state_format IS NOT NULL
                ) AS has_extraction_rules,
                COALESCE(ng.unit_ng_count, 0) AS unit_ng_count
            FROM public.suppliers s
            LEFT JOIN LATERAL (
                SELECT COUNT(ar.id) AS unit_ng_count
                FROM public.supplier_channels sc
                JOIN public.source_messages sm ON sm.supplier_channel_id = sc.id AND sm.is_active = TRUE
                JOIN public.extraction_jobs ej ON ej.source_message_id = sm.id
                JOIN public.extraction_items ei ON ei.extraction_job_id = ej.id
                JOIN public.analysis_results ar ON ar.extraction_item_id = ei.id
                WHERE sc.supplier_id = s.id
                  AND ar.unit_resolved = FALSE
            ) ng ON TRUE
            WHERE s.tenant_id IS NULL AND s.is_active = TRUE
            ORDER BY ng.unit_ng_count DESC, s.name ASC
            """
        )
    )
    return [
        SupplierExtractionOverviewItem(
            supplier_id=row["supplier_id"],
            supplier_code=row["supplier_code"],
            name=row["name"],
            has_extraction_rules=bool(row["has_extraction_rules"]),
            unit_ng_count=int(row["unit_ng_count"] or 0),
        )
        for row in result.mappings().all()
    ]


@router.get(
    "/super-admin/suppliers/{supplier_id}/extraction-rules",
    response_model=SupplierExtractionRulesResponse,
    dependencies=[Depends(require_super_admin)],
    summary="仕入元の抽出ルール取得（最新原文付き）",
)
async def get_supplier_extraction_rules(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
) -> SupplierExtractionRulesResponse:
    """仕入元の抽出ルール列 + 最新 source_messages.raw_text を返す。"""
    row = (
        await db.execute(
            text(
                f"SELECT id, {_EXTRACTION_RULE_COLS} "
                "FROM public.suppliers WHERE id = :id AND tenant_id IS NULL"
            ),
            {"id": supplier_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="仕入元が見つかりません")

    # 最新原文を取得
    raw_row = (
        await db.execute(
            text(
                """
                SELECT sm.raw_text
                FROM public.source_messages sm
                JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
                WHERE sc.supplier_id = :sid AND sm.is_active = TRUE
                ORDER BY sm.received_at DESC NULLS LAST
                LIMIT 1
                """
            ),
            {"sid": supplier_id},
        )
    ).mappings().first()

    return SupplierExtractionRulesResponse(
        supplier_id=supplier_id,
        extraction_price_format=row["extraction_price_format"],
        extraction_qty_format=row["extraction_qty_format"],
        extraction_order_pattern=row["extraction_order_pattern"],
        extraction_default_unit=row["extraction_default_unit"],
        extraction_notes=row["extraction_notes"],
        extraction_state_format=row["extraction_state_format"],
        latest_raw_text=raw_row["raw_text"] if raw_row else None,
    )


@router.patch(
    "/super-admin/suppliers/{supplier_id}/extraction-rules",
    response_model=SupplierExtractionRulesResponse,
    dependencies=[Depends(require_super_admin)],
    summary="仕入元の抽出ルール更新",
)
async def update_supplier_extraction_rules(
    supplier_id: int,
    data: SupplierExtractionRulesUpdate,
    db: AsyncSession = Depends(get_db),
) -> SupplierExtractionRulesResponse:
    """仕入元の extraction_* 列を更新する。未指定フィールドは変更しない。"""
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _EXTRACTION_RULE_UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")

    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = supplier_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.suppliers SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id IS NULL "
                f"RETURNING id, {_EXTRACTION_RULE_COLS}"
            ),
            update_data,
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新エラー: {exc}") from exc

    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="仕入元が見つかりません")
    await db.commit()

    return SupplierExtractionRulesResponse(
        supplier_id=row["id"],
        extraction_price_format=row["extraction_price_format"],
        extraction_qty_format=row["extraction_qty_format"],
        extraction_order_pattern=row["extraction_order_pattern"],
        extraction_default_unit=row["extraction_default_unit"],
        extraction_notes=row["extraction_notes"],
        extraction_state_format=row["extraction_state_format"],
        latest_raw_text=None,  # PATCH 応答では原文は含まない
    )


# ============================================================================
# 仕入元チャンネル原文メッセージ一覧
#   GET /super-admin/suppliers/{id}/source-messages
# ============================================================================


@router.get(
    "/super-admin/suppliers/{supplier_id}/source-messages",
    response_model=SupplierSourceMessagesResponse,
    dependencies=[Depends(require_super_admin)],
    summary="仕入元の原文メッセージ一覧取得",
)
async def list_supplier_source_messages(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
) -> SupplierSourceMessagesResponse:
    """仕入元チャンネルに紐付く source_messages を新着順で返す。"""
    result = await db.execute(
        text(
            """
            SELECT sm.id, sm.raw_text, sm.created_at
            FROM public.source_messages sm
            JOIN public.supplier_channels sc ON sm.supplier_channel_id = sc.id
            WHERE sc.supplier_id = :supplier_id AND sm.is_active = true
            ORDER BY sm.created_at DESC
            """
        ),
        {"supplier_id": supplier_id},
    )
    rows = result.mappings().all()
    messages = [
        {"id": row["id"], "raw_text": row["raw_text"], "created_at": str(row["created_at"])}
        for row in rows
    ]
    return SupplierSourceMessagesResponse(messages=messages, total=len(messages))
