"""閲覧者の Discord 受付（ADR-1019 段4c / D6）。

ボタン → 申込コードの小窓 → 照合 → 本人だけの部屋の作成 → トライアル開始。
顧客用チケット（ticket_channel_creator.py）とは処理を分け、部屋の部品だけを共有する。
leads には入れない。ログに email・コード・パスワード・表示名を出さない。
"""
from __future__ import annotations

import asyncio
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

import discord
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth.password_policy import check_password
from app.auth.passwords import hash_password
from app.auth.viewer_signup_code import normalize_signup_code, signup_code_sha256
from app.cache import get_redis
from app.discord_gateway import private_channel
from app.discord_gateway import viewer_bot_texts as T

logger = logging.getLogger(__name__)

_TRIAL_DAYS = 14
_FAIL_LIMIT = 5
_FAIL_WINDOW_SEC = 3600
_SWEEP_MAX_DELETE = 10
_ROOM_NAME_RE = re.compile(r"^trial-(\d+)$")
_ROOM_TOPIC_RE = re.compile(r"^在庫集計ツールのお試し（番号 (\d+)）$")  # fullmatch で使う。T.ROOM_TOPIC と同じ形
_ROOM_NAME_MAX = 100


def _room_name(viewer_id: int, line_name: str | None) -> str:
    name = (line_name or "").strip()[:_ROOM_NAME_MAX]
    return name or f"trial-{viewer_id}"


class ViewerDiscordConfig(NamedTuple):
    guild_id: str
    reception_channel_id: str
    ticket_category_id: str
    staff_role_id: str


async def load_config(db_factory: Any) -> ViewerDiscordConfig | None:
    async with db_factory() as session:
        row = (
            await session.execute(
                text(
                    "SELECT guild_id, reception_channel_id, ticket_category_id, staff_role_id "
                    "FROM public.viewer_discord_config WHERE id = 1"
                )
            )
        ).first()
    if row is None:
        return None
    return ViewerDiscordConfig(row[0], row[1], row[2], row[3])


class ViewerTrialCodeModal(discord.ui.Modal):
    """申込コードの入力小窓。応答は on_interaction 側（viewer_trial.handle_interaction）で行う。"""

    code = discord.ui.TextInput(
        label=T.CODE_INPUT_LABEL,
        custom_id=T.CODE_INPUT_CUSTOM_ID,
        min_length=16,
        max_length=19,
        required=True,
    )

    def __init__(self) -> None:
        super().__init__(title=T.CODE_MODAL_TITLE, custom_id=T.CODE_MODAL_CUSTOM_ID, timeout=900)


async def _reply(interaction: Any, message: str, deferred: bool) -> None:
    try:
        if deferred:
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] reply failed")


async def handle_interaction(interaction: Any, db_factory: Any) -> None:
    custom_id = (interaction.data or {}).get("custom_id", "")
    if custom_id == T.OPEN_BUTTON_CUSTOM_ID:
        handler = on_open
    elif custom_id == T.CODE_MODAL_CUSTOM_ID:
        handler = on_code_submit
    else:
        return

    guild = interaction.guild
    member = interaction.user
    if guild is None or not isinstance(member, discord.Member):
        await _reply(interaction, T.WRONG_SERVER, False)
        return
    try:
        config = await load_config(db_factory)
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] config load failed")
        await _reply(interaction, T.TRY_LATER, False)
        return
    if config is None or str(guild.id) != config.guild_id:
        await _reply(interaction, T.WRONG_SERVER, False)
        return
    await handler(interaction, db_factory, config)


async def _create_room(
    guild: Any, member: Any, config: ViewerDiscordConfig, viewer_id: int, line_name: str | None
):
    category = private_channel.resolve_category(
        guild, int(config.ticket_category_id), "viewer_trial"
    )
    if category is None:
        return None
    fallback_name = f"trial-{viewer_id}"
    name = _room_name(viewer_id, line_name)
    topic = T.ROOM_TOPIC.format(viewer_id=viewer_id)

    async def _make(room_name: str):
        return await private_channel.create_private_text_channel(
            guild,
            category,
            member,
            config.staff_role_id,
            name=room_name,
            reason="SalesAnchor viewer trial",
            log_context="viewer_trial",
            topic=topic,
            log_name=fallback_name,
        )

    channel = await _make(name)
    if channel is None and name != fallback_name:
        channel = await _make(fallback_name)
    return channel


async def _discard_room(channel: Any) -> None:
    if channel is None:
        return
    try:
        await channel.delete(reason="SalesAnchor viewer trial rollback")
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] rollback channel delete failed channel=%s", channel.id)


async def on_open(interaction: Any, db_factory: Any, config: ViewerDiscordConfig) -> None:
    guild = interaction.guild
    member = interaction.user
    try:
        async with db_factory() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT id, email, discord_channel_id, line_name FROM public.viewer_accounts "
                        "WHERE discord_user_id = :uid"
                    ),
                    {"uid": str(member.id)},
                )
            ).first()
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] open lookup failed")
        await _reply(interaction, T.TRY_LATER, False)
        return

    if row is None:
        await interaction.response.send_modal(ViewerTrialCodeModal())
        return

    viewer_id, email, channel_id = int(row[0]), row[1], row[2]
    await interaction.response.defer(ephemeral=True, thinking=True)
    channel = guild.get_channel(int(channel_id)) if channel_id else None
    if isinstance(channel, discord.TextChannel):
        await _reply(interaction, T.YOUR_ROOM.format(channel_id=channel.id), True)
        return

    new_channel = await _create_room(guild, member, config, viewer_id, row[3])
    if new_channel is None:
        await _reply(interaction, T.TRY_LATER, True)
        return
    try:
        async with db_factory() as session:
            await session.execute(
                text(
                    "UPDATE public.viewer_accounts SET discord_channel_id = :ch, "
                    "updated_at = now() WHERE id = :id"
                ),
                {"ch": str(new_channel.id), "id": viewer_id},
            )
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] room recreate save failed viewer=%d", viewer_id)
        await _discard_room(new_channel)
        await _reply(interaction, T.TRY_LATER, True)
        return
    try:
        await new_channel.send(T.ROOM_RECREATED.format(email=email))
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] recreated post failed viewer=%d", viewer_id)
    await _reply(interaction, T.YOUR_ROOM.format(channel_id=new_channel.id), True)


def _find_input_value(components: Any, custom_id: str) -> str | None:
    if not isinstance(components, list):
        return None
    for comp in components:
        if not isinstance(comp, dict):
            continue
        if comp.get("custom_id") == custom_id and isinstance(comp.get("value"), str):
            return comp["value"]
        found = _find_input_value(comp.get("components"), custom_id)
        if found is not None:
            return found
    return None


async def _count_failure(redis: Any, key: str) -> None:
    n = await redis.incr(key)
    if n == 1:
        await redis.expire(key, _FAIL_WINDOW_SEC)


async def on_code_submit(interaction: Any, db_factory: Any, config: ViewerDiscordConfig) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    member = interaction.user

    raw = _find_input_value((interaction.data or {}).get("components"), T.CODE_INPUT_CUSTOM_ID)
    if raw is None:
        await _reply(interaction, T.CODE_INVALID, True)
        return

    redis = get_redis()
    if redis is None:
        await _reply(interaction, T.TRY_LATER, True)
        return
    key = f"viewer_code_fail:{member.id}"
    try:
        if int(await redis.get(key) or 0) >= _FAIL_LIMIT:
            await _reply(interaction, T.TOO_MANY_ATTEMPTS, True)
            return
        normalized = normalize_signup_code(raw)
        if normalized is None:
            await _count_failure(redis, key)
            await _reply(interaction, T.CODE_INVALID, True)
            return
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] attempt counter failed")
        await _reply(interaction, T.TRY_LATER, True)
        return

    channel = None
    try:
        async with db_factory() as session:
            try:
                got = (
                    await session.execute(
                        text(
                            "DELETE FROM public.viewer_login_tokens "
                            "WHERE token_sha256 = :h AND purpose = 'signup_code' "
                            "AND expires_at > now() RETURNING viewer_account_id"
                        ),
                        {"h": signup_code_sha256(normalized)},
                    )
                ).first()
                if got is None:
                    await session.rollback()
                    await _count_failure(redis, key)
                    await _reply(interaction, T.CODE_INVALID, True)
                    return
                vid = int(got[0])
                v = (
                    await session.execute(
                        text(
                            "SELECT id, email, status, trial_expires_at, discord_user_id, line_name "
                            "FROM public.viewer_accounts WHERE id = :vid FOR UPDATE"
                        ),
                        {"vid": vid},
                    )
                ).first()
                if (
                    v is None
                    or v[2] not in ("pending", "trial", "active")
                    or v[4] is not None  # もう Discord と結び付いている
                ):
                    await session.rollback()
                    await _count_failure(redis, key)
                    await _reply(interaction, T.CODE_INVALID, True)
                    return
                email, old_expires, prior_status = v[1], v[3], v[2]

                channel = await _create_room(guild, member, config, vid, v[5])
                if channel is None:
                    await session.rollback()
                    await _reply(interaction, T.TRY_LATER, True)
                    return

                password = secrets.token_urlsafe(18)
                if check_password(password) is not None:
                    await session.rollback()
                    await _discard_room(channel)
                    await _reply(interaction, T.TRY_LATER, True)
                    return
                pw_hash = await asyncio.to_thread(hash_password, password)

                now = datetime.now(timezone.utc)
                if prior_status == "pending":
                    exp = now + timedelta(days=_TRIAL_DAYS)
                    await session.execute(
                        text(
                            "UPDATE public.viewer_accounts SET status='trial', "
                            "trial_expires_at=:exp, discord_user_id=:uid, discord_channel_id=:ch, "
                            "password_argon2_hash=:h, password_must_change=true, updated_at=:now "
                            "WHERE id=:vid"
                        ),
                        {
                            "exp": exp,
                            "uid": str(member.id),
                            "ch": str(channel.id),
                            "h": pw_hash,
                            "now": now,
                            "vid": vid,
                        },
                    )
                    await session.execute(
                        text(
                            "INSERT INTO public.viewer_status_changes (viewer_id, action, "
                            "from_status, to_status, from_expires_at, to_expires_at, extend_days, "
                            "actor, actor_user_id, created_at) VALUES (:vid, 'start_trial', "
                            "'pending', 'trial', :old, :exp, NULL, 'system', NULL, :now)"
                        ),
                        {"vid": vid, "old": old_expires, "exp": exp, "now": now},
                    )
                else:
                    # お試し中・本契約: 状態と期限は変えず、部屋とパスワードだけ付ける
                    await session.execute(
                        text(
                            "UPDATE public.viewer_accounts SET "
                            "discord_user_id=:uid, discord_channel_id=:ch, "
                            "password_argon2_hash=:h, password_must_change=true, updated_at=:now "
                            "WHERE id=:vid"
                        ),
                        {
                            "uid": str(member.id),
                            "ch": str(channel.id),
                            "h": pw_hash,
                            "now": now,
                            "vid": vid,
                        },
                    )
                await session.execute(
                    text(
                        "INSERT INTO public.viewer_login_events (viewer_id, event_type, "
                        "client_ip, user_agent, created_at) VALUES "
                        "(:vid, 'code_matched', NULL, NULL, :now)"
                    ),
                    {"vid": vid, "now": now},
                )
                await session.commit()
            except IntegrityError:
                await session.rollback()
                await _discard_room(channel)
                await _reply(interaction, T.DISCORD_ALREADY_LINKED, True)
                return
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] code submit failed")
        await _discard_room(channel)
        await _reply(interaction, T.TRY_LATER, True)
        return

    try:
        await channel.send(T.ROOM_WELCOME.format(email=email, password=password))
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] welcome post failed viewer=%d", vid)
    await _reply(interaction, T.YOUR_ROOM.format(channel_id=channel.id), True)


async def sweep_orphan_rooms(guild: Any, db_factory: Any, config: ViewerDiscordConfig) -> int:
    """消された閲覧者の部屋を片付け、今の trial-<id> の部屋を LINE 名へ1回だけ直す。

    部屋の番号は説明（ROOM_TOPIC）を先に、無ければ名前（trial-<id>）から読む。1回の上限は
    消す10件・名前直し10件（別々に数える）。
    """
    category = guild.get_channel(int(config.ticket_category_id))
    if not isinstance(category, discord.CategoryChannel):
        return 0
    rooms: list[tuple[Any, int]] = []
    for ch in category.channels:
        if not isinstance(ch, discord.TextChannel):
            continue
        topic = ch.topic if isinstance(ch.topic, str) else None
        m = _ROOM_TOPIC_RE.fullmatch(topic) if topic is not None else None
        if m is None:
            m = _ROOM_NAME_RE.match(ch.name)
        if m:
            rooms.append((ch, int(m.group(1))))
    missing: list[Any] = []
    to_rename: list[tuple[Any, int, str]] = []
    try:
        async with db_factory() as session:
            for ch, vid in rooms:
                row = (
                    await session.execute(
                        text(
                            "SELECT line_name, discord_channel_id "
                            "FROM public.viewer_accounts WHERE id = :id"
                        ),
                        {"id": vid},
                    )
                ).first()
                if row is None:
                    missing.append(ch)
                    continue
                topic = ch.topic if isinstance(ch.topic, str) else None
                wanted = _room_name(vid, row[0])
                if (
                    _ROOM_NAME_RE.match(ch.name)
                    and (topic is None or _ROOM_TOPIC_RE.fullmatch(topic) is None)
                    and row[1] == str(ch.id)
                    and wanted != ch.name
                ):
                    to_rename.append((ch, vid, wanted))
    except Exception:  # noqa: BLE001
        logger.warning("[viewer-trial] sweep read failed; nothing deleted")
        return 0
    if len(missing) > _SWEEP_MAX_DELETE:
        logger.warning(
            "[viewer-trial] sweep cap reached cap=%d orphans=%d", _SWEEP_MAX_DELETE, len(missing)
        )
    deleted = 0
    for ch in missing[:_SWEEP_MAX_DELETE]:
        try:
            await ch.delete(reason="SalesAnchor viewer account deleted")
            deleted += 1
        except Exception:  # noqa: BLE001
            logger.warning("[viewer-trial] sweep delete failed channel=%s", ch.id)
    renamed = 0
    reason = "SalesAnchor viewer room renamed to LINE name"
    for ch, vid, wanted in to_rename[:_SWEEP_MAX_DELETE]:
        topic = T.ROOM_TOPIC.format(viewer_id=vid)
        try:
            await ch.edit(name=wanted, topic=topic, reason=reason)
            renamed += 1
            continue
        except Exception:  # noqa: BLE001
            pass
        try:
            # 名前を Discord が拒んでも目印は付け、翌日から対象にしない
            await ch.edit(topic=topic, reason=reason)
        except Exception:  # noqa: BLE001
            logger.warning("[viewer-trial] sweep rename failed channel=%s", ch.id)
    logger.info(
        "[viewer-trial] sweep deleted=%d renamed=%d checked=%d", deleted, renamed, len(rooms)
    )
    return deleted
