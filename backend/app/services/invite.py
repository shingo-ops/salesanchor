"""初回設定の鍵（purpose=invite・72 時間）を作る（ADR-1013 便4a）。

register（super admin）と POST /staff（新しい利用者ができたとき）の両方から呼ぶ。
鍵の実体（生の値）は DB に置かず sha256 だけ保存する。呼び出し側のトランザクション内で実行し、commit はしない。
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import self_tokens

INVITE_TTL = timedelta(hours=72)


def invite_enabled() -> bool:
    """初回設定の鍵とメールを作るか。AUTH_PROVIDER=self のときだけ（firebase の間は作らない）。"""
    return self_tokens.auth_provider() == "self"


async def create_invite_token(db: AsyncSession, user_id: int) -> str:
    """purpose=invite の鍵を 1 行 INSERT し、メールのリンクに入れる生の値を返す。"""
    now = datetime.now(timezone.utc)
    raw = secrets.token_urlsafe(32)
    await db.execute(
        text(
            "INSERT INTO public.password_reset_tokens (user_id, purpose, token_hash, expires_at, created_at) "
            "VALUES (:uid, 'invite', :h, :exp, :now)"
        ),
        {"uid": user_id, "h": self_tokens._hash_token(raw), "exp": now + INVITE_TTL, "now": now},
    )
    return raw


def invite_url(raw: str) -> str:
    """初回設定メールのリンク。再設定ページと同じ画面を開く。"""
    return f"{self_tokens.rp_origin()}/reset-password?token={raw}"
