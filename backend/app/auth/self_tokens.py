"""自社ログインのトークン（アクセストークン・更新用トークン）。ADR-1013 便2。

環境変数は import 時に固定せず、呼び出し時に読む（テストの setenv を効かせるため）。
更新用トークンの表 public.auth_refresh_tokens は models.py に載せず、生 SQL で読み書きする
（migration-guard チェック1 を避けるため）。
"""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_AUTH_PROVIDER = "firebase"  # firebase | self
DEFAULT_RP_ORIGIN = "https://app.salesanchor.jp"
DEFAULT_RP_ID = "app.salesanchor.jp"
ISSUER = "salesanchor"
ACCESS_TOKEN_TTL_SECONDS = 900
REFRESH_ABSOLUTE_TTL = timedelta(days=30)
REFRESH_COOKIE_NAME = "sa_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"
MIN_SECRET_LENGTH = 32
LOGIN_FAIL_LIMIT = 10
LOGIN_LOCK_DURATION = timedelta(minutes=15)

_VALID_PROVIDERS = ("firebase", "self")
_ALGORITHM = "HS256"


# ── 設定の読み取り（毎回 os.getenv） ─────────────────────────────

def auth_provider() -> str:
    return os.getenv("AUTH_PROVIDER", DEFAULT_AUTH_PROVIDER).strip().lower()


def _secret() -> str:
    return os.getenv("AUTH_JWT_SECRET", "")


def _secret_previous() -> str:
    return os.getenv("AUTH_JWT_SECRET_PREVIOUS", "")


def rp_origin() -> str:
    return os.getenv("AUTH_RP_ORIGIN", DEFAULT_RP_ORIGIN)


def rp_id() -> str:
    """パスキーが結びつくドメイン（design.md:85。後から変えると登録済みのパスキーが全部使えなくなる）。"""
    return os.getenv("AUTH_RP_ID", DEFAULT_RP_ID)


def cookie_secure() -> bool:
    return os.getenv("AUTH_COOKIE_SECURE", "true").strip().lower() != "false"


def _kid(secret: str) -> str:
    """鍵そのものを出さずに鍵を見分ける印。"""
    return hashlib.sha256(secret.encode()).hexdigest()[:8]


def is_issuance_enabled() -> bool:
    """login・refresh・passkey/login を有効にするか。"""
    return auth_provider() == "self" and bool(_secret())


def is_verification_enabled() -> bool:
    """自社トークンを受け付けるか（秘密があれば受ける）。"""
    return bool(_secret())


def validate_settings() -> None:
    """起動時検査。メッセージに秘密の値は入れない。"""
    provider = auth_provider()
    if provider not in _VALID_PROVIDERS:
        raise RuntimeError("AUTH_PROVIDER must be one of: firebase, self")
    if provider == "self" and not _secret():
        raise RuntimeError("AUTH_JWT_SECRET is required when AUTH_PROVIDER=self")
    for name, value in (("AUTH_JWT_SECRET", _secret()), ("AUTH_JWT_SECRET_PREVIOUS", _secret_previous())):
        if value and len(value) < MIN_SECRET_LENGTH:
            raise RuntimeError(f"{name} must be at least {MIN_SECRET_LENGTH} characters")


# ── アクセストークン ───────────────────────────────────────────

def create_access_token(user_id: int, email: str, amr: str | None, sid: str | None = None) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    claims: dict = {
        "iss": ISSUER,
        "sub": str(user_id),
        "email": email,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL_SECONDS,
    }
    if amr is not None:
        claims["amr"] = [amr]
    if sid is not None:
        # 更新トークンの組の id（ADR-1055 D8）。組を失効させたとき、このアクセストークンも即座に拒むための印
        claims["sid"] = sid
    return jwt.encode(claims, _secret(), algorithm=_ALGORITHM, headers={"kid": _kid(_secret())})


def peek_issuer(token: str) -> str | None:
    """振り分けにだけ使う（署名は見ていないので信用しない）。"""
    try:
        iss = jwt.get_unverified_claims(token).get("iss")
    except Exception:
        return None
    return iss if isinstance(iss, str) else None


def decode_access_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    current, previous = _secret(), _secret_previous()
    if current and kid == _kid(current):
        key = current
    elif previous and kid == _kid(previous):
        key = previous
    else:
        raise JWTError("unknown kid")
    return jwt.decode(
        token,
        key,
        algorithms=[_ALGORITHM],
        issuer=ISSUER,
        options={
            "require_exp": True,
            "require_iat": True,
            "require_sub": True,
            "require_jti": True,
            "require_iss": True,
        },
    )


# ── 更新用トークン ─────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()


def _as_utc(value: datetime | str | None) -> datetime | None:
    """SQLite は text() の結果を str で返すため、比較の前に必ず通す。"""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


async def issue_refresh_token(
    db: AsyncSession,
    user_id: int,
    user_agent: str | None,
    family_id: str | None = None,
    family_created_at: datetime | None = None,
    trusted_device_id: int | None = None,
) -> tuple[str, datetime]:
    now = _now()
    family = family_id or str(uuid.uuid4())
    family_start = family_created_at or now
    expires_at = family_start + REFRESH_ABSOLUTE_TTL
    raw = secrets.token_urlsafe(32)
    ua_hash = hashlib.sha256(user_agent.encode()).digest() if user_agent else None
    await db.execute(
        text(
            "INSERT INTO public.auth_refresh_tokens "
            "(user_id, token_hash, family_id, family_created_at, expires_at, created_at, user_agent_hash, "
            "trusted_device_id) "
            "VALUES (:uid, :h, :fid, :fca, :exp, :now, :ua, :tdid)"
        ),
        {
            "uid": user_id,
            "h": _hash_token(raw),
            "fid": family,
            "fca": family_start,
            "exp": expires_at,
            "now": now,
            "ua": ua_hash,
            "tdid": trusted_device_id,
        },
    )
    return raw, expires_at


class RotatedRefresh(NamedTuple):
    """更新に成功したときの結果（ADR-1055 D8・D4）。組の id と機械の結び付きを引き継ぐ。"""

    user_id: int
    raw: str
    expires_at: datetime
    family_id: str
    family_created_at: datetime | None
    trusted_device_id: int | None


async def rotate_refresh_token(db: AsyncSession, raw: str, user_agent: str | None) -> RotatedRefresh | None:
    """成功なら RotatedRefresh。失敗は None。"""
    now = _now()
    token_hash = _hash_token(raw)
    # 1 文で失効させて取り出す（競合しても 2 回使えない）
    result = await db.execute(
        text(
            "UPDATE public.auth_refresh_tokens SET revoked_at = :now, last_used_at = :now "
            "WHERE token_hash = :h AND revoked_at IS NULL AND expires_at > :now "
            "RETURNING user_id, family_id, family_created_at, created_at, trusted_device_id"
        ),
        {"now": now, "h": token_hash},
    )
    row = result.first()
    if row is None:
        # 失効済みが使われた = 使い回し。同じ組を全部失効させる
        seen = await db.execute(
            text("SELECT family_id, revoked_at FROM public.auth_refresh_tokens WHERE token_hash = :h"),
            {"h": token_hash},
        )
        old = seen.first()
        if old is not None and old.revoked_at is not None:
            await db.execute(
                text(
                    "UPDATE public.auth_refresh_tokens SET revoked_at = :now "
                    "WHERE family_id = :f AND revoked_at IS NULL"
                ),
                {"now": now, "f": str(old.family_id)},
            )
        return None

    user_id, family_id, family_created_at, token_created_at, trusted_device_id = row
    user_row = (
        await db.execute(
            text("SELECT id, email, is_active, password_changed_at FROM public.users WHERE id = :uid"),
            {"uid": user_id},
        )
    ).first()
    if user_row is None or not user_row.is_active:
        return None
    changed_at = _as_utc(user_row.password_changed_at)
    if changed_at is not None and changed_at > _as_utc(token_created_at):
        return None

    family_start = _as_utc(family_created_at)
    new_raw, expires_at = await issue_refresh_token(
        db,
        user_id,
        user_agent,
        family_id=str(family_id),
        family_created_at=family_start,
        trusted_device_id=trusted_device_id,
    )
    return RotatedRefresh(user_id, new_raw, expires_at, str(family_id), family_start, trusted_device_id)


async def revoke_refresh_token(db: AsyncSession, raw: str) -> None:
    await db.execute(
        text(
            "UPDATE public.auth_refresh_tokens SET revoked_at = :now "
            "WHERE token_hash = :h AND revoked_at IS NULL"
        ),
        {"now": _now(), "h": _hash_token(raw)},
    )
