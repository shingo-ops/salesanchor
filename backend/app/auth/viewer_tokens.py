"""閲覧専用アカウントのトークン（ADR-1019 段1）。

アプリのトークン（self_tokens.py・iss=salesanchor）とは、発行者（iss）も鍵も別。
鍵は呼び出し時に毎回環境変数から読む（テストの setenv を効かせるため）。
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from jose import JWTError, jwt

VIEWER_ISSUER = "salesanchor-viewer"
VIEWER_TOKEN_TTL_SECONDS = 12 * 3600
_ALGORITHM = "HS256"  # self_tokens.py と同じ


def _secret() -> str:
    return os.getenv("AUTH_VIEWER_JWT_SECRET", "")


def create_viewer_access_token(viewer_id: int) -> tuple[str, datetime]:
    secret = _secret()
    if not secret:
        raise JWTError("AUTH_VIEWER_JWT_SECRET is not set")
    iat = int(time.time())
    exp = iat + VIEWER_TOKEN_TTL_SECONDS
    claims = {
        "iss": VIEWER_ISSUER,
        "sub": f"viewer:{viewer_id}",
        "iat": iat,
        "exp": exp,
    }
    token = jwt.encode(claims, secret, algorithm=_ALGORITHM)
    return token, datetime.fromtimestamp(exp, timezone.utc)


def decode_viewer_token(token: str) -> dict:
    secret = _secret()
    if not secret:
        raise JWTError("AUTH_VIEWER_JWT_SECRET is not set")
    return jwt.decode(
        token,
        secret,
        algorithms=[_ALGORITHM],
        issuer=VIEWER_ISSUER,
        options={
            "require_exp": True,
            "require_iat": True,
            "require_sub": True,
            "require_iss": True,
        },
    )
