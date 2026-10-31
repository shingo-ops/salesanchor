"""いつもの機械に出す「新しい機械からのログイン」の一覧（ADR-1055 A-2「回数の枠」）。

一覧は /api/v1/auth/ の外に置く。nginx では location /api/（30回/秒）に入り、login の枠（10回/分）を使わない。
画面を開くたび・つなぎ直し・タブに戻るたびに読まれても、普段の画面と自動点検が 429 にならないため。
GET なので Origin の確認はしない・NO_SIGNAL_ROUTES にも入れない。
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User

router = APIRouter()


class PendingLoginRequest(BaseModel):
    id: str = Field(description="依頼の ID（UUID）")
    label: str | None = Field(default=None, description="待つ機械の種類（例 iPhone・Safari）")
    location: str | None = Field(default=None, description="場所の目安（IP Geolocation by DB-IP）")
    created_at: str | None = Field(default=None, description="依頼した日時")
    expires_at: str | None = Field(default=None, description="期限")
    candidates: list[str] = Field(description="番号の候補3つ（正しい番号は待つ機械に出ている）")


class PendingLoginRequestList(BaseModel):
    items: list[PendingLoginRequest]


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


@router.get("/login-approvals/pending", response_model=PendingLoginRequestList)
async def login_approvals_pending(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """自分宛ての許可待ちの一覧。本人の pending で期限内のものだけ（他人の依頼は出ない）。"""
    rows = (
        await db.execute(
            text(
                "SELECT id, label, location, created_at, expires_at, candidates "
                "FROM public.auth_login_requests "
                "WHERE user_id = :uid AND status = 'pending' AND expires_at > :now "
                "ORDER BY created_at DESC"
            ),
            {"uid": current_user.id, "now": datetime.now(timezone.utc)},
        )
    ).all()
    return PendingLoginRequestList(
        items=[
            PendingLoginRequest(
                id=str(r.id),
                label=r.label,
                location=r.location,
                created_at=_iso(r.created_at),
                expires_at=_iso(r.expires_at),
                candidates=[c for c in str(r.candidates).split(",") if c],
            )
            for r in rows
        ]
    )
