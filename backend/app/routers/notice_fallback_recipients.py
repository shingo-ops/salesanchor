"""アプリ内の鈴: 担当者がいないときに知らせを受け取る人の設定（設計 docs/handoff/in-app-notice-bell/design.md §4-改訂2）。

- 置き場所: 各社スキーマ {tenant}.notice_fallback_recipients（行が 0 件 = 未設定 = オーナー全員）。
- GET / PUT とも notifications.manage が必要。
- 候補は同じ会社・有効な public.users の user_id と名前だけ。Discord の id・メールは返さない。
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    is_postgresql,
    require_permission,
    reset_tenant_context,
    tenant_table_ref,
)
from app.database import get_db
from app.models import User

router = APIRouter()


class FallbackCandidate(BaseModel):
    user_id: int = Field(description="public.users.id")
    name: str | None = Field(default=None, description="表示名（full_name が空ならユーザー名）")


class FallbackRecipients(BaseModel):
    selected: list[int] = Field(description="担当者がいないときに受け取る人の user_id（未設定は空）")
    defaulted_to_owner: bool = Field(description="未設定、または設定の人が全員無効でオーナーに戻っているとき true")
    candidates: list[FallbackCandidate] = Field(description="選べる人（同じ会社・有効）")


class FallbackRecipientsUpdate(BaseModel):
    user_ids: list[int] = Field(description="受け取る人の user_id の一覧（丸ごと置き換え。空で未設定に戻す）")


def _users_ref(db: AsyncSession) -> str:
    return "public.users" if is_postgresql(db) else "users"


async def _candidates(db: AsyncSession, tenant_id: int) -> list[FallbackCandidate]:
    rows = (
        await db.execute(
            text(
                "SELECT u.id AS user_id, COALESCE(NULLIF(u.full_name, ''), u.username) AS name "
                f"FROM {_users_ref(db)} u "
                "WHERE u.tenant_id = :tid AND u.is_active = :active ORDER BY u.id"
            ),
            {"tid": tenant_id, "active": True},
        )
    ).mappings().all()
    return [FallbackCandidate(user_id=int(r["user_id"]), name=r["name"]) for r in rows]


async def _build(db: AsyncSession, tenant_id: int) -> FallbackRecipients:
    fb_t = tenant_table_ref(db, tenant_id, "notice_fallback_recipients")
    selected = [int(r[0]) for r in (await db.execute(text(f"SELECT user_id FROM {fb_t} ORDER BY user_id"))).all()]
    candidates = await _candidates(db, tenant_id)
    valid_ids = {c.user_id for c in candidates}
    effective = [uid for uid in selected if uid in valid_ids]
    return FallbackRecipients(
        selected=selected,
        defaulted_to_owner=not effective,
        candidates=candidates,
    )


@router.get("/notice-fallback-recipients", response_model=FallbackRecipients)
async def get_notice_fallback_recipients(
    current_user: User = Depends(require_permission("notifications.manage")),
    db: AsyncSession = Depends(get_db),
):
    """今の設定と、選べる人の一覧。未設定ならオーナー全員に届く（defaulted_to_owner）。"""
    if not current_user.tenant_id:
        return FallbackRecipients(selected=[], defaulted_to_owner=True, candidates=[])
    return await _build(db, current_user.tenant_id)


@router.put("/notice-fallback-recipients", response_model=FallbackRecipients)
async def put_notice_fallback_recipients(
    body: FallbackRecipientsUpdate,
    current_user: User = Depends(require_permission("notifications.manage")),
    db: AsyncSession = Depends(get_db),
):
    """受け取る人を丸ごと置き換える。別会社・無効・存在しない id が 1 つでもあれば 422。"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会社が見つかりません")
    tenant_id = current_user.tenant_id
    wanted = sorted(set(body.user_ids))
    if wanted:
        stmt = text(
            f"SELECT id FROM {_users_ref(db)} "
            "WHERE id IN :ids AND tenant_id = :tid AND is_active = :active"
        ).bindparams(bindparam("ids", expanding=True))
        found = {int(r[0]) for r in (await db.execute(stmt, {"ids": wanted, "tid": tenant_id, "active": True})).all()}
        if found != set(wanted):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="同じ会社の有効な人だけを選べます",
            )
    fb_t = tenant_table_ref(db, tenant_id, "notice_fallback_recipients")
    await db.execute(text(f"DELETE FROM {fb_t}"))
    now = datetime.now(timezone.utc)
    for uid in wanted:
        await db.execute(
            text(f"INSERT INTO {fb_t} (user_id, updated_by, updated_at) VALUES (:uid, :by, :now)"),
            {"uid": uid, "by": current_user.id, "now": now},
        )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return await _build(db, tenant_id)
