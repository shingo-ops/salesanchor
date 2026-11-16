from __future__ import annotations

"""
アプリ内カレンダー CRUD エンドポイント。

エンドポイント一覧:
  GET    /calendar/events         — イベント一覧（期間・タイプ指定）
  POST   /calendar/events         — イベント作成（DB保存 → Google同期）
  PATCH  /calendar/events/{id}    — イベント更新
  DELETE /calendar/events/{id}    — イベント削除
  GET    /calendar/events/search  — 題名で予定を探す
  GET    /calendar/holidays       — 日本の祝日（期間・言語）
  GET    /calendar/sync-mode      — 同期モード確認
  PATCH  /calendar/sync-mode      — 同期モード変更（admin のみ）

認証: 全エンドポイントで Bearer トークン必須（get_current_tenant）
"""

import logging
from datetime import date
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    get_user_system_keys,
    load_user_permissions,
    require_tenant_admin,
    reset_tenant_context,
)
from app.auth.system_roles import is_tenant_admin
from app.database import get_db
from app.models import User
from app.services import calendar_service as cal_svc
from app.services import holiday_service

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_SYNC_MODES = ("bidirectional", "read_only", "write_only", "none")
# ADR-1059 で ADR-1057 の取り込み停止を置き換え。write_only・none は取り込みの非常停止
_ACCEPTED_SYNC_MODES = ("bidirectional", "read_only", "write_only", "none")
_VALID_OWNER_SHARE_MODES = ("self", "view", "edit")
_DEFAULT_OWNER_COLOR = "#1a73e8"


def _owner_display_name(row: dict) -> str:
    given = (row.get("given_name_jp") or "").strip()
    surname = (row.get("surname_jp") or "").strip()
    full_name = f"{surname} {given}".strip()
    if full_name:
        return full_name
    return (row.get("primary_email") or "").strip() or f"担当者 {row.get('id')}"


async def _current_staff_row(db: AsyncSession, current_user: User) -> dict | None:
    result = await db.execute(
        text("""
            SELECT s.id, s.tenant_id, s.user_id, s.staff_code, s.surname_jp, s.given_name_jp,
                   u.email AS primary_email
            FROM staff s
            JOIN public.users u ON u.id = s.user_id
            WHERE s.user_id = :uid
            LIMIT 1
        """),
        {"uid": current_user.id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


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
# Pydantic モデル
# ---------------------------------------------------------------------------


MEET_NOT_ALLOWED_DETAIL = "Google Meet は Google カレンダーをつないだ本人の予定にだけ付けられます"

RecurrenceValue = Literal["none", "daily", "weekly", "monthly_nth", "monthly_last", "yearly", "weekdays"]
RecurrenceScope = Literal["this", "following", "all"]


class CreateEventBody(BaseModel):
    title: str
    start_datetime: str
    end_datetime: str
    calendar_type: str = "shared"
    description: Optional[str] = None
    location: Optional[str] = None
    is_all_day: bool = False
    add_meet: bool = False
    recurrence: RecurrenceValue = "none"


class UpdateEventBody(BaseModel):
    title: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_all_day: Optional[bool] = None
    calendar_type: Optional[str] = None
    add_meet: Optional[bool] = None
    recurrence: Optional[RecurrenceValue] = None
    scope: Optional[RecurrenceScope] = None
    occurrence_start: Optional[str] = None


class SyncModeBody(BaseModel):
    sync_mode: str


# ---------------------------------------------------------------------------
# イベント一覧
# ---------------------------------------------------------------------------


@router.get("/calendar/events", tags=["calendar"])
async def list_events(
    start: str = Query(..., description="ISO 8601 形式 例: 2025-05-01T00:00:00Z"),
    end: str = Query(..., description="ISO 8601 形式 例: 2025-05-31T23:59:59Z"),
    type: Optional[str] = Query(None, description="'shared' | 'personal' | None（両方）"),
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """カレンダーイベントを期間・タイプで取得する。"""
    events = await cal_svc.list_events(
        db,
        tenant_id=tenant_id,
        start=start,
        end=end,
        calendar_type=type,
        user_id=user.id,
    )
    return {"events": events}


_SEARCH_MAX_RESULTS = 50


@router.get("/calendar/events/search", tags=["calendar"])
async def search_events(
    q: str = Query(..., description="題名の一部（前後の空白は除く・1〜100 文字）"),
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """題名の一部で予定を探す。見せてよい予定の決まりは list_events と同じ。新しい順・最大 50 件。"""
    query = q.strip()
    if not 1 <= len(query) <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid search query",
        )
    events = await cal_svc.list_events(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        title_query=query,
        limit=_SEARCH_MAX_RESULTS,
    )
    return {"events": events}


class HolidayItem(BaseModel):
    date: str
    name: str


class HolidayListResponse(BaseModel):
    holidays: list[HolidayItem]


# 長すぎる期間は断る（月の表示は最大 31 日。年をまたぐ見方も 400 日に収まる）
_HOLIDAY_MAX_DAYS = 400


@router.get("/calendar/holidays", tags=["calendar"], response_model=HolidayListResponse)
async def list_holidays(
    start: date = Query(..., description="この日から（含む） 例: 2026-11-01"),
    end: date = Query(..., description="この日まで（含まない） 例: 2026-12-01"),
    lang: str = Query("ja", pattern="^(ja|en)$", description="祝日の名前の言語"),
    tenant_id: int = Depends(get_current_tenant),
):
    """日本の祝日を期間で返す。会社によらず同じ（ログインは要る）。"""
    if end <= start or (end - start).days > _HOLIDAY_MAX_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid holiday range",
        )
    return {"holidays": holiday_service.list_japan_holidays(start, end, lang)}


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
            detail="not_found:my_staff_profile",
        )

    current_staff_id = int(current_staff["id"])
    query = """
        SELECT
            s.id, s.user_id, s.staff_code, s.surname_jp, s.given_name_jp, u.email AS primary_email,
            COALESCE(cos.color, :default_color) AS color,
            COALESCE(cos.is_visible, FALSE) AS is_visible,
            COALESCE(cos.share_mode, 'self') AS share_mode
        FROM staff s
        JOIN public.users u ON u.id = s.user_id
        LEFT JOIN calendar_owner_settings cos ON cos.staff_id = s.user_id
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


@router.patch("/calendar/owners/{user_id}", tags=["calendar"], response_model=OwnerRosterItem)
async def update_calendar_owner(
    user_id: int,
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
            detail="no_fields_to_update",
        )

    staff_row = await db.execute(
        text("""
            SELECT s.id, s.tenant_id, s.user_id, s.staff_code, s.surname_jp, s.given_name_jp,
                   u.email AS primary_email
            FROM staff s
            JOIN public.users u ON u.id = s.user_id
            WHERE s.user_id = :user_id
            LIMIT 1
        """),
        {"user_id": user_id},
    )
    if not staff_row.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not_found:calendar_owner",
        )

    current_staff = await _current_staff_row(db, user)
    current_staff_id = int(current_staff["id"]) if current_staff else None

    insert_columns = ["staff_id"]
    insert_values = [":staff_id"]
    params: dict[str, object] = {"staff_id": user_id}
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
                s.id, s.user_id, s.staff_code, s.surname_jp, s.given_name_jp, u.email AS primary_email,
                COALESCE(cos.color, :default_color) AS color,
                COALESCE(cos.is_visible, FALSE) AS is_visible,
                COALESCE(cos.share_mode, 'self') AS share_mode
            FROM staff s
            JOIN public.users u ON u.id = s.user_id
            LEFT JOIN calendar_owner_settings cos ON cos.staff_id = s.user_id
            WHERE s.user_id = :user_id
            LIMIT 1
        """),
        {"user_id": user_id, "default_color": _DEFAULT_OWNER_COLOR},
    )
    row = refreshed.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not_found:calendar_owner",
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
    # 繰り返しの判定（Meet の判定より前。繰り返しと add_meet が両方あれば recurrence_meet_not_allowed）
    recurrence_error = cal_svc.check_create_recurrence(body.model_dump())
    if recurrence_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=recurrence_error)
    # Meet は Google をつないだ本人の予定にだけ付ける。判定はサービスを呼ぶ try の前で行う
    # （下の except Exception が HTTPException を 500 に変えてしまうため）
    if body.add_meet and not await cal_svc.can_add_meet(db, tenant_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=MEET_NOT_ALLOWED_DETAIL,
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
    scope = payload.pop("scope", None)
    occurrence_start = payload.pop("occurrence_start", None)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="no_fields_to_update",
        )

    # 権限確認: 自分のイベントか tenant admin（owner / admin のシステムロール）のみ
    event = await cal_svc.read_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:calendar_event")
    # 例外の行は元の行の値で持ち主・見せ方を判定する
    owner_row = event
    if event["recurring_event_id"] is not None:
        owner_row = await cal_svc.read_event(db, event["recurring_event_id"])
        if not owner_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:calendar_event")

    created_by, event_calendar_type, event_user_id = (
        owner_row["created_by_user_id"],
        owner_row["calendar_type"],
        owner_row["user_id"],
    )
    event_google_id, event_meet_url = event["google_event_id"], event["meet_url"]
    event_owner = event_user_id if event_user_id is not None else created_by
    # 他人の「自分だけ」予定は存在しないものとして扱う（管理者でも）
    if event_calendar_type == "personal" and event_owner != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:calendar_event")

    if created_by != user.id and not is_tenant_admin(await get_user_system_keys(db, user.id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="編集権限がありません")

    if "calendar_type" in payload:
        if payload["calendar_type"] not in ("shared", "personal"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="calendar_type は 'shared' または 'personal' を指定してください",
            )
        if event_owner != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="見せ方を変えられるのは予定の持ち主だけです",
            )
        if payload["calendar_type"] == "personal":
            payload["user_id"] = user.id

    # 繰り返しの判定（Meet の判定より前。422 はどれも下の try の前）
    recurrence_error = await cal_svc.check_recurrence_request(
        db, event=event, payload=payload, scope=scope, occurrence_start=occurrence_start
    )
    if recurrence_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=recurrence_error)

    if payload.get("add_meet"):
        # Meet を付けてよいのは、つないだ本人が持ち主の、Google に送ってある予定だけ。
        # 欠けていれば 422 で何も変えない（判定は try の前。上の create_event と同じ理由）
        if (
            not await cal_svc.can_add_meet(db, tenant_id, user.id)
            or not event_google_id
            or event_owner != user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=MEET_NOT_ALLOWED_DETAIL,
            )
        if event_meet_url:
            # すでに Meet がある。頼み直さない
            payload.pop("add_meet")
            if not payload:
                return {"id": event_id, "meet_url": event_meet_url}

    is_recurring = event["recurrence_rule"] is not None or event["recurring_event_id"] is not None
    try:
        if not is_recurring and payload.get("recurrence") in (None, "none"):
            result = await cal_svc.update_event(
                db,
                tenant_id=tenant_id,
                event_id=event_id,
                user_id=user.id,
                payload=payload,
            )
        else:
            result = await cal_svc.update_recurring_event(
                db,
                tenant_id,
                user.id,
                event,
                payload,
                scope,
                cal_svc.parse_occurrence(occurrence_start),
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
    scope: Annotated[Optional[RecurrenceScope], Query()] = None,
    occurrence_start: Annotated[Optional[str], Query()] = None,
):
    """アプリ内のイベントを削除し、Google Calendar からも削除する。"""
    event = await cal_svc.read_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:calendar_event")
    # 例外の行は元の行の値で持ち主を確かめる
    owner_row = event
    if event["recurring_event_id"] is not None:
        owner_row = await cal_svc.read_event(db, event["recurring_event_id"])
        if not owner_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:calendar_event")

    event_owner = owner_row["user_id"] if owner_row["user_id"] is not None else owner_row["created_by_user_id"]
    if owner_row["calendar_type"] == "personal" and event_owner != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:calendar_event")

    if owner_row["created_by_user_id"] != user.id and not is_tenant_admin(
        await get_user_system_keys(db, user.id)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="削除権限がありません")

    recurrence_error = await cal_svc.check_recurrence_request(
        db, event=event, payload=None, scope=scope, occurrence_start=occurrence_start
    )
    if recurrence_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=recurrence_error)

    if event["recurrence_rule"] is None and event["recurring_event_id"] is None:
        await cal_svc.delete_event(db, tenant_id=tenant_id, event_id=event_id)
    else:
        await cal_svc.delete_recurring_event(
            db, tenant_id, event, scope, cal_svc.parse_occurrence(occurrence_start)
        )


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
    user: User = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    """同期モードを変更する（admin のみ）。"""

    if body.sync_mode not in _VALID_SYNC_MODES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"sync_mode は {_VALID_SYNC_MODES} のいずれかを指定してください",
        )
    if body.sync_mode not in _ACCEPTED_SYNC_MODES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google の予定をアプリへ取り込む設定は使えません（ADR-1057）",
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
        registered = await webhook_svc.register_webhook(db, tenant_id)
        if registered:
            # 最初の全部読みをすぐ始める
            from app.tasks.google_calendar_sync import sync_google_calendar_tenant

            sync_google_calendar_tenant.delay(tenant_id)
    else:
        await webhook_svc.stop_webhook(db, tenant_id)

    return {"sync_mode": body.sync_mode}
