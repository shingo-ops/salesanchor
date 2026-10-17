"""閲覧者（社外の在庫閲覧専用アカウント）の管理 API（ADR-1019 段4a-2）。

すべて require_super_admin で保護する。

API:
  GET  /api/v1/super-admin/viewers
  GET  /api/v1/super-admin/viewers/{viewer_id}/logins
  POST /api/v1/super-admin/viewers/{viewer_id}/activate
  POST /api/v1/super-admin/viewers/{viewer_id}/suspend
  POST /api/v1/super-admin/viewers/{viewer_id}/unsuspend
  POST /api/v1/super-admin/viewers/{viewer_id}/extend
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.services import viewer_admin
from app.services.viewer_admin import ViewerAdminError

router = APIRouter()

_ERROR_STATUS = {
    "not_found": (status.HTTP_404_NOT_FOUND, "viewer_not_found"),
    "conflict": (status.HTTP_409_CONFLICT, "viewer_status_conflict"),
    "invalid_days": (status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_days"),
}


class ViewerAdminItem(BaseModel):
    """管理画面の閲覧者1行。"""

    id: int = Field(..., description="閲覧者 viewer_accounts.id")
    email: str = Field(..., description="メールアドレス（小文字）")
    line_name: str = Field(..., description="LINE の表示名")
    inventory_issue: str | None = Field(None, description="在庫関連の課題（任意）")
    status: str = Field(..., description="pending／verified／trial／active／suspended")
    trial_expires_at: datetime | None = Field(None, description="お試しの期限")
    created_at: datetime = Field(..., description="登録した時刻")
    discord_user_id: str | None = Field(None, description="Discord の利用者 ID")
    discord_channel_id: str | None = Field(None, description="Discord のチケット部屋 ID")
    discord_channel_url: str | None = Field(None, description="Discord のチケット部屋を開く URL")
    flag_many_ips: bool = Field(..., description="目印: 24時間以内に3種類以上の IP からログイン")
    flag_shared_ip: bool = Field(..., description="目印: 別の閲覧者と同じ IP からログイン")


class ViewerAdminListResponse(BaseModel):
    items: list[ViewerAdminItem] = Field(..., description="閲覧者の一覧（登録が新しい順）")


class ViewerLoginItem(BaseModel):
    """ログイン記録1行。"""

    created_at: datetime = Field(..., description="記録した時刻")
    event_type: str = Field(..., description="記録の種類")
    client_ip: str | None = Field(None, description="クライアント IP")
    user_agent: str | None = Field(None, description="User-Agent")


class ViewerLoginListResponse(BaseModel):
    items: list[ViewerLoginItem] = Field(..., description="ログイン記録（新しい順・最大500行）")


class ExtendRequest(BaseModel):
    days: int = Field(..., ge=1, le=365, strict=True, description="延長する日数（1〜365）")


def _http_error(exc: ViewerAdminError) -> HTTPException:
    code, detail = _ERROR_STATUS[exc.code]
    return HTTPException(status_code=code, detail=detail)


@router.get(
    "/super-admin/viewers",
    response_model=ViewerAdminListResponse,
    dependencies=[Depends(require_super_admin)],
)
async def list_viewers_endpoint(db: AsyncSession = Depends(get_db)):
    return {"items": await viewer_admin.list_viewers(db)}


@router.get(
    "/super-admin/viewers/{viewer_id}/logins",
    response_model=ViewerLoginListResponse,
    dependencies=[Depends(require_super_admin)],
)
async def list_logins_endpoint(viewer_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return {"items": await viewer_admin.list_logins(db, viewer_id)}
    except ViewerAdminError as exc:
        raise _http_error(exc) from None


async def _change(
    db: AsyncSession, current_user: User, viewer_id: int, action: str, days: int | None = None
) -> dict:
    try:
        item = await viewer_admin.change_status(
            db,
            viewer_id,
            action,
            actor=viewer_admin.ACTOR_PO,
            actor_user_id=int(current_user.id),
            days=days,
        )
        await db.commit()
    except ViewerAdminError as exc:
        await db.rollback()
        raise _http_error(exc) from None
    return item


@router.post("/super-admin/viewers/{viewer_id}/activate", response_model=ViewerAdminItem)
async def activate_endpoint(
    viewer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return await _change(db, current_user, viewer_id, "activate")


@router.post("/super-admin/viewers/{viewer_id}/suspend", response_model=ViewerAdminItem)
async def suspend_endpoint(
    viewer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return await _change(db, current_user, viewer_id, "suspend")


@router.post("/super-admin/viewers/{viewer_id}/unsuspend", response_model=ViewerAdminItem)
async def unsuspend_endpoint(
    viewer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return await _change(db, current_user, viewer_id, "unsuspend")


@router.post("/super-admin/viewers/{viewer_id}/extend", response_model=ViewerAdminItem)
async def extend_endpoint(
    viewer_id: int,
    payload: ExtendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return await _change(db, current_user, viewer_id, "extend", days=payload.days)
