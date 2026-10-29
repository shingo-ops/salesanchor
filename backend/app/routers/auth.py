from __future__ import annotations

import asyncio
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import self_tokens
from app.auth.dependencies import (
    _get_client_ip,
    clear_tenant_context,
    get_current_user,
    require_super_admin,
    set_tenant_context,
)
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
from app.schemas.auth import PasswordChange
from app.services.audit import record_audit_log
from app.services.auth_mail import send_invite_email, send_password_reset_email
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
    await record_audit_log(
        db=db,
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


def _require_app_origin(request: Request) -> None:
    if request.headers.get("origin") != self_tokens.rp_origin():
        raise HTTPException(status_code=403, detail="forbidden_origin")


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


def _clear_refresh_cookie(response: Response | JSONResponse) -> None:
    response.delete_cookie(
        self_tokens.REFRESH_COOKIE_NAME,
        path=self_tokens.REFRESH_COOKIE_PATH,
        secure=self_tokens.cookie_secure(),
        httponly=True,
        samesite="strict",
    )


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


@router.post("/login", response_model=SelfTokenResponse)
async def self_login(
    data: SelfLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """自社ログイン。失敗理由は区別せず 1 種類の文言で返す。"""
    _require_issuance_enabled()
    _require_app_origin(request)
    ip = _get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail="too_many_attempts")

    now = datetime.now(timezone.utc)
    email = data.email.strip().lower()
    user_row = (
        await db.execute(
            text(
                "SELECT id, email, tenant_id, is_active, password_argon2_hash, failed_login_count, locked_until "
                "FROM public.users WHERE lower(email) = :email"
            ),
            {"email": email},
        )
    ).first()
    locked_until = self_tokens._as_utc(user_row.locked_until) if user_row else None
    if user_row is None or not user_row.is_active or (locked_until is not None and locked_until > now):
        await asyncio.to_thread(verify_password, None, data.password)
        await record_auth_failure(ip)
        raise _invalid_credentials()

    if not await asyncio.to_thread(verify_password, user_row.password_argon2_hash, data.password):
        await _count_login_failure(db, user_row, ip, now)
        raise _invalid_credentials()

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
    raw, expires_at = await self_tokens.issue_refresh_token(
        db, user_row.id, request.headers.get("user-agent")
    )
    await db.commit()
    _set_refresh_cookie(response, raw, expires_at)
    return SelfTokenResponse(
        access_token=self_tokens.create_access_token(user_row.id, user_row.email, "pwd"),
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
    user_id, new_raw, expires_at = rotated
    email = (
        await db.execute(text("SELECT email FROM public.users WHERE id = :id"), {"id": user_id})
    ).scalar_one()
    await db.commit()
    _set_refresh_cookie(response, new_raw, expires_at)
    return SelfTokenResponse(
        access_token=self_tokens.create_access_token(user_id, email, None),
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
    await db.execute(
        text(
            "UPDATE public.auth_refresh_tokens SET revoked_at = :now "
            "WHERE user_id = :uid AND revoked_at IS NULL"
        ),
        {"now": now, "uid": user_row.id},
    )
    await record_audit_log(
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
    await db.execute(
        text(
            "UPDATE public.auth_refresh_tokens SET revoked_at = :now "
            "WHERE user_id = :uid AND revoked_at IS NULL"
        ),
        {"now": now, "uid": user_row.id},
    )
    await record_audit_log(
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
        raw, expires_at = await self_tokens.issue_refresh_token(
            db, user_row.id, request.headers.get("user-agent")
        )
        await db.commit()
        _set_refresh_cookie(response, raw, expires_at)
        issued = PasswordChangeResponse(
            status="password_updated",
            access_token=self_tokens.create_access_token(user_row.id, user_row.email, "pwd"),
            token_type="bearer",
            expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS,
        )
    else:
        await db.commit()
        issued = PasswordChangeResponse(status="password_updated")
    return issued
