"""アプリ内の鈴: 自分宛ての知らせの一覧と既読（設計 docs/handoff/in-app-notice-bell/design.md §7-1）。

本人の行だけを読み書きする。他人・他社の id は 404。本文・Discord の id は返さない（表にも無い）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, reset_tenant_context, tenant_table_ref
from app.database import get_db
from app.models import User

router = APIRouter()

LIST_LIMIT = 50


class NoticeItem(BaseModel):
    id: int = Field(description="知らせの ID")
    kind: str = Field(description="知らせの種類（例 discord_outside_ticket_post）")
    actor_name: str | None = Field(default=None, description="書いた人の Discord の表示名")
    channel_name: str | None = Field(default=None, description="書き込まれたチャンネル名")
    link_url: str | None = Field(default=None, description="書き込みへのリンク")
    created_at: str | None = Field(default=None, description="知らせの日時（ISO 8601）")
    read_at: str | None = Field(default=None, description="既読にした日時（未読は null）")


class NoticeList(BaseModel):
    items: list[NoticeItem] = Field(description="新しい順・最大 50 件")
    unread_count: int = Field(description="未読の件数（一覧の 50 件に限らない）")


class NoticeReadResult(BaseModel):
    unread_count: int = Field(description="既読にした後の未読の件数")


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


async def _unread_count(db: AsyncSession, notices_t: str, user_id: int) -> int:
    row = (
        await db.execute(
            text(f"SELECT COUNT(*) FROM {notices_t} WHERE user_id = :uid AND read_at IS NULL"),
            {"uid": user_id},
        )
    ).first()
    return int(row[0]) if row else 0


@router.get("/notices", response_model=NoticeList)
async def list_notices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """自分宛ての知らせを新しい順に最大 50 件と、未読の件数。テナントの無い人は空。"""
    if not current_user.tenant_id:
        return NoticeList(items=[], unread_count=0)
    notices_t = tenant_table_ref(db, current_user.tenant_id, "user_notices")
    rows = (
        await db.execute(
            text(
                "SELECT id, kind, actor_name, channel_name, link_url, created_at, read_at "
                f"FROM {notices_t} WHERE user_id = :uid "
                "ORDER BY created_at DESC, id DESC LIMIT :lim"
            ),
            {"uid": current_user.id, "lim": LIST_LIMIT},
        )
    ).mappings().all()
    items = [
        NoticeItem(
            id=r["id"], kind=r["kind"], actor_name=r["actor_name"],
            channel_name=r["channel_name"], link_url=r["link_url"],
            created_at=_iso(r["created_at"]), read_at=_iso(r["read_at"]),
        )
        for r in rows
    ]
    return NoticeList(items=items, unread_count=await _unread_count(db, notices_t, current_user.id))


@router.post("/notices/{notice_id}/read", response_model=NoticeReadResult)
async def mark_notice_read(
    notice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """本人の行だけ既読にする（既読なら変えない）。他人・他社の id は 404。"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知らせが見つかりません")
    notices_t = tenant_table_ref(db, current_user.tenant_id, "user_notices")
    found = (
        await db.execute(
            text(f"SELECT id FROM {notices_t} WHERE id = :id AND user_id = :uid"),
            {"id": notice_id, "uid": current_user.id},
        )
    ).first()
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知らせが見つかりません")
    await db.execute(
        text(
            f"UPDATE {notices_t} SET read_at = :now "
            "WHERE id = :id AND user_id = :uid AND read_at IS NULL"
        ),
        {"now": datetime.now(timezone.utc), "id": notice_id, "uid": current_user.id},
    )
    await db.commit()
    await reset_tenant_context(db, current_user.tenant_id)  # ADR-072
    return NoticeReadResult(unread_count=await _unread_count(db, notices_t, current_user.id))
