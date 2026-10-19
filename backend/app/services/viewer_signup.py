"""閲覧者の申込コード発行の唯一の入口（ADR-1019 段5）。

/signup と管理画面の「作り直し」の両方がここを呼ぶ。コードは DB に sha256 だけ保存する。
commit はしない（呼び出し側が commit する）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.viewer_signup_code import generate_signup_code, signup_code_sha256

SIGNUP_CODE_TTL = timedelta(days=7)


async def replace_signup_code(db: AsyncSession, viewer_id: int) -> tuple[str, datetime]:
    """その人の申込コードを差し替える。旧コードは消え、新しい (コード, 期限) を返す。"""
    await db.execute(
        text("DELETE FROM public.viewer_login_tokens WHERE viewer_account_id = :id AND purpose = 'signup_code'"),
        {"id": viewer_id},
    )
    code = generate_signup_code()
    expires_at = datetime.now(timezone.utc) + SIGNUP_CODE_TTL
    await db.execute(
        text(
            "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
            "VALUES (:id, :h, 'signup_code', :exp)"
        ),
        {"id": viewer_id, "h": signup_code_sha256(code), "exp": expires_at},
    )
    return code, expires_at
