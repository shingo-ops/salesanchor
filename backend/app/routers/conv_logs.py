"""SA-02 Stage 3: 手動会話ログ API。

エンドポイント:
  POST   /api/v1/leads/{lead_id}/conv-logs        — 手動記録の作成
  GET    /api/v1/leads/{lead_id}/conv-logs        — lead別 会話ログ一覧
  PATCH  /api/v1/leads/{lead_id}/conv-logs/{log_id} — 手動記録の編集
  DELETE /api/v1/leads/{lead_id}/conv-logs/{log_id} — 手動記録の論理削除

設計原則（ADR-096・SA-02-design.md §3）:
  - connection_type='auto' のチャネルには手動入力不可（入口排他）
  - 削除は論理削除のみ（deleted_at SET）。物理削除なし。
  - 保存・編集時に translate_inbound を発火（try/except で非致命的）
  - 編集・削除は record_audit_log で履歴を残す（record_audit_log 流用）
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
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
from app.services.conv_log_writer import _get_company_id_for_lead, _get_contact_id_for_lead

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ConvLogCreate(BaseModel):
    channel_type: str
    direction: str = "inbound"
    content_text: str
    occurred_at: datetime
    allow_duplicate: bool = False  # 重複確認後の強制保存用

    @field_validator("direction")
    @classmethod
    def check_direction(cls, v: str) -> str:
        if v not in ("inbound", "outbound"):
            raise ValueError("direction は 'inbound' または 'outbound' のみ有効")
        return v


class ConvLogUpdate(BaseModel):
    content_text: str | None = None
    occurred_at: datetime | None = None


class ChannelMasterCreate(BaseModel):
    platform: str = Field(..., max_length=20)  # 例: "whatsapp_personal"（meta_messages.platform が VARCHAR(20)）
    display_name: str  # 例: "WhatsApp（個人）"


class ChannelVisibilityUpdate(BaseModel):
    is_hidden: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_conv_log(
    db: AsyncSession,
    tenant_id: int,
    log_id: int,
) -> dict[str, Any] | None:
    """meta_messages から 1 行取得（deleted は除外しない）。"""
    schema = f"tenant_{tenant_id:03d}"
    result = await db.execute(
        text(
            f"SELECT id, lead_id, platform, direction, message_text, "
            f"occurred_at, deleted_at, recorded_by_user_id, message_id, is_manual "
            f"FROM {schema}.meta_messages "
            f"WHERE id = :id"
        ),
        {"id": log_id},
    )
    row = result.first()
    if row is None:
        return None
    return {
        "id": row[0],
        "lead_id": row[1],
        "channel_type": row[2],
        "direction": row[3],
        "content_text": row[4],
        "occurred_at": row[5],
        "deleted_at": row[6],
        "recorded_by_user_id": row[7],
        "message_id": row[8],
        "is_manual": row[9],
    }


async def _fire_translation(
    db: AsyncSession,
    tenant_id: int,
    message_id: str,
    content_text: str,
    direction: str = "inbound",
) -> None:
    """ensure_inbound_translations を発火し、原文の言語を meta_messages に書き戻す。

    outbound（担当者発言）は inbound 専用翻訳を呼ばない（early return）。
    失敗しても呼び出し元の処理は継続する（try/except で非致命的）。
    """
    if direction != "inbound":
        logger.debug("[conv_logs] skip translation for outbound message_id=%s", message_id)
        return

    from app.services.message_translator import ensure_inbound_translations

    schema = f"tenant_{tenant_id:03d}"
    table_ref = f"{schema}.message_translations"

    try:
        await set_tenant_context(db, tenant_id)  # reset_tenant_context 後に RLS 用コンテキストを再設定
        results = await ensure_inbound_translations(
            db=db,
            tenant_id=tenant_id,
            table_ref=table_ref,
            message_id=message_id,
            message_text=content_text,
        )
        result = results.get("ja", next(iter(results.values())))
        await db.execute(
            text(
                f"UPDATE {schema}.meta_messages "
                f"SET original_language = :lang "
                f"WHERE message_id = :mid"
            ),
            {
                "lang": result.original_language,
                "mid": message_id,
            },
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)
        logger.info("[conv_logs] translation done message_id=%s conf=%.2f", message_id, result.confidence)
    except Exception:
        logger.warning(
            "[conv_logs] translation failed channel=conv_log ext_id=%s（処理は継続）",
            message_id, exc_info=True,
        )


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
# POST /api/v1/leads/{lead_id}/conv-logs — 手動記録作成
# ---------------------------------------------------------------------------


@router.post(
    "/leads/{lead_id}/conv-logs",
    status_code=status.HTTP_201_CREATED,
    summary="手動会話ログの作成",
    tags=["conv-logs"],
)
async def create_conv_log(
    lead_id: int,
    body: ConvLogCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await set_tenant_context(db, tenant_id)

    # 入口排他: auto チャネルには手動入力不可
    channel = await channel_masters.get_channel(db, tenant_id, body.channel_type)
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"チャネル '{body.channel_type}' はこのテナントで有効ではありません",
        )
    if channel["connection_type"] == "auto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"チャネル '{body.channel_type}' は自動連携チャネルのため手動入力は禁止です（SA-02-design §4）",
        )

    if len(body.channel_type) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="連絡手段の名前が長すぎます",
        )

    schema = f"tenant_{tenant_id:03d}"

    # 重複チェック: 同一 lead_id + channel_type + content_text + occurred_at ±1h + deleted_at IS NULL
    if not body.allow_duplicate:
        dup_result = await db.execute(
            text(
                f"SELECT id, occurred_at FROM {schema}.meta_messages "
                f"WHERE lead_id = :lead_id "
                f"  AND is_manual = TRUE "
                f"  AND platform = :channel_type "
                f"  AND message_text = :content_text "
                f"  AND deleted_at IS NULL "
                f"  AND occurred_at BETWEEN :oc_min AND :oc_max "
                f"LIMIT 1"
            ),
            {
                "lead_id": lead_id,
                "channel_type": body.channel_type,
                "content_text": body.content_text.strip(),
                "oc_min": body.occurred_at - timedelta(hours=1),
                "oc_max": body.occurred_at + timedelta(hours=1),
            },
        )
        dup_row = dup_result.first()
        if dup_row is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_CONV_LOG",
                    "existing_id": dup_row[0],
                    "existing_occurred_at": dup_row[1].isoformat() if dup_row[1] else None,
                    "message": "同一内容の会話ログが近接日時に既に存在します（重複登録防止）",
                },
            )

    company_id = await _get_company_id_for_lead(db, lead_id)
    contact_id = await _get_contact_id_for_lead(db, lead_id)
    message_id = f"manual_{uuid.uuid4().hex}"

    # 会話の流れは created_at 順で並ぶため、created_at も occurred_at と同じ値にする
    result = await db.execute(
        text(
            f"INSERT INTO {schema}.meta_messages "
            f"(tenant_id, lead_id, company_id, contact_id, platform, direction, message_text, "
            f" occurred_at, created_at, recorded_by_user_id, is_manual, sender_id, sender_name, "
            f" message_id) "
            f"VALUES (:tenant_id, :lead_id, :company_id, :contact_id, :channel_type, :direction, "
            f"        :content_text, :occurred_at, :occurred_at, :user_id, TRUE, :sender_id, NULL, "
            f"        :message_id) "
            f"RETURNING id"
        ),
        {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "company_id": company_id,
            "contact_id": contact_id,
            "channel_type": body.channel_type,
            "direction": body.direction,
            "content_text": body.content_text,
            "occurred_at": body.occurred_at,
            "user_id": current_user.id,
            "sender_id": f"manual:user_{current_user.id}",
            "message_id": message_id,
        },
    )
    log_id = result.scalar_one()
    await record_audit_log(
        db, tenant_id, current_user.id, "create", "meta_messages",
        record_id=log_id,
        new_data={
            "lead_id": lead_id,
            "company_id": company_id,
            "channel_type": body.channel_type,
            "direction": body.direction,
            "content_text": body.content_text,
            "occurred_at": body.occurred_at.isoformat(),
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    # 翻訳を非同期発火（失敗しても 201 を返す）
    if body.content_text:
        await _fire_translation(db, tenant_id, message_id, body.content_text, body.direction)

    return {"id": log_id}


# ---------------------------------------------------------------------------
# GET /api/v1/leads/{lead_id}/conv-logs — 一覧取得
# ---------------------------------------------------------------------------


@router.get(
    "/leads/{lead_id}/conv-logs",
    summary="lead別 会話ログ一覧",
    tags=["conv-logs"],
)
async def list_conv_logs(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await set_tenant_context(db, tenant_id)
    schema = f"tenant_{tenant_id:03d}"
    result = await db.execute(
        text(
            f"SELECT m.id, m.platform, m.direction, m.message_text, "
            f"(SELECT mt.translated_text FROM {schema}.message_translations mt "
            f" WHERE mt.message_id = m.message_id "
            f" ORDER BY (mt.target_language = 'ja') DESC, mt.id ASC LIMIT 1), "
            f"m.occurred_at, m.recorded_by_user_id, m.created_at "
            f"FROM {schema}.meta_messages m "
            f"WHERE m.lead_id = :lead_id AND m.is_manual = TRUE AND m.deleted_at IS NULL "
            f"ORDER BY m.occurred_at ASC, m.id ASC"
        ),
        {"lead_id": lead_id},
    )
    rows = result.fetchall()
    return [
        {
            "id": r[0],
            "channel_type": r[1],
            "direction": r[2],
            "content_text": r[3],
            "translated_text": r[4],
            "occurred_at": r[5].isoformat() if r[5] else None,
            "recorded_by_user_id": r[6],
            "created_at": r[7].isoformat() if r[7] else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# PATCH /api/v1/leads/{lead_id}/conv-logs/{log_id} — 手動記録編集
# ---------------------------------------------------------------------------


@router.patch(
    "/leads/{lead_id}/conv-logs/{log_id}",
    summary="手動会話ログの編集",
    tags=["conv-logs"],
)
async def update_conv_log(
    lead_id: int,
    log_id: int,
    body: ConvLogUpdate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await set_tenant_context(db, tenant_id)

    existing = await _fetch_conv_log(db, tenant_id, log_id)
    if (
        existing is None
        or existing.get("lead_id") != lead_id
        or existing.get("is_manual") not in (True, 1)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:conv_log")
    if existing.get("deleted_at") is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="削除済みの会話ログは編集できません")

    # 変更フィールドのみ更新
    updates: dict[str, Any] = {}
    if body.content_text is not None:
        updates["content_text"] = body.content_text
    if body.occurred_at is not None:
        updates["occurred_at"] = body.occurred_at

    if not updates:
        return {"id": log_id, "updated": False}

    schema = f"tenant_{tenant_id:03d}"
    set_parts: list[str] = []
    if "content_text" in updates:
        set_parts.append("message_text = :content_text")
    if "occurred_at" in updates:
        # 会話の流れは created_at 順で並ぶため、occurred_at と同じ値にそろえる
        set_parts.append("occurred_at = :occurred_at")
        set_parts.append("created_at = :occurred_at")
    set_clause = ", ".join(set_parts)
    await db.execute(
        text(f"UPDATE {schema}.meta_messages SET {set_clause} WHERE id = :id"),
        {**updates, "id": log_id},
    )
    old_data = {
        "content_text": existing["content_text"],
        "occurred_at": existing["occurred_at"].isoformat() if existing["occurred_at"] else None,
    }
    await record_audit_log(
        db, tenant_id, current_user.id, "update", "meta_messages",
        record_id=log_id,
        old_data=old_data,
        new_data={k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in updates.items()},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    # content_text 変更時は再翻訳
    new_text = updates.get("content_text")
    if new_text:
        await _fire_translation(db, tenant_id, existing["message_id"], new_text, existing["direction"])

    return {"id": log_id, "updated": True}


# ---------------------------------------------------------------------------
# DELETE /api/v1/leads/{lead_id}/conv-logs/{log_id} — 論理削除
# ---------------------------------------------------------------------------


@router.delete(
    "/leads/{lead_id}/conv-logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="手動会話ログの論理削除（ゴミ箱方式）",
    tags=["conv-logs"],
)
async def delete_conv_log(
    lead_id: int,
    log_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    await set_tenant_context(db, tenant_id)

    existing = await _fetch_conv_log(db, tenant_id, log_id)
    if (
        existing is None
        or existing.get("lead_id") != lead_id
        or existing.get("is_manual") not in (True, 1)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:conv_log")
    if existing.get("deleted_at") is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="すでに削除済みです")

    schema = f"tenant_{tenant_id:03d}"
    now = datetime.now(tz=timezone.utc)
    await db.execute(
        text(
            f"UPDATE {schema}.meta_messages "
            f"SET deleted_at = :now WHERE id = :id"
        ),
        {"now": now, "id": log_id},
    )
    await record_audit_log(
        db, tenant_id, current_user.id, "delete", "meta_messages",
        record_id=log_id,
        old_data={
            "content_text": existing["content_text"],
            "channel_type": existing["channel_type"],
            "occurred_at": existing["occurred_at"].isoformat() if existing["occurred_at"] else None,
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)


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
