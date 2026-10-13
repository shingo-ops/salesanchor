from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import self_tokens
from app.auth.dependencies import _get_client_ip, require_super_admin, set_tenant_context
from app.auth.passwords import hash_password, needs_rehash, verify_password
from app.auth.schemas import UserRegister, UserResponse
from app.auth.utils import set_tenant_claim
from app.cache import (
    blacklist_token,
    check_auth_rate_limit,
    invalidate_user_permissions,
    record_auth_failure,
)
from app.database import get_db
from app.models import Tenant, User
from app.services.audit import record_audit_log

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    ユーザー登録API（super admin のみ実行可能）。

    フロー:
      ① super admin 権限を確認
      ② tenant_codeからテナントを検索
      ③ 同じメールアドレスのユーザーがいないか確認（いれば409）
      ④ usersテーブルにユーザーを作成
      ⑤ Firebaseカスタムクレームにテナントを設定

    注意:
      - 認証は Firebase Authentication が担当。DB にパスワードは保存しない。
    """
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

    # メールアドレスの重複チェック
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このメールアドレスは既に登録されています",
        )

    # ユーザー作成（認証は Firebase が担当、DB にパスワードは保存しない）
    user = User(
        tenant_id=tenant.id,
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()

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

    # FirebaseカスタムクレームにテナントIDを埋め込み（同期APIをスレッドで実行）
    import asyncio
    try:
        await asyncio.to_thread(set_tenant_claim, data.firebase_uid, tenant.id)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase連携に失敗しました。再度お試しください",
        )

    await db.commit()
    await db.refresh(user)

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
                "SELECT id, email, is_active, password_argon2_hash, failed_login_count, locked_until "
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
        await db.commit()
        await record_auth_failure(ip)
        raise _invalid_credentials()

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
