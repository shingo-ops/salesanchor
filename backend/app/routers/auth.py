from __future__ import annotations

import asyncio
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import options_to_json, verify_authentication_response, verify_registration_response
from webauthn.helpers import parse_authentication_credential_json, parse_registration_credential_json
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import CredentialDeviceType

from app.auth import devices, geo, passkeys, recovery_codes, self_tokens
from app.auth.dependencies import (
    CurrentSession,
    _get_client_ip,
    clear_tenant_context,
    get_current_session,
    get_current_user,
    require_super_admin,
    resolve_current_session,
    set_tenant_context,
)
from app.auth.origin import require_app_origin as _require_app_origin
from app.auth.password_policy import check_password
from app.auth.passwords import hash_password, needs_rehash, verify_password
from app.auth.schemas import UserRegister, UserResponse
from app.cache import (
    PASSWORD_RESET_REQUEST_MAX,
    blacklist_token,
    check_auth_rate_limit,
    count_password_reset_request,
    invalidate_user_permissions,
    record_auth_failure,
)
from app.database import get_db
from app.models import Tenant, User
from app.realtime.publisher import publish_user_change
from app.realtime.topics import TOPIC_AUTH_LOGIN_REQUEST
from app.schemas.auth import PasswordChange
from app.services.audit import record_audit_log
from app.services.auth_mail import send_invite_email, send_new_device_mail, send_password_reset_email
from app.services.invite import create_invite_token, invite_enabled, invite_url

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    data: UserRegister,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    ユーザー登録API（super admin のみ実行可能）。

    フロー:
      ① Origin と super admin 権限を確認
      ② tenant_codeからテナントを検索
      ③ 同じメールアドレスのユーザーがいないか確認（いれば409）
      ④ usersテーブルにユーザーを作成（パスワードは NULL）
      ⑤ AUTH_PROVIDER=self のとき、初回設定の鍵（purpose=invite・72時間）を作り、
         commit の後に初回設定メールを送る（firebase の間は鍵もメールも作らない）

    注意:
      - パスワードは本人が初回設定メールのリンクから決める（ADR-1013 便4a）。
    """
    _require_app_origin(request)
    # super admin 権限チェック（require_super_admin との二重防御）
    if not getattr(current_user, "is_super_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ユーザー登録はsuper adminのみ可能です",
        )

    # テナントの存在確認（エラーメッセージにテナントコードを含めない）
    result = await db.execute(
        select(Tenant).where(
            Tenant.tenant_code == data.tenant_code,
            Tenant.is_active == True,
        )
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="テナントコードが無効です",
        )

    # メールアドレスの重複チェック（小文字で照合する）
    email = data.email.strip().lower()
    result = await db.execute(
        select(User).where(func.lower(User.email) == email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このメールアドレスは既に登録されています",
        )

    # ユーザー作成（パスワードは NULL。初回設定メールのリンクで本人が決める）
    await set_tenant_context(db, tenant.id)
    user = User(
        tenant_id=tenant.id,
        username=data.username,
        email=email,
        full_name=data.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await clear_tenant_context(db)

    # 監査ログ記録（パスワード等の機密情報は記録しない）
    await _record_auth_audit(
        db,
        tenant_id=tenant.id,
        user_id=user.id,
        action="create",
        table_name="users",
        record_id=user.id,
        new_data={
            "email": user.email,
            "username": user.username,
        },
    )

    # 新規ユーザーにデフォルトロール（CS）を自動付与（Phase 1以降）
    # CSロール未作成（Phase 1マイグレーション未適用）の場合はスキップ
    from app.services.tenant import DEFAULT_NEW_USER_ROLE
    await set_tenant_context(db, tenant.id)
    default_role = await db.execute(
        text("SELECT id FROM roles WHERE tenant_id = :tid AND name = :name"),
        {"tid": tenant.id, "name": DEFAULT_NEW_USER_ROLE},
    )
    default_row = default_role.first()
    if default_row:
        await db.execute(
            text("""
                INSERT INTO user_roles (user_id, role_id, assigned_by)
                VALUES (:uid, :rid, :by)
                ON CONFLICT (user_id, role_id) DO NOTHING
            """),
            {"uid": user.id, "rid": default_row[0], "by": current_user.id},
        )
        await invalidate_user_permissions(tenant.id, user.id)

    invite_raw = await create_invite_token(db, user.id) if invite_enabled() else None

    await db.commit()
    await db.refresh(user)

    if invite_raw is not None:
        background_tasks.add_task(send_invite_email, user.email, invite_url(invite_raw))

    return user


@router.post("/logout", status_code=200)
async def logout(
    request: Request,
    response: Response,
    cred: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    ログアウトAPI。
    トークンをブラックリストに追加し、以降の利用を拒否する。
    Firebase IDトークンの残存有効期限（最大1時間）をTTLとする。
    自社ログインの更新用トークン（Cookie）があれば失効させ、Cookie を消す。
    """
    token = cred.credentials
    success = await blacklist_token(token, ttl=3600)
    if not success:
        raise HTTPException(
            status_code=503,
            detail="ログアウト処理に失敗しました。しばらく待ってから再試行してください。",
        )
    raw_refresh = request.cookies.get(self_tokens.REFRESH_COOKIE_NAME)
    if raw_refresh:
        await self_tokens.revoke_refresh_token(db, raw_refresh)
        await db.commit()
        _clear_refresh_cookie(response)
    return {"message": "ログアウトしました"}


# ── 自社ログイン（ADR-1013 便2。AUTH_PROVIDER=self のときだけ有効） ────────────

INVALID_CREDENTIALS = "invalid_credentials"
INVALID_TOKEN_DETAIL = "無効な認証トークンです"


class SelfLoginRequest(BaseModel):
    email: EmailStr = Field(description="ログインに使うメールアドレス")
    password: str = Field(min_length=1, max_length=1024, description="パスワード")


class SelfTokenResponse(BaseModel):
    access_token: str = Field(description="自社アクセストークン（Bearer）")
    token_type: str = Field(default="bearer", description="トークン種別")
    expires_in: int = Field(description="アクセストークンの有効秒数")


def _require_issuance_enabled() -> None:
    if not self_tokens.is_issuance_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


def _audit(
    request: Request,
    *,
    user_id: int | None,
    reason: str,
    is_new_device: bool | None = None,
    event_type: str | None = None,
) -> None:
    """認証の記録（K9・D7）に渡す値を request.state に入れる。middleware が同じ行に書く。
    パスワード・合言葉・Cookie の値は入れない。"""
    state: dict = {"user_id": user_id, "reason": reason, "is_new_device": is_new_device}
    if event_type:
        state["event_type"] = event_type
    request.state.auth_audit = state


def _set_refresh_cookie(response: Response, raw: str, expires_at: datetime) -> None:
    max_age = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 0)
    response.set_cookie(
        self_tokens.REFRESH_COOKIE_NAME,
        raw,
        httponly=True,
        secure=self_tokens.cookie_secure(),
        samesite="strict",
        path=self_tokens.REFRESH_COOKIE_PATH,
        max_age=max_age,
    )


def _issue_session_tokens(
    response: Response, raw: str, expires_at: datetime, user_id: int, email: str, amr: str | None, sid: str
) -> str:
    """更新用 Cookie を付け、アクセストークンを返す。トークンを出す口は全部ここを通る（ADR-1048 admin-2fa/design.md:66）。
    sid は更新トークンの組の id（ADR-1055 D8）。"""
    _set_refresh_cookie(response, raw, expires_at)
    return self_tokens.create_access_token(user_id, email, amr, sid=sid)


def _clear_refresh_cookie(response: Response | JSONResponse) -> None:
    response.delete_cookie(
        self_tokens.REFRESH_COOKIE_NAME,
        path=self_tokens.REFRESH_COOKIE_PATH,
        secure=self_tokens.cookie_secure(),
        httponly=True,
        samesite="strict",
    )


async def _record_auth_audit(
    db: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    action: str,
    table_name: str,
    record_id: int | None,
    new_data: dict,
) -> None:
    """自社ログインの監査記録を書く。

    audit_logs の行の制限は app.tenant_id を整数に直すため、空のままだと 500 になる。
    会社を指定してから書き、書いたら空に戻す（便5 追補）。
    """
    await set_tenant_context(db, tenant_id)
    await record_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        new_data=new_data,
    )
    await clear_tenant_context(db)


def _invalid_credentials() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)


async def _count_login_failure(db: AsyncSession, user_row, ip: str, now: datetime) -> None:
    """照合失敗を口座単位で数え、上限で停止期限を入れる（login と password/change で共通）。commit まで行う。"""
    await set_tenant_context(db, user_row.tenant_id)
    counted = (
        await db.execute(
            text(
                "UPDATE public.users SET failed_login_count = failed_login_count + 1 "
                "WHERE id = :id RETURNING failed_login_count"
            ),
            {"id": user_row.id},
        )
    ).scalar_one()
    if counted >= self_tokens.LOGIN_FAIL_LIMIT:
        await db.execute(
            text(
                "UPDATE public.users SET locked_until = :until, failed_login_count = 0 WHERE id = :id"
            ),
            {"until": now + self_tokens.LOGIN_LOCK_DURATION, "id": user_row.id},
        )
    await clear_tenant_context(db)
    await db.commit()
    await record_auth_failure(ip)


class LoginApprovalRequired(BaseModel):
    """知らない機械からのログイン（202）。トークンは出さない。いつもの機械で許可するまで待つ（ADR-1055）。"""

    status: str = Field(default="device_approval_required", description="許可待ち")
    match_number: str = Field(description="待つ機械に出す2けたの番号")
    expires_in: int = Field(description="依頼の有効秒数")
    has_trusted_device: bool = Field(description="いつもの機械があるか")
    has_recovery_codes: bool = Field(description="予備の合言葉が残っているか")


async def _notify_new_request(
    background_tasks: BackgroundTasks, email: str, new: devices.NewRequest, user_id: int
) -> None:
    """許可依頼を、いつもの機械の画面（SSE）とメールで知らせる。失敗しても依頼は作ってある。"""
    await publish_user_change(user_id, TOPIC_AUTH_LOGIN_REQUEST)
    background_tasks.add_task(
        send_new_device_mail,
        email,
        when=devices.jst_text(),
        device=new.label,
        location=new.location,
    )


@router.post(
    "/login",
    response_model=SelfTokenResponse,
    responses={202: {"model": LoginApprovalRequired, "description": "知らない機械。いつもの機械で許可するまで待つ"}},
)
async def self_login(
    data: SelfLoginRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """自社ログイン。失敗理由は区別せず 1 種類の文言で返す。

    AUTH_DEVICE_APPROVAL=off（既定）は今までと同じ。enforce のとき、知らない機械は 202 で止める（ADR-1055）。
    """
    _require_issuance_enabled()
    _require_app_origin(request)
    ip = _get_client_ip(request)
    if await check_auth_rate_limit(ip):
        _audit(request, user_id=None, reason="rate_limited")
        raise HTTPException(status_code=429, detail="too_many_attempts")

    now = datetime.now(timezone.utc)
    email = data.email.strip().lower()
    user_row = (
        await db.execute(
            text(
                "SELECT id, email, tenant_id, is_active, password_argon2_hash, failed_login_count, locked_until, "
                "last_login FROM public.users WHERE lower(email) = :email"
            ),
            {"email": email},
        )
    ).first()
    locked_until = self_tokens._as_utc(user_row.locked_until) if user_row else None
    if user_row is None or not user_row.is_active or (locked_until is not None and locked_until > now):
        if user_row is None:
            _audit(request, user_id=None, reason="unknown_user")
        else:
            _audit(request, user_id=user_row.id, reason="inactive" if not user_row.is_active else "locked")
        await asyncio.to_thread(verify_password, None, data.password)
        await record_auth_failure(ip)
        raise _invalid_credentials()

    if not await asyncio.to_thread(verify_password, user_row.password_argon2_hash, data.password):
        _audit(request, user_id=user_row.id, reason="bad_password")
        await _count_login_failure(db, user_row, ip, now)
        raise _invalid_credentials()

    # 機械の判定（ADR-1055 D2〜D5・D11）。off は今までと同じ（機械の登録も印の発行もしない）
    trusted_device_id: int | None = None
    device_cookie_raw: str | None = None
    audit_reason, audit_new_device = "ok", None
    if devices.is_enforced():
        cookie_raw = request.cookies.get(devices.DEVICE_COOKIE_NAME)
        found = await devices.find_trusted_device(db, user_row.id, cookie_raw)
        if found is not None:
            # いつもの機械: 使った時刻を更新し、印の期限を延ばす
            await devices.touch_device(db, found.id, request)
            trusted_device_id = found.id
            device_cookie_raw = devices.clean_cookie_value(cookie_raw)
            audit_new_device = False
        elif user_row.last_login is None and await devices.count_all_devices(db, user_row.id) == 0:
            # D5: 一度もログインしていない人の最初のログイン。この機械を最初のいつもの機械にする
            trusted_device_id, device_cookie_raw = await devices.register_device(
                db, user_row.id, cookie_raw, "first_login", request
            )
            audit_reason, audit_new_device = "first_login", True
            background_tasks.add_task(
                send_new_device_mail,
                user_row.email,
                when=devices.jst_text(),
                device=devices.describe_user_agent(request.headers.get("user-agent")),
                location=geo.lookup(ip),
                note="この機械を最初のいつもの機械として登録しました。 / This device was registered as your first trusted device.",
            )
        else:
            # 知らない機械: 許可依頼を作って 202（トークンは出さない）
            new = await devices.create_login_request(db, user_row.id, request, cookie_raw)
            has_trusted = await devices.has_any_trusted_device(db, user_row.id)
            has_codes = (await recovery_codes.remaining(db, user_row.id)) > 0
            await db.commit()
            await _notify_new_request(background_tasks, user_row.email, new, user_row.id)
            pending = JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content=LoginApprovalRequired(
                    match_number=new.match_number,
                    expires_in=int(devices.REQUEST_TTL.total_seconds()),
                    has_trusted_device=has_trusted,
                    has_recovery_codes=has_codes,
                ).model_dump(),
            )
            devices.set_pending_cookie(pending, new.pending_raw)
            _audit(
                request,
                user_id=user_row.id,
                reason="device_approval_required",
                is_new_device=True,
                event_type="auth_pending",
            )
            return pending

    await set_tenant_context(db, user_row.tenant_id)
    await db.execute(
        text(
            "UPDATE public.users SET failed_login_count = 0, locked_until = NULL, last_login = :now "
            "WHERE id = :id"
        ),
        {"now": now, "id": user_row.id},
    )
    if needs_rehash(user_row.password_argon2_hash):
        new_hash = await asyncio.to_thread(hash_password, data.password)
        await db.execute(
            text("UPDATE public.users SET password_argon2_hash = :h WHERE id = :id"),
            {"h": new_hash, "id": user_row.id},
        )
    await clear_tenant_context(db)
    family_id = str(uuid.uuid4())
    raw, expires_at = await self_tokens.issue_refresh_token(
        db,
        user_row.id,
        request.headers.get("user-agent"),
        family_id=family_id,
        trusted_device_id=trusted_device_id,
    )
    await db.commit()
    access = _issue_session_tokens(response, raw, expires_at, user_row.id, user_row.email, "pwd", family_id)
    if device_cookie_raw:
        devices.set_device_cookie(response, device_cookie_raw)
    _audit(request, user_id=user_row.id, reason=audit_reason, is_new_device=audit_new_device)
    return SelfTokenResponse(
        access_token=access,
        token_type="bearer",
        expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS,
    )


@router.post("/refresh", response_model=SelfTokenResponse)
async def self_refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """更新用 Cookie を入れ替え、新しいアクセストークンを返す。"""
    _require_issuance_enabled()
    _require_app_origin(request)
    raw = request.cookies.get(self_tokens.REFRESH_COOKIE_NAME)
    if not raw:
        raise _invalid_credentials()
    rotated = await self_tokens.rotate_refresh_token(db, raw, request.headers.get("user-agent"))
    if rotated is None:
        await db.commit()  # 使い回し検知による組の失効を確定させる
        failure = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": INVALID_CREDENTIALS})
        _clear_refresh_cookie(failure)
        return failure
    user_id, new_raw, expires_at = rotated.user_id, rotated.raw, rotated.expires_at
    sid = rotated.family_id
    email = (
        await db.execute(text("SELECT email FROM public.users WHERE id = :id"), {"id": user_id})
    ).scalar_one()

    # 機械の確かめ（ADR-1055 D4）。組の機械が取り消されていたら 401
    device_cookie_raw: str | None = None
    audit_reason, audit_new_device = "ok", None
    trusted_id = rotated.trusted_device_id
    if trusted_id is not None and not await devices.is_device_active(db, trusted_id):
        await devices.revoke_user_sessions(db, user_id, device_id=trusted_id)
        await devices.revoke_family(db, user_id, sid)
        await db.commit()
        _audit(request, user_id=user_id, reason="device_revoked")
        failure = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": INVALID_CREDENTIALS})
        _clear_refresh_cookie(failure)
        return failure
    if trusted_id is not None:
        await devices.touch_device(db, trusted_id, request)
    elif devices.is_enforced():
        # 組に機械が無い。締切より前に作られた組は、この機械をいつもの機械として登録する（bootstrap）。
        # 締切より後に作られた組は 401（締切の1秒前は登録・ちょうどは 401）
        cutoff = devices.bootstrap_cutoff()
        if cutoff is not None and rotated.family_created_at is not None and rotated.family_created_at < cutoff:
            device_id, device_cookie_raw = await devices.register_device(
                db, user_id, request.cookies.get(devices.DEVICE_COOKIE_NAME), "bootstrap", request
            )
            await devices.bind_family_to_device(db, sid, user_id, device_id)
            audit_reason, audit_new_device = "bootstrap", False
        else:
            await devices.revoke_family(db, user_id, sid)
            await db.commit()
            _audit(request, user_id=user_id, reason="device_not_trusted")
            failure = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": INVALID_CREDENTIALS}
            )
            _clear_refresh_cookie(failure)
            return failure
    await db.commit()
    access = _issue_session_tokens(response, new_raw, expires_at, user_id, email, None, sid)
    if device_cookie_raw:
        devices.set_device_cookie(response, device_cookie_raw)
    _audit(request, user_id=user_id, reason=audit_reason, is_new_device=audit_new_device)
    return SelfTokenResponse(
        access_token=access,
        token_type="bearer",
        expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS,
    )


# ── パスワード再設定（ADR-1013 便3。AUTH_PROVIDER に関係なく動く） ─────────────

INVALID_OR_EXPIRED_TOKEN = "invalid_or_expired_token"
PASSWORD_RESET_TTL = timedelta(minutes=30)


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(description="再設定したいアカウントのメールアドレス")


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256, description="再設定メールのリンクに入っている鍵")
    new_password: str = Field(min_length=1, max_length=1024, description="新しいパスワード（15〜64 文字）")


class PasswordResetAccepted(BaseModel):
    status: str = Field(default="accepted", description="申請を受け付けた（メールが送られたかは区別しない）")


class PasswordResetDone(BaseModel):
    status: str = Field(default="password_updated", description="パスワードを更新した")


def _password_reset_allowed(email: str) -> bool:
    """再設定メールを送ってよい相手か。self なら全員。firebase の間は許可リストに載った email だけ（未設定・空は誰にも送らない）。"""
    if self_tokens.auth_provider() == "self":
        return True
    allowed = {e.strip().lower() for e in os.getenv("AUTH_PASSWORD_RESET_ALLOWLIST", "").split(",") if e.strip()}
    return email in allowed


@router.post("/password-reset/request", response_model=PasswordResetAccepted)
async def password_reset_request(
    data: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """再設定メールの申請。存在・停止・許可外の区別を応答に出さない（常に 200）。"""
    _require_app_origin(request)
    email = data.email.strip().lower()
    if await count_password_reset_request(email) > PASSWORD_RESET_REQUEST_MAX:
        raise HTTPException(status_code=429, detail="too_many_attempts")

    row = (
        await db.execute(
            text("SELECT id, tenant_id, email, is_active FROM public.users WHERE lower(email) = :email"),
            {"email": email},
        )
    ).first()
    if row is not None and row.is_active and _password_reset_allowed(email):
        now = datetime.now(timezone.utc)
        await db.execute(
            text(
                "UPDATE public.password_reset_tokens SET used_at = :now "
                "WHERE user_id = :uid AND used_at IS NULL"
            ),
            {"now": now, "uid": row.id},
        )
        raw = secrets.token_urlsafe(32)
        await db.execute(
            text(
                "INSERT INTO public.password_reset_tokens (user_id, purpose, token_hash, expires_at, created_at) "
                "VALUES (:uid, 'reset', :h, :exp, :now)"
            ),
            {"uid": row.id, "h": self_tokens._hash_token(raw), "exp": now + PASSWORD_RESET_TTL, "now": now},
        )
        await db.commit()
        reset_url = f"{self_tokens.rp_origin()}/reset-password?token={raw}"
        background_tasks.add_task(send_password_reset_email, row.email, reset_url)
    return PasswordResetAccepted(status="accepted")


@router.post("/password-reset/confirm", response_model=PasswordResetDone)
async def password_reset_confirm(
    data: PasswordResetConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """新しいパスワードの確定。鍵は 1 回だけ・期限内だけ使える。自動ログインはしない。"""
    _require_app_origin(request)
    ip = _get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail="too_many_attempts")

    reason = check_password(data.new_password)
    if reason is not None:
        raise HTTPException(status_code=422, detail=reason)

    now = datetime.now(timezone.utc)
    token_row = (
        await db.execute(
            text(
                "UPDATE public.password_reset_tokens SET used_at = :now "
                "WHERE token_hash = :h AND used_at IS NULL AND expires_at > :now "
                "RETURNING user_id, purpose"
            ),
            {"now": now, "h": self_tokens._hash_token(data.token)},
        )
    ).first()
    if token_row is None:
        await record_auth_failure(ip)
        raise HTTPException(status_code=400, detail=INVALID_OR_EXPIRED_TOKEN)

    user_row = (
        await db.execute(
            text("SELECT id, tenant_id, is_active FROM public.users WHERE id = :uid"),
            {"uid": token_row.user_id},
        )
    ).first()
    if user_row is None or not user_row.is_active:
        await db.commit()  # 鍵は消費済みのまま
        raise HTTPException(status_code=400, detail=INVALID_OR_EXPIRED_TOKEN)

    new_hash = await asyncio.to_thread(hash_password, data.new_password)
    await set_tenant_context(db, user_row.tenant_id)
    await db.execute(
        text(
            "UPDATE public.users SET password_argon2_hash = :h, password_changed_at = :now, "
            "failed_login_count = 0, locked_until = NULL WHERE id = :uid"
        ),
        {"h": new_hash, "now": now, "uid": user_row.id},
    )
    await clear_tenant_context(db)
    await devices.revoke_user_sessions(db, user_row.id)
    await _record_auth_audit(
        db,
        tenant_id=user_row.tenant_id,
        user_id=user_row.id,
        action="update",
        table_name="users",
        record_id=user_row.id,
        new_data={"event": "password_reset_confirmed", "purpose": token_row.purpose},
    )
    await db.commit()
    return PasswordResetDone(status="password_updated")


# ── パスワード変更（ADR-1013 便4a。AUTH_PROVIDER に関係なく動く） ─────────────

class PasswordChangeResponse(BaseModel):
    status: str = Field(default="password_updated", description="パスワードを更新した")
    access_token: str | None = Field(default=None, description="新しい自社アクセストークン（自社ログインが有効なときだけ）")
    token_type: str | None = Field(default=None, description="トークン種別")
    expires_in: int | None = Field(default=None, description="アクセストークンの有効秒数")


@router.post("/password/change", response_model=PasswordChangeResponse)
async def password_change(
    data: PasswordChange,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ログイン中の本人のパスワード変更。

    照合失敗は 400 invalid_credentials（401 は画面が「ログインが切れた」と読むため使わない）。
    成功でその人の更新用トークンを全部失効させ、自社ログインが有効なときだけ今の端末に
    新しいアクセストークンと更新用 Cookie を出し直す。
    """
    _require_app_origin(request)
    ip = _get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail="too_many_attempts")

    now = datetime.now(timezone.utc)
    user_row = (
        await db.execute(
            text(
                "SELECT id, email, tenant_id, is_active, password_argon2_hash, failed_login_count, locked_until "
                "FROM public.users WHERE id = :id"
            ),
            {"id": current_user.id},
        )
    ).first()
    if user_row is None or not user_row.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_TOKEN_DETAIL)

    locked_until = self_tokens._as_utc(user_row.locked_until)
    if locked_until is not None and locked_until > now:
        await asyncio.to_thread(verify_password, None, data.current_password)
        await record_auth_failure(ip)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_CREDENTIALS)

    if not await asyncio.to_thread(verify_password, user_row.password_argon2_hash, data.current_password):
        await _count_login_failure(db, user_row, ip, now)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_CREDENTIALS)

    # enforce のときだけ、今の組と機械を引く（ADR-1055 D16）。off は引数もここも今まで通り。
    # 現在のパスワードの照合の後・新パスワードの検査より前で確かめる（403 のときパスワードは変わらない）
    inherit_device_id: int | None = None
    bootstrap_device = False
    if devices.is_enforced() and self_tokens.is_issuance_enabled():
        # sid の無いトークンは 403 session_upgrade_required
        session = await resolve_current_session(request, db, current_user)
        if session.trusted_device_id is not None:
            inherit_device_id = session.trusted_device_id
        else:
            cutoff = devices.bootstrap_cutoff()
            if cutoff is not None and session.family_created_at is not None and session.family_created_at < cutoff:
                bootstrap_device = True
            else:
                _audit(request, user_id=user_row.id, reason="device_not_trusted")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="device_not_trusted")

    reason = check_password(data.new_password)
    if reason is not None:
        raise HTTPException(status_code=422, detail=reason)

    new_hash = await asyncio.to_thread(hash_password, data.new_password)
    # アクセストークンの iat は秒単位なので、変更時刻も秒に切り捨てて保存する（同じ秒に出す新トークンを拒否しない）
    changed_at = now.replace(microsecond=0)
    await set_tenant_context(db, user_row.tenant_id)
    await db.execute(
        text(
            "UPDATE public.users SET password_argon2_hash = :h, password_changed_at = :at, "
            "failed_login_count = 0, locked_until = NULL WHERE id = :uid"
        ),
        {"h": new_hash, "at": changed_at, "uid": user_row.id},
    )
    await clear_tenant_context(db)
    await devices.revoke_user_sessions(db, user_row.id)
    await _record_auth_audit(
        db,
        tenant_id=user_row.tenant_id,
        user_id=user_row.id,
        action="update",
        table_name="users",
        record_id=user_row.id,
        new_data={"event": "password_changed"},
    )

    issued: PasswordChangeResponse
    if self_tokens.is_issuance_enabled():
        device_cookie_raw: str | None = None
        if bootstrap_device:
            inherit_device_id, device_cookie_raw = await devices.register_device(
                db, user_row.id, request.cookies.get(devices.DEVICE_COOKIE_NAME), "bootstrap", request
            )
        family_id = str(uuid.uuid4())
        raw, expires_at = await self_tokens.issue_refresh_token(
            db,
            user_row.id,
            request.headers.get("user-agent"),
            family_id=family_id,
            trusted_device_id=inherit_device_id,
        )
        await db.commit()
        access = _issue_session_tokens(response, raw, expires_at, user_row.id, user_row.email, "pwd", family_id)
        if device_cookie_raw:
            devices.set_device_cookie(response, device_cookie_raw)
        issued = PasswordChangeResponse(
            status="password_updated",
            access_token=access,
            token_type="bearer",
            expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS,
        )
    else:
        await db.commit()
        issued = PasswordChangeResponse(status="password_updated")
    return issued


# ── パスキー（ADR-1013 便5。顔・指紋でのログイン） ───────────────────────────────


class PasskeyChallengeResponse(BaseModel):
    challenge_id: str = Field(description="challenge の引換券（300 秒・1 回限り）")
    options: dict = Field(description="WebAuthn の options（ブラウザへそのまま渡す）")


class PasskeyRegisterVerify(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=64)
    credential: dict
    label: str | None = Field(default=None, description="端末の名前（任意）")


class PasskeyLoginVerify(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=64)
    credential: dict


class PasskeyCreated(BaseModel):
    id: int
    label: str | None = None
    created_at: str


class PasskeyItem(BaseModel):
    id: int
    label: str | None = None
    created_at: str | None = None
    last_used_at: str | None = None


class PasskeyList(BaseModel):
    items: list[PasskeyItem]


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


class PasskeyRegisterOptionsRequest(BaseModel):
    auto: bool = False


class PasskeyPromptStatus(BaseModel):
    can_auto: bool
    show_prompt: bool


def _is_fresh_password_login(request: Request, user: User) -> bool:
    """パスワードを打って FRESH_LOGIN_SECONDS 以内の合図か（便6 の自動作成と案内だけに使う）。"""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return False
    token = header[7:].strip()
    if self_tokens.peek_issuer(token) != self_tokens.ISSUER:
        return False
    try:
        claims = self_tokens.decode_access_token(token)
        issued_at = int(claims["iat"])
    except (JWTError, ValueError, KeyError, TypeError):
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    return (
        claims.get("sub") == str(user.id)
        and claims.get("amr") == ["pwd"]
        and 0 <= now - issued_at <= passkeys.FRESH_LOGIN_SECONDS
    )


async def _passkey_count(db: AsyncSession, user_id: int) -> int:
    row = (
        await db.execute(
            text("SELECT count(*) AS n FROM public.webauthn_credentials WHERE user_id = :uid"),
            {"uid": user_id},
        )
    ).one()
    return int(row.n)


async def _recent_prompt_skips(db: AsyncSession, user_id: int) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=passkeys.PROMPT_SKIP_WINDOW_DAYS)
    row = (
        await db.execute(
            text(
                "SELECT count(*) AS n FROM public.passkey_enroll_prompt_skips "
                "WHERE user_id = :uid AND skipped_at > :since"
            ),
            {"uid": user_id, "since": since},
        )
    ).one()
    return int(row.n)


@router.get("/passkey/prompt", response_model=PasskeyPromptStatus)
async def passkey_prompt_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ログイン直後のパスキー登録（自動作成・案内）を出してよいか。

    読むだけの口なので出どころの確認はしない（ブラウザは同じサイトあての GET に Origin を付けない）。
    本人の Bearer トークンが要るので、他のサイトからは読めない。
    """
    if not _is_fresh_password_login(request, current_user):
        return PasskeyPromptStatus(can_auto=False, show_prompt=False)
    count = await _passkey_count(db, current_user.id)
    skips = await _recent_prompt_skips(db, current_user.id)
    return PasskeyPromptStatus(
        can_auto=count < passkeys.MAX_PASSKEYS_PER_USER,
        show_prompt=count == 0 and skips < passkeys.PROMPT_SKIP_LIMIT,
    )


@router.post("/passkey/prompt/skip", status_code=204)
async def passkey_prompt_skip(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """「今はスキップ」の記録。"""
    _require_app_origin(request)
    if not _is_fresh_password_login(request, current_user):
        raise HTTPException(status_code=403, detail="auto_not_allowed")
    await db.execute(
        text("INSERT INTO public.passkey_enroll_prompt_skips (user_id) VALUES (:uid)"),
        {"uid": current_user.id},
    )
    await db.commit()
    return Response(status_code=204)


@router.post("/passkey/register/options", response_model=PasskeyChallengeResponse)
async def passkey_register_options(
    request: Request,
    data: PasskeyRegisterOptionsRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """パスキー登録の options を作る（ログイン中の本人だけ）。"""
    _require_app_origin(request)
    auto = bool(data and data.auto)
    if auto and not _is_fresh_password_login(request, current_user):
        raise HTTPException(status_code=403, detail="auto_not_allowed")
    rows = (
        await db.execute(
            text("SELECT credential_id FROM public.webauthn_credentials WHERE user_id = :uid"),
            {"uid": current_user.id},
        )
    ).all()
    if len(rows) >= passkeys.MAX_PASSKEYS_PER_USER:
        raise HTTPException(status_code=409, detail="passkey_limit")
    options = passkeys.registration_options(
        current_user.id, current_user.email, [bytes(r.credential_id) for r in rows]
    )
    challenge_id = await passkeys.store_challenge(
        "reg_auto" if auto else "reg", str(current_user.id), options.challenge
    )
    return PasskeyChallengeResponse(challenge_id=challenge_id, options=json.loads(options_to_json(options)))


@router.post("/passkey/register/verify", response_model=PasskeyCreated, status_code=201)
async def passkey_register_verify(
    data: PasskeyRegisterVerify,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """パスキー登録の応答を確かめ、公開鍵を保存する。"""
    _require_app_origin(request)
    auto = False
    challenge = await passkeys.take_challenge("reg", str(current_user.id), data.challenge_id)
    if challenge is None:
        challenge = await passkeys.take_challenge("reg_auto", str(current_user.id), data.challenge_id)
        auto = challenge is not None
    if challenge is None:
        raise HTTPException(status_code=400, detail="challenge_expired")
    # 自動作成の道だけは UP・UV の印を求めない（ブラウザが裏で作るため）。設定画面の道は今のまま。
    verify_extra = {"require_user_presence": False, "require_user_verification": False} if auto else {
        "require_user_verification": True
    }
    try:
        parsed = parse_registration_credential_json(data.credential)
        verified = verify_registration_response(
            credential=parsed,
            expected_challenge=challenge,
            expected_rp_id=self_tokens.rp_id(),
            expected_origin=self_tokens.rp_origin(),
            **verify_extra,
        )
    except (WebAuthnException, ValueError):
        raise HTTPException(status_code=400, detail="passkey_invalid")

    label = (data.label or "").strip()[: passkeys.LABEL_MAX] or None
    now = datetime.now(timezone.utc)
    try:
        row = (
            await db.execute(
                text(
                    "INSERT INTO public.webauthn_credentials "
                    "(user_id, credential_id, public_key, sign_count, transports, backup_eligible, "
                    "backup_state, aaguid, label, created_at) "
                    "VALUES (:uid, :cid, :pk, :sc, :tr, :be, :bs, :aaguid, :label, :now) "
                    "RETURNING id, created_at"
                ),
                {
                    "uid": current_user.id,
                    "cid": verified.credential_id,
                    "pk": verified.credential_public_key,
                    "sc": verified.sign_count,
                    "tr": [t.value for t in (parsed.response.transports or [])],
                    "be": verified.credential_device_type == CredentialDeviceType.MULTI_DEVICE,
                    "bs": verified.credential_backed_up,
                    "aaguid": verified.aaguid,
                    "label": label,
                    "now": now,
                },
            )
        ).one()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="passkey_exists")
    await clear_tenant_context(db)
    await _record_auth_audit(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="create",
        table_name="webauthn_credentials",
        record_id=row.id,
        new_data={"event": "passkey_registered", "auto": auto},
    )
    await db.commit()
    return PasskeyCreated(id=row.id, label=label, created_at=_iso(row.created_at))


@router.post("/passkey/login/options", response_model=PasskeyChallengeResponse)
async def passkey_login_options(request: Request):
    """パスキーでのログインの options を作る（認証なし）。"""
    _require_issuance_enabled()
    _require_app_origin(request)
    ip = _get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail="too_many_attempts")
    options = passkeys.authentication_options()
    challenge_id = await passkeys.store_challenge("login", "-", options.challenge)
    return PasskeyChallengeResponse(challenge_id=challenge_id, options=json.loads(options_to_json(options)))


@router.post("/passkey/login/verify", response_model=SelfTokenResponse)
async def passkey_login_verify(
    data: PasskeyLoginVerify,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """パスキーの応答を確かめてログインさせる。失敗はどの理由でも同じ 401。"""
    _require_issuance_enabled()
    _require_app_origin(request)
    ip = _get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail="too_many_attempts")

    async def fail() -> HTTPException:
        await record_auth_failure(ip)
        return _invalid_credentials()

    challenge = await passkeys.take_challenge("login", "-", data.challenge_id)
    if challenge is None:
        raise await fail()
    try:
        parsed = parse_authentication_credential_json(data.credential)
    except (WebAuthnException, ValueError):
        raise await fail()

    cred = (
        await db.execute(
            text(
                "SELECT c.id, c.user_id, c.public_key, c.sign_count, u.email, u.tenant_id, u.is_active "
                "FROM public.webauthn_credentials c JOIN public.users u ON u.id = c.user_id "
                "WHERE c.credential_id = :cid"
            ),
            {"cid": parsed.raw_id},
        )
    ).first()
    if cred is None or not cred.is_active:
        raise await fail()
    # ライブラリは user handle を照らさないので、持ち主をここで確かめる
    if parsed.response.user_handle is None or parsed.response.user_handle != passkeys.user_handle(cred.user_id):
        raise await fail()

    # 使用回数はライブラリには照らさせず（0 を渡す）、署名が通った後に自分で照らす
    try:
        verified = verify_authentication_response(
            credential=parsed,
            expected_challenge=challenge,
            expected_rp_id=self_tokens.rp_id(),
            expected_origin=self_tokens.rp_origin(),
            credential_public_key=bytes(cred.public_key),
            credential_current_sign_count=0,
            require_user_verification=True,
        )
    except (WebAuthnException, ValueError):
        raise await fail()

    if passkeys.sign_count_rejected(cred.sign_count, verified.new_sign_count):
        await _record_auth_audit(
            db,
            tenant_id=cred.tenant_id,
            user_id=cred.user_id,
            action="update",
            table_name="webauthn_credentials",
            record_id=cred.id,
            new_data={
                "event": "passkey_sign_count_rejected",
                "stored": cred.sign_count,
                "received": verified.new_sign_count,
            },
        )
        await db.commit()
        raise await fail()

    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "UPDATE public.webauthn_credentials SET sign_count = :n, backup_state = :b, last_used_at = :now "
            "WHERE id = :id"
        ),
        {"n": verified.new_sign_count, "b": verified.credential_backed_up, "now": now, "id": cred.id},
    )
    await set_tenant_context(db, cred.tenant_id)
    await db.execute(
        text("UPDATE public.users SET last_login = :now WHERE id = :uid"),
        {"now": now, "uid": cred.user_id},
    )
    await clear_tenant_context(db)

    # D3: enforce のときだけ。パスキーは知らない機械でも入れて、その機械をいつもの機械に加える（メールで知らせる）
    trusted_device_id: int | None = None
    device_cookie_raw: str | None = None
    audit_reason, audit_new_device = "ok", None
    if devices.is_enforced():
        cookie_raw = request.cookies.get(devices.DEVICE_COOKIE_NAME)
        found = await devices.find_trusted_device(db, cred.user_id, cookie_raw)
        if found is not None:
            await devices.touch_device(db, found.id, request)
            trusted_device_id = found.id
            device_cookie_raw = devices.clean_cookie_value(cookie_raw)
            audit_new_device = False
        else:
            trusted_device_id, device_cookie_raw = await devices.register_device(
                db, cred.user_id, cookie_raw, "passkey", request
            )
            audit_reason, audit_new_device = "passkey_new_device", True
            background_tasks.add_task(
                send_new_device_mail,
                cred.email,
                when=devices.jst_text(),
                device=devices.describe_user_agent(request.headers.get("user-agent")),
                location=geo.lookup(ip),
                note="パスキーでログインし、この機械をいつもの機械に加えました。 / Signed in with a passkey; this device was added as a trusted device.",
            )
    family_id = str(uuid.uuid4())
    raw, expires_at = await self_tokens.issue_refresh_token(
        db,
        cred.user_id,
        request.headers.get("user-agent"),
        family_id=family_id,
        trusted_device_id=trusted_device_id,
    )
    await db.commit()
    access = _issue_session_tokens(response, raw, expires_at, cred.user_id, cred.email, "webauthn", family_id)
    if device_cookie_raw:
        devices.set_device_cookie(response, device_cookie_raw)
    _audit(request, user_id=cred.user_id, reason=audit_reason, is_new_device=audit_new_device)
    return SelfTokenResponse(
        access_token=access,
        token_type="bearer",
        expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS,
    )


@router.get("/passkeys", response_model=PasskeyList)
async def passkey_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """本人のパスキーの一覧。"""
    rows = (
        await db.execute(
            text(
                "SELECT id, label, created_at, last_used_at FROM public.webauthn_credentials "
                "WHERE user_id = :uid ORDER BY created_at"
            ),
            {"uid": current_user.id},
        )
    ).all()
    return PasskeyList(
        items=[
            PasskeyItem(
                id=r.id, label=r.label, created_at=_iso(r.created_at), last_used_at=_iso(r.last_used_at)
            )
            for r in rows
        ]
    )


@router.delete("/passkeys/{passkey_id}", status_code=204)
async def passkey_delete(
    passkey_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """本人のパスキーを 1 件消す。他人のものも「無い」と同じ 404。"""
    _require_app_origin(request)
    row = (
        await db.execute(
            text("DELETE FROM public.webauthn_credentials WHERE id = :id AND user_id = :uid RETURNING id"),
            {"id": passkey_id, "uid": current_user.id},
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="passkey_not_found")
    await clear_tenant_context(db)
    await _record_auth_audit(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="delete",
        table_name="webauthn_credentials",
        record_id=passkey_id,
        new_data={"event": "passkey_deleted"},
    )
    await db.commit()
    return Response(status_code=204)


# ── 新しい機械の許可（ADR-1055。知らない機械は、いつもの機械で許可するまで入れない） ──────────


class LoginRequestPollResponse(BaseModel):
    status: str = Field(description="pending・rejected・expired・completed。completed でトークンがあれば入れた")
    access_token: str | None = Field(default=None, description="入れたときだけ。自社アクセストークン（Bearer）")
    token_type: str | None = Field(default=None, description="トークン種別")
    expires_in: int | None = Field(default=None, description="アクセストークンの有効秒数")


class LoginRequestApprove(BaseModel):
    number: str = Field(min_length=1, max_length=8, description="待つ機械に出ている2けたの番号")


class LoginRequestDecision(BaseModel):
    status: str = Field(description="approved＝許可／rejected＝拒否")
    reason: str | None = Field(default=None, description="拒否の理由（wrong_number など）")


class LoginRequestRecovery(BaseModel):
    code: str = Field(min_length=1, max_length=64, description="予備の合言葉（ABCD-EFGHJ-KMNPQ の形）")


class DeviceItem(BaseModel):
    id: int = Field(description="機械の ID")
    label: str = Field(description="機械の種類（例 iPhone・Safari）")
    location: str | None = Field(default=None, description="場所の目安（IP Geolocation by DB-IP）")
    created_via: str = Field(description="登録の経路")
    created_at: str | None = Field(default=None, description="登録した日時")
    last_used_at: str | None = Field(default=None, description="最後に使った日時")
    is_current: bool = Field(description="いま使っている機械か")


class DeviceList(BaseModel):
    items: list[DeviceItem]


class RecoveryCodesStatus(BaseModel):
    remaining: int = Field(description="使える予備の合言葉の残り数")


class RecoveryCodesCreated(BaseModel):
    codes: list[str] = Field(description="作った予備の合言葉（このとき1回だけ見せる）")


async def _load_login_request(db: AsyncSession, request: Request):
    """Cookie sa_login_pending の hash で依頼を1件引く。無ければ None。"""
    raw = request.cookies.get(devices.PENDING_COOKIE_NAME)
    if not raw:
        return None
    return (
        await db.execute(
            text(
                "SELECT id, user_id, status, expires_at, decided_via, failed_code_attempts "
                "FROM public.auth_login_requests WHERE pending_token_hash = :h"
            ),
            {"h": devices.hash_value(raw)},
        )
    ).first()


def _pending_closed(status_value: str) -> JSONResponse:
    out = JSONResponse(status_code=200, content=LoginRequestPollResponse(status=status_value).model_dump())
    devices.clear_pending_cookie(out)
    return out


async def _complete_pending_login(
    db: AsyncSession,
    request: Request,
    response: Response,
    user_row,
    device_id: int,
    device_raw: str,
) -> SelfTokenResponse:
    """許可で入れたときの仕上げ。login と同じく失敗回数と停止を戻し、last_login を更新してトークンを出す。"""
    now = datetime.now(timezone.utc)
    await set_tenant_context(db, user_row.tenant_id)
    await db.execute(
        text(
            "UPDATE public.users SET failed_login_count = 0, locked_until = NULL, last_login = :now "
            "WHERE id = :id"
        ),
        {"now": now, "id": user_row.id},
    )
    await clear_tenant_context(db)
    family_id = str(uuid.uuid4())
    raw, expires_at = await self_tokens.issue_refresh_token(
        db,
        user_row.id,
        request.headers.get("user-agent"),
        family_id=family_id,
        trusted_device_id=device_id,
    )
    await db.commit()
    access = _issue_session_tokens(response, raw, expires_at, user_row.id, user_row.email, "pwd", family_id)
    devices.set_device_cookie(response, device_raw)
    devices.clear_pending_cookie(response)
    return SelfTokenResponse(
        access_token=access,
        token_type="bearer",
        expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS,
    )


@router.post("/login-requests/poll", response_model=LoginRequestPollResponse)
async def login_request_poll(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """待つ機械の確認（Cookie sa_login_pending だけで動く。画面は15秒ごと）。

    pending → そのまま。approved → 1回だけ（条件付き更新が通ったときだけ）印を登録してトークンを出す。
    rejected・expired → 状態を返して Cookie を消す。
    """
    _require_issuance_enabled()
    _require_app_origin(request)
    row = await _load_login_request(db, request)
    if row is None:
        return _pending_closed("expired")
    now = datetime.now(timezone.utc)
    state = row.status
    if state == "pending" and self_tokens._as_utc(row.expires_at) <= now:
        expired = (
            await db.execute(
                text(
                    "UPDATE public.auth_login_requests SET status = 'expired', decided_at = :now "
                    "WHERE id = :id AND status = 'pending' RETURNING id"
                ),
                {"now": now, "id": str(row.id)},
            )
        ).first()
        await db.commit()
        if expired is not None:
            await publish_user_change(row.user_id, TOPIC_AUTH_LOGIN_REQUEST)
        _audit(request, user_id=row.user_id, reason="expired")
        return _pending_closed("expired")
    if state == "pending":
        return LoginRequestPollResponse(status="pending")
    if state != "approved":
        return _pending_closed(state)

    # approved: 条件付き更新が1行返したときだけ発行する（同時の poll でも発行は1回）
    done = (
        await db.execute(
            text(
                "UPDATE public.auth_login_requests SET status = 'completed' "
                "WHERE id = :id AND status = 'approved' RETURNING id"
            ),
            {"id": str(row.id)},
        )
    ).first()
    if done is None:
        await db.rollback()
        return _pending_closed("completed")
    user_row = (
        await db.execute(
            text("SELECT id, email, tenant_id, is_active FROM public.users WHERE id = :id"),
            {"id": row.user_id},
        )
    ).first()
    if user_row is None or not user_row.is_active:
        await db.commit()
        return _pending_closed("rejected")
    via = "admin_approval" if row.decided_via == "admin" else "device_approval"
    device_id, device_raw = await devices.register_device(
        db, user_row.id, request.cookies.get(devices.DEVICE_COOKIE_NAME), via, request
    )
    issued = await _complete_pending_login(db, request, response, user_row, device_id, device_raw)
    _audit(
        request,
        user_id=user_row.id,
        reason="approved_admin" if row.decided_via == "admin" else "approved_device",
        is_new_device=True,
    )
    return LoginRequestPollResponse(
        status="completed",
        access_token=issued.access_token,
        token_type=issued.token_type,
        expires_in=issued.expires_in,
    )


@router.post("/login-requests/recovery", response_model=SelfTokenResponse)
async def login_request_recovery(
    data: LoginRequestRecovery,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """予備の合言葉で入る（待つ機械・Cookie sa_login_pending）。

    間違いは依頼の failed_code_attempts（5回で依頼を rejected）と口座の失敗回数の両方に数える。
    合えば合言葉を使用済みにし、印を登録（recovery_code）してトークンを出す。
    """
    _require_issuance_enabled()
    _require_app_origin(request)
    ip = _get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail="too_many_attempts")
    row = await _load_login_request(db, request)
    now = datetime.now(timezone.utc)
    if row is None:
        raise HTTPException(status_code=400, detail="request_not_found")
    if row.status != "pending" or self_tokens._as_utc(row.expires_at) <= now:
        raise HTTPException(status_code=400, detail="request_closed")
    user_row = (
        await db.execute(
            text(
                "SELECT id, email, tenant_id, is_active, failed_login_count, locked_until "
                "FROM public.users WHERE id = :id"
            ),
            {"id": row.user_id},
        )
    ).first()
    if user_row is None or not user_row.is_active:
        raise HTTPException(status_code=400, detail="request_closed")
    locked_until = self_tokens._as_utc(user_row.locked_until)
    locked = locked_until is not None and locked_until > now

    code_row_id = None
    if not locked:
        code_row_id = await recovery_codes.verify(db, user_row.id, data.code, request_id=str(row.id))
    else:
        await asyncio.to_thread(verify_password, None, data.code)
    if code_row_id is None:
        attempts = (
            await db.execute(
                text(
                    "UPDATE public.auth_login_requests SET failed_code_attempts = failed_code_attempts + 1 "
                    "WHERE id = :id AND status = 'pending' RETURNING failed_code_attempts"
                ),
                {"id": str(row.id)},
            )
        ).scalar_one_or_none()
        closed = attempts is not None and int(attempts) >= devices.RECOVERY_MAX_FAILED_ATTEMPTS
        if closed:
            await db.execute(
                text(
                    "UPDATE public.auth_login_requests SET status = 'rejected', decided_at = :now, "
                    "reject_reason = 'too_many_code_attempts' WHERE id = :id AND status = 'pending'"
                ),
                {"now": now, "id": str(row.id)},
            )
        # 口座の失敗回数にも数える（commit まで行う）
        await _count_login_failure(db, user_row, ip, now)
        if closed:
            await publish_user_change(user_row.id, TOPIC_AUTH_LOGIN_REQUEST)
        _audit(request, user_id=user_row.id, reason="recovery_code_wrong")
        raise HTTPException(status_code=400, detail="request_closed" if closed else "recovery_code_wrong")

    # 合った: 依頼を1回だけ completed にできたときだけ入れる（取れなければ合言葉も使わなかったことにする）
    done = (
        await db.execute(
            text(
                "UPDATE public.auth_login_requests SET status = 'completed', decided_via = 'recovery_code', "
                "decided_at = :now WHERE id = :id AND status = 'pending' AND expires_at > :now RETURNING id"
            ),
            {"now": now, "id": str(row.id)},
        )
    ).first()
    if done is None:
        await db.rollback()
        raise HTTPException(status_code=400, detail="request_closed")
    device_id, device_raw = await devices.register_device(
        db, user_row.id, request.cookies.get(devices.DEVICE_COOKIE_NAME), "recovery_code", request
    )
    issued = await _complete_pending_login(db, request, response, user_row, device_id, device_raw)
    await publish_user_change(user_row.id, TOPIC_AUTH_LOGIN_REQUEST)
    _audit(request, user_id=user_row.id, reason="approved_recovery", is_new_device=True)
    return issued


@router.post("/login-requests/{request_id}/approve", response_model=LoginRequestDecision)
async def login_request_approve(
    request_id: str,
    data: LoginRequestApprove,
    request: Request,
    session: CurrentSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    """いつもの機械で番号を選んで許可する（D1・D15）。正しい番号＝許可。違う番号＝その依頼だけ拒否（全ログアウトはしない）。

    本人の依頼だけを1行の条件付き更新で1回だけ決める。1行も返らなければ、id が無い・他人の依頼・決まり済みの
    どれでも 404（他人の依頼の有無を漏らさない）。取り消された機械の組からは 403 device_not_trusted。
    """
    _require_app_origin(request)
    rid = devices.parse_request_id(request_id)
    if rid is None:
        raise HTTPException(status_code=404, detail="not_found")
    if session.trusted_device_id is None:
        _audit(request, user_id=session.user.id, reason="device_not_trusted")
        raise HTTPException(status_code=403, detail="device_not_trusted")
    now = datetime.now(timezone.utc)
    decided = (
        await db.execute(
            text(
                "UPDATE public.auth_login_requests SET "
                "status = CASE WHEN match_number = :num THEN 'approved' ELSE 'rejected' END, "
                "reject_reason = CASE WHEN match_number = :num THEN NULL ELSE 'wrong_number' END, "
                "decided_at = :now, decided_via = 'device', decided_device_id = :dev "
                "WHERE id = :id AND user_id = :uid AND status = 'pending' AND expires_at > :now "
                "RETURNING status"
            ),
            {"num": data.number.strip(), "now": now, "dev": session.trusted_device_id, "id": rid, "uid": session.user.id},
        )
    ).first()
    if decided is None:
        raise HTTPException(status_code=404, detail="not_found")
    await db.commit()
    await publish_user_change(session.user.id, TOPIC_AUTH_LOGIN_REQUEST)
    if decided.status == "approved":
        _audit(request, user_id=session.user.id, reason="approved_device")
        return LoginRequestDecision(status="approved")
    _audit(request, user_id=session.user.id, reason="wrong_number")
    return LoginRequestDecision(status="rejected", reason="wrong_number")


@router.post("/login-requests/{request_id}/reject", response_model=LoginRequestDecision)
async def login_request_reject(
    request_id: str,
    request: Request,
    session: CurrentSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    """「私ではない」。待っていた機械は入れない。押した機械以外の組は全部ログアウト（K4）。"""
    _require_app_origin(request)
    rid = devices.parse_request_id(request_id)
    if rid is None:
        raise HTTPException(status_code=404, detail="not_found")
    if session.trusted_device_id is None:
        _audit(request, user_id=session.user.id, reason="device_not_trusted")
        raise HTTPException(status_code=403, detail="device_not_trusted")
    now = datetime.now(timezone.utc)
    decided = (
        await db.execute(
            text(
                "UPDATE public.auth_login_requests SET status = 'rejected', reject_reason = 'user_rejected', "
                "decided_at = :now, decided_via = 'device', decided_device_id = :dev "
                "WHERE id = :id AND user_id = :uid AND status = 'pending' AND expires_at > :now RETURNING id"
            ),
            {"now": now, "dev": session.trusted_device_id, "id": rid, "uid": session.user.id},
        )
    ).first()
    if decided is None:
        raise HTTPException(status_code=404, detail="not_found")
    await devices.revoke_user_sessions(db, session.user.id, except_family_id=session.sid)
    await db.commit()
    await publish_user_change(session.user.id, TOPIC_AUTH_LOGIN_REQUEST)
    _audit(request, user_id=session.user.id, reason="rejected")
    return LoginRequestDecision(status="rejected", reason="user_rejected")


@router.get("/devices", response_model=DeviceList)
async def device_list(
    session: CurrentSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    """本人の「ログインしている機械」の一覧（K8）。場所の目安の出どころは IP Geolocation by DB-IP。"""
    rows = (
        await db.execute(
            text(
                "SELECT id, label, user_agent, created_via, created_at, last_used_at, last_location, created_location "
                "FROM public.user_trusted_devices WHERE user_id = :uid AND revoked_at IS NULL "
                "ORDER BY COALESCE(last_used_at, created_at) DESC"
            ),
            {"uid": session.user.id},
        )
    ).all()
    return DeviceList(
        items=[
            DeviceItem(
                id=r.id,
                label=r.label or devices.describe_user_agent(r.user_agent),
                location=r.last_location or r.created_location,
                created_via=r.created_via,
                created_at=_iso(r.created_at),
                last_used_at=_iso(r.last_used_at),
                is_current=(r.id == session.trusted_device_id),
            )
            for r in rows
        ]
    )


@router.delete("/devices/{device_id}", status_code=204)
async def device_revoke(
    device_id: int,
    request: Request,
    session: CurrentSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    """本人の機械を取り消す。結び付いた組は失効し、その機械のアクセストークンも次の要求で 401。他人の id は 404。"""
    _require_app_origin(request)
    if not await devices.revoke_device(db, session.user.id, device_id):
        raise HTTPException(status_code=404, detail="not_found")
    await db.commit()
    return Response(status_code=204)


@router.get("/recovery-codes/status", response_model=RecoveryCodesStatus)
async def recovery_codes_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """予備の合言葉の残り数。"""
    return RecoveryCodesStatus(remaining=await recovery_codes.remaining(db, current_user.id))


@router.post("/recovery-codes", response_model=RecoveryCodesCreated)
async def recovery_codes_create(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """予備の合言葉を10個作る（作り直しもここ。古い未使用は無効になる）。生の値はこの応答の1回だけ。"""
    _require_app_origin(request)
    codes = await recovery_codes.generate(db, current_user.id)
    await _record_auth_audit(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="create",
        table_name="user_recovery_codes",
        record_id=None,
        new_data={"event": "recovery_codes_created", "count": len(codes)},
    )
    await db.commit()
    return RecoveryCodesCreated(codes=codes)
