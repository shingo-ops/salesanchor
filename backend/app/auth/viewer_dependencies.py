"""閲覧者を確かめる dependency（ADR-1019 段1）。

アプリの get_current_user とは別の経路。Redis の jwt: 名前空間（cache_jwt_result・get_cached_jwt）は使わない。
毎回 DB の1行を主キーで読む（キャッシュしない）。
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.viewer_tokens import decode_viewer_token
from app.cache import is_token_blacklisted
from app.database import get_db

viewer_security = HTTPBearer()

_SUB_RE = re.compile(r"^viewer:(\d+)$")
_INVALID = "invalid viewer token"


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _as_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


async def _load_viewer_row(db: AsyncSession, viewer_id: int):
    return (
        await db.execute(
            text(
                "SELECT id, email, status, password_must_change, password_changed_at, trial_expires_at "
                "FROM public.viewer_accounts WHERE id = :id"
            ),
            {"id": viewer_id},
        )
    ).first()


async def get_current_viewer(
    cred: HTTPAuthorizationCredentials = Depends(viewer_security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    token = cred.credentials
    if await is_token_blacklisted(token):
        raise _unauthorized()
    try:
        claims = decode_viewer_token(token)
    except (JWTError, ValueError, KeyError, TypeError):
        raise _unauthorized()

    match = _SUB_RE.match(str(claims.get("sub", "")))
    iat = claims.get("iat")
    if match is None or not isinstance(iat, int) or isinstance(iat, bool):
        raise _unauthorized()
    viewer_id = int(match.group(1))

    row = await _load_viewer_row(db, viewer_id)
    if row is None:
        raise _unauthorized()

    changed_at = _as_utc(row.password_changed_at)
    if changed_at is not None and iat < math.floor(changed_at.timestamp()):
        raise _unauthorized()

    now = datetime.now(timezone.utc)
    if row.status == "active":
        pass
    elif row.status == "trial":
        expires = _as_utc(row.trial_expires_at)
        if expires is None or expires <= now:
            raise _forbidden("viewer_trial_expired")
    elif row.status == "suspended":
        raise _forbidden("viewer_suspended")
    else:  # pending・verified・未知の値
        raise _forbidden("viewer_pending")

    return {
        "id": row.id,
        "email": row.email,
        "status": row.status,
        "password_must_change": bool(row.password_must_change),
        "trial_expires_at": _as_utc(row.trial_expires_at),
    }


async def require_viewer_password_ok(viewer: dict = Depends(get_current_viewer)) -> dict:
    if viewer["password_must_change"]:
        raise _forbidden("password_change_required")
    return viewer
