"""スタッフ自己登録の Discord 受付（ADR-1068・設計 docs/handoff/staff-self-registration/design.md §4-3）。

ボタン → 登録番号の小窓 → 照合 → 本人と管理者だけの個室 → 仮パスワード。
閲覧者の受付（viewer_trial.py）と同じ順で、自社サーバー（purpose='own'）のスタッフ用。
顧客用チケット（ticket_channel_creator.py）には入らず、leads は作らない。
ログに email・番号・パスワードを出さない。
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

import discord
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import clear_tenant_context, reset_tenant_context, set_tenant_context
from app.auth.password_policy import check_password
from app.auth.passwords import hash_password
from app.auth.system_roles import ROLE_KEY_ADMIN, ROLE_KEY_OWNER
from app.auth.viewer_signup_code import normalize_signup_code, signup_code_sha256
from app.cache import get_redis
from app.discord_gateway import private_channel
from app.discord_gateway import staff_join_texts as T
from app.services.discord_own_staff_sync import schedule_own_staff_sync
from app.services.staff_join import ROOMS_CATEGORY_KEY, find_blueprint_channel_id

logger = logging.getLogger(__name__)

_FAIL_LIMIT = 5
_FAIL_WINDOW_SEC = 3600
_SWEEP_MAX_DELETE = 10
_SWEEP_MIN_AGE = timedelta(minutes=10)  # 照合の途中は discord_channel_id がまだ空なので、作って間もない部屋は見ない
_ROOM_NAME_RE = re.compile(r"^staff-join-(\d+)$")
_DISCORD_ID_RE = re.compile(r"^[0-9]+$")

# 管理者のロール＝その会社の roles のうち staff.create を持ち discord_role_id がある物。
# 権限の表は load_user_permissions（auth/dependencies.py）と同じ role_permissions × public.permissions。
# owner / admin のシステムロールは role_permissions の行ではなく権限マスタから計算される
# （auth/system_roles.py compute_permission_keys）ので、system_key でも拾う。
_ADMIN_ROLES_SQL = (
    "SELECT DISTINCT r.discord_role_id FROM roles r "
    "WHERE r.tenant_id = :tid AND r.discord_role_id IS NOT NULL AND r.discord_role_id <> '' "
    "AND (r.system_key IN (:k_owner, :k_admin) OR EXISTS ("
    "SELECT 1 FROM role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id "
    "WHERE rp.role_id = r.id AND p.key = 'staff.create'))"
)


class _Precheck(NamedTuple):
    registered: bool
    admin_role_ids: list[str]


async def resolve_own_tenant_id(db_factory: Any, guild_id: str) -> int | None:
    """guild の番号から自社サーバー（purpose='own'）の会社を引く。client._resolve_tenant_id（customer 専用）と同じ表。"""
    try:
        async with db_factory() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT tenant_id FROM public.tenant_discord_config"
                        " WHERE guild_id = :gid AND purpose = 'own' LIMIT 1"
                    ),
                    {"gid": guild_id},
                )
            ).first()
        return int(row[0]) if row else None
    except Exception:  # noqa: BLE001
        logger.warning("[staff-join] tenant lookup failed")
        return None


async def list_own_guilds(db_factory: Any) -> list[tuple[int, str]]:
    """自社サーバーを持つ会社の (tenant_id, guild_id) の一覧（片付けの繰り返し用）。"""
    async with db_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT tenant_id, guild_id FROM public.tenant_discord_config"
                    " WHERE purpose = 'own' AND guild_id IS NOT NULL AND guild_id <> ''"
                )
            )
        ).all()
    return [(int(r[0]), str(r[1])) for r in rows]


class StaffJoinCodeModal(discord.ui.Modal):
    """登録番号の入力小窓。応答は on_interaction 側（staff_join.handle_interaction）で行う。"""

    code = discord.ui.TextInput(
        label=T.CODE_INPUT_LABEL,
        custom_id=T.CODE_INPUT_CUSTOM_ID,
        min_length=16,
        max_length=19,
        required=True,
    )

    def __init__(self) -> None:
        super().__init__(title=T.CODE_MODAL_TITLE, custom_id=T.CODE_MODAL_CUSTOM_ID, timeout=900)


async def _send_ephemeral(interaction: Any, message: str, deferred: bool) -> bool:
    """本人だけに見える返事。送れたら True。"""
    try:
        if deferred:
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return True
    except Exception:  # noqa: BLE001
        return False


async def _reply(interaction: Any, message: str, deferred: bool) -> None:
    if not await _send_ephemeral(interaction, message, deferred):
        logger.warning("[staff-join] reply failed")


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
    # 自社サーバーの guild だけ。お客様のサーバー（customer）の guild では動かない
    tenant_id = await resolve_own_tenant_id(db_factory, str(guild.id))
    if tenant_id is None:
        await _reply(interaction, T.WRONG_SERVER, False)
        return
    await handler(interaction, db_factory, tenant_id)


async def on_open(interaction: Any, db_factory: Any, tenant_id: int) -> None:
    await interaction.response.send_modal(StaffJoinCodeModal())


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


async def _clear(session: Any) -> None:
    """プールへ返す前に会社の文脈を外す（ADR-131）。失敗しても何もしない。"""
    try:
        await clear_tenant_context(session)
    except Exception:  # noqa: BLE001
        pass


async def _precheck(db_factory: Any, tenant_id: int, discord_user_id: str) -> _Precheck:
    """照合の前に見る2つ（どちらも失敗には数えない）: 既に登録済みか・管理者のロールがあるか。"""
    async with db_factory() as session:
        try:
            await set_tenant_context(session, tenant_id)
            registered = (
                await session.execute(
                    text("SELECT 1 FROM staff WHERE discord_user_id = :uid LIMIT 1"),
                    {"uid": discord_user_id},
                )
            ).first() is not None
            rows = (
                await session.execute(
                    text(_ADMIN_ROLES_SQL),
                    {"tid": tenant_id, "k_owner": ROLE_KEY_OWNER, "k_admin": ROLE_KEY_ADMIN},
                )
            ).all()
            await session.rollback()
        finally:
            await _clear(session)
    role_ids = sorted({str(r[0]) for r in rows if _DISCORD_ID_RE.match(str(r[0]))})
    return _Precheck(registered, role_ids)


async def _resolve_rooms_category(guild: Any, tenant_id: int) -> Any:
    """設計図の key staff_join_rooms のカテゴリ。見つからなければ None。"""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        return None
    try:
        category_id = await find_blueprint_channel_id(str(guild.id), token, tenant_id, ROOMS_CATEGORY_KEY, 4)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[staff-join] category lookup failed kind=%s", type(exc).__name__)
        return None
    if category_id is None:
        return None
    return private_channel.resolve_category(guild, int(category_id), "staff_join")


async def _create_room(guild: Any, member: Any, category: Any, invite_id: int, admin_role_ids: list[str]):
    return await private_channel.create_private_text_channel(
        guild,
        category,
        member,
        None,
        name=T.ROOM_NAME.format(invite_id=invite_id),
        reason="SalesAnchor staff join",
        log_context="staff_join",
        topic=T.ROOM_TOPIC.format(invite_id=invite_id),
        log_name=T.ROOM_NAME.format(invite_id=invite_id),
        extra_view_role_ids=admin_role_ids,
    )


async def _discard_room(channel: Any) -> None:
    if channel is None:
        return
    try:
        await channel.delete(reason="SalesAnchor staff join rollback")
    except Exception:  # noqa: BLE001
        logger.warning("[staff-join] rollback channel delete failed channel=%s", channel.id)


async def on_code_submit(interaction: Any, db_factory: Any, tenant_id: int) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    member = interaction.user
    uid = str(member.id)

    raw = _find_input_value((interaction.data or {}).get("components"), T.CODE_INPUT_CUSTOM_ID)
    if raw is None:
        await _reply(interaction, T.CODE_INVALID, True)
        return

    redis = get_redis()
    if redis is None:
        await _reply(interaction, T.TRY_LATER, True)
        return
    key = f"staff_code_fail:{member.id}"
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
        logger.warning("[staff-join] attempt counter failed")
        await _reply(interaction, T.TRY_LATER, True)
        return

    # 照合の前に、既に登録済みか・管理者のロールがあるかを見る（どちらも失敗に数えない・何も変えない）
    try:
        pre = await _precheck(db_factory, tenant_id, uid)
    except Exception:  # noqa: BLE001
        logger.warning("[staff-join] precheck failed")
        await _reply(interaction, T.TRY_LATER, True)
        return
    if pre.registered:
        await _reply(interaction, T.ALREADY_REGISTERED, True)
        return
    if not pre.admin_role_ids:
        await _reply(interaction, T.NOT_READY, True)
        return
    category = await _resolve_rooms_category(guild, tenant_id)
    if category is None:
        await _reply(interaction, T.NOT_READY, True)
        return

    channel = None
    committed = False
    invite_id = 0
    email = ""
    password = ""
    try:
        async with db_factory() as session:
            try:
                await set_tenant_context(session, tenant_id)
                got = (
                    await session.execute(
                        text(
                            "SELECT id, user_id, staff_id FROM public.staff_join_invites "
                            "WHERE tenant_id = :tid AND reg_code_hash = :h AND status = 'submitted' "
                            "AND reg_code_expires_at > now() FOR UPDATE"
                        ),
                        {"tid": tenant_id, "h": signup_code_sha256(normalized)},
                    )
                ).first()
                if got is None or got[1] is None or got[2] is None:
                    await session.rollback()
                    await _count_failure(redis, key)
                    await _reply(interaction, T.CODE_INVALID, True)
                    return
                invite_id, user_id, staff_id = int(got[0]), int(got[1]), int(got[2])

                person = (
                    await session.execute(
                        text(
                            "SELECT u.email, s.discord_user_id FROM public.users u "
                            "JOIN staff s ON s.user_id = u.id WHERE u.id = :uid AND s.id = :sid"
                        ),
                        {"uid": user_id, "sid": staff_id},
                    )
                ).first()
                if person is None:
                    await session.rollback()
                    await _count_failure(redis, key)
                    await _reply(interaction, T.CODE_INVALID, True)
                    return
                email = person[0]
                other = (
                    await session.execute(
                        text("SELECT 1 FROM staff WHERE discord_user_id = :d AND id <> :sid LIMIT 1"),
                        {"d": uid, "sid": staff_id},
                    )
                ).first()
                if person[1] or other is not None:  # 本人が連携済み・この Discord ID を別の staff が持っている
                    await session.rollback()
                    await _reply(interaction, T.ALREADY_REGISTERED, True)
                    return

                channel = await _create_room(guild, member, category, invite_id, pre.admin_role_ids)
                if channel is None:
                    await session.rollback()
                    await _reply(interaction, T.ROOM_FAILED, True)
                    return

                password = secrets.token_urlsafe(18)
                if check_password(password) is not None:
                    await session.rollback()
                    await _discard_room(channel)
                    await _reply(interaction, T.TRY_LATER, True)
                    return
                pw_hash = await asyncio.to_thread(hash_password, password)

                now = datetime.now(timezone.utc)
                await session.execute(
                    text(
                        "UPDATE public.users SET password_argon2_hash = :h, password_must_change = true, "
                        "is_active = true WHERE id = :uid"
                    ),
                    {"h": pw_hash, "uid": user_id},
                )
                # staff.status は pending のまま（3回目で active にする）
                await session.execute(
                    text("UPDATE staff SET discord_user_id = :d WHERE id = :sid"),
                    {"d": uid, "sid": staff_id},
                )
                await session.execute(
                    text(
                        "UPDATE public.staff_join_invites SET status = 'linked', discord_channel_id = :ch, "
                        "linked_at = :now, reg_code_hash = NULL WHERE id = :id AND tenant_id = :tid"
                    ),
                    {"ch": str(channel.id), "now": now, "id": invite_id, "tid": tenant_id},
                )
                await session.commit()
                committed = True
                try:
                    await reset_tenant_context(session, tenant_id)
                except Exception:  # noqa: BLE001
                    logger.warning("[staff-join] context reset failed after commit")
            except IntegrityError:
                await session.rollback()
                await _discard_room(channel)
                await _reply(interaction, T.ALREADY_REGISTERED, True)
                return
            finally:
                await _clear(session)
    except Exception:  # noqa: BLE001
        if not committed:
            logger.warning("[staff-join] code submit failed")
            await _discard_room(channel)
            await _reply(interaction, T.TRY_LATER, True)
            return
        logger.warning("[staff-join] session close failed after commit invite=%d", invite_id)

    welcome_text = T.room_welcome(email, password)
    posted = False
    try:
        await channel.send(welcome_text)
        posted = True
    except Exception:  # noqa: BLE001
        logger.warning("[staff-join] welcome post failed invite=%d", invite_id)
    if posted:
        await _reply(interaction, T.ROOM_CREATED.format(channel_id=channel.id), True)
    elif not await _send_ephemeral(interaction, welcome_text, True):
        # パスワードは記録に出さない。本人は「パスワードを忘れた」から再設定する（is_active は真）
        logger.error("[staff-join] welcome delivery failed invite=%d", invite_id)
    schedule_own_staff_sync(tenant_id)


async def sweep_orphan_rooms(guild: Any, db_factory: Any, tenant_id: int, *, now: datetime | None = None) -> int:
    """持ち主のいない個室（staff-join-<id>）を片付ける。1回に消すのは10件まで。

    作ってから 10 分たった部屋だけを見る（照合の途中は discord_channel_id がまだ空のため）。
    その招待の discord_channel_id がこの部屋でなければ持ち主なしとみなす。
    """
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        return 0
    try:
        category_id = await find_blueprint_channel_id(str(guild.id), token, tenant_id, ROOMS_CATEGORY_KEY, 4)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[staff-join] sweep category lookup failed kind=%s", type(exc).__name__)
        return 0
    if category_id is None:
        return 0
    category = guild.get_channel(int(category_id))
    if not isinstance(category, discord.CategoryChannel):
        return 0

    current = now or datetime.now(timezone.utc)
    rooms: list[tuple[Any, int]] = []
    for ch in category.channels:
        if not isinstance(ch, discord.TextChannel):
            continue
        m = _ROOM_NAME_RE.match(ch.name)
        if m is None:
            continue
        created = getattr(ch, "created_at", None)
        if created is None or current - created < _SWEEP_MIN_AGE:
            continue
        rooms.append((ch, int(m.group(1))))

    orphans: list[Any] = []
    try:
        async with db_factory() as session:
            try:
                await set_tenant_context(session, tenant_id)
                for ch, invite_id in rooms:
                    row = (
                        await session.execute(
                            text(
                                "SELECT discord_channel_id FROM public.staff_join_invites "
                                "WHERE id = :id AND tenant_id = :tid"
                            ),
                            {"id": invite_id, "tid": tenant_id},
                        )
                    ).first()
                    if row is None or row[0] != str(ch.id):
                        orphans.append(ch)
                await session.rollback()
                await reset_tenant_context(session, tenant_id)
            finally:
                await _clear(session)
    except Exception:  # noqa: BLE001
        logger.warning("[staff-join] sweep read failed; nothing deleted")
        return 0
    if len(orphans) > _SWEEP_MAX_DELETE:
        logger.warning("[staff-join] sweep cap reached cap=%d orphans=%d", _SWEEP_MAX_DELETE, len(orphans))
    deleted = 0
    for ch in orphans[:_SWEEP_MAX_DELETE]:
        try:
            await ch.delete(reason="SalesAnchor staff join room without owner")
            deleted += 1
        except Exception:  # noqa: BLE001
            logger.warning("[staff-join] sweep delete failed channel=%s", ch.id)
    logger.info("[staff-join] sweep deleted=%d checked=%d", deleted, len(rooms))
    return deleted
