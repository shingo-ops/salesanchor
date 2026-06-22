from __future__ import annotations

"""
アプリ内カレンダー CRUD エンドポイント。

エンドポイント一覧:
  GET    /calendar/events         — イベント一覧（期間・タイプ指定）
  POST   /calendar/events         — イベント作成（DB保存 → Google同期）
  PATCH  /calendar/events/{id}    — イベント更新
  DELETE /calendar/events/{id}    — イベント削除
  GET    /calendar/sync-mode      — 同期モード確認
  PATCH  /calendar/sync-mode      — 同期モード変更（admin のみ）

認証: 全エンドポイントで Bearer トークン必須（get_current_tenant）
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    load_user_permissions,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.services import calendar_service as cal_svc

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_SYNC_MODES = ("bidirectional", "read_only", "write_only", "none")
_VALID_OWNER_SHARE_MODES = ("self", "view", "edit")
_DEFAULT_OWNER_COLOR = "#1a73e8"
CalendarCategory = Literal["personal", "meeting", "purchase", "shipping", "billing", "release", "holiday"]


def _require_admin(user: User) -> None:
    if getattr(user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作は管理者のみ実行できます",
        )


def _owner_display_name(row: dict) -> str:
    given = (row.get("given_name_jp") or "").strip()
    surname = (row.get("surname_jp") or "").strip()
    full_name = f"{surname} {given}".strip()
    if full_name:
        return full_name
    return (row.get("primary_email") or "").strip() or f"担当者 {row.get('id')}"


async def _current_staff_row(db: AsyncSession, current_user: User) -> dict | None:
    user_email = getattr(current_user, "email", None)
    result = await db.execute(
        text("""
            SELECT id, tenant_id, user_id, staff_code, surname_jp, given_name_jp, primary_email
            FROM staff
            WHERE user_id = :uid OR primary_email = :email
            ORDER BY CASE WHEN user_id = :uid THEN 0 ELSE 1 END, id ASC
            LIMIT 1
        """),
        {"uid": current_user.id, "email": user_email},
    )
    row = result.mappings().first()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Pydantic モデル
# ---------------------------------------------------------------------------


class CreateEventBody(BaseModel):
    title: str
    start_datetime: str
    end_datetime: str
    calendar_type: str = "shared"
    category: Optional[CalendarCategory] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_all_day: bool = False


class UpdateEventBody(BaseModel):
    title: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    category: Optional[CalendarCategory] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_all_day: Optional[bool] = None


class SyncModeBody(BaseModel):
    sync_mode: str


class OwnerSettingsBody(BaseModel):
    color: Optional[str] = None
    is_visible: Optional[bool] = None
    share_mode: Optional[str] = None


class OwnerRosterItem(BaseModel):
    staff_id: int
    user_id: Optional[int]
    staff_code: str
    name: str
    primary_email: Optional[str]
    color: str
    is_visible: bool
    share_mode: str
    is_self: bool


class OwnerRosterResponse(BaseModel):
    can_manage_others: bool
    current_staff_id: Optional[int]
    current_user_id: int
    owners: list[OwnerRosterItem]


# ---------------------------------------------------------------------------
# イベント一覧
# ---------------------------------------------------------------------------


@router.get("/calendar/events", tags=["calendar"])
async def list_events(
    start: str = Query(..., description="ISO 8601 形式 例: 2025-05-01T00:00:00Z"),
    end: str = Query(..., description="ISO 8601 形式 例: 2025-05-31T23:59:59Z"),
    type: Optional[str] = Query(None, description="'shared' | 'personal' | None（両方）"),
    user_id: Optional[int] = Query(None, description="personal カレンダーの所有者ユーザーID"),
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """カレンダーイベントを期間・タイプで取得する。"""
    if user_id is not None and user_id != user.id:
        perms = await load_user_permissions(db, tenant_id, user.id)
        if "staff.view" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="他担当の予定を閲覧する権限がありません",
            )
        if type is None:
            type = "personal"
    events = await cal_svc.list_events(
        db,
        tenant_id=tenant_id,
        start=start,
        end=end,
        calendar_type=type,
        user_id=user_id if user_id is not None else user.id,
    )
    return {"events": events}


# ---------------------------------------------------------------------------
# 担当者一覧 / 設定
# ---------------------------------------------------------------------------


@router.get("/calendar/owners", tags=["calendar"], response_model=OwnerRosterResponse)
async def list_calendar_owners(
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    perms = await load_user_permissions(db, tenant_id, user.id)
    can_manage_others = "staff.view" in perms
    current_staff = await _current_staff_row(db, user)
    if not current_staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="現在のユーザーに紐づく担当者が見つかりません",
        )

    current_staff_id = int(current_staff["id"])
    query = """
        SELECT
            s.id, s.user_id, s.staff_code, s.surname_jp, s.given_name_jp, s.primary_email,
            COALESCE(cos.color, :default_color) AS color,
            COALESCE(cos.is_visible, FALSE) AS is_visible,
            COALESCE(cos.share_mode, 'self') AS share_mode
        FROM staff s
        LEFT JOIN calendar_owner_settings cos ON cos.staff_id = s.id
    """
    params = {"default_color": _DEFAULT_OWNER_COLOR}
    if can_manage_others:
        query += " ORDER BY s.staff_code, s.id"
    else:
        query += " WHERE s.id = :current_staff_id ORDER BY s.staff_code, s.id"
        params["current_staff_id"] = current_staff_id

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    if not can_manage_others and not rows:
        rows = [current_staff]

    owners = [
        OwnerRosterItem(
            staff_id=row["id"],
            user_id=row["user_id"],
            staff_code=row["staff_code"],
            name=_owner_display_name(dict(row)),
            primary_email=row.get("primary_email"),
            color=row.get("color") or _DEFAULT_OWNER_COLOR,
            is_visible=bool(row.get("is_visible")) if row.get("is_visible") is not None else False,
            share_mode=row.get("share_mode") or "self",
            is_self=int(row["id"]) == current_staff_id,
        )
        for row in rows
    ]
    return OwnerRosterResponse(
        can_manage_others=can_manage_others,
        current_staff_id=current_staff_id,
        current_user_id=user.id,
        owners=owners,
    )


@router.patch("/calendar/owners/{staff_id}", tags=["calendar"], response_model=OwnerRosterItem)
async def update_calendar_owner(
    staff_id: int,
    body: OwnerSettingsBody,
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    perms = await load_user_permissions(db, tenant_id, user.id)
    if "staff.view" not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作にはマネージャー権限が必要です",
        )

    payload: dict[str, object] = {}
    if body.color is not None:
        payload["color"] = body.color
    if body.is_visible is not None:
        payload["is_visible"] = body.is_visible
    if body.share_mode is not None:
        if body.share_mode not in _VALID_OWNER_SHARE_MODES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"share_mode は {_VALID_OWNER_SHARE_MODES} のいずれかを指定してください",
            )
        payload["share_mode"] = body.share_mode

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="更新フィールドが指定されていません",
        )

    staff_row = await db.execute(
        text("""
            SELECT id, tenant_id, user_id, staff_code, surname_jp, given_name_jp, primary_email
            FROM staff
            WHERE id = :staff_id
            LIMIT 1
        """),
        {"staff_id": staff_id},
    )
    if not staff_row.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="担当者が見つかりません",
        )

    current_staff = await _current_staff_row(db, user)
    current_staff_id = int(current_staff["id"]) if current_staff else None

    insert_columns = ["staff_id"]
    insert_values = [":staff_id"]
    params: dict[str, object] = {"staff_id": staff_id}
    update_parts: list[str] = []
    for key in ("color", "is_visible", "share_mode"):
        if key in payload:
            insert_columns.append(key)
            insert_values.append(f":{key}")
            params[key] = payload[key]
            update_parts.append(f"{key} = EXCLUDED.{key}")

    await db.execute(
        text(
            "INSERT INTO calendar_owner_settings ("
            + ", ".join(insert_columns)
            + ") VALUES ("
            + ", ".join(insert_values)
            + ") ON CONFLICT (staff_id) DO UPDATE SET "
            + ", ".join(update_parts)
            + ", updated_at = NOW()"
        ),
        params,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5

    refreshed = await db.execute(
        text("""
            SELECT
                s.id, s.user_id, s.staff_code, s.surname_jp, s.given_name_jp, s.primary_email,
                COALESCE(cos.color, :default_color) AS color,
                COALESCE(cos.is_visible, FALSE) AS is_visible,
                COALESCE(cos.share_mode, 'self') AS share_mode
            FROM staff s
            LEFT JOIN calendar_owner_settings cos ON cos.staff_id = s.id
            WHERE s.id = :staff_id
            LIMIT 1
        """),
        {"staff_id": staff_id, "default_color": _DEFAULT_OWNER_COLOR},
    )
    row = refreshed.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="担当者が見つかりません",
        )
    data = dict(row)
    return OwnerRosterItem(
        staff_id=data["id"],
        user_id=data["user_id"],
        staff_code=data["staff_code"],
        name=_owner_display_name(data),
        primary_email=data.get("primary_email"),
        color=data.get("color") or _DEFAULT_OWNER_COLOR,
        is_visible=bool(data.get("is_visible")) if data.get("is_visible") is not None else False,
        share_mode=data.get("share_mode") or "self",
        is_self=(current_staff_id == data["id"]) if current_staff_id is not None else False,
    )


# ---------------------------------------------------------------------------
# イベント作成
# ---------------------------------------------------------------------------


@router.post("/calendar/events", status_code=status.HTTP_201_CREATED, tags=["calendar"])
async def create_event(
    body: CreateEventBody,
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """アプリ内にイベントを作成し、Google Calendar に同期する。"""
    if body.calendar_type not in ("shared", "personal"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="calendar_type は 'shared' または 'personal' を指定してください",
        )
    try:
        result = await cal_svc.create_event(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            payload=body.model_dump(exclude_none=True),
        )
    except Exception as e:
        logger.error("イベント作成エラー: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="イベントの作成に失敗しました",
        )
    return result


# ---------------------------------------------------------------------------
# イベント更新
# ---------------------------------------------------------------------------


@router.patch("/calendar/events/{event_id}", tags=["calendar"])
async def update_event(
    event_id: int,
    body: UpdateEventBody,
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """アプリ内のイベントを更新し、Google Calendar に同期する。"""
    payload = body.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="更新フィールドが指定されていません",
        )

    # 権限確認: 自分のイベントか admin のみ
    row = await db.execute(
        text("SELECT created_by_user_id, calendar_type FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    record = row.first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="イベントが見つかりません")

    created_by, _ = record[0], record[1]
    if created_by != user.id and getattr(user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="編集権限がありません")

    try:
        result = await cal_svc.update_event(
            db,
            tenant_id=tenant_id,
            event_id=event_id,
            user_id=user.id,
            payload=payload,
        )
    except Exception as e:
        logger.error("イベント更新エラー: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="イベントの更新に失敗しました",
        )
    return result


# ---------------------------------------------------------------------------
# イベント削除
# ---------------------------------------------------------------------------


@router.delete("/calendar/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["calendar"])
async def delete_event(
    event_id: int,
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """アプリ内のイベントを削除し、Google Calendar からも削除する。"""
    row = await db.execute(
        text("SELECT created_by_user_id FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    record = row.first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="イベントが見つかりません")

    if record[0] != user.id and getattr(user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="削除権限がありません")

    await cal_svc.delete_event(db, tenant_id=tenant_id, event_id=event_id)


# ---------------------------------------------------------------------------
# 同期モード確認 / 変更
# ---------------------------------------------------------------------------


@router.get("/calendar/sync-mode", tags=["calendar"])
async def get_sync_mode(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """現在の同期モードを返す。"""
    row = await db.execute(
        text(
            "SELECT sync_mode FROM tenant_google_calendar_config WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    record = row.first()
    return {"sync_mode": record[0] if record else "none"}


@router.patch("/calendar/sync-mode", tags=["calendar"])
async def update_sync_mode(
    body: SyncModeBody,
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """同期モードを変更する（admin のみ）。"""
    _require_admin(user)

    if body.sync_mode not in _VALID_SYNC_MODES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"sync_mode は {_VALID_SYNC_MODES} のいずれかを指定してください",
        )

    await db.execute(
        text(
            "UPDATE tenant_google_calendar_config"
            " SET sync_mode = :mode, updated_at = NOW()"
            " WHERE tenant_id = :tid"
        ),
        {"mode": body.sync_mode, "tid": tenant_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5

    # Webhook の登録/解除を同期モードに合わせて調整
    from app.services import google_webhook as webhook_svc

    if body.sync_mode in ("bidirectional", "read_only"):
        await webhook_svc.register_webhook(db, tenant_id)
    else:
        await webhook_svc.stop_webhook(db, tenant_id)

    return {"sync_mode": body.sync_mode}
