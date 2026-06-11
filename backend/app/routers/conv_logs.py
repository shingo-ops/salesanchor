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
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    reset_tenant_context,
    set_tenant_context,
)
from app.database import get_db
from app.models import User
from app.services.audit import record_audit_log

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
    platform: str  # 例: "whatsapp_personal"
    display_name: str  # 例: "WhatsApp（個人）"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_channel_master(
    db: AsyncSession,
    tenant_id: int,
    platform: str,
) -> dict[str, Any] | None:
    """channel_masters から接続種別を取得する。"""
    schema = f"tenant_{tenant_id:03d}"
    result = await db.execute(
        text(
            f"SELECT id, platform, display_name, connection_type "
            f"FROM {schema}.channel_masters "
            f"WHERE platform = :platform AND is_active = true"
        ),
        {"platform": platform},
    )
    row = result.first()
    if row is None:
        return None
    return {"id": row[0], "platform": row[1], "display_name": row[2], "connection_type": row[3]}


async def _fetch_conv_log(
    db: AsyncSession,
    tenant_id: int,
    log_id: int,
) -> dict[str, Any] | None:
    """conversation_logs から 1 行取得（deleted は除外しない）。"""
    schema = f"tenant_{tenant_id:03d}"
    result = await db.execute(
        text(
            f"SELECT id, lead_id, channel_type, direction, content_text, "
            f"occurred_at, deleted_at, recorded_by_user_id "
            f"FROM {schema}.conversation_logs "
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
    }


async def _fire_translation(
    db: AsyncSession,
    tenant_id: int,
    log_id: int,
    content_text: str,
) -> None:
    """translate_inbound を発火し、結果を conversation_logs に書き戻す。

    失敗しても呼び出し元の処理は継続する（try/except で非致命的）。
    """
    from app.services.message_translator import translate_inbound

    schema = f"tenant_{tenant_id:03d}"
    table_ref = f"{schema}.message_translations"
    message_id = f"conv_log_{log_id}"

    try:
        result = await translate_inbound(
            db=db,
            tenant_id=tenant_id,
            table_ref=table_ref,
            message_id=message_id,
            message_text=content_text,
            target_language="ja",
        )
        await db.execute(
            text(
                f"UPDATE {schema}.conversation_logs "
                f"SET translated_text = :translated_text, "
                f"    original_language = :original_language "
                f"WHERE id = :id"
            ),
            {
                "translated_text": result.translated_text,
                "original_language": result.original_language,
                "id": log_id,
            },
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)
        logger.info("[conv_logs] translation done log_id=%d conf=%.2f", log_id, result.confidence)
    except Exception:
        logger.warning(
            "[conv_logs] translation failed log_id=%d channel=conv_log ext_id=%s（処理は継続）",
            log_id, message_id, exc_info=True,
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
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await set_tenant_context(db, tenant_id)
    schema = f"tenant_{tenant_id:03d}"
    result = await db.execute(
        text(
            f"SELECT id, platform, display_name, connection_type, is_active "
            f"FROM {schema}.channel_masters "
            f"WHERE is_active = true ORDER BY platform"
        )
    )
    return [
        {
            "id": r[0],
            "platform": r[1],
            "display_name": r[2],
            "connection_type": r[3],
            "is_active": r[4],
        }
        for r in result.fetchall()
    ]


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
    channel = await _get_channel_master(db, tenant_id, body.channel_type)
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

    schema = f"tenant_{tenant_id:03d}"

    # 重複チェック: 同一 lead_id + channel_type + content_text + occurred_at ±1h + deleted_at IS NULL
    if not body.allow_duplicate:
        dup_result = await db.execute(
            text(
                f"SELECT id, occurred_at FROM {schema}.conversation_logs "
                f"WHERE lead_id = :lead_id "
                f"  AND channel_type = :channel_type "
                f"  AND content_text = :content_text "
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

    result = await db.execute(
        text(
            f"INSERT INTO {schema}.conversation_logs "
            f"(tenant_id, lead_id, channel_type, direction, content_text, "
            f" occurred_at, recorded_by_user_id) "
            f"VALUES (:tenant_id, :lead_id, :channel_type, :direction, :content_text, "
            f"        :occurred_at, :user_id) "
            f"RETURNING id"
        ),
        {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "channel_type": body.channel_type,
            "direction": body.direction,
            "content_text": body.content_text,
            "occurred_at": body.occurred_at,
            "user_id": current_user.id,
        },
    )
    log_id = result.scalar_one()
    await record_audit_log(
        db, tenant_id, current_user.id, "create", "conversation_logs",
        record_id=log_id,
        new_data={
            "lead_id": lead_id,
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
        await _fire_translation(db, tenant_id, log_id, body.content_text)

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
            f"SELECT id, channel_type, direction, content_text, translated_text, "
            f"occurred_at, recorded_by_user_id, created_at "
            f"FROM {schema}.conversation_logs "
            f"WHERE lead_id = :lead_id AND deleted_at IS NULL "
            f"ORDER BY occurred_at ASC"
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
    if existing is None or existing.get("lead_id") != lead_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会話ログが見つかりません")
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
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    await db.execute(
        text(f"UPDATE {schema}.conversation_logs SET {set_clause} WHERE id = :id"),
        {**updates, "id": log_id},
    )
    old_data = {
        "content_text": existing["content_text"],
        "occurred_at": existing["occurred_at"].isoformat() if existing["occurred_at"] else None,
    }
    await record_audit_log(
        db, tenant_id, current_user.id, "update", "conversation_logs",
        record_id=log_id,
        old_data=old_data,
        new_data={k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in updates.items()},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    # content_text 変更時は再翻訳
    new_text = updates.get("content_text")
    if new_text:
        await _fire_translation(db, tenant_id, log_id, new_text)

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
    if existing is None or existing.get("lead_id") != lead_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会話ログが見つかりません")
    if existing.get("deleted_at") is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="すでに削除済みです")

    schema = f"tenant_{tenant_id:03d}"
    now = datetime.now(tz=timezone.utc)
    await db.execute(
        text(
            f"UPDATE {schema}.conversation_logs "
            f"SET deleted_at = :now WHERE id = :id"
        ),
        {"now": now, "id": log_id},
    )
    await record_audit_log(
        db, tenant_id, current_user.id, "delete", "conversation_logs",
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
)
async def create_channel_master(
    body: ChannelMasterCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await set_tenant_context(db, tenant_id)
    schema = f"tenant_{tenant_id:03d}"
    result = await db.execute(
        text(
            f"INSERT INTO {schema}.channel_masters "
            f"(platform, display_name, connection_type, is_active) "
            f"VALUES (:platform, :display_name, 'manual', true) "
            f"RETURNING id"
        ),
        {"platform": body.platform, "display_name": body.display_name},
    )
    new_id = result.scalar_one()
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return {"id": new_id}


# ---------------------------------------------------------------------------
# DELETE /api/v1/admin/channel-masters/{master_id} — チャネル無効化
# ---------------------------------------------------------------------------


@router.delete(
    "/admin/channel-masters/{master_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="チャネルの無効化（テナント管理者）",
    tags=["conv-logs"],
)
async def deactivate_channel_master(
    master_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    await set_tenant_context(db, tenant_id)
    schema = f"tenant_{tenant_id:03d}"
    result = await db.execute(
        text(f"SELECT id, connection_type FROM {schema}.channel_masters WHERE id = :id"),
        {"id": master_id},
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チャネルが見つかりません")
    if row[1] == "auto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自動連携チャネルは削除できません（SA-02-design §4）",
        )
    await db.execute(
        text(f"UPDATE {schema}.channel_masters SET is_active = false WHERE id = :id"),
        {"id": master_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
