"""Discord Guild 設定 API (Sprint D2 / F5 subset).

テナント admin が Discord サーバー (Guild) の設定を管理するエンドポイント。
ロールマッピングは固定 (Small→Member, Large→Partner) なので設定不要。

API:
  GET    /api/v1/admin/discord-config   — 現在の設定取得
  DELETE /api/v1/admin/discord-config   — Discord 切断（行削除）
  GET    /api/v1/admin/discord-config/own — 自社用の登録の取得
  DELETE /api/v1/admin/discord-config/own — 自社用の登録の解除

権限:
  GET:    tenant.profile.view
  DELETE: tenant.profile.edit
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant, get_current_user, require_permission, reset_tenant_context
from app.database import get_db
from app.models import User
from app.services.audit import record_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()


class DiscordConfigResponse(BaseModel):
    guild_id: str | None = None
    connected_at: str | None = None
    connected_by_staff_name: str | None = None
    role_member: str = "Member"
    role_partner: str = "Partner"


@router.get(
    "/admin/discord-config",
    response_model=DiscordConfigResponse,
    dependencies=[Depends(require_permission("tenant.profile.view"))],
)
async def get_discord_config(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> DiscordConfigResponse:
    """Discord Guild 設定を取得する。未設定の場合は guild_id=None を返す。"""
    result = await db.execute(
        text("""
            SELECT guild_id, updated_at
            FROM public.tenant_discord_config
            WHERE tenant_id = :tid AND purpose = 'customer'
        """),
        {"tid": tenant_id},
    )
    row = result.first()
    guild_id = str(row[0]) if row else None
    connected_at = str(row[1]) if row and row[1] else None
    connected_by_staff_name = None  # staff 名解決は別 PR で対応

    # ロール名は tenant_discord_ticket_config から取得（テーブル未作成時はデフォルト）
    role_member, role_partner = "Member", "Partner"
    try:
        tc = await db.execute(
            text("""
                SELECT COALESCE(small_role_name, 'Member'),
                       COALESCE(large_role_name, 'Partner')
                FROM public.tenant_discord_ticket_config
                WHERE tenant_id = :tid
            """),
            {"tid": tenant_id},
        )
        tc_row = tc.first()
        if tc_row:
            role_member, role_partner = tc_row[0], tc_row[1]
    except Exception:  # noqa: BLE001 — SQLite テスト環境など
        pass

    return DiscordConfigResponse(
        guild_id=guild_id,
        connected_at=connected_at,
        connected_by_staff_name=connected_by_staff_name,
        role_member=role_member,
        role_partner=role_partner,
    )


@router.delete(
    "/admin/discord-config",
    status_code=204,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def delete_discord_config(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> None:
    """Discord 連携を切断する（tenant_discord_config 行を削除）。"""
    await db.execute(
        text("DELETE FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'customer'"),
        {"tid": tenant_id},
    )
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="delete",
        table_name="tenant_discord_config",
        record_id=tenant_id,
        new_data={"source": "discord_disconnect"},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    logger.info(
        "[discord_config] disconnected tenant=%d by user=%d",
        tenant_id, current_user.id,
    )


class DiscordOwnConfigResponse(BaseModel):
    guild_id: str | None = None
    connected_at: str | None = None


@router.get(
    "/admin/discord-config/own",
    response_model=DiscordOwnConfigResponse,
    dependencies=[Depends(require_permission("tenant.profile.view"))],
)
async def get_discord_own_config(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> DiscordOwnConfigResponse:
    """自社用サーバーの登録を取得する。未登録なら guild_id=None。"""
    result = await db.execute(
        text("""
            SELECT guild_id, updated_at
            FROM public.tenant_discord_config
            WHERE tenant_id = :tid AND purpose = 'own'
        """),
        {"tid": tenant_id},
    )
    row = result.first()
    return DiscordOwnConfigResponse(
        guild_id=str(row[0]) if row else None,
        connected_at=str(row[1]) if row and row[1] else None,
    )


@router.delete(
    "/admin/discord-config/own",
    status_code=204,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def delete_discord_own_config(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> None:
    """自社用サーバーの登録を外す（own の行だけ消す。顧客用の行と Discord のサーバーそのものは消えない）。"""
    await db.execute(
        text("DELETE FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
        {"tid": tenant_id},
    )
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="delete",
        table_name="tenant_discord_config",
        record_id=tenant_id,
        new_data={"source": "discord_own_disconnect", "purpose": "own"},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    logger.info(
        "[discord_config] own server disconnected tenant=%d by user=%d",
        tenant_id, current_user.id,
    )
