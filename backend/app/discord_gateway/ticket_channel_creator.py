"""チケットチャンネル作成サービス (ADR-091 KPI3 Phase 2).

顧客がボタンを押したとき、専用プライベートチャンネルを冪等に作成する。
gateway bot が閲覧できるようにし、lead が未作成なら同時に作成・紐付けする。

フロー:
  1. DB から tenant_discord_ticket_config を取得
  2. leads で discord_user_id を検索（既存チャンネルID確認）
  3. チャンネルが既存なら Guild から取得して返す（冪等）
  4. 新規なら category 配下に private channel を作成
     - @everyone: view 禁止
     - member: view / send / history 許可
     - staff_role（設定済みなら）: view / send / history 許可
     - gateway bot: view / send / history 許可
  5. ウェルカムメッセージを送信
  6. leads.discord_user_id / leads.discord_guild_channel_id を upsert
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import discord
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import set_tenant_context

logger = logging.getLogger(__name__)

_DEFAULT_WELCOME = "ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。"


@dataclass(frozen=True)
class _LeadState:
    lead_id: int
    discord_guild_channel_id: str | None
    customer_name: str | None


async def get_ticket_config(session: AsyncSession, tenant_id: int) -> dict | None:
    """tenant_discord_ticket_config を取得する。未設定なら None。"""
    result = await session.execute(
        text("""
            SELECT ticket_category_id, ticket_button_channel_id,
                   staff_role_id, welcome_template
            FROM public.tenant_discord_ticket_config
            WHERE tenant_id = :tid
        """),
        {"tid": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        return None
    return dict(row)


async def _get_existing_channel_id(
    session: AsyncSession,
    tenant_id: int,
    discord_user_id: str,
) -> str | None:
    """leads.discord_guild_channel_id を返す。未設定なら None。"""
    schema = f"tenant_{tenant_id:03d}"
    result = await session.execute(
        text(f"""
            SELECT discord_guild_channel_id
            FROM {schema}.leads
            WHERE discord_user_id = :uid
            LIMIT 1
        """),  # noqa: S608
        {"uid": discord_user_id},
    )
    row = result.first()
    if not row or not row[0]:
        return None
    return str(row[0])


async def _get_lead_state(
    session: AsyncSession,
    tenant_id: int,
    discord_user_id: str,
) -> _LeadState | None:
    """discord_user_id から lead を取得する。未存在なら None。"""
    schema = f"tenant_{tenant_id:03d}"
    result = await session.execute(
        text(f"""
            SELECT id, discord_guild_channel_id, customer_name
            FROM {schema}.leads
            WHERE discord_user_id = :uid
            LIMIT 1
        """),  # noqa: S608
        {"uid": discord_user_id},
    )
    row = result.first()
    if not row:
        return None
    return _LeadState(
        lead_id=int(row[0]),
        discord_guild_channel_id=str(row[1]) if row[1] else None,
        customer_name=str(row[2]) if row[2] else None,
    )


async def _ensure_lead_channel(
    session: AsyncSession,
    tenant_id: int,
    lead_id: int,
    discord_user_id: str,
    display_name: str,
) -> None:
    """lead_channels に discord 行が無ければ補完する（冪等）。"""
    schema = f"tenant_{tenant_id:03d}"
    await session.execute(
        text(f"""
            INSERT INTO {schema}.lead_channels (lead_id, platform, external_id, display_name)
            VALUES (:lead_id, 'discord', :external_id, :name)
            ON CONFLICT (platform, external_id) DO NOTHING
        """),
        {"lead_id": lead_id, "external_id": discord_user_id, "name": display_name},
    )


async def _update_lead_channel_id(
    session: AsyncSession,
    tenant_id: int,
    discord_user_id: str,
    channel_id: str,
) -> None:
    """leads.discord_guild_channel_id を更新する。"""
    schema = f"tenant_{tenant_id:03d}"
    await session.execute(
        text(f"""
            UPDATE {schema}.leads
            SET discord_guild_channel_id = :ch_id,
                updated_at = NOW()
            WHERE discord_user_id = :uid
        """),
        {"ch_id": channel_id, "uid": discord_user_id},
    )


def _bot_permission_overwrites(guild: discord.Guild) -> dict[Any, discord.PermissionOverwrite]:
    """gateway bot に必要な可視性を付与する。

    welcome メッセージ送信と受信箱への後続投稿を安定させるため、
    read_message_history / send_messages も付与する。
    """
    bot_member = getattr(guild, "me", None)
    if bot_member is None:
        logger.warning("[ticket] guild.me unavailable; bot overwrite skipped")
        return {}
    return {
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=True,
        ),
    }


def _channel_name_for(member: discord.Member) -> str:
    """チャンネル名を生成する。Discord の命名制限 (小文字・ハイフン) に準拠。"""
    safe_name = "".join(
        c if c.isalnum() or c == "-" else "-"
        for c in member.display_name.lower()
    ).strip("-")[:20] or "customer"
    user_suffix = str(member.id)[-4:]
    return f"ticket-{safe_name}-{user_suffix}"


async def get_or_create_ticket_channel(
    guild: discord.Guild,
    config: dict,
    member: discord.Member,
    tenant_id: int,
    db_factory: Any,
) -> discord.TextChannel | None:
    """チケットチャンネルを冪等に取得または作成する。

    Returns:
        作成/取得したチャンネル。設定不備 or 権限エラーの場合 None。
    """
    category_id = int(config["ticket_category_id"])
    staff_role_id = config.get("staff_role_id")
    welcome_template = config.get("welcome_template") or _DEFAULT_WELCOME

    category = guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        logger.error(
            "[ticket] category not found or not a CategoryChannel: %s tenant=%d",
            category_id,
            tenant_id,
        )
        return None

    discord_user_id = str(member.id)
    customer_name = member.display_name or f"Discord User {discord_user_id}"
    schema = f"tenant_{tenant_id:03d}"

    # 既存チャンネル確認（冪等）
    async with db_factory() as session:
        await set_tenant_context(session, tenant_id)
        lead_state = await _get_lead_state(session, tenant_id, discord_user_id)
        existing_ch_id = lead_state.discord_guild_channel_id if lead_state else None

    if existing_ch_id:
        ch = guild.get_channel(int(existing_ch_id))
        if isinstance(ch, discord.TextChannel):
            logger.info(
                "[ticket] existing channel %s returned for user=%s tenant=%d",
                existing_ch_id,
                discord_user_id,
                tenant_id,
            )
            return ch
        # チャンネルが削除済みの場合は再作成へ
        logger.warning(
            "[ticket] stored channel_id=%s not found in guild, recreating for user=%s",
            existing_ch_id,
            discord_user_id,
        )

    # 権限設定
    overwrites: dict[Any, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
    }
    overwrites.update(_bot_permission_overwrites(guild))
    if staff_role_id:
        staff_role = guild.get_role(int(staff_role_id))
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )
        else:
            logger.warning(
                "[ticket] staff_role_id=%s not found in guild tenant=%d",
                staff_role_id,
                tenant_id,
            )

    channel_name = _channel_name_for(member)
    try:
        new_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"SalesAnchor ticket for {member.display_name}",
        )
    except discord.Forbidden:
        logger.error(
            "[ticket] Forbidden: cannot create channel in category=%s tenant=%d",
            category_id,
            tenant_id,
        )
        return None
    except discord.HTTPException as exc:
        logger.error(
            "[ticket] HTTPException creating channel tenant=%d: %s",
            tenant_id,
            exc,
        )
        return None

    logger.info(
        "[ticket] created channel=%s (%s) for user=%s tenant=%d",
        new_channel.id,
        channel_name,
        discord_user_id,
        tenant_id,
    )

    # ウェルカムメッセージ送信
    try:
        await new_channel.send(welcome_template)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ticket] failed to send welcome message: %s", exc)

    # leads.discord_user_id / leads.discord_guild_channel_id 更新
    async with db_factory() as session:
        await set_tenant_context(session, tenant_id)
        if lead_state is None:
            insert_lead = await session.execute(
                text(f"""
                    INSERT INTO {schema}.leads
                        (tenant_id, customer_name, channel_type, initiative, type, status,
                         discord_user_id, discord_guild_channel_id, created_at, updated_at)
                    VALUES
                        (:tenant_id, :customer_name, 'discord', 'inbound', 'Inbound', 'lead',
                         :discord_user_id, :channel_id, NOW(), NOW())
                    RETURNING id
                """),
                {
                    "tenant_id": tenant_id,
                    "customer_name": customer_name,
                    "discord_user_id": discord_user_id,
                    "channel_id": str(new_channel.id),
                },
            )
            row = insert_lead.first()
            if row is None:
                logger.error(
                    "[ticket] lead insert failed tenant=%d user=%s channel=%s",
                    tenant_id,
                    discord_user_id,
                    new_channel.id,
                )
                await session.rollback()
                return None
            lead_id = int(row[0])
            await _ensure_lead_channel(
                session,
                tenant_id=tenant_id,
                lead_id=lead_id,
                discord_user_id=discord_user_id,
                display_name=customer_name,
            )
        else:
            await _update_lead_channel_id(
                session,
                tenant_id=tenant_id,
                discord_user_id=discord_user_id,
                channel_id=str(new_channel.id),
            )
            await _ensure_lead_channel(
                session,
                tenant_id=tenant_id,
                lead_id=lead_state.lead_id,
                discord_user_id=discord_user_id,
                display_name=lead_state.customer_name or customer_name,
            )
        await session.commit()

    return new_channel
