"""閲覧専用ページの API（ADR-1019 段2・設計 D1/D2）。

POST /login・POST /logout・GET /inventory の3本。signup・password・password-reset は段4。
アプリの get_current_user とは別の経路で、Redis の jwt: 名前空間（キャッシュ関数）は使わない。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import verify_password
from app.auth.viewer_dependencies import (
    get_current_viewer,
    require_viewer_password_ok,
    viewer_security,
)
from app.auth.viewer_email import normalize_viewer_email
from app.auth.viewer_tokens import create_viewer_access_token, decode_viewer_token
from app.cache import (
    AUTH_FAIL_LOCKOUT_TTL,
    AUTH_FAIL_MAX,
    blacklist_token,
    check_auth_rate_limit,
    get_redis,
    record_auth_failure,
)
from app.database import get_db
from app.routers.auth import _require_app_origin
from app.tasks.viewer_inventory_cache import CACHE_KEY

router = APIRouter()
logger = logging.getLogger(__name__)

TOO_MANY = "viewer_too_many_attempts"
INVALID_CREDENTIALS = "viewer_invalid_credentials"


class ViewerLoginRequest(BaseModel):
    email: str = Field(max_length=320, description="ログインに使うメールアドレス")
    password: str = Field(max_length=256, description="パスワード")


def _client_ip(request: Request) -> str:
    """X-Real-IP の値。X-Forwarded-For は読まない（偽装できるため）。"""
    real = (request.headers.get("x-real-ip") or "").strip()
    if real:
        return real
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


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
    ip = _client_ip(request)
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
