"""管理者がログインの許可待ちを許可する（ADR-1055 K7）。

いつもの機械も予備の合言葉も無い人のために、super admin が本人確認のうえ許可する。
本人確認の手順: 依頼の機械の種類・場所・時刻を、本人に、登録済みの電話番号か対面で読み上げてもらい、
一致したときだけ許可する。確かめた方法を note に書く（例「対面で確認」「登録の電話で確認」）。
管理者の口は /api/v1/auth/ の外なので、認証の記録（auth_events）には入らない。管理者の操作は
_record_auth_audit（会社別の audit_logs）に残す。note の中身は書かない。
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import devices
from app.auth.dependencies import require_super_admin
from app.auth.origin import require_app_origin
from app.database import get_db
from app.models import User
from app.realtime.publisher import publish_user_change
from app.realtime.topics import TOPIC_AUTH_LOGIN_REQUEST
from app.routers.auth import _record_auth_audit

router = APIRouter()


class AdminLoginRequestItem(BaseModel):
    id: str = Field(description="依頼の ID（UUID）")
    user_id: int = Field(description="依頼した人")
    email: str | None = Field(default=None, description="依頼した人のメールアドレス")
    full_name: str | None = Field(default=None, description="依頼した人の名前")
    status: str = Field(description="依頼の状態")
    label: str | None = Field(default=None, description="待つ機械の種類")
    location: str | None = Field(default=None, description="場所の目安（IP Geolocation by DB-IP）")
    created_at: str | None = Field(default=None, description="依頼した日時")
    expires_at: str | None = Field(default=None, description="期限")


class AdminLoginRequestList(BaseModel):
    items: list[AdminLoginRequestItem]


class AdminApproveBody(BaseModel):
    note: str = Field(min_length=1, max_length=200, description="本人確認の方法（必須・200字まで）")


class AdminApproveResult(BaseModel):
    status: str = Field(default="approved", description="許可した")


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


@router.get("/super-admin/login-requests", response_model=AdminLoginRequestList)
async def list_login_requests(
    status: str = Query(default="pending", pattern="^(pending|approved|rejected|expired|completed)$"),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """ログインの許可待ちの一覧（pending は期限内だけ）。"""
    sql = (
        "SELECT r.id, r.user_id, u.email, u.full_name, r.status, r.label, r.location, "
        "r.created_at, r.expires_at "
        "FROM public.auth_login_requests r JOIN public.users u ON u.id = r.user_id "
        "WHERE r.status = :st"
    )
    params: dict = {"st": status}
    if status == "pending":
        sql += " AND r.expires_at > :now"
        params["now"] = datetime.now(timezone.utc)
    sql += " ORDER BY r.created_at DESC LIMIT 200"
    rows = (await db.execute(text(sql), params)).all()
    return AdminLoginRequestList(
        items=[
            AdminLoginRequestItem(
                id=str(r.id),
                user_id=r.user_id,
                email=r.email,
                full_name=r.full_name,
                status=r.status,
                label=r.label,
                location=r.location,
                created_at=_iso(r.created_at),
                expires_at=_iso(r.expires_at),
            )
            for r in rows
        ]
    )


@router.post("/super-admin/login-requests/{request_id}/approve", response_model=AdminApproveResult)
async def approve_login_request(
    request_id: str,
    body: AdminApproveBody,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理者が許可する。自分の依頼は 403。待つ機械は poll で入る（auth_events の reason は approved_admin）。"""
    require_app_origin(request)
    rid = devices.parse_request_id(request_id)
    if rid is None:
        raise HTTPException(status_code=404, detail="not_found")
    target = (
        await db.execute(
            text(
                "SELECT r.user_id, u.tenant_id FROM public.auth_login_requests r "
                "JOIN public.users u ON u.id = r.user_id WHERE r.id = :id"
            ),
            {"id": rid},
        )
    ).first()
    if target is None:
        raise HTTPException(status_code=404, detail="not_found")
    if target.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="cannot_approve_own_request")
    now = datetime.now(timezone.utc)
    decided = (
        await db.execute(
            text(
                "UPDATE public.auth_login_requests SET status = 'approved', decided_at = :now, "
                "decided_via = 'admin', decided_by_user_id = :admin, decided_note = :note "
                "WHERE id = :id AND status = 'pending' AND expires_at > :now RETURNING id"
            ),
            {"now": now, "admin": current_user.id, "note": body.note.strip(), "id": rid},
        )
    ).first()
    if decided is None:
        raise HTTPException(status_code=404, detail="not_found")
    # 依頼した人の会社の履歴に残す。依頼の id は UUID で整数の列に入らないので record_id は None、note の中身は書かない
    await _record_auth_audit(
        db,
        tenant_id=target.tenant_id,
        user_id=current_user.id,
        action="update",
        table_name="auth_login_requests",
        record_id=None,
        new_data={
            "event": "login_request_approved_admin",
            "request_id": rid,
            "target_user_id": target.user_id,
        },
    )
    await db.commit()
    await publish_user_change(target.user_id, TOPIC_AUTH_LOGIN_REQUEST)
    return AdminApproveResult(status="approved")
