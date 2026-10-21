"""閲覧者（社外の在庫閲覧専用アカウント）の管理 API（ADR-1019 段4a-2）。

すべて require_super_admin で保護する。

API:
  GET  /api/v1/super-admin/viewers
  GET  /api/v1/super-admin/viewers/{viewer_id}/logins
  PATCH /api/v1/super-admin/viewers/{viewer_id}   （LINE名だけ直す）
  POST /api/v1/super-admin/viewers/{viewer_id}/activate
  POST /api/v1/super-admin/viewers/{viewer_id}/suspend
  POST /api/v1/super-admin/viewers/{viewer_id}/unsuspend
  POST /api/v1/super-admin/viewers/{viewer_id}/extend
  POST /api/v1/super-admin/viewers/{viewer_id}/reissue-signup-code
  GET  /api/v1/super-admin/viewers/signup-request   （①申込のお願いの文を返す）
  GET  /api/v1/super-admin/viewer-templates         （段11: 文面テンプレート9件の一覧）
  PUT  /api/v1/super-admin/viewer-templates/{key}   （段11 便2: 本文を直す。検査 422・競合 409）
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.auth.viewer_signup_code import format_signup_code
from app.database import get_db
from app.discord_gateway import viewer_bot_texts
from app.models import User
from app.services import viewer_admin, viewer_message_templates, viewer_room_notice
from app.services.viewer_admin import ViewerAdminError
from app.services.viewer_invite import create_viewer_invite

_TEMPLATE_NOT_FOUND = "template_not_found"

# 詳細欄からコピーできる文（その人のデータだけで埋まるもの）。表示順もこの順。
COPYABLE_KEYS = (
    "signup_request",
    "room_recreated",
    "notice_extended",
    "interview_request",
    "notice_activated",
    "notice_suspended",
)

router = APIRouter()

_ERROR_STATUS = {
    "not_found": (status.HTTP_404_NOT_FOUND, "viewer_not_found"),
    "conflict": (status.HTTP_409_CONFLICT, "viewer_status_conflict"),
    "invalid_days": (status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_days"),
    "already_linked": (status.HTTP_409_CONFLICT, "viewer_already_linked"),
    "invalid_line_name": (status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_line_name"),
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


class ViewerStatusChangeResponse(ViewerAdminItem):
    """状態変更（activate／suspend／unsuspend／extend）の応答。部屋へのお知らせの結果つき。"""

    room_notice: Literal["sent", "failed", "no_room", "no_template"] | None = Field(
        None,
        description="部屋へのお知らせの結果（unsuspend は null。no_template はテンプレートが使えず送らなかった）",
    )
    room_notice_text: str | None = Field(
        None, description="部屋へ送ろうとした文（送れなかったとき画面でコピーする）"
    )


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
    days: int | None = Field(None, ge=1, le=365, strict=True, description="延長する日数（1〜365）")
    until_date: date | None = Field(
        None, description="この日の終わり（日本時間 23:59:59）まで延長する。今日より後・365日以内"
    )

    @model_validator(mode="after")
    def _exactly_one(self) -> "ExtendRequest":
        if (self.days is None) == (self.until_date is None):
            raise ValueError("days か until_date のどちらか一つだけを指定してください")
        return self


class LineNameUpdate(BaseModel):
    line_name: str = Field(
        ..., max_length=200, description="新しい LINE名（前後の空白を除いて 1〜100 文字）"
    )


class ViewerReissueResponse(BaseModel):
    """作り直した申込コードと招待リンク（この応答でしか見られない）。"""

    signup_code: str = Field(..., description="申込コード（XXXX-XXXX-XXXX-XXXX）")
    expires_at: datetime | str = Field(..., description="申込コードの有効期限")
    invite_url: str | None = Field(None, description="Discord 招待リンク（作れなければ null）")
    message: str = Field(..., description="そのまま送れる案内文（招待には外部ブラウザの目印付き）")


class SignupRequestResponse(BaseModel):
    text: str = Field(..., description="①申込のお願いの文")


class ViewerTemplateTextResponse(BaseModel):
    text: str = Field(..., description="その人の値を差し込んだ、そのまま送れる文")


class ViewerTemplateItem(BaseModel):
    """文面テンプレート1件（台帳の1鍵）。"""

    key: str = Field(..., description="文面の鍵（台帳の9件）")
    body: str | None = Field(None, description="本文。DB に行が無ければ null")
    copy_text: str | None = Field(None, description="コピー用の文。{signup_url} だけ入れ済み。body が null なら null")
    placeholders: list[str] = Field(..., description="差し込み項目（台帳の順）")
    send_mode: Literal["manual", "auto"] = Field(..., description="手で送る／自動")
    updated_at: datetime | None = Field(None, description="最後に直した時刻")
    updated_by_name: str | None = Field(None, description="最後に直した人の名前（full_name、空なら username）")


class ViewerTemplateUpdate(BaseModel):
    body: str = Field(..., description="新しい本文（差し込み項目は台帳どおり・1〜1800文字）")
    expected_updated_at: datetime | None = Field(
        None, description="画面で開いた時の updated_at。未登録の行を新しく入れるときは null"
    )


class ViewerTemplateListResponse(BaseModel):
    items: list[ViewerTemplateItem]


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
    "/super-admin/viewers/signup-request",
    response_model=SignupRequestResponse,
    dependencies=[Depends(require_super_admin)],
)
async def signup_request_endpoint(db: AsyncSession = Depends(get_db)):
    text = await viewer_message_templates.load_rendered(
        db, "signup_request", signup_url=viewer_bot_texts.SIGNUP_URL
    )
    if text is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_TEMPLATE_NOT_FOUND)
    return {"text": text}


@router.get(
    "/super-admin/viewers/{viewer_id}/template-text",
    response_model=ViewerTemplateTextResponse,
    dependencies=[Depends(require_super_admin)],
)
async def viewer_template_text_endpoint(
    viewer_id: int, key: str, db: AsyncSession = Depends(get_db)
):
    if key not in COPYABLE_KEYS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="template_not_copyable")
    try:
        item = await viewer_admin._get_item(db, viewer_id)
    except ViewerAdminError as exc:
        raise _http_error(exc) from None
    values: dict[str, object] = {}
    if key == "signup_request":
        values["signup_url"] = viewer_bot_texts.SIGNUP_URL
    elif key == "room_recreated":
        values["email"] = item["email"]
    elif key in ("notice_extended", "interview_request"):
        expires = item["trial_expires_at"]
        if expires is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="no_trial_expiry")
        name = "until_date" if key == "notice_extended" else "expires_date"
        values[name] = viewer_bot_texts.format_jst_date(expires)
    text = await viewer_message_templates.load_rendered(db, key, **values)
    if text is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_TEMPLATE_NOT_FOUND)
    return {"text": text}


@router.get(
    "/super-admin/viewer-templates",
    response_model=ViewerTemplateListResponse,
    dependencies=[Depends(require_super_admin)],
)
async def list_viewer_templates_endpoint(db: AsyncSession = Depends(get_db)):
    return {"items": await viewer_message_templates.list_rows(db)}


@router.put(
    "/super-admin/viewer-templates/{key}",
    response_model=ViewerTemplateItem,
)
async def update_viewer_template_endpoint(
    key: str,
    payload: ViewerTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    if viewer_message_templates.get_spec(key) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TEMPLATE_NOT_FOUND)
    try:
        await viewer_message_templates.save_body(
            db, key, payload.body, payload.expected_updated_at, int(current_user.id)
        )
        await db.commit()
    except viewer_message_templates.TemplateInvalid as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"template_{exc.code}"
        ) from None
    except viewer_message_templates.TemplateConflict:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="template_conflict") from None
    rows = await viewer_message_templates.list_rows(db)
    return next(r for r in rows if r["key"] == key)


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
    db: AsyncSession,
    current_user: User,
    viewer_id: int,
    action: str,
    days: int | None = None,
    until_date: date | None = None,
) -> dict:
    try:
        item = await viewer_admin.change_status(
            db,
            viewer_id,
            action,
            actor=viewer_admin.ACTOR_PO,
            actor_user_id=int(current_user.id),
            days=days,
            until_date=until_date,
        )
        # お知らせの文は commit の前（同じトランザクション）に DB から読む。無くても状態は変える
        prepared = await viewer_room_notice.prepare_notice(db, action, item)
        await db.commit()
    except ViewerAdminError as exc:
        await db.rollback()
        raise _http_error(exc) from None
    # commit の後に送る（DB を開けたまま Discord を待たない・commit の後に DB を読まない）。
    # 送れなくても・テンプレートが無くても操作は成功のまま
    room_notice, room_notice_text = await viewer_room_notice.notify_prepared(prepared, item)
    return {**item, "room_notice": room_notice, "room_notice_text": room_notice_text}


@router.patch(
    "/super-admin/viewers/{viewer_id}",
    response_model=ViewerAdminItem,
    dependencies=[Depends(require_super_admin)],
)
async def update_line_name_endpoint(
    viewer_id: int, payload: LineNameUpdate, db: AsyncSession = Depends(get_db)
):
    try:
        item = await viewer_admin.update_line_name(db, viewer_id, payload.line_name)
        await db.commit()
    except ViewerAdminError as exc:
        await db.rollback()
        raise _http_error(exc) from None
    return item


@router.post("/super-admin/viewers/{viewer_id}/activate", response_model=ViewerStatusChangeResponse)
async def activate_endpoint(
    viewer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return await _change(db, current_user, viewer_id, "activate")


@router.post("/super-admin/viewers/{viewer_id}/suspend", response_model=ViewerStatusChangeResponse)
async def suspend_endpoint(
    viewer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return await _change(db, current_user, viewer_id, "suspend")


@router.post("/super-admin/viewers/{viewer_id}/unsuspend", response_model=ViewerStatusChangeResponse)
async def unsuspend_endpoint(
    viewer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return await _change(db, current_user, viewer_id, "unsuspend")


@router.post("/super-admin/viewers/{viewer_id}/extend", response_model=ViewerStatusChangeResponse)
async def extend_endpoint(
    viewer_id: int,
    payload: ExtendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return await _change(db, current_user, viewer_id, "extend", days=payload.days, until_date=payload.until_date)


@router.post(
    "/super-admin/viewers/{viewer_id}/reissue-signup-code",
    response_model=ViewerReissueResponse,
    dependencies=[Depends(require_super_admin)],
)
async def reissue_signup_code_endpoint(viewer_id: int, db: AsyncSession = Depends(get_db)):
    # 申込コードを作り直す前に案内文を読む（どちらを使うかは招待の作成後に決まるので両方）。無ければ 503・何も変えない
    with_invite_body = await viewer_message_templates.load_body(db, "reissue_notice")
    no_invite_body = await viewer_message_templates.load_body(db, "reissue_notice_no_invite")
    if with_invite_body is None or no_invite_body is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_TEMPLATE_NOT_FOUND)
    try:
        code, expires_at = await viewer_admin.reissue_signup_code(db, viewer_id)
    except ViewerAdminError as exc:
        await db.rollback()
        raise _http_error(exc) from None
    await db.commit()
    invite_url = await create_viewer_invite(db)  # commit の後（Discord を待つ間 DB を開けない）
    item = await viewer_admin._get_item(db, viewer_id)
    formatted_code = format_signup_code(code)
    message = viewer_message_templates.render(
        "reissue_notice" if invite_url else "reissue_notice_no_invite",
        with_invite_body if invite_url else no_invite_body,
        line_name=(item.get("line_name") or "").strip(),
        code=formatted_code,
        expires=viewer_bot_texts.format_jst_datetime(expires_at),
        invite_url=viewer_bot_texts.external_browser_url(invite_url) if invite_url else "",
    )
    if message is None:  # 読んだ本文は検査済みなので通常は起きない
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_TEMPLATE_NOT_FOUND)
    return {
        "signup_code": formatted_code,
        "expires_at": expires_at.isoformat(),
        "invite_url": invite_url,
        "message": message,
    }
