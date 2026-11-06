"""会社のオーナーが、同じ会社の社員のログインの許可待ちを許可する（ADR-1063）。

社員が新しい機械で「会社の管理者に頼む」を押した依頼だけが並ぶ。オーナー（system_key=owner）だけが使える。
表 auth_login_requests には RLS が無いので、SQL には必ず会社の絞り込み（u.tenant_id）を入れる（devices の部品が入れる）。
許可の部品は super admin の許可（ADR-1055 K7）と同じ devices.approve_request_as_admin。
本人確認の方法（note）は記録に書かない。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import devices
from app.auth.dependencies import get_current_tenant, require_tenant_owner, reset_tenant_context
from app.auth.origin import require_app_origin
from app.database import get_db
from app.models import User
from app.realtime.publisher import publish_user_change
from app.realtime.topics import TOPIC_AUTH_LOGIN_REQUEST
from app.routers.auth import _record_auth_audit
from app.routers.super_admin_login_requests import (
    AdminApproveBody,
    AdminApproveResult,
    AdminLoginRequestItem,
    _iso,
)

router = APIRouter()


class TenantLoginRequestItem(AdminLoginRequestItem):
    admin_requested_at: str | None = Field(default=None, description="会社の管理者に頼んだ日時")


class TenantLoginRequestList(BaseModel):
    items: list[TenantLoginRequestItem]


@router.get("/tenant/login-requests", response_model=TenantLoginRequestList)
async def list_tenant_login_requests(
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_tenant_owner),
    db: AsyncSession = Depends(get_db),
):
    """同じ会社の人が「会社の管理者に頼む」を押した、待っている依頼。自分の依頼は出さない。"""
    rows = await devices.list_admin_requested(db, tenant_id=tenant_id, exclude_user_id=current_user.id)
    return TenantLoginRequestList(
        items=[
            TenantLoginRequestItem(
                id=str(r.id),
                user_id=r.user_id,
                email=r.email,
                full_name=r.full_name,
                status=r.status,
                label=r.label,
                location=r.location,
                created_at=_iso(r.created_at),
                expires_at=_iso(r.expires_at),
                admin_requested_at=_iso(r.admin_requested_at),
            )
            for r in rows
        ]
    )


@router.post("/tenant/login-requests/{request_id}/approve", response_model=AdminApproveResult)
async def approve_tenant_login_request(
    request_id: str,
    body: AdminApproveBody,
    request: Request,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_tenant_owner),
    db: AsyncSession = Depends(get_db),
):
    """オーナーが許可する。別の会社の依頼・頼んでいない依頼は 404、自分の依頼は 403。待つ機械は poll で入る。"""
    require_app_origin(request)
    rid = devices.parse_request_id(request_id)
    if rid is None:
        raise HTTPException(status_code=404, detail="not_found")
    decision = await devices.approve_request_as_admin(
        db,
        request_id=rid,
        approver_user_id=current_user.id,
        note=body.note.strip(),
        tenant_id=tenant_id,
        require_admin_requested=True,
    )
    if decision.outcome == "own_request":
        raise HTTPException(status_code=403, detail="cannot_approve_own_request")
    if decision.outcome != "approved":
        raise HTTPException(status_code=404, detail="not_found")
    # 依頼の id は UUID で整数の列に入らないので record_id は None、note の中身は書かない
    await _record_auth_audit(
        db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="update",
        table_name="auth_login_requests",
        record_id=None,
        new_data={
            "event": "login_request_approved_owner",
            "request_id": rid,
            "target_user_id": decision.target_user_id,
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    await publish_user_change(decision.target_user_id, TOPIC_AUTH_LOGIN_REQUEST)
    return AdminApproveResult(status="approved")
