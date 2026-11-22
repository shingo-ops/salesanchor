"""Meta 審査用の会社だけのログインのスイッチの判定（ADR-1055 What 11）。

ADR-1055 What 11。Meta の審査員が登録していない機械から入るための会社006だけの例外。
ほかの会社に広げない。

判定はこのファイルの関数に集める。「印の会社（tenants.meta_review_tenant）・super admin でない」の
条件は、このファイルの2つの SQL にだけ書く。ログイン・更新・4つの口はこのファイルの関数を呼ぶ。
devices・dependencies からこのファイルは読み込まない（循環させない）。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import devices, self_tokens
from app.auth.dependencies import resolve_current_session

META_REVIEW_MAX_DAYS = 14


def is_meta_review_on(until: datetime | str | None) -> bool:
    """Meta 審査用の会社のスイッチ（ADR-1055 What 11）。期限が今より後のときだけ True。
    SQLite は時刻を文字列で返すので、既存と同じく _as_utc を通してから比べる。"""
    value = self_tokens._as_utc(until)
    return value is not None and value > devices._now()


async def meta_review_until(db: AsyncSession, user_id: int) -> datetime | str | None:
    """その人に効くスイッチの値。印の会社の人で、super admin でないときだけ値を返す。"""
    return (
        await db.execute(
            text(
                "SELECT t.meta_review_login_until FROM public.users u "
                "JOIN public.tenants t ON t.id = u.tenant_id "
                "WHERE u.id = :id AND t.meta_review_tenant AND NOT u.is_super_admin"
            ),
            {"id": user_id},
        )
    ).scalar_one_or_none()


async def is_meta_review_member(db: AsyncSession, user_id: int) -> bool:
    """印の会社の人で、super admin でないか（スイッチの ON／OFF に関わらない）。"""
    return (
        await db.execute(
            text(
                "SELECT 1 FROM public.users u JOIN public.tenants t ON t.id = u.tenant_id "
                "WHERE u.id = :id AND t.meta_review_tenant AND NOT u.is_super_admin"
            ),
            {"id": user_id},
        )
    ).first() is not None


async def is_meta_review_session(db: AsyncSession, request: Request, user) -> bool:
    """スイッチで入った組（印の会社の人で、機械の無い組）か。スイッチの ON／OFF では判断しない。

    OFF の直後や14日の自動 OFF の直後も、残ったトークンでパスキー・予備の合言葉を作らせないため。
    """
    if not devices.is_enforced():
        return False
    if not await is_meta_review_member(db, user.id):
        return False
    current = await resolve_current_session(request, db, user)
    return current.trusted_device_id is None
