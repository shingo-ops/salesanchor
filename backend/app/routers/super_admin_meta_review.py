"""Meta 審査用の会社だけのログインのスイッチの管理の口（ADR-1055 What 11）。

Meta の審査員が登録していない機械から入るための、印の付いた1社だけの例外。ほかの会社に広げない。
動かせるのは super admin だけ。書くのは meta_review_login_until だけで、印（meta_review_tenant）を書く道は作らない。
会社の表は運営の文脈のときだけ書ける（set_operator_context）。書き込みの道はこの口1本にして、監査記録を必ず残す。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import devices, meta_review
from app.auth.dependencies import require_super_admin, reset_operator_context, set_operator_context
from app.auth.origin import require_app_origin
from app.cache import mark_family_revoked
from app.database import get_db
from app.models import User
from app.routers.auth import _record_auth_audit

router = APIRouter()


class MetaReviewStatus(BaseModel):
    tenant_name: str | None = Field(default=None, description="印の付いた会社の名前（無ければ null）")
    is_on: bool = Field(description="今スイッチが ON か")
    until: str | None = Field(default=None, description="スイッチの期限（過ぎていてもそのまま。手で OFF のときは null）")


class MetaReviewSwitchBody(BaseModel):
    on: bool = Field(description="true で ON（今から14日）、false で OFF")


class MetaReviewLoginItem(BaseModel):
    created_at: str | None = Field(default=None, description="ログインを試みた日時")
    email: str | None = Field(default=None, description="試みたアカウントのメールアドレス")
    path: str = Field(description="口の道")
    status_code: int = Field(description="結果の番号（200 成功・202 許可待ち・それ以外は失敗）")
    reason: str | None = Field(default=None, description="理由")
    device: str = Field(description="機械の種類")


class MetaReviewLoginList(BaseModel):
    items: list[MetaReviewLoginItem]


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


@router.get("/super-admin/meta-review", response_model=MetaReviewStatus)
async def get_meta_review(
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """スイッチの今の状態。until は保存された値をそのまま返す（過ぎていても NULL に直さない）。"""
    row = (
        await db.execute(
            text(
                "SELECT tenant_name, meta_review_login_until FROM public.tenants "
                "WHERE meta_review_tenant"
            )
        )
    ).first()
    if row is None:
        return MetaReviewStatus(tenant_name=None, is_on=False, until=None)
    return MetaReviewStatus(
        tenant_name=row.tenant_name,
        is_on=meta_review.is_meta_review_on(row.meta_review_login_until),
        until=_iso(row.meta_review_login_until),
    )


@router.put("/super-admin/meta-review", response_model=MetaReviewStatus)
async def put_meta_review(
    body: MetaReviewSwitchBody,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """スイッチを ON（今から14日）または OFF にする。印の会社が無ければ 409。"""
    require_app_origin(request)
    until: datetime | None = devices._now() + timedelta(days=meta_review.META_REVIEW_MAX_DAYS) if body.on else None
    await set_operator_context(db)
    try:
        row = (
            await db.execute(
                text(
                    "UPDATE public.tenants SET meta_review_login_until = :until "
                    "WHERE meta_review_tenant RETURNING id, tenant_name"
                ),
                {"until": until},
            )
        ).first()
        if row is None:
            await db.rollback()
            raise HTTPException(status_code=409, detail="meta_review_tenant_missing")
        revoked: list[str] = []
        if not body.on:
            # 手で OFF にしたら、その会社の人（super admin を除く）の機械の無い組をすぐ失効させる
            rows = (
                await db.execute(
                    text(
                        "UPDATE public.auth_refresh_tokens SET revoked_at = :now "
                        "WHERE revoked_at IS NULL AND trusted_device_id IS NULL AND user_id IN ("
                        "SELECT id FROM public.users WHERE tenant_id = :tid AND NOT is_super_admin"
                        ") RETURNING family_id"
                    ),
                    {"now": devices._now(), "tid": row.id},
                )
            ).fetchall()
            revoked = sorted({str(r[0]) for r in rows})
            for family in revoked:
                await mark_family_revoked(family)
        await _record_auth_audit(
            db,
            tenant_id=row.id,
            user_id=current_user.id,
            action="update",
            table_name="tenants",
            record_id=row.id,
            new_data={
                "event": "meta_review_on" if body.on else "meta_review_off",
                "until": _iso(until),
                "revoked_families": len(revoked),
            },
        )
        await db.commit()
    finally:
        await reset_operator_context(db)
    return MetaReviewStatus(
        tenant_name=row.tenant_name,
        is_on=meta_review.is_meta_review_on(until),
        until=_iso(until),
    )


@router.get("/super-admin/meta-review/logins", response_model=MetaReviewLoginList)
async def list_meta_review_logins(
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """印の会社の人のログイン履歴（新しい順）。人の付かない記録（打ち間違い・回数制限）は出ない。"""
    rows = (
        await db.execute(
            text(
                "SELECT e.created_at, u.email, e.path, e.status_code, e.reason, e.user_agent "
                "FROM public.auth_events e "
                "JOIN public.users u ON u.id = e.user_id "
                "JOIN public.tenants t ON t.id = u.tenant_id "
                "WHERE t.meta_review_tenant "
                "AND ( "
                "e.path IN ('/api/v1/auth/login', '/api/v1/auth/passkey/login/verify') "
                "OR (e.path = '/api/v1/auth/login-requests/poll' AND e.reason IN ('approved_admin', 'approved_device')) "
                "OR e.path = '/api/v1/auth/login-requests/recovery' "
                ") "
                "ORDER BY e.created_at DESC "
                "LIMIT :limit"
            ),
            {"limit": limit},
        )
    ).all()
    return MetaReviewLoginList(
        items=[
            MetaReviewLoginItem(
                created_at=_iso(r.created_at),
                email=r.email,
                path=r.path,
                status_code=r.status_code,
                reason=r.reason,
                device=devices.describe_user_agent(r.user_agent),
            )
            for r in rows
        ]
    )
