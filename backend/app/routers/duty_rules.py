"""関税の額の決まりの入口（invoice-create-portfolio 便B・design.md §3-3・§3-6・K18・K20）。

- 見る: tenant.profile.view か tenant.profile.edit。足す・直す・消す: tenant.profile.edit。
- 書いたら同じ取引で、その会社の audit_logs に1行ずつ残す（K20）。
- 失敗の detail は識別子だけの dict にする（test_error_detail_guard.py）。画面が辞書の文に置き換える。
"""
from __future__ import annotations

import json
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    set_tenant_context,
)
from app.database import get_db
from app.models import User
from app.schemas.duty_rules import DUTY_BASES, DutyRuleIn, DutyRuleOptions, DutyRuleRead
from app.services import duty_rules as svc
from app.services.audit import record_audit_log
from app.services.fx_currencies import list_invoice_currencies

router = APIRouter()

_TABLE = "tenant_duty_rules"


def _audit_dict(rule: dict) -> dict:
    return json.loads(DutyRuleRead.model_validate(rule).model_dump_json())


def _raise_for(exc: Exception) -> NoReturn:
    if isinstance(exc, svc.DutyRuleNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "duty_rule_not_found"})
    if isinstance(exc, svc.DutyCountryInvalid):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "duty_country"})
    if isinstance(exc, svc.DutyRuleOverlap):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duty_rule_overlap", "rule_ids": exc.rule_ids},
        )
    raise exc


@router.get(
    "/admin/duty-rules",
    response_model=list[DutyRuleRead],
    summary="関税の額の決まりの一覧",
    dependencies=[Depends(require_permission("tenant.profile.view", "tenant.profile.edit"))],
)
async def list_rules(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await set_tenant_context(db, tenant_id)
    return await svc.list_duty_rules(db, tenant_id)


@router.get(
    "/admin/duty-rules/options",
    response_model=DutyRuleOptions,
    summary="関税の額の画面の選択肢（関税の条件・通貨・基準）",
    dependencies=[Depends(require_permission("tenant.profile.view", "tenant.profile.edit"))],
)
async def get_options(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> DutyRuleOptions:
    await set_tenant_context(db, tenant_id)
    incoterms = await svc.get_duty_incoterms(db, tenant_id)
    if incoterms is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "tenant_settings_missing"})
    currencies = await list_invoice_currencies(db)
    return DutyRuleOptions(duty_incoterms=incoterms, currencies=currencies, bases=list(DUTY_BASES))


@router.post(
    "/admin/duty-rules",
    response_model=DutyRuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="関税の額の決まりを足す",
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def create_rule(
    body: DutyRuleIn,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, tenant_id)
    try:
        created = await svc.create_duty_rule(db, tenant_id, body)
    except (svc.DutyCountryInvalid, svc.DutyRuleOverlap) as exc:
        await db.rollback()
        _raise_for(exc)
    await record_audit_log(
        db, tenant_id, current_user.id, "create", _TABLE,
        record_id=created["id"], new_data=_audit_dict(created),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return created


@router.put(
    "/admin/duty-rules/{rule_id}",
    response_model=DutyRuleRead,
    summary="関税の額の決まりを直す",
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def update_rule(
    rule_id: int,
    body: DutyRuleIn,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, tenant_id)
    try:
        before, after = await svc.update_duty_rule(db, tenant_id, rule_id, body)
    except (svc.DutyRuleNotFound, svc.DutyCountryInvalid, svc.DutyRuleOverlap) as exc:
        await db.rollback()
        _raise_for(exc)
    await record_audit_log(
        db, tenant_id, current_user.id, "update", _TABLE,
        record_id=rule_id, old_data=_audit_dict(before), new_data=_audit_dict(after),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return after


@router.delete(
    "/admin/duty-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="関税の額の決まりを消す",
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    await set_tenant_context(db, tenant_id)
    try:
        before = await svc.delete_duty_rule(db, tenant_id, rule_id)
    except svc.DutyRuleNotFound as exc:
        await db.rollback()
        _raise_for(exc)
    await record_audit_log(
        db, tenant_id, current_user.id, "delete", _TABLE,
        record_id=rule_id, old_data=_audit_dict(before),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
