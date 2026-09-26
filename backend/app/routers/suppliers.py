from __future__ import annotations

"""
仕入先管理API（CRUD）。

変更履歴:
  2026-04-17: 初版作成（Phase 3）
  2026-09-19: Sprint 2 — テナント用 CSV エクスポート・インポート追加
"""

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
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from app.services.audit import record_audit_log

router = APIRouter()

_COLS = """
    id, supplier_code, name, contact_name, email, phone, address,
    notes, is_active, created_at, updated_at
"""
_UPDATABLE = {"name", "contact_name", "email", "phone", "address", "notes", "is_active"}

# ============================================================================
# ADR-155: テナント用仕入元マスタ CSV エクスポート・インポート (Sprint 2)
# NOTE: CSV constants and helpers must be declared before any route that uses
#       them. The export route /suppliers/export must also be declared BEFORE
#       /suppliers/{supplier_id} to avoid the literal "export" being matched
#       as a path parameter (FastAPI routes are evaluated in registration order).
# ============================================================================

_CSV_EXPORT_COLS = (
    "supplier_code", "name", "supplier_type", "line_name", "contact_name",
    "email", "phone", "postal_code", "prefecture", "city", "address1",
    "address2", "notes", "is_active",
)

_VALID_SUPPLIER_TYPES = {"corporate", "individual"}
_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}

_MAX_CSV_BYTES = 2 * 1024 * 1024


def _tenant_compute_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


async def _tenant_read_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="SUPPLIER_IMPORT_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="SUPPLIER_IMPORT_EMPTY_FILE")
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="SUPPLIER_IMPORT_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="SUPPLIER_IMPORT_NOT_UTF8") from exc
    return raw


def _tenant_parse_and_validate(raw: bytes) -> tuple[list[dict], list[str]]:
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


@router.get("/suppliers", response_model=list[SupplierResponse],
            dependencies=[Depends(require_permission("suppliers.view"))])
async def list_suppliers(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": per_page, "offset": offset}
    if active_only:
        conditions.append("is_active = TRUE")
    if search:
        conditions.append("(name ILIKE :search OR contact_name ILIKE :search OR supplier_code ILIKE :search)")
        params["search"] = f"%{search}%"
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(f"SELECT {_COLS} FROM suppliers {where} ORDER BY name LIMIT :limit OFFSET :offset"), params)
    return [SupplierResponse(**row) for row in result.mappings().all()]


@router.get("/suppliers/catalog", response_model=list[SupplierResponse],
            dependencies=[Depends(require_permission("purchase_orders.view"))])
async def list_supplier_catalog(
    search: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """発注用の仕入元プルダウン: 中央カタログ public.suppliers を返す（全テナント共有）。

    在庫表（public.suppliers 由来）とソースを統一する。返す id は public.suppliers.id。
    発注作成 (POST /purchase-orders) 側で tenant.suppliers へ複製して FK を満たす。
    """
    conditions = ["is_active = TRUE"]
    params: dict = {}
    if search:
        conditions.append("(name ILIKE :search OR supplier_code ILIKE :search)")
        params["search"] = f"%{search}%"
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(f"SELECT {_COLS} FROM public.suppliers {where} ORDER BY name"),
        params,
    )
    return [SupplierResponse(**row) for row in result.mappings().all()]


# NOTE: /suppliers/export must come BEFORE /suppliers/{supplier_id} to prevent
# FastAPI from matching the literal string "export" as the supplier_id parameter.
@router.get(
    "/suppliers/export",
    dependencies=[Depends(require_permission("suppliers.view"))],
    summary="テナント用仕入元マスタ CSVエクスポート",
)
async def export_tenant_suppliers_csv(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export active suppliers for current tenant as CSV."""
    result = await db.execute(
        text(
            "SELECT supplier_code, name, supplier_type, line_name, contact_name, "
            "       email, phone, postal_code, prefecture, city, address1, address2, "
            "       notes, is_active "
            "FROM suppliers "
            "WHERE tenant_id = :tenant_id AND is_active = TRUE "
            "ORDER BY name"
        ),
        {"tenant_id": tenant_id},
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


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse,
            dependencies=[Depends(require_permission("suppliers.view"))])
async def get_supplier(supplier_id: int, db: AsyncSession = Depends(get_db),
                       tenant_id: int = Depends(get_current_tenant),
                       current_user: User = Depends(get_current_user)):
    result = await db.execute(
        text(f"SELECT {_COLS} FROM suppliers WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": supplier_id, "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="仕入先が見つかりません")
    return SupplierResponse(**row)


@router.post("/suppliers", response_model=SupplierResponse, status_code=201,
             dependencies=[Depends(require_permission("suppliers.create"))])
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db),
                          tenant_id: int = Depends(get_current_tenant),
                          current_user: User = Depends(get_current_user)):
    result = await db.execute(
        text("""
            INSERT INTO suppliers (tenant_id, name, contact_name, email, phone, address, notes)
            VALUES (:tid, :name, :contact, :email, :phone, :addr, :notes)
            RETURNING id
        """),
        {"tid": tenant_id, "name": data.name, "contact": data.contact_name,
         "email": data.email, "phone": data.phone, "addr": data.address, "notes": data.notes},
    )
    new_id = result.scalar_one()
    await db.execute(text("UPDATE suppliers SET supplier_code = :code WHERE id = :id"),
                     {"code": f"SP-{new_id:05d}", "id": new_id})
    fetched = await db.execute(text(f"SELECT {_COLS} FROM suppliers WHERE id = :id"), {"id": new_id})
    row = fetched.mappings().first()
    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="create", table_name="suppliers", record_id=new_id,
                           new_data=data.model_dump(exclude_none=True))
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2
    return SupplierResponse(**row)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse,
              dependencies=[Depends(require_permission("suppliers.update"))])
async def update_supplier(supplier_id: int, data: SupplierUpdate,
                          db: AsyncSession = Depends(get_db),
                          tenant_id: int = Depends(get_current_tenant),
                          current_user: User = Depends(get_current_user)):
    old = await db.execute(
        text(f"SELECT {_COLS} FROM suppliers WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": supplier_id, "tenant_id": tenant_id},
    )
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="仕入先が見つかりません")
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = supplier_id
    update_data["tenant_id"] = tenant_id
    result = await db.execute(
        text(f"UPDATE suppliers SET {set_clauses}, updated_at = NOW() WHERE id = :id AND tenant_id = :tenant_id RETURNING {_COLS}"),
        update_data)
    row = result.mappings().first()
    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="update", table_name="suppliers", record_id=supplier_id,
                           old_data=dict(old_row), new_data=update_data)
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2
    return SupplierResponse(**dict(row))


@router.delete("/suppliers/{supplier_id}", status_code=204,
               dependencies=[Depends(require_permission("suppliers.delete"))])
async def delete_supplier(supplier_id: int, db: AsyncSession = Depends(get_db),
                          tenant_id: int = Depends(get_current_tenant),
                          current_user: User = Depends(get_current_user)):
    old = await db.execute(
        text(f"SELECT {_COLS} FROM suppliers WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": supplier_id, "tenant_id": tenant_id},
    )
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="仕入先が見つかりません")
    await db.execute(
        text("UPDATE suppliers SET is_active = FALSE, updated_at = NOW() WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": supplier_id, "tenant_id": tenant_id},
    )
    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="soft_delete", table_name="suppliers", record_id=supplier_id,
                           old_data=dict(old_row))
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2


@router.post(
    "/suppliers/import/preview",
    dependencies=[Depends(require_permission("suppliers.create"))],
    summary="テナント用仕入元マスタ CSVインポート プレビュー",
)
async def import_tenant_suppliers_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Validate CSV and return preview. Does NOT write to DB."""
    raw = await _tenant_read_upload(file)
    rows, errors = _tenant_parse_and_validate(raw)
    digest = _tenant_compute_digest(raw)

    inserts = 0
    updates = 0
    for row in rows:
        if row["supplier_code"]:
            # Check if exists in DB for this tenant (update mode)
            result = await db.execute(
                text(
                    "SELECT 1 FROM suppliers "
                    "WHERE supplier_code = :code AND tenant_id = :tenant_id"
                ),
                {"code": row["supplier_code"], "tenant_id": tenant_id},
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
    "/suppliers/import/commit",
    dependencies=[Depends(require_permission("suppliers.create"))],
    summary="テナント用仕入元マスタ CSVインポート 確定",
)
async def import_tenant_suppliers_commit(
    file: UploadFile = File(...),
    digest: str = Form(..., description="Preview で受け取った SHA-256 digest"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Re-validate CSV, verify digest, then write to DB in a transaction."""
    raw = await _tenant_read_upload(file)

    # Verify digest matches
    actual_digest = _tenant_compute_digest(raw)
    if actual_digest != digest:
        raise HTTPException(
            status_code=409,
            detail="SUPPLIER_IMPORT_DIGEST_MISMATCH",
        )

    rows, errors = _tenant_parse_and_validate(raw)
    if errors:
        return {"inserted": 0, "updated": 0, "errors": errors}

    inserted = 0
    updated = 0
    try:
        for row in rows:
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            if data["supplier_code"]:
                # Check if exists for this tenant (update mode)
                exists_result = await db.execute(
                    text(
                        "SELECT id FROM suppliers "
                        "WHERE supplier_code = :code AND tenant_id = :tenant_id"
                    ),
                    {"code": data["supplier_code"], "tenant_id": tenant_id},
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
                        updatable["tenant_id"] = tenant_id
                        await db.execute(
                            text(
                                f"UPDATE suppliers SET {set_clauses}, updated_at = NOW() "
                                f"WHERE id = :id AND tenant_id = :tenant_id"
                            ),
                            updatable,
                        )
                    updated += 1
                    continue

            # Insert mode (supplier_code absent or not found for this tenant)
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
                "tenant_id": tenant_id,
            }
            ins_result = await db.execute(
                text(
                    "INSERT INTO suppliers "
                    "(name, supplier_type, line_name, contact_name, email, phone, "
                    " postal_code, prefecture, city, address1, address2, notes, "
                    " is_active, tenant_id) "
                    "VALUES (:name, :supplier_type, :line_name, :contact_name, :email, :phone, "
                    "        :postal_code, :prefecture, :city, :address1, :address2, :notes, "
                    "        :is_active, :tenant_id) "
                    "RETURNING id"
                ),
                insert_data,
            )
            new_id = ins_result.fetchone()[0]
            # Auto-generate supplier_code as SP-{id:05d}
            await db.execute(
                text(
                    "UPDATE suppliers SET supplier_code = :code "
                    "WHERE id = :id AND supplier_code IS NULL"
                ),
                {"code": f"SP-{new_id:05d}", "id": new_id},
            )
            inserted += 1

        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"SUPPLIER_IMPORT_COMMIT_ERROR: {exc}",
        ) from exc

    return {"inserted": inserted, "updated": updated, "errors": []}
