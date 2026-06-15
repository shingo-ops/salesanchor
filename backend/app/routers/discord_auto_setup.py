"""Discord Bot招待後サーバー初期構築ウィザード (ADR-091 拡張).

Bot招待後、Sales Anchor から1ボタンで Discord サーバーを自動構築する。

API:
  POST /api/v1/admin/discord/auto-setup — カテゴリ・チャンネル・ロール・チケットボタンを自動作成

前提:
  - Bot が guild に招待済み（tenant_discord_config.guild_id 設定済み）
  - DISCORD_BOT_TOKEN_{tenant_id} 環境変数設定済み
  - 既存 permissions=268504082 で MANAGE_CHANNELS / MANAGE_ROLES / SEND_MESSAGES をカバー済み

冪等動作:
  - ロール: 名前で検索し存在すればスキップ（_get_or_create_role と同一パターン）
  - カテゴリ/チャンネル: 保存済みIDが Discord に存在すればスキップ・削除済みなら再作成
  - 2回目以降も安全に実行可能

MVP対象外:
  - Staff ロール自動付与（手動でDiscord設定、role-order-guide.md 参照）
  - voice チャンネル
  - チャンネル名カスタマイズ UI
"""
from __future__ import annotations

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

# Discord 権限ビット
_VIEW_CHANNEL = 1024
_SEND_MESSAGES = 2048
_READ_MESSAGE_HISTORY = 65536

# Botロール順ガイド URL
_ROLE_ORDER_GUIDE_URL = (
    "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/discord-role-order-guide.md"
)


class AutoSetupStep(BaseModel):
    step: str
    status: str  # "created" | "skipped" | "posted" | "failed"
    discord_id: str | None = None
    error: str | None = None


class AutoSetupResponse(BaseModel):
    status: str  # "completed" | "partial" | "failed"
    steps: list[AutoSetupStep]
    role_order_guide_url: str = _ROLE_ORDER_GUIDE_URL
    error_hint: str | None = None


@router.post(
    "/admin/discord/auto-setup",
    response_model=AutoSetupResponse,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def run_auto_setup(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> AutoSetupResponse:
    """Discord サーバー自動セットアップを実行する。

    ロール・カテゴリ・チャンネル・チケットボタンを順番に作成し、
    作成したIDを tenant_discord_ticket_config に upsert する（ADR-072準拠）。
    """
    # 1. guild_id 取得
    result = await db.execute(
        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(
            status_code=422,
            detail="Discord サーバーが未接続です。先に Bot を招待してください。",
        )
    guild_id = str(row[0])

    # 2. Bot トークン取得
    bot_token: str | None = os.environ.get(f"DISCORD_BOT_TOKEN_{tenant_id}")
    if not bot_token:
        raise HTTPException(
            status_code=503,
            detail=f"Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN_{tenant_id} を確認してください。",
        )

    # 3. 既存設定取得（冪等チェック用）
    cfg_result = await db.execute(
        text("""
            SELECT ticket_category_id, ticket_button_channel_id, staff_role_id,
                   small_channel_id, large_channel_id,
                   COALESCE(small_role_name, 'Member')  AS small_role_name,
                   COALESCE(large_role_name, 'Partner') AS large_role_name
            FROM public.tenant_discord_ticket_config
            WHERE tenant_id = :tid
        """),
        {"tid": tenant_id},
    )
    cfg = cfg_result.mappings().first()

    existing_category_id = str(cfg["ticket_category_id"]) if cfg and cfg["ticket_category_id"] else None
    existing_ticket_ch_id = str(cfg["ticket_button_channel_id"]) if cfg and cfg["ticket_button_channel_id"] else None
    existing_staff_role_id = str(cfg["staff_role_id"]) if cfg and cfg["staff_role_id"] else None
    existing_small_ch_id = str(cfg["small_channel_id"]) if cfg and cfg["small_channel_id"] else None
    existing_large_ch_id = str(cfg["large_channel_id"]) if cfg and cfg["large_channel_id"] else None
    small_role_name: str = cfg["small_role_name"] if cfg else "Member"
    large_role_name: str = cfg["large_role_name"] if cfg else "Partner"

    # 4. Discord 上の既存ロール・チャンネル一覧取得（冪等チェック）
    try:
        existing_roles: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/roles",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
        existing_channels: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/channels",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
    except DiscordAPIError as exc:
        raise HTTPException(status_code=502, detail=f"Discord API 接続エラー: {exc}") from exc

    # ---- ステップ実行 ----
    steps: list[AutoSetupStep] = []

    # 保存するID（Noneは既存値を引き継ぐ）
    staff_role_id = existing_staff_role_id
    category_id = existing_category_id
    ticket_ch_id = existing_ticket_ch_id
    small_ch_id = existing_small_ch_id
    large_ch_id = existing_large_ch_id

    # Step 1a: Sales Anchor Staff ロール
    step = await _get_or_create_role_step(
        step_name="role_staff",
        role_name="Sales Anchor Staff",
        existing_roles=existing_roles,
        guild_id=guild_id,
        bot_token=bot_token,
    )
    steps.append(step)
    if step.discord_id:
        staff_role_id = step.discord_id

    # Step 1b: Partner ロール（large_role_name、IDは保存しない）
    step = await _get_or_create_role_step(
        step_name="role_partner",
        role_name=large_role_name,
        existing_roles=existing_roles,
        guild_id=guild_id,
        bot_token=bot_token,
    )
    steps.append(step)
    partner_role_id: str | None = step.discord_id

    # Step 1c: Member ロール（small_role_name、IDは保存しない）
    step = await _get_or_create_role_step(
        step_name="role_member",
        role_name=small_role_name,
        existing_roles=existing_roles,
        guild_id=guild_id,
        bot_token=bot_token,
    )
    steps.append(step)
    member_role_id: str | None = step.discord_id

    # Step 2a: "Sales Anchor" カテゴリ（@everyone view禁止）
    step = await _get_or_create_channel_step(
        step_name="category",
        channel_name="Sales Anchor",
        channel_type=4,  # GUILD_CATEGORY
        parent_id=None,
        existing_id=existing_category_id,
        existing_channels=existing_channels,
        guild_id=guild_id,
        bot_token=bot_token,
        permission_overwrites=[
            {
                "id": guild_id,  # @everyone role id == guild_id
                "type": 0,
                "allow": "0",
                "deny": str(_VIEW_CHANNEL | _SEND_MESSAGES | _READ_MESSAGE_HISTORY),
            },
        ],
    )
    steps.append(step)
    if step.discord_id:
        category_id = step.discord_id

    # カテゴリが存在しない場合は配下チャンネルを作成しない（ルート直下防止）
    if not category_id:
        _no_category_msg = "カテゴリ作成に失敗したためチャンネルを作成できません"
        steps.append(AutoSetupStep(step="ch_ticket", status="failed", error=_no_category_msg))
        steps.append(AutoSetupStep(step="ch_member", status="failed", error=_no_category_msg))
        steps.append(AutoSetupStep(step="ch_partner", status="failed", error=_no_category_msg))
        steps.append(AutoSetupStep(step="button", status="failed", error=_no_category_msg))
    else:
        # Step 3a: "ticket-start" チャンネル（@everyone view可・Staff送信可）
        ch_ticket_step = await _get_or_create_channel_step(
            step_name="ch_ticket",
            channel_name="ticket-start",
            channel_type=0,  # GUILD_TEXT
            parent_id=category_id,
            existing_id=existing_ticket_ch_id,
            existing_channels=existing_channels,
            guild_id=guild_id,
            bot_token=bot_token,
            permission_overwrites=_ticket_ch_overwrites(guild_id, staff_role_id),
        )
        steps.append(ch_ticket_step)
        if ch_ticket_step.discord_id:
            ticket_ch_id = ch_ticket_step.discord_id

        # Step 3b: "member-announcements" チャンネル（Member/Partner view可・Staff送信可）
        step = await _get_or_create_channel_step(
            step_name="ch_member",
            channel_name="member-announcements",
            channel_type=0,
            parent_id=category_id,
            existing_id=existing_small_ch_id,
            existing_channels=existing_channels,
            guild_id=guild_id,
            bot_token=bot_token,
            permission_overwrites=_member_announcements_overwrites(
                guild_id, member_role_id, partner_role_id, staff_role_id
            ),
        )
        steps.append(step)
        if step.discord_id:
            small_ch_id = step.discord_id

        # Step 3c: "partner-announcements" チャンネル（Partner view可・Staff送信可）
        step = await _get_or_create_channel_step(
            step_name="ch_partner",
            channel_name="partner-announcements",
            channel_type=0,
            parent_id=category_id,
            existing_id=existing_large_ch_id,
            existing_channels=existing_channels,
            guild_id=guild_id,
            bot_token=bot_token,
            permission_overwrites=_partner_announcements_overwrites(
                guild_id, partner_role_id, staff_role_id
            ),
        )
        steps.append(step)
        if step.discord_id:
            large_ch_id = step.discord_id

        # Step 4a: チケットボタン投稿
        # ch_ticket が新規作成時のみ POST。スキップ・失敗時はボタンも同じ扱いにする
        if ch_ticket_step.status == "created":
            step = await _post_ticket_button_step(
                step_name="button",
                ticket_ch_id=ticket_ch_id,
                bot_token=bot_token,
            )
        elif ch_ticket_step.status == "skipped":
            step = AutoSetupStep(step="button", status="skipped", discord_id=None)
        else:
            step = AutoSetupStep(
                step="button", status="failed",
                error="ticket-start チャンネルの作成に失敗したためボタン投稿をスキップしました。",
            )
        steps.append(step)

    # ---- DB 保存（COALESCE で失敗ステップの既存値を保持）----
    # 初回実行（cfg=None）かつ NOT NULL カラム（ticket_category_id / ticket_button_channel_id）が
    # 揃っていない場合は INSERT をスキップする（Cause E: NotNullViolationError 防止）。
    # UPDATE 経路（ON CONFLICT）は COALESCE で安全なため常時実行。
    _can_upsert = cfg is not None or (category_id is not None and ticket_ch_id is not None)
    if _can_upsert:
        await db.execute(
            text("""
                INSERT INTO public.tenant_discord_ticket_config
                    (tenant_id, staff_role_id, ticket_category_id, ticket_button_channel_id,
                     small_channel_id, large_channel_id, updated_at)
                VALUES
                    (:tid, :staff_role_id, :category_id, :ticket_ch_id,
                     :small_ch_id, :large_ch_id, NOW())
                ON CONFLICT (tenant_id) DO UPDATE SET
                    staff_role_id            = COALESCE(EXCLUDED.staff_role_id,
                                                        tenant_discord_ticket_config.staff_role_id),
                    ticket_category_id       = COALESCE(EXCLUDED.ticket_category_id,
                                                        tenant_discord_ticket_config.ticket_category_id),
                    ticket_button_channel_id = COALESCE(EXCLUDED.ticket_button_channel_id,
                                                        tenant_discord_ticket_config.ticket_button_channel_id),
                    small_channel_id         = COALESCE(EXCLUDED.small_channel_id,
                                                        tenant_discord_ticket_config.small_channel_id),
                    large_channel_id         = COALESCE(EXCLUDED.large_channel_id,
                                                        tenant_discord_ticket_config.large_channel_id),
                    updated_at               = NOW()
            """),
            {
                "tid": tenant_id,
                "staff_role_id": staff_role_id,
                "category_id": category_id,
                "ticket_ch_id": ticket_ch_id,
                "small_ch_id": small_ch_id,
                "large_ch_id": large_ch_id,
            },
        )
        await record_audit_log(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            action="create",
            table_name="discord_auto_setup",
            record_id=tenant_id,
            new_data={
                "staff_role_id": staff_role_id,
                "ticket_category_id": category_id,
                "ticket_button_channel_id": ticket_ch_id,
                "small_channel_id": small_ch_id,
                "large_channel_id": large_ch_id,
            },
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072

    # ---- 全体ステータス決定 ----
    failed_steps = [s for s in steps if s.status == "failed"]
    if not failed_steps:
        overall = "completed"
        error_hint = None
    elif len(failed_steps) == len(steps):
        overall = "failed"
        error_hint = "Bot ロールの権限を確認してください。"
    else:
        overall = "partial"
        error_hint = (
            "一部のステップが失敗しました。Bot ロールの権限と Discord サーバーの設定を確認してください。"
        )

    logger.info(
        "[discord_auto_setup] tenant=%d guild=%s status=%s steps=%s",
        tenant_id, guild_id, overall,
        [{"step": s.step, "status": s.status} for s in steps],
    )
    return AutoSetupResponse(
        status=overall,
        steps=steps,
        role_order_guide_url=_ROLE_ORDER_GUIDE_URL,
        error_hint=error_hint,
    )


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------


def _find_role_id(roles: list[dict[str, Any]], name: str) -> str | None:
    for role in roles:
        if role.get("name") == name:
            return str(role["id"])
    return None


def _find_channel(
    channels: list[dict[str, Any]],
    name: str,
    channel_type: int,
    parent_id: str | None = None,
) -> str | None:
    """Discord チャンネル/カテゴリを名前・type・parent_id で検索する。

    カテゴリ (type=4) は parent_id=None で検索。
    テキストチャンネル (type=0) は name + type + parent_id が全一致した場合のみ返す。
    """
    for ch in channels:
        if ch.get("name") != name:
            continue
        if ch.get("type") != channel_type:
            continue
        ch_parent = ch.get("parent_id")
        if parent_id is None:
            if ch_parent is not None:
                continue  # カテゴリ: parent なしのみマッチ
        else:
            if ch_parent is None or str(ch_parent) != parent_id:
                continue  # テキストチャンネル: parent_id が一致しないとスキップ
        return str(ch["id"])
    return None


async def _get_or_create_role_step(
    *,
    step_name: str,
    role_name: str,
    existing_roles: list[dict[str, Any]],
    guild_id: str,
    bot_token: str,
) -> AutoSetupStep:
    """ロールを名前で検索し、存在すればスキップ・なければ作成する。"""
    existing_id = _find_role_id(existing_roles, role_name)
    if existing_id:
        return AutoSetupStep(step=step_name, status="skipped", discord_id=existing_id)

    try:
        created = await discord_api_request(
            method="POST",
            path=f"/guilds/{guild_id}/roles",
            bot_token=bot_token,
            json={"name": role_name},
            expected_statuses=(200,),
        )
        assert created is not None
        return AutoSetupStep(step=step_name, status="created", discord_id=str(created["id"]))
    except DiscordAPIError as exc:
        logger.warning(
            "[discord_auto_setup] role creation failed step=%s role=%s: %s",
            step_name, role_name, exc,
        )
        return AutoSetupStep(step=step_name, status="failed", error=str(exc))


async def _get_or_create_channel_step(
    *,
    step_name: str,
    channel_name: str,
    channel_type: int,
    parent_id: str | None,
    existing_id: str | None,
    existing_channels: list[dict[str, Any]],
    guild_id: str,
    bot_token: str,
    permission_overwrites: list[dict[str, Any]],
) -> AutoSetupStep:
    """チャンネル/カテゴリを冪等に作成する。

    1. DB保存済みIDが Discord に存在する場合はスキップ。
    2. DB未保存でも Discord 上に同名・同type・同parent_id のチャンネルがあればスキップ
       （初回失敗→DB未保存→再実行時の重複作成防止）。
    3. どちらでもなければ新規作成。
    """
    existing_channel_ids = {str(ch["id"]) for ch in existing_channels}

    # 1. DB保存済みID が Discord 上に存在するならスキップ
    if existing_id and existing_id in existing_channel_ids:
        return AutoSetupStep(step=step_name, status="skipped", discord_id=existing_id)

    # 2. 名前+type+parent_id で Discord 上に既存チャンネルを検索（DB未保存対応）
    found_id = _find_channel(existing_channels, channel_name, channel_type, parent_id)
    if found_id:
        return AutoSetupStep(step=step_name, status="skipped", discord_id=found_id)

    payload: dict[str, Any] = {
        "name": channel_name,
        "type": channel_type,
        "permission_overwrites": permission_overwrites,
    }
    if parent_id:
        payload["parent_id"] = parent_id

    try:
        created = await discord_api_request(
            method="POST",
            path=f"/guilds/{guild_id}/channels",
            bot_token=bot_token,
            json=payload,
            expected_statuses=(200, 201),
        )
        assert created is not None
        return AutoSetupStep(step=step_name, status="created", discord_id=str(created["id"]))
    except DiscordAPIError as exc:
        logger.warning(
            "[discord_auto_setup] channel creation failed step=%s name=%s: %s",
            step_name, channel_name, exc,
        )
        return AutoSetupStep(step=step_name, status="failed", error=str(exc))


async def _post_ticket_button_step(
    *,
    step_name: str,
    ticket_ch_id: str | None,
    bot_token: str,
) -> AutoSetupStep:
    """ticket-start チャンネルにチケット開始ボタンを投稿する。"""
    if not ticket_ch_id:
        return AutoSetupStep(
            step=step_name,
            status="failed",
            error="ticket-start チャンネルが未作成のためボタン投稿をスキップしました。",
        )

    payload = {
        "content": "サポートが必要な場合は下のボタンを押してください。",
        "components": [
            {
                "type": 1,  # ActionRow
                "components": [
                    {
                        "type": 2,  # Button
                        "style": 1,  # Primary（青）
                        "label": "チケットを開く",
                        "custom_id": "ticket_open",
                        "emoji": {"name": "🎫"},
                    }
                ],
            }
        ],
    }
    try:
        created = await discord_api_request(
            method="POST",
            path=f"/channels/{ticket_ch_id}/messages",
            bot_token=bot_token,
            json=payload,
            expected_statuses=(200, 201),
        )
        assert created is not None
        return AutoSetupStep(step=step_name, status="posted", discord_id=str(created["id"]))
    except DiscordAPIError as exc:
        logger.warning(
            "[discord_auto_setup] button post failed ch=%s: %s",
            ticket_ch_id, exc,
        )
        return AutoSetupStep(step=step_name, status="failed", error=str(exc))


# ---------------------------------------------------------------------------
# 権限オーバーライドビルダー
# ---------------------------------------------------------------------------


def _ticket_ch_overwrites(
    guild_id: str,
    staff_role_id: str | None,
) -> list[dict[str, Any]]:
    """ticket-start: @everyone view可（チケットを開くためのチャンネル）、Staff送信可。"""
    overwrites: list[dict[str, Any]] = [
        {
            "id": guild_id,  # @everyone
            "type": 0,
            "allow": str(_VIEW_CHANNEL | _READ_MESSAGE_HISTORY),
            "deny": str(_SEND_MESSAGES),
        },
    ]
    if staff_role_id:
        overwrites.append({
            "id": staff_role_id,
            "type": 0,
            "allow": str(_SEND_MESSAGES),
            "deny": "0",
        })
    return overwrites


def _member_announcements_overwrites(
    guild_id: str,
    member_role_id: str | None,
    partner_role_id: str | None,
    staff_role_id: str | None,
) -> list[dict[str, Any]]:
    """member-announcements 権限設計（design.md §2 参照）。

    | 対象           | view | read_history | send |
    |---------------|------|-------------|------|
    | @everyone     | deny | deny        | deny |
    | Member        | allow| allow       | deny |
    | Partner       | allow| allow       | deny |  ← Large顧客のみ付与の可能性あり
    | Staff         | allow| allow       | allow|
    """
    overwrites: list[dict[str, Any]] = [
        {
            "id": guild_id,  # @everyone
            "type": 0,
            "allow": "0",
            "deny": str(_VIEW_CHANNEL | _SEND_MESSAGES | _READ_MESSAGE_HISTORY),
        },
    ]
    if member_role_id:
        overwrites.append({
            "id": member_role_id,
            "type": 0,
            "allow": str(_VIEW_CHANNEL | _READ_MESSAGE_HISTORY),
            "deny": str(_SEND_MESSAGES),
        })
    if partner_role_id:
        overwrites.append({
            "id": partner_role_id,
            "type": 0,
            "allow": str(_VIEW_CHANNEL | _READ_MESSAGE_HISTORY),
            "deny": str(_SEND_MESSAGES),
        })
    if staff_role_id:
        overwrites.append({
            "id": staff_role_id,
            "type": 0,
            "allow": str(_VIEW_CHANNEL | _SEND_MESSAGES | _READ_MESSAGE_HISTORY),
            "deny": "0",
        })
    return overwrites


def _partner_announcements_overwrites(
    guild_id: str,
    partner_role_id: str | None,
    staff_role_id: str | None,
) -> list[dict[str, Any]]:
    """partner-announcements: Partner view可・Staff送信可。"""
    overwrites: list[dict[str, Any]] = [
        {
            "id": guild_id,  # @everyone
            "type": 0,
            "allow": "0",
            "deny": str(_VIEW_CHANNEL | _SEND_MESSAGES | _READ_MESSAGE_HISTORY),
        },
    ]
    if partner_role_id:
        overwrites.append({
            "id": partner_role_id,
            "type": 0,
            "allow": str(_VIEW_CHANNEL | _READ_MESSAGE_HISTORY),
            "deny": str(_SEND_MESSAGES),
        })
    if staff_role_id:
        overwrites.append({
            "id": staff_role_id,
            "type": 0,
            "allow": str(_VIEW_CHANNEL | _SEND_MESSAGES | _READ_MESSAGE_HISTORY),
            "deny": "0",
        })
    return overwrites
