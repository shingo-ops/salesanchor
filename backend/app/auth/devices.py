"""いつもの機械（ADR-1055）。印・許可依頼・組の失効の部品。

表 public.user_trusted_devices・public.auth_login_requests は生 SQL で読み書きする
（self_tokens.py と同じ理由で ORM を作らない）。印も待ちの鍵も、生の値は保存せず sha256 だけを置く。
環境変数は import 時に固定せず、呼び出し時に読む（テストの setenv を効かせるため）。
トランザクションの commit は呼び出し側が行う。
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from fastapi import HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import geo, self_tokens
from app.cache import mark_family_revoked
from app.client_ip import get_client_ip

logger = logging.getLogger(__name__)

DEVICE_COOKIE_NAME = "sa_device"
DEVICE_COOKIE_PATH = "/api/v1/auth"
DEVICE_COOKIE_MAX_AGE = 180 * 24 * 3600
DEVICE_IDLE_DAYS = 180

PENDING_COOKIE_NAME = "sa_login_pending"
PENDING_COOKIE_PATH = "/api/v1/auth/login-requests"
REQUEST_TTL = timedelta(minutes=30)
REQUEST_HOURLY_LIMIT = 5
RECOVERY_MAX_FAILED_ATTEMPTS = 5

_COOKIE_VALUE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")

CREATED_VIA = (
    "bootstrap",
    "first_login",
    "passkey",
    "device_approval",
    "recovery_code",
    "admin_approval",
    "cli",
)


# ── 設定（毎回 os.getenv） ───────────────────────────────────


def approval_mode() -> str:
    """AUTH_DEVICE_APPROVAL=off|enforce（既定 off。off はログインの止め方が今と同じ）。"""
    return "enforce" if os.getenv("AUTH_DEVICE_APPROVAL", "off").strip().lower() == "enforce" else "off"


def is_enforced() -> bool:
    return approval_mode() == "enforce"


def bootstrap_cutoff() -> datetime | None:
    """AUTH_DEVICE_BOOTSTRAP_CUTOFF（UTC の固定値）。空・読めないときは None（D4 の登録をしない）。"""
    raw = os.getenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "").strip()
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("AUTH_DEVICE_BOOTSTRAP_CUTOFF を読めない（D4 の登録をしない）")
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_value(raw: str) -> bytes:
    return self_tokens._hash_token(raw)


# ── Cookie ───────────────────────────────────────────────────


def clean_cookie_value(raw: str | None) -> str | None:
    """クライアントが送ってきた印の値の形を確かめる。合わなければ None（新しく作り直す）。"""
    if raw and _COOKIE_VALUE_RE.match(raw):
        return raw
    return None


def set_device_cookie(response: Response, raw: str) -> None:
    """印 Cookie sa_device（HttpOnly・Secure・SameSite=Strict・path /api/v1/auth・180日）。ログインのたび延長する。"""
    response.set_cookie(
        DEVICE_COOKIE_NAME,
        raw,
        httponly=True,
        secure=self_tokens.cookie_secure(),
        samesite="strict",
        path=DEVICE_COOKIE_PATH,
        max_age=DEVICE_COOKIE_MAX_AGE,
    )


def set_pending_cookie(response: Response, raw: str) -> None:
    """許可待ちの Cookie sa_login_pending（30分・path /api/v1/auth/login-requests）。"""
    response.set_cookie(
        PENDING_COOKIE_NAME,
        raw,
        httponly=True,
        secure=self_tokens.cookie_secure(),
        samesite="strict",
        path=PENDING_COOKIE_PATH,
        max_age=int(REQUEST_TTL.total_seconds()),
    )


def clear_pending_cookie(response: Response) -> None:
    response.delete_cookie(
        PENDING_COOKIE_NAME,
        path=PENDING_COOKIE_PATH,
        secure=self_tokens.cookie_secure(),
        httponly=True,
        samesite="strict",
    )


# ── 機械の種類（D10） ─────────────────────────────────────────


def describe_user_agent(ua: str | None) -> str:
    """User-Agent から「iPhone・Safari」「Mac・Chrome」等を作る（依存を足さない）。"""
    if not ua:
        return "不明な機械"
    s = ua
    if "iPhone" in s:
        device = "iPhone"
    elif "iPad" in s:
        device = "iPad"
    elif "Android" in s:
        device = "Android"
    elif "Windows" in s:
        device = "Windows"
    elif "Macintosh" in s or "Mac OS X" in s:
        device = "Mac"
    elif "CrOS" in s:
        device = "Chromebook"
    elif "Linux" in s:
        device = "Linux"
    else:
        device = "不明な機械"
    if "Edg/" in s or "EdgA/" in s or "EdgiOS/" in s:
        browser = "Edge"
    elif "OPR/" in s or "Opera" in s:
        browser = "Opera"
    elif "FxiOS/" in s or "Firefox/" in s:
        browser = "Firefox"
    elif "CriOS/" in s or "Chrome/" in s:
        browser = "Chrome"
    elif "Safari/" in s:
        browser = "Safari"
    else:
        browser = ""
    return f"{device}・{browser}" if browser else device


def jst_text(moment: datetime | None = None) -> str:
    """メールと画面に出す日本時間の文字列。"""
    jst = timezone(timedelta(hours=9))
    return (moment or _now()).astimezone(jst).strftime("%Y-%m-%d %H:%M")


# ── いつもの機械 ──────────────────────────────────────────────


class DeviceRow(NamedTuple):
    id: int
    created_via: str


async def find_trusted_device(db: AsyncSession, user_id: int, raw_cookie: str | None) -> DeviceRow | None:
    """印がその人のいつもの機械か（取り消されていない・180日以内に使った）。"""
    raw = clean_cookie_value(raw_cookie)
    if raw is None:
        return None
    cutoff = _now() - timedelta(days=DEVICE_IDLE_DAYS)
    row = (
        await db.execute(
            text(
                "SELECT id, created_via FROM public.user_trusted_devices "
                "WHERE user_id = :uid AND token_hash = :h AND revoked_at IS NULL "
                "AND COALESCE(last_used_at, created_at) > :cutoff"
            ),
            {"uid": user_id, "h": hash_value(raw), "cutoff": cutoff},
        )
    ).first()
    return DeviceRow(int(row.id), row.created_via) if row else None


async def has_any_trusted_device(db: AsyncSession, user_id: int) -> bool:
    """取り消されていない機械が1つでもあるか（登録の有無。D5 は「機械の登録が0件」で判定する）。"""
    count = (
        await db.execute(
            text("SELECT count(*) FROM public.user_trusted_devices WHERE user_id = :uid AND revoked_at IS NULL"),
            {"uid": user_id},
        )
    ).scalar_one()
    return int(count) > 0


async def count_all_devices(db: AsyncSession, user_id: int) -> int:
    """取り消し済みを含む機械の行数（D5 の「機械の登録が0件」）。"""
    return int(
        (
            await db.execute(
                text("SELECT count(*) FROM public.user_trusted_devices WHERE user_id = :uid"),
                {"uid": user_id},
            )
        ).scalar_one()
    )


async def register_device(
    db: AsyncSession,
    user_id: int,
    raw_cookie: str | None,
    created_via: str,
    request: Request,
) -> tuple[int, str]:
    """機械を登録して (device_id, 印の生の値) を返す。印が無ければ作る。既にある印は同じ値を使う。

    bootstrap と first_login では、取り消し済みの印を生き返らせない（新しい値を作る）。
    """
    if created_via not in CREATED_VIA:
        raise ValueError("unknown created_via")
    raw = clean_cookie_value(raw_cookie)
    if raw is not None and created_via in ("bootstrap", "first_login"):
        revoked = (
            await db.execute(
                text(
                    "SELECT 1 FROM public.user_trusted_devices "
                    "WHERE user_id = :uid AND token_hash = :h AND revoked_at IS NOT NULL"
                ),
                {"uid": user_id, "h": hash_value(raw)},
            )
        ).first()
        if revoked is not None:
            raw = None
    if raw is None:
        raw = secrets.token_urlsafe(32)
    now = _now()
    ip = get_client_ip(request)
    location = geo.lookup(ip)
    ua = (request.headers.get("user-agent") or "")[:500] or None
    row = (
        await db.execute(
            text(
                "INSERT INTO public.user_trusted_devices "
                "(user_id, token_hash, label, user_agent, created_via, created_ip, created_location, "
                " created_at, last_used_at, last_ip, last_location) "
                "VALUES (:uid, :h, :label, :ua, :via, :ip, :loc, :now, :now, :ip, :loc) "
                "ON CONFLICT (user_id, token_hash) DO UPDATE SET revoked_at = NULL, last_used_at = :now, "
                "last_ip = :ip, last_location = :loc "
                "RETURNING id"
            ),
            {
                "uid": user_id,
                "h": hash_value(raw),
                "label": describe_user_agent(ua)[:100],
                "ua": ua,
                "via": created_via,
                "ip": ip[:45] if ip else None,
                "loc": location,
                "now": now,
            },
        )
    ).first()
    return int(row[0]), raw


async def touch_device(db: AsyncSession, device_id: int, request: Request) -> None:
    """使った時刻・IP・場所の目安を更新する。"""
    ip = get_client_ip(request)
    await db.execute(
        text(
            "UPDATE public.user_trusted_devices SET last_used_at = :now, last_ip = :ip, last_location = :loc "
            "WHERE id = :id"
        ),
        {"now": _now(), "ip": ip[:45] if ip else None, "loc": geo.lookup(ip), "id": device_id},
    )


async def revoke_user_sessions(
    db: AsyncSession,
    user_id: int,
    except_family_id: str | None = None,
    device_id: int | None = None,
) -> list[str]:
    """更新トークンの組を失効させる共通関数（D8）。失効した組の id を返し、Redis に auth:fam_revoked:{sid} を置く。

    except_family_id: この組は残す（「押した機械以外の全部のログアウト」）。
    device_id: この機械に結び付いた組だけ失効させる。
    """
    sql = "UPDATE public.auth_refresh_tokens SET revoked_at = :now WHERE user_id = :uid AND revoked_at IS NULL"
    params: dict = {"now": _now(), "uid": user_id}
    if except_family_id is not None:
        sql += " AND family_id <> :ex"
        params["ex"] = str(except_family_id)
    if device_id is not None:
        sql += " AND trusted_device_id = :dev"
        params["dev"] = device_id
    sql += " RETURNING family_id"
    rows = (await db.execute(text(sql), params)).fetchall()
    families = sorted({str(r[0]) for r in rows})
    for family in families:
        await mark_family_revoked(family)
    return families


async def revoke_family(db: AsyncSession, user_id: int, family_id: str) -> None:
    """1つの組だけ失効させる（refresh で機械が取り消されていた・締切後で機械が無いとき）。"""
    await db.execute(
        text(
            "UPDATE public.auth_refresh_tokens SET revoked_at = :now "
            "WHERE family_id = :fid AND user_id = :uid AND revoked_at IS NULL"
        ),
        {"now": _now(), "fid": str(family_id), "uid": user_id},
    )
    await mark_family_revoked(str(family_id))


async def revoke_device(db: AsyncSession, user_id: int, device_id: int) -> bool:
    """本人の機械を取り消し、結び付いた組を失効させる。他人の id・無い id は False。"""
    row = (
        await db.execute(
            text(
                "UPDATE public.user_trusted_devices SET revoked_at = :now "
                "WHERE id = :id AND user_id = :uid AND revoked_at IS NULL RETURNING id"
            ),
            {"now": _now(), "id": device_id, "uid": user_id},
        )
    ).first()
    if row is None:
        return False
    await revoke_user_sessions(db, user_id, device_id=device_id)
    return True


async def bind_family_to_device(db: AsyncSession, family_id: str, user_id: int, device_id: int) -> None:
    """有効な組の行に機械を結び付ける（D4・password change の bootstrap）。"""
    await db.execute(
        text(
            "UPDATE public.auth_refresh_tokens SET trusted_device_id = :dev "
            "WHERE family_id = :fid AND user_id = :uid AND revoked_at IS NULL"
        ),
        {"dev": device_id, "fid": str(family_id), "uid": user_id},
    )


async def is_device_active(db: AsyncSession, device_id: int) -> bool:
    row = (
        await db.execute(
            text("SELECT 1 FROM public.user_trusted_devices WHERE id = :id AND revoked_at IS NULL"),
            {"id": device_id},
        )
    ).first()
    return row is not None


# ── 許可依頼（D6・D15） ────────────────────────────────────────


class NewRequest(NamedTuple):
    id: str
    pending_raw: str
    match_number: str
    candidates: str
    expires_at: datetime
    label: str
    location: str | None


def _numbers() -> tuple[str, str]:
    """(正しい番号, 候補3つの文字列) を作る。候補は2けたの番号3つで、正しい番号を含む。"""
    rng = secrets.SystemRandom()
    picked = rng.sample(range(100), 3)
    match = picked[0]
    rng.shuffle(picked)
    return f"{match:02d}", ",".join(f"{n:02d}" for n in picked)


async def create_login_request(
    db: AsyncSession,
    user_id: int,
    request: Request,
    device_raw: str | None,
) -> NewRequest:
    """許可依頼を作る。1人1時間に5件まで（超えたら 429 too_many_requests）。commit は呼び出し側。"""
    now = _now()
    recent = (
        await db.execute(
            text("SELECT count(*) FROM public.auth_login_requests WHERE user_id = :uid AND created_at > :since"),
            {"uid": user_id, "since": now - timedelta(hours=1)},
        )
    ).scalar_one()
    if int(recent) >= REQUEST_HOURLY_LIMIT:
        raise HTTPException(status_code=429, detail="too_many_requests")
    request_id = str(uuid.uuid4())
    pending_raw = secrets.token_urlsafe(32)
    match_number, candidates = _numbers()
    expires_at = now + REQUEST_TTL
    ip = get_client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:500] or None
    device_clean = clean_cookie_value(device_raw)
    label = describe_user_agent(ua)[:100]
    location = geo.lookup(ip)
    await db.execute(
        text(
            "INSERT INTO public.auth_login_requests "
            "(id, user_id, status, match_number, candidates, pending_token_hash, device_token_hash, "
            " label, user_agent, ip, location, created_at, expires_at) "
            "VALUES (:id, :uid, 'pending', :num, :cands, :ph, :dh, :label, :ua, :ip, :loc, :now, :exp)"
        ),
        {
            "id": request_id,
            "uid": user_id,
            "num": match_number,
            "cands": candidates,
            "ph": hash_value(pending_raw),
            "dh": hash_value(device_clean) if device_clean else None,
            "label": label,
            "ua": ua,
            "ip": ip[:45] if ip else None,
            "loc": location,
            "now": now,
            "exp": expires_at,
        },
    )
    return NewRequest(request_id, pending_raw, match_number, candidates, expires_at, label, location)


def parse_request_id(value: str) -> str | None:
    """パスの依頼 id を UUID の文字列にする。形が違えば None（口は 404 を返す）。"""
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        return None
