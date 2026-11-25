"""書類に載せる会社情報（国内用・海外用）の口（ADR-1061 便2-2c2b。design.md §3-4・§3-4b）。

- GET /admin/issuer-profiles: 国内用・海外用の行（無い方は null）と、旧来の会社情報の6欄（読むだけ）。
- PUT /admin/issuer-profiles/{region}: 片方の行を丸ごと保存する。決まり違いは 422 と欄ごとの理由（detail.fields）。
- 旧来の会社情報を読むのは app.services.issuer.read_legacy_issuer_values の1か所だけ（A40）。
- 権限は今の会社情報の口と同じ（tenant.profile.view で読む・tenant.profile.edit で書く）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    tenant_table_ref,
)
from app.database import get_db
from app.models import User
from app.schemas.issuer_profiles import (
    IssuerProfileResponse,
    IssuerProfilesResponse,
    IssuerProfileUpdate,
    IssuerRegion,
    LegacyIssuerValues,
)
from app.services.audit import record_audit_log
from app.services.issuer import read_legacy_issuer_values
from app.services.issuer_rules import check_issuer_codes, check_issuer_fields, normalize_issuer_payload

router = APIRouter()

_COLUMNS = (
    "company_name", "email", "website", "country_code", "postal_code", "prefecture_code",
    "state_region", "city", "address1", "address2", "phone", "is_invoice_registered",
    "registration_number",
)
_SELECT = "SELECT id, region, " + ", ".join(_COLUMNS) + ", updated_at"


async def _read_region(db: AsyncSession, tenant_id: int, region: str) -> dict[str, Any] | None:
    table = tenant_table_ref(db, tenant_id, "tenant_issuer_profiles")
    row = (await db.execute(
        text(f"{_SELECT} FROM {table} WHERE tenant_id = :tenant_id AND region = :region"),
        {"tenant_id": tenant_id, "region": region},
    )).mappings().first()
    return dict(row) if row else None


def _audit_values(row: dict[str, Any] | None) -> dict[str, Any] | None:
    return {key: row[key] for key in _COLUMNS} if row else None


@router.get(
    "/admin/issuer-profiles",
    response_model=IssuerProfilesResponse,
    dependencies=[Depends(require_permission("tenant.profile.view"))],
)
async def get_issuer_profiles(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """国内用・海外用の行と、旧来の会社情報の6欄を返す。"""
    domestic = await _read_region(db, tenant_id, "domestic")
    overseas = await _read_region(db, tenant_id, "overseas")
    legacy = await read_legacy_issuer_values(db, tenant_id)
    return IssuerProfilesResponse(
        domestic=IssuerProfileResponse(**domestic) if domestic else None,
        overseas=IssuerProfileResponse(**overseas) if overseas else None,
        legacy=LegacyIssuerValues(**legacy) if legacy else None,
    )


@router.put(
    "/admin/issuer-profiles/{region}",
    response_model=IssuerProfileResponse,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def put_issuer_profile(
    region: IssuerRegion,
    data: IssuerProfileUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """片方の地域の行を丸ごと保存する（無ければ作る）。"""
    values = normalize_issuer_payload(data.model_dump())
    errors = check_issuer_fields(values)
    for key, code in (await check_issuer_codes(db, values)).items():
        errors.setdefault(key, code)
    if errors:
        raise HTTPException(status_code=422, detail={"fields": errors})

    table = tenant_table_ref(db, tenant_id, "tenant_issuer_profiles")
    before = await _read_region(db, tenant_id, region)
    params = {key: values[key] for key in _COLUMNS}
    params.update({"tenant_id": tenant_id, "region": region, "user_id": current_user.id})
    if before:
        set_sql = ", ".join(f"{key} = :{key}" for key in _COLUMNS)
        result = await db.execute(
            text(
                f"UPDATE {table} SET {set_sql}, updated_by_user_id = :user_id, "
                "updated_at = CURRENT_TIMESTAMP WHERE tenant_id = :tenant_id AND region = :region"
            ),
            params,
        )
        action = "update"
    else:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{key}" for key in _COLUMNS)
        result = await db.execute(
            text(
                f"INSERT INTO {table} (tenant_id, region, {columns}, updated_by_user_id) "
                f"VALUES (:tenant_id, :region, {placeholders}, :user_id)"
            ),
            params,
        )
        action = "create"
    if result.rowcount != 1:
        raise HTTPException(status_code=500, detail="issuer_profile_not_saved")

    after = await _read_region(db, tenant_id, region)
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action=action, table_name="tenant_issuer_profiles",
        record_id=after["id"], old_data=_audit_values(before), new_data=_audit_values(after),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    saved = await _read_region(db, tenant_id, region)
    return IssuerProfileResponse(**saved)
