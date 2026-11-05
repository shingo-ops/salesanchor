"""自社用 Discord サーバーの今の姿の読み取り（discord-server-management 便2・設計 §4-6）。

API:
  POST /api/v1/admin/discord/own-server/snapshot — 自社用サーバーのロールとチャンネルを読み、
    public.discord_server_snapshots に 1 行入れる

約束:
  - 読むだけ。Discord の物を作らない・変えない・消さない（呼ぶのは GET だけ）
  - サーバーの番号は記録に入れない。@everyone（番号がサーバーの番号と同じ）は "@everyone" と書く
  - 人の名前・書き込みは入れない。人ごとの上書き（type=1）は外し、数だけ残す
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.services.audit import record_audit_log
from app.services.discord_rest import DiscordAPIError, discord_api_request

logger = logging.getLogger(__name__)
router = APIRouter()

SNAPSHOT_VERSION = 1
EVERYONE = "@everyone"
# Discord のロールとチャンネルの項目（Context7 /discord/discord-api-docs の Role Structure・Channel Structure）
_ROLE_FIELDS = ("name", "color", "colors", "hoist", "mentionable", "permissions", "position", "managed")
_CHANNEL_FIELDS = ("type", "name", "position", "topic", "nsfw")


class OwnServerSnapshotResponse(BaseModel):
    snapshot_id: int
    role_count: int
    channel_count: int


def _ref(discord_id: Any, guild_id: str) -> str:
    """番号を文字にする。サーバーの番号と同じなら @everyone と書く（記録にサーバーの番号を残さない）。"""
    value = str(discord_id)
    return EVERYONE if value == guild_id else value


def build_snapshot_body(
    roles: list[dict[str, Any]], channels: list[dict[str, Any]], guild_id: str
) -> dict[str, Any]:
    """Discord の返事から、記録に入れる形を作る。"""
    out_roles: list[dict[str, Any]] = []
    for role in roles:
        item: dict[str, Any] = {"discord_id": _ref(role.get("id"), guild_id)}
        for field in _ROLE_FIELDS:
            item[field] = role.get(field)
        out_roles.append(item)
    out_channels: list[dict[str, Any]] = []
    for ch in channels:
        item = {"discord_id": str(ch.get("id"))}
        for field in _CHANNEL_FIELDS:
            item[field] = ch.get(field)
        parent = ch.get("parent_id")
        item["parent_id"] = str(parent) if parent is not None else None
        overwrites = ch.get("permission_overwrites") or []
        item["permission_overwrites"] = [
            {
                "target": _ref(ow.get("id"), guild_id),
                "allow": str(ow.get("allow", "0")),
                "deny": str(ow.get("deny", "0")),
            }
            for ow in overwrites
            if ow.get("type") == 0
        ]
        item["member_overwrite_count"] = sum(1 for ow in overwrites if ow.get("type") == 1)
        out_channels.append(item)
    return {"version": SNAPSHOT_VERSION, "roles": out_roles, "channels": out_channels}


def _insert_sql(db: AsyncSession) -> str:
    """PostgreSQL では JSONB に CAST する。SQLite（試験）では素の文字で入れる（backend/app/routers/meta_inbox.py:152-158 と同じ分け方）。"""
    bind = db.get_bind() if hasattr(db, "get_bind") else getattr(db, "bind", None)
    name = getattr(getattr(bind, "dialect", None), "name", "") or ""
    body_expr = "CAST(:body AS JSONB)" if name.startswith("postgresql") else ":body"
    return (
        "INSERT INTO public.discord_server_snapshots (tenant_id, purpose, body, taken_by)"
        f" VALUES (:tid, 'own', {body_expr}, :uid) RETURNING id"
    )


@router.post(
    "/admin/discord/own-server/snapshot",
    response_model=OwnServerSnapshotResponse,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def take_own_server_snapshot(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> OwnServerSnapshotResponse:
    """自社用サーバーのロールとチャンネルを読み、記録に 1 行入れる。"""
    result = await db.execute(
        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
        {"tid": tenant_id},
    )
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(
            status_code=422,
            detail="自社用サーバーが未登録です。先に Bot を招待してください。",
        )
    guild_id = str(row[0])

    bot_token: str | None = os.environ.get("DISCORD_BOT_TOKEN") or None
    if not bot_token:
        raise HTTPException(
            status_code=503,
            detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。",
        )

    try:
        roles: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/roles",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
        channels: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/channels",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
    except DiscordAPIError as exc:
        logger.warning("[discord_own_server] snapshot read failed tenant=%d: %s", tenant_id, exc)
        raise HTTPException(status_code=502, detail="Discord から読み取れませんでした。") from exc

    body = build_snapshot_body(roles, channels, guild_id)
    inserted = await db.execute(
        text(_insert_sql(db)),
        {"tid": tenant_id, "body": json.dumps(body, ensure_ascii=False), "uid": current_user.id},
    )
    snapshot_id = int(inserted.scalar_one())
    role_count = len(body["roles"])
    channel_count = len(body["channels"])
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="create",
        table_name="discord_server_snapshots",
        record_id=snapshot_id,
        new_data={"role_count": role_count, "channel_count": channel_count},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    logger.info(
        "[discord_own_server] snapshot tenant=%d id=%d roles=%d channels=%d",
        tenant_id, snapshot_id, role_count, channel_count,
    )
    return OwnServerSnapshotResponse(
        snapshot_id=snapshot_id, role_count=role_count, channel_count=channel_count
    )
