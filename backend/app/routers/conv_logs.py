"""連絡手段の名簿（channel_masters）の API。

エンドポイント:
  GET    /api/v1/channel-masters                        — 名簿の一覧
  POST   /api/v1/admin/channel-masters                  — 窓口の追加（テナント管理者）
  PUT    /api/v1/admin/channel-masters/{id}/visibility  — 会社ごとの「隠す」切り替え
  DELETE /api/v1/admin/channel-masters/{id}             — 窓口の無効化
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    set_tenant_context,
)
from app.database import get_db
from app.models import User
from app.services import channel_masters
from app.services.audit import record_audit_log

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ChannelMasterCreate(BaseModel):
    platform: str = Field(..., max_length=20)  # 例: "whatsapp_personal"（meta_messages.platform が VARCHAR(20)）
    display_name: str  # 例: "WhatsApp（個人）"


class ChannelVisibilityUpdate(BaseModel):
    is_hidden: bool


# ---------------------------------------------------------------------------
# GET /api/v1/channel-masters — チャネルマスタ一覧（UI 判定用）
# ---------------------------------------------------------------------------


@router.get(
    "/channel-masters",
    summary="チャネルマスタ一覧（connection_type 判定用）",
    tags=["conv-logs"],
)
async def list_channel_masters(
    for_: str | None = Query(None, alias="for"),
    keep: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await set_tenant_context(db, tenant_id)
    if for_ == "picker":
        return await channel_masters.list_channels_for_picker(db, tenant_id, keep_platform=keep)
    return await channel_masters.list_channels(db, tenant_id)


# ---------------------------------------------------------------------------
# POST /api/v1/admin/channel-masters — チャネルマスタ追加
# ---------------------------------------------------------------------------


@router.post(
    "/admin/channel-masters",
    status_code=status.HTTP_201_CREATED,
    summary="手動チャネルの追加（テナント管理者）",
    tags=["conv-logs"],
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def create_channel_master(
    body: ChannelMasterCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await set_tenant_context(db, tenant_id)
    existing = await channel_masters.get_channel(db, tenant_id, body.platform)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同じ名前の連絡手段が既にあります",
        )
    result = await db.execute(
        text(
            f"INSERT INTO {channel_masters.CHANNEL_MASTERS_TABLE} "
            f"(tenant_id, platform, display_name, connection_type, conversation_store, "
            f"is_verbatim, conversion_item, is_active) "
            f"VALUES (:tenant_id, :platform, :display_name, 'manual', 'meta_messages', "
            f"TRUE, NULL, true) "
            f"RETURNING id"
        ),
        {"tenant_id": tenant_id, "platform": body.platform, "display_name": body.display_name},
    )
    new_id = result.scalar_one()
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return {"id": new_id}


# ---------------------------------------------------------------------------
# PUT /api/v1/admin/channel-masters/{master_id}/visibility — 会社ごとの「隠す」切り替え
# ---------------------------------------------------------------------------


@router.put(
    "/admin/channel-masters/{master_id}/visibility",
    summary="チャネルを隠す／戻す（テナント管理者）",
    tags=["conv-logs"],
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def update_channel_master_visibility(
    master_id: int,
    body: ChannelVisibilityUpdate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await set_tenant_context(db, tenant_id)
    row = await channel_masters.get_channel_by_id(db, tenant_id, master_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:channel_master")
    if row["connection_type"] == "auto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自動連携チャネルは隠せません",
        )
    before = bool(row["is_hidden"])
    await channel_masters.set_hidden(db, tenant_id, master_id, body.is_hidden, current_user.id)
    await record_audit_log(
        db, tenant_id, current_user.id, "update", "channel_master_tenant_settings",
        record_id=master_id,
        old_data={"is_hidden": before},
        new_data={"is_hidden": body.is_hidden},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return {"id": master_id, "is_hidden": body.is_hidden}


# ---------------------------------------------------------------------------
# DELETE /api/v1/admin/channel-masters/{master_id} — チャネル無効化
# ---------------------------------------------------------------------------


@router.delete(
    "/admin/channel-masters/{master_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="チャネルの無効化（テナント管理者）",
    tags=["conv-logs"],
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def deactivate_channel_master(
    master_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    await set_tenant_context(db, tenant_id)
    row = await channel_masters.get_channel_by_id(db, tenant_id, master_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:channel_master")
    if row["connection_type"] == "auto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自動連携チャネルは削除できません（SA-02-design §4）",
        )
    if row["is_shared"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="共用の連絡手段は消せません。隠す切り替えを使ってください",
        )
    await db.execute(
        text(
            f"UPDATE {channel_masters.CHANNEL_MASTERS_TABLE} "
            f"SET is_active = false, updated_at = CURRENT_TIMESTAMP "
            f"WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": master_id, "tenant_id": tenant_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
