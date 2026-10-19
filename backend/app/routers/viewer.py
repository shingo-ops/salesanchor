"""閲覧専用ページの API（ADR-1019 段2・設計 D1/D2）。

POST /login・POST /logout・GET /inventory・POST /password・POST /password-reset/request・
POST /password-reset/confirm・POST /signup の7本。
アプリの get_current_user とは別の経路で、Redis の jwt: 名前空間（キャッシュ関数）は使わない。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import self_tokens
from app.auth.password_policy import check_password
from app.auth.passwords import hash_password, verify_password
from app.auth.viewer_dependencies import (
    get_current_viewer,
    require_viewer_password_ok,
    viewer_security,
)
from app.auth.viewer_email import normalize_viewer_email
from app.auth.viewer_signup_code import format_signup_code, generate_signup_code
from app.auth.viewer_tokens import create_viewer_access_token, decode_viewer_token
from app.cache import (
    AUTH_FAIL_LOCKOUT_TTL,
    AUTH_FAIL_MAX,
    PASSWORD_RESET_REQUEST_MAX,
    VIEWER_SIGNUP_EMAIL_MAX,
    VIEWER_SIGNUP_IP_MAX,
    blacklist_token,
    check_auth_rate_limit,
    count_viewer_password_reset_request,
    count_viewer_signup,
    get_redis,
    record_auth_failure,
)
from app.client_ip import get_client_ip
from app.database import get_db
from app.routers.auth import PASSWORD_RESET_TTL, _require_app_origin
from app.services.auth_mail import send_viewer_password_reset_email
from app.services.viewer_invite import create_viewer_invite
from app.services.viewer_signup import SIGNUP_CODE_TTL, replace_signup_code
from app.tasks.viewer_inventory_cache import CACHE_KEY

router = APIRouter()
logger = logging.getLogger(__name__)

TOO_MANY = "viewer_too_many_attempts"
INVALID_CREDENTIALS = "viewer_invalid_credentials"
INVALID_CURRENT_PASSWORD = "viewer_invalid_current_password"
RESET_INVALID_OR_EXPIRED = "viewer_reset_invalid_or_expired"
# 再発行メールを送ってよい状態（pending・verified・suspended には送らない）
_RESET_MAIL_STATUSES = ("trial", "active")


class ViewerLoginRequest(BaseModel):
    email: str = Field(max_length=320, description="ログインに使うメールアドレス")
    password: str = Field(max_length=256, description="パスワード")


class ViewerPasswordChangeRequest(BaseModel):
    current_password: str = Field(max_length=256, description="今のパスワード")
    new_password: str = Field(max_length=256, description="新しいパスワード（15〜64 文字）")


class ViewerPasswordResetRequest(BaseModel):
    email: str = Field(max_length=320, description="再発行したいメールアドレス")


class ViewerPasswordResetConfirmRequest(BaseModel):
    token: str = Field(max_length=256, description="再発行メールのリンクに入っている鍵")
    new_password: str = Field(max_length=256, description="新しいパスワード（15〜64 文字）")


class ViewerSignupRequest(BaseModel):
    email: str = Field(max_length=254, description="メールアドレス")
    line_name: str = Field(max_length=200, description="LINE の表示名（前後の空白を除いて1〜100文字）")
    inventory_issue: str | None = Field(default=None, max_length=1000, description="在庫関連の課題（任意）")
    website: str | None = Field(default=None, max_length=200, description="ボット対策の隠し欄。人は空のまま")


def _normalize_or_none(raw: str) -> str | None:
    try:
        return normalize_viewer_email(raw)
    except ValueError:
        return None


def _email_fail_key(email: str) -> str:
    normalized = _normalize_or_none(email)
    basis = normalized if normalized is not None else email.strip().lower()
    return "viewer_login_fail:" + hashlib.sha256(basis.encode()).hexdigest()


async def _record_event(db: AsyncSession, viewer_id: int, event_type: str, ip: str, user_agent: str | None) -> None:
    await db.execute(
        text(
            "INSERT INTO public.viewer_login_events (viewer_id, event_type, client_ip, user_agent) "
            "VALUES (:viewer_id, :event_type, :ip, :ua)"
        ),
        {
            "viewer_id": viewer_id,
            "event_type": event_type,
            "ip": ip[:45],
            "ua": (user_agent or "")[:500] or None,
        },
    )


async def _email_locked(key: str) -> bool:
    r = get_redis()
    if not r:
        return False
    try:
        return int(await r.get(key) or 0) >= AUTH_FAIL_MAX
    except Exception:
        logger.warning("viewer login: email 単位の回数確認に失敗（fail-open）")
        return False


async def _email_failure(key: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, AUTH_FAIL_LOCKOUT_TTL)
    except Exception:
        logger.warning("viewer login: email 単位の失敗記録に失敗")


async def _email_clear(key: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        await r.delete(key)
    except Exception:
        logger.warning("viewer login: email 単位の回数消去に失敗")


@router.post("/login")
async def viewer_login(
    data: ViewerLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """閲覧者のログイン。失敗の理由は区別せず 1 種類の文言で返す（停止中・期限切れは正しいパスワードのときだけ別）。"""
    _require_app_origin(request)
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail=TOO_MANY)
    fail_key = _email_fail_key(data.email)
    if await _email_locked(fail_key):
        raise HTTPException(status_code=429, detail=TOO_MANY)

    email = _normalize_or_none(data.email)
    row = None
    if email is not None:
        row = (
            await db.execute(
                text(
                    "SELECT id, status, password_argon2_hash, password_must_change, trial_expires_at "
                    "FROM public.viewer_accounts WHERE lower(email) = :email"
                ),
                {"email": email},
            )
        ).first()

    password_ok = False
    if row is None or row.password_argon2_hash is None:
        await asyncio.to_thread(verify_password, None, data.password)
    else:
        password_ok = await asyncio.to_thread(verify_password, row.password_argon2_hash, data.password)

    if row is not None and password_ok and row.status in ("suspended", "trial", "active"):
        if row.status == "suspended":
            await _record_event(db, row.id, "login_failed", ip, user_agent)
            await db.commit()
            raise HTTPException(status_code=403, detail="viewer_suspended")
        if row.status == "trial":
            expires = row.trial_expires_at
            if expires is not None and expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires is None or expires <= datetime.now(timezone.utc):
                await _record_event(db, row.id, "login_failed", ip, user_agent)
                await db.commit()
                raise HTTPException(status_code=403, detail="viewer_trial_expired")
        token, exp = create_viewer_access_token(row.id)
        await _record_event(db, row.id, "login_succeeded", ip, user_agent)
        await db.commit()
        await _email_clear(fail_key)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": exp.isoformat(),
            "must_change_password": bool(row.password_must_change),
        }

    # 失敗扱い: 行が無い・ハッシュが NULL・パスワード違い・pending／verified／未知の status
    await record_auth_failure(ip)
    await _email_failure(fail_key)
    if row is not None:
        await _record_event(db, row.id, "login_failed", ip, user_agent)
        await db.commit()
    raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)


@router.post("/logout")
async def viewer_logout(
    cred: HTTPAuthorizationCredentials = Depends(viewer_security),
    viewer: dict = Depends(get_current_viewer),
):
    """ログアウト。パスワード変更前の人もできる（require_viewer_password_ok ではなく get_current_viewer）。"""
    claims = decode_viewer_token(cred.credentials)
    ttl = max(1, int(claims["exp"]) - int(time.time()))
    if not await blacklist_token(cred.credentials, ttl=ttl):
        raise HTTPException(status_code=503, detail="logout_unavailable")
    return {"ok": True}


@router.get("/inventory")
async def viewer_inventory(viewer: dict = Depends(require_viewer_password_ok)):
    """作り置きの在庫の JSON をそのまま返す（読み直して組み立てない）。"""
    r = get_redis()
    value = None
    if r:
        try:
            value = await r.get(CACHE_KEY)
        except Exception:
            logger.warning("viewer inventory: 作り置きの読み出しに失敗")
    if not value:
        raise HTTPException(status_code=503, detail="viewer_inventory_not_ready")
    return Response(content=value, media_type="application/json", headers={"Cache-Control": "no-store"})


_SET_PASSWORD_SQL = (
    "UPDATE public.viewer_accounts SET password_argon2_hash = :h, password_must_change = false, "
    "password_changed_at = :now, updated_at = :now WHERE id = :id"
)


@router.post("/password")
async def viewer_change_password(
    data: ViewerPasswordChangeRequest,
    request: Request,
    viewer: dict = Depends(get_current_viewer),
    db: AsyncSession = Depends(get_db),
):
    """パスワードの変更。must_change の人も呼べる（require_viewer_password_ok ではなく get_current_viewer）。

    変更後、それより前に出したトークンは使えなくなるので、新しいトークンを返す。
    """
    ip = get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail=TOO_MANY)

    row = (
        await db.execute(
            text("SELECT password_argon2_hash FROM public.viewer_accounts WHERE id = :id"),
            {"id": viewer["id"]},
        )
    ).first()
    stored = row.password_argon2_hash if row is not None else None
    current_ok = await asyncio.to_thread(verify_password, stored, data.current_password)
    if not current_ok:
        await record_auth_failure(ip)
        raise HTTPException(status_code=401, detail=INVALID_CURRENT_PASSWORD)

    reason = check_password(data.new_password)
    if reason is not None:
        raise HTTPException(status_code=422, detail=reason)
    if data.new_password == data.current_password:
        raise HTTPException(status_code=422, detail="password_same_as_current")

    new_hash = await asyncio.to_thread(hash_password, data.new_password)
    now = datetime.now(timezone.utc)  # トークンを作る前に取る（iat は秒の整数で、これの切り捨て以上になる）
    await db.execute(text(_SET_PASSWORD_SQL), {"h": new_hash, "now": now, "id": viewer["id"]})
    await _record_event(db, viewer["id"], "password_changed", ip, request.headers.get("user-agent"))
    await db.commit()
    token, exp = create_viewer_access_token(viewer["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": exp.isoformat(),
        "must_change_password": False,
    }


@router.post("/password-reset/request")
async def viewer_password_reset_request(
    data: ViewerPasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """再発行メールの申請。登録の有無・状態を応答に出さない（常に 200）。"""
    _require_app_origin(request)
    accepted = {"status": "accepted"}
    email = _normalize_or_none(data.email)
    if email is None:
        return accepted
    if await count_viewer_password_reset_request(email) > PASSWORD_RESET_REQUEST_MAX:
        return accepted  # 429 にしない（回数を超えたことも知らせない）

    row = (
        await db.execute(
            text(
                "SELECT id, email, status, trial_expires_at FROM public.viewer_accounts "
                "WHERE lower(email) = :email"
            ),
            {"email": email},
        )
    ).first()
    if row is None or row.status not in _RESET_MAIL_STATUSES:
        return accepted

    now = datetime.now(timezone.utc)
    await db.execute(
        text("DELETE FROM public.viewer_login_tokens WHERE viewer_account_id = :id AND purpose = 'password_reset'"),
        {"id": row.id},
    )
    raw = secrets.token_urlsafe(32)
    await db.execute(
        text(
            "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
            "VALUES (:id, :h, 'password_reset', :exp)"
        ),
        {"id": row.id, "h": hashlib.sha256(raw.encode()).digest(), "exp": now + PASSWORD_RESET_TTL},
    )
    await _record_event(
        db, row.id, "password_reset_requested", get_client_ip(request), request.headers.get("user-agent")
    )
    await db.commit()
    reset_url = f"{self_tokens.rp_origin()}/viewer/#reset={raw}"
    background_tasks.add_task(send_viewer_password_reset_email, row.email, reset_url)
    return accepted


@router.post("/password-reset/confirm")
async def viewer_password_reset_confirm(
    data: ViewerPasswordResetConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """新しいパスワードの確定。鍵は 1 回だけ・期限内だけ使える。12 時間トークンは返さない（ログインし直す）。"""
    _require_app_origin(request)
    ip = get_client_ip(request)
    if await check_auth_rate_limit(ip):
        raise HTTPException(status_code=429, detail=TOO_MANY)

    reason = check_password(data.new_password)
    if reason is not None:
        raise HTTPException(status_code=422, detail=reason)  # 鍵はまだ消費しない

    now = datetime.now(timezone.utc)
    token_row = (
        await db.execute(
            text(
                "DELETE FROM public.viewer_login_tokens "
                "WHERE token_sha256 = :h AND purpose = 'password_reset' AND expires_at > :now "
                "RETURNING viewer_account_id"
            ),
            {"h": hashlib.sha256(data.token.encode()).digest(), "now": now},
        )
    ).first()
    if token_row is None:
        await record_auth_failure(ip)
        raise HTTPException(status_code=400, detail=RESET_INVALID_OR_EXPIRED)

    account = (
        await db.execute(
            text("SELECT id, status FROM public.viewer_accounts WHERE id = :id"),
            {"id": token_row.viewer_account_id},
        )
    ).first()
    if account is None or account.status not in _RESET_MAIL_STATUSES:
        await db.commit()  # 鍵は消費済みのまま
        raise HTTPException(status_code=400, detail=RESET_INVALID_OR_EXPIRED)

    new_hash = await asyncio.to_thread(hash_password, data.new_password)
    await db.execute(text(_SET_PASSWORD_SQL), {"h": new_hash, "now": now, "id": account.id})
    await _record_event(db, account.id, "password_reset_done", ip, request.headers.get("user-agent"))
    await db.commit()
    return {"status": "password_updated"}


_SIGNUP_INVALID = "viewer_signup_invalid"


def _signup_response(code: str, expires_at: datetime, invite_url: str | None) -> dict:
    return {"signup_code": format_signup_code(code), "expires_at": expires_at.isoformat(), "invite_url": invite_url}


async def _find_viewer(db: AsyncSession, email: str):
    return (
        await db.execute(
            text("SELECT id, status FROM public.viewer_accounts WHERE lower(email) = :email"),
            {"email": email},
        )
    ).first()


@router.post("/signup")
async def viewer_signup(
    data: ViewerSignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """申込。pending の行と申込コード（DB には sha256 だけ）を作り、コードとその人専用の招待リンクを返す。

    応答の形は、新規・pending の再申込・登録済み（捨てのコード）・隠し欄ありで同じ。ログに email・コード・招待を出さない。
    """
    _require_app_origin(request)
    email = _normalize_or_none(data.email)
    line_name = data.line_name.strip()
    if email is None or not 1 <= len(line_name) <= 100:
        raise HTTPException(status_code=422, detail=_SIGNUP_INVALID)
    issue = (data.inventory_issue or "").strip() or None

    ip = get_client_ip(request)
    n_ip = await count_viewer_signup("ip", ip)
    if n_ip is not None and n_ip > VIEWER_SIGNUP_IP_MAX:
        raise HTTPException(status_code=429, detail=TOO_MANY)
    n_mail = await count_viewer_signup("email", email)
    if n_mail is not None and n_mail > VIEWER_SIGNUP_EMAIL_MAX:
        raise HTTPException(status_code=429, detail=TOO_MANY)
    limits_ok = n_ip is not None and n_mail is not None  # 数えられないときは申込は通すが、招待は作らない

    code = generate_signup_code()
    expires_at = datetime.now(timezone.utc) + SIGNUP_CODE_TTL

    if (data.website or "").strip():
        return _signup_response(code, expires_at, None)  # ボットに入口を渡さない（行も招待も作らない）

    user_exists = (
        await db.execute(text("SELECT 1 FROM public.users WHERE lower(email) = :email"), {"email": email})
    ).first()
    if user_exists is None:
        row = await _find_viewer(db, email)
        viewer_id: int | None = None
        if row is None:
            inserted = (
                await db.execute(
                    text(
                        "INSERT INTO public.viewer_accounts (email, line_name, inventory_issue, status) "
                        "VALUES (:email, :line_name, :issue, 'pending') ON CONFLICT DO NOTHING RETURNING id"
                    ),
                    {"email": email, "line_name": line_name, "issue": issue},
                )
            ).first()
            if inserted is not None:
                viewer_id = inserted.id
            else:  # 同時の申込に先を越された
                row = await _find_viewer(db, email)
        if viewer_id is None and row is not None and row.status == "pending":
            viewer_id = row.id
        if viewer_id is not None:
            code, expires_at = await replace_signup_code(db, viewer_id)
            await _record_event(db, viewer_id, "signup", ip, request.headers.get("user-agent"))
            await db.commit()
        # それ以外（pending 以外の状態）は捨てのコード。DB は書かない

    invite_url = await create_viewer_invite(db) if limits_ok else None  # commit の後（Discord を待つ間 DB を開けない）
    return _signup_response(code, expires_at, invite_url)
