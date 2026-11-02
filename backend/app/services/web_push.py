"""いつもの機械のホーム画面のアプリへ、許可依頼の通知（web push）を送る（ADR-1055 段W）。

- 鍵（VAPID）の3つの環境変数は呼び出し時に読む。値はログに出さない。3つそろわなければ送らない。
- 送るのは「本人の、取り消されていない機械の、取り消されていない購読」だけ。
- 通知の中身に確認番号（match_number）は入れない（番号は許可する側の画面でだけ見せる）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import NamedTuple
from urllib.parse import urlsplit

import urllib3.util
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# 送り先として受ける通知サービスのホスト名（その下の名前も可）。出どころは公開の実装例1件で、各社の公式文書では未確認。
_ALLOWED_PUSH_HOSTS = (
    "fcm.googleapis.com",
    "android.googleapis.com",
    "push.services.mozilla.com",
    "push.apple.com",
    "notify.windows.com",
)
_HOST_RE = re.compile(r"^[a-z0-9.-]+$")
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+=*$")
_BAD_CHARS_RE = re.compile(r"[\\@\x00-\x20\x7f]")
_MAX_ENDPOINT = 2048
_MAX_P256DH = 200
_MAX_AUTH = 100


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def is_configured() -> bool:
    """VAPID の3つ（秘密の鍵・公開の鍵・名乗り）が空でないとき True。"""
    return bool(
        _env("WEBPUSH_VAPID_PRIVATE_KEY") and _env("WEBPUSH_VAPID_PUBLIC_KEY") and _env("WEBPUSH_VAPID_SUBJECT")
    )


def public_key() -> str | None:
    """画面が購読に使う公開の鍵。未設定なら None。"""
    if not is_configured():
        return None
    return _env("WEBPUSH_VAPID_PUBLIC_KEY")


def _reject(host: str | None) -> HTTPException:
    # URL 全体と鍵は書かない。ホスト名だけ（一覧の出どころが公式文書でないため、外れた要求を後で見直せるように）。
    logger.warning("web push: 受けない送り先を断った host=%s", (host or "")[:100])
    return HTTPException(status_code=422, detail="invalid_push_subscription")


def validate_subscription(endpoint: str, p256dh: str, auth: str) -> None:
    """送り先 URL と鍵の形を確かめる（サーバーが利用者の渡した URL へ送るため）。外れたら 422。"""
    if (
        not isinstance(endpoint, str)
        or not isinstance(p256dh, str)
        or not isinstance(auth, str)
        or not endpoint
        or len(endpoint) > _MAX_ENDPOINT
        or not p256dh
        or len(p256dh) > _MAX_P256DH
        or not auth
        or len(auth) > _MAX_AUTH
        or not _B64URL_RE.match(p256dh)
        or not _B64URL_RE.match(auth)
    ):
        raise _reject(None)
    if _BAD_CHARS_RE.search(endpoint):
        raise _reject(None)
    host: str | None = None
    try:
        parts = urlsplit(endpoint)
        host = (parts.hostname or "").lower()
        if parts.scheme != "https" or not host:
            raise _reject(host)
        if parts.username is not None or parts.password is not None:
            raise _reject(host)
        port = parts.port
        if port is not None and port != 443:
            raise _reject(host)
        if not _HOST_RE.match(host):
            raise _reject(host)
        if all(seg.isdigit() for seg in host.split(".") if seg) or host.replace(".", "").isdigit():
            raise _reject(host)  # IP の数字
        other_host = (urllib3.util.parse_url(endpoint).host or "").lower()
        if other_host != host:
            raise _reject(host)
    except HTTPException:
        raise
    except Exception:  # urlsplit・.port・parse_url の例外は 500 にしない
        raise _reject(host) from None
    if not any(host == d or host.endswith("." + d) for d in _ALLOWED_PUSH_HOSTS):
        raise _reject(host)


class PushTarget(NamedTuple):
    id: int
    endpoint: str
    p256dh: str
    auth: str


async def list_targets(db: AsyncSession, user_id: int) -> list[PushTarget]:
    """本人の有効な購読。取り消された機械の購読は JOIN で外す（他人の購読へは送らない要は s.user_id）。"""
    rows = (
        await db.execute(
            text(
                "SELECT s.id, s.endpoint, s.p256dh, s.auth "
                "FROM public.user_push_subscriptions s "
                "JOIN public.user_trusted_devices d ON d.id = s.trusted_device_id "
                "WHERE s.user_id = :uid AND s.revoked_at IS NULL AND d.revoked_at IS NULL "
                "ORDER BY s.id"
            ),
            {"uid": user_id},
        )
    ).all()
    return [PushTarget(r.id, r.endpoint, r.p256dh, r.auth) for r in rows]


def _send_one(target: PushTarget, body: str) -> None:
    from pywebpush import webpush

    webpush(
        subscription_info={"endpoint": target.endpoint, "keys": {"p256dh": target.p256dh, "auth": target.auth}},
        data=body,
        vapid_private_key=_env("WEBPUSH_VAPID_PRIVATE_KEY"),
        vapid_claims={"sub": _env("WEBPUSH_VAPID_SUBJECT")},  # 送るたびに新しい dict（webpush が書き足すため）
        ttl=1800,
        headers={"Urgency": "high"},
        timeout=10,
    )


async def deliver(targets: list[PushTarget], payload: dict) -> list[tuple[int, str]]:
    """1件ずつ送る。結果は (購読の id, "ok" | "gone" | "failed")。1件の失敗で残りを止めない。"""
    from pywebpush import WebPushException

    body = json.dumps(payload, ensure_ascii=False)
    results: list[tuple[int, str]] = []
    for t in targets:
        try:
            await asyncio.to_thread(_send_one, t, body)
            results.append((t.id, "ok"))
        except WebPushException as exc:
            code = getattr(getattr(exc, "response", None), "status_code", None)
            if code in (404, 410):
                results.append((t.id, "gone"))
            else:
                logger.warning("web push: 送れなかった id=%s status=%s", t.id, code)
                results.append((t.id, "failed"))
        except Exception:
            logger.warning("web push: 送れなかった id=%s", t.id)
            results.append((t.id, "failed"))
    return results


async def record_results(db: AsyncSession, results: list[tuple[int, str]]) -> None:
    """送った結果を表に書く。ok は成功の日時、gone は取り消し、failed は失敗の回数を1つ増やす。"""
    now = datetime.now(timezone.utc)
    for sub_id, outcome in results:
        if outcome == "ok":
            await db.execute(
                text(
                    "UPDATE public.user_push_subscriptions SET last_success_at = :now, failed_count = 0 WHERE id = :id"
                ),
                {"now": now, "id": sub_id},
            )
        elif outcome == "gone":
            await db.execute(
                text("UPDATE public.user_push_subscriptions SET revoked_at = :now WHERE id = :id"),
                {"now": now, "id": sub_id},
            )
        else:
            await db.execute(
                text(
                    "UPDATE public.user_push_subscriptions "
                    "SET failed_count = LEAST(failed_count + 1, 32767) WHERE id = :id"
                ),
                {"id": sub_id},
            )
    await db.commit()


async def send_login_request_push(targets: list[PushTarget], *, when: str, device: str, location: str | None) -> None:
    """知らない機械からの許可依頼を通知する。どこで失敗しても外へ出さない（依頼は作ってある）。"""
    try:
        body = f"{when} / {device}"
        if location:
            body += f" / {location}"
        payload = {
            "title": "新しい機械からのログインの許可依頼 / New sign-in request",
            "body": body,
            "url": "/",
        }
        results = await deliver(targets, payload)
        async with AsyncSessionLocal() as db:
            await record_results(db, results)
    except Exception:
        logger.exception("web push: 許可依頼の通知に失敗")
