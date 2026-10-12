"""
中央 admin 用 public.payment_fee_settings CRUD ルーター。

§D01: PO承認2026-10-02
パターン: public + NULLパターン（public.unitsと同一方式）

API:
  GET    /api/v1/super-admin/payment-fee-settings
  POST   /api/v1/super-admin/payment-fee-settings
  PATCH  /api/v1/super-admin/payment-fee-settings/{id}
  DELETE /api/v1/super-admin/payment-fee-settings/{id}

認証: require_super_admin
書き込み対象: tenant_id IS NULL の共用行のみ
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.schemas.payment_fee_setting import (
    PaymentFeeSettingCreate,
    PaymentFeeSettingResponse,
    PaymentFeeSettingUpdate,
)

router = APIRouter()

_COLS = (
    "id, tenant_id, service, fee_type, rate_pct, fixed_amount, threshold, threshold_rule, "
    "currency, effective_from, effective_to, source_url, note, created_at, updated_at"
)

_UPDATABLE = {
    "service",
    "fee_type",
    "rate_pct",
    "fixed_amount",
    "threshold",
    "threshold_rule",
    "currency",
    "effective_from",
    "effective_to",
    "source_url",
    "note",
}


@router.get(
    "/super-admin/payment-fee-settings",
    response_model=list[PaymentFeeSettingResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_payment_fee_settings(
    service: str | None = Query(default=None, max_length=30),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    conditions: list[str] = ["tenant_id IS NULL"]
    params: dict = {"limit": per_page, "offset": offset}
    if service:
        conditions.append("service = :service")
        params["service"] = service
    where = f"WHERE {' AND '.join(conditions)}"
    result = await db.execute(
        text(
            f"SELECT {_COLS} FROM public.payment_fee_settings {where} "
            "ORDER BY service, fee_type, effective_from LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return [PaymentFeeSettingResponse(**dict(row)) for row in result.mappings().all()]


@router.post(
    "/super-admin/payment-fee-settings",
    response_model=PaymentFeeSettingResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_payment_fee_setting(
    data: PaymentFeeSettingCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.payment_fee_settings "
                "(tenant_id, service, fee_type, rate_pct, fixed_amount, threshold, threshold_rule, "
                " currency, effective_from, effective_to, source_url, note) "
                "VALUES (NULL, :service, :fee_type, :rate_pct, :fixed_amount, :threshold, :threshold_rule, "
                "        :currency, :effective_from, :effective_to, :source_url, :note) "
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
    return PaymentFeeSettingResponse(**dict(row))


@router.patch(
    "/super-admin/payment-fee-settings/{setting_id}",
    response_model=PaymentFeeSettingResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_payment_fee_setting(
    setting_id: int,
    data: PaymentFeeSettingUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = setting_id
    try:
        result = await db.execute(
            text(
                f"UPDATE public.payment_fee_settings SET {set_clauses}, updated_at = NOW() "
                f"WHERE id = :id AND tenant_id IS NULL RETURNING {_COLS}"
            ),
            update_data,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"制約違反: {exc.orig}")
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="決済手数料設定が見つかりません")
    await db.commit()
    return PaymentFeeSettingResponse(**dict(row))


@router.delete(
    "/super-admin/payment-fee-settings/{setting_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_payment_fee_setting(
    setting_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text(
            "DELETE FROM public.payment_fee_settings "
            "WHERE id = :id AND tenant_id IS NULL"
        ),
        {"id": setting_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="決済手数料設定が見つかりません")
    await db.commit()
