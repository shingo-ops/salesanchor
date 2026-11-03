"""アプリ内の鈴（各社スキーマ user_notices）: 宛先の決定・知らせの作成・合図。

設計: docs/handoff/in-app-notice-bell/design.md §4〜§6。
- 宛先 = 担当者だけ。いなければ設定の人、無ければオーナー（設計 §4-改訂1・2）。担当者は leads.assigned_to（受信箱と同じ列）。
- 本文・Discord の id は表にもログにも入れない。ログは人数だけ。
- テナント表はすべてスキーマ名つき（ADR-072）。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import bindparam, text

from app.auth.dependencies import is_postgresql, tenant_table_ref
from app.auth.system_roles import ROLE_KEY_OWNER
from app.realtime.publisher import publish_user_change
from app.realtime.topics import TOPIC_NOTICES

logger = logging.getLogger(__name__)

KIND_OUTSIDE_TICKET_POST = "discord_outside_ticket_post"
MAX_MENTIONS = 50  # Discord の allowed_mentions.users 上限 100 と本文 2000 文字に対する余裕


def _users_ref(db: Any) -> str:
    return "public.users" if is_postgresql(db) else "users"


async def _valid_user_ids(db: Any, tenant_id: int, ids: set[int]) -> list[int]:
    """同じ会社で有効な人だけ残す（assigned_to・user_roles.user_id には FK が無い）。"""
    if not ids:
        return []
    stmt = text(
        f"SELECT id FROM {_users_ref(db)} "
        "WHERE id IN :ids AND tenant_id = :tid AND is_active = :active ORDER BY id"
    ).bindparams(bindparam("ids", expanding=True))
    rows = (await db.execute(stmt, {"ids": sorted(ids), "tid": tenant_id, "active": True})).all()
    return [int(r[0]) for r in rows]


async def _assignee_candidates(db: Any, tenant_id: int, discord_user_id: str) -> list[int]:
    leads_t = tenant_table_ref(db, tenant_id, "leads")
    channels_t = tenant_table_ref(db, tenant_id, "lead_channels")
    found: set[int] = set()
    # 道 a: leads.discord_user_id の全件（LIMIT 1 にしない）
    rows = (
        await db.execute(
            text(
                f"SELECT assigned_to FROM {leads_t} "
                "WHERE discord_user_id = :uid AND assigned_to IS NOT NULL"
            ),
            {"uid": discord_user_id},
        )
    ).all()
    found.update(int(r[0]) for r in rows)
    # 道 b: lead_channels（platform='discord'）
    rows = (
        await db.execute(
            text(
                f"SELECT l.assigned_to FROM {channels_t} lc JOIN {leads_t} l ON l.id = lc.lead_id "
                "WHERE lc.platform = 'discord' AND lc.external_id = :uid "
                "AND l.assigned_to IS NOT NULL"
            ),
            {"uid": discord_user_id},
        )
    ).all()
    found.update(int(r[0]) for r in rows)
    return await _valid_user_ids(db, tenant_id, found)


async def _owner_user_ids(db: Any, tenant_id: int) -> list[int]:
    """オーナー（system_key='owner'）の有効な人全員。admin は入れない。"""
    roles_t = tenant_table_ref(db, tenant_id, "roles")
    user_roles_t = tenant_table_ref(db, tenant_id, "user_roles")
    rows = (
        await db.execute(
            text(
                f"SELECT DISTINCT ur.user_id FROM {user_roles_t} ur "
                f"JOIN {roles_t} r ON r.id = ur.role_id "
                "WHERE r.system_key = :owner"
            ),
            {"owner": ROLE_KEY_OWNER},
        )
    ).all()
    return await _valid_user_ids(db, tenant_id, {int(r[0]) for r in rows})


async def _fallback_selected_ids(db: Any, tenant_id: int) -> list[int]:
    """担当者がいないときに受け取る人として保存された user_id（有効かは見ない）。"""
    fb_t = tenant_table_ref(db, tenant_id, "notice_fallback_recipients")
    rows = (await db.execute(text(f"SELECT user_id FROM {fb_t} ORDER BY user_id"))).all()
    return [int(r[0]) for r in rows]


async def resolve_fallback_recipients(db: Any, tenant_id: int) -> list[int]:
    """担当者がいないときの宛先: 設定の人のうち有効な人。0 件か有効 0 人ならオーナー全員。"""
    selected = await _fallback_selected_ids(db, tenant_id)
    valid = await _valid_user_ids(db, tenant_id, set(selected))
    if valid:
        return valid
    return await _owner_user_ids(db, tenant_id)


async def resolve_notice_recipients(db: Any, tenant_id: int, discord_user_id: str) -> list[int]:
    """書いた人の Discord の id から宛先（public.users.id）を決める（読むだけ）。

    担当者の候補（有効な人・重複除去後）が 1 人以上 → 担当者だけ（別々なら全員）。
    0 人 → 設定の人（有効な人だけ）。設定が無い・全員無効 → オーナー全員。admin は足さない。
    """
    candidates = await _assignee_candidates(db, tenant_id, str(discord_user_id))
    if candidates:
        return candidates
    return await resolve_fallback_recipients(db, tenant_id)


async def discord_ids_for_users(db: Any, tenant_id: int, user_ids: list[int]) -> list[str]:
    """宛先の Discord の id（staff.discord_user_id・数字だけ）。無い人は呼ばない。最大 MAX_MENTIONS 人。"""
    if not user_ids:
        return []
    staff_t = tenant_table_ref(db, tenant_id, "staff")
    stmt = text(
        f"SELECT user_id, discord_user_id FROM {staff_t} WHERE user_id IN :ids ORDER BY user_id"
    ).bindparams(bindparam("ids", expanding=True))
    rows = (await db.execute(stmt, {"ids": list(user_ids)})).all()
    result: list[str] = []
    for _uid, did in rows:
        value = str(did or "")
        if value.isdigit() and value not in result:
            result.append(value)
        if len(result) >= MAX_MENTIONS:
            break
    return result


async def insert_notices(
    db: Any,
    tenant_id: int,
    user_ids: list[int],
    *,
    kind: str,
    actor_name: str | None,
    channel_name: str | None,
    link_url: str | None,
) -> None:
    """宛先の人数分の行を入れる（commit は呼び出し側）。"""
    notices_t = tenant_table_ref(db, tenant_id, "user_notices")
    now = datetime.now(timezone.utc)
    for uid in user_ids:
        await db.execute(
            text(
                f"INSERT INTO {notices_t} (user_id, kind, actor_name, channel_name, link_url, created_at) "
                "VALUES (:uid, :kind, :actor, :chan, :link, :now)"
            ),
            {
                "uid": uid, "kind": kind, "actor": actor_name,
                "chan": channel_name, "link": link_url, "now": now,
            },
        )


async def signal_notices_changed(user_ids: list[int]) -> None:
    """commit の後に宛先 1 人ずつへ合図を出す（送り口はここ 1 か所。失敗は握る）。"""
    for uid in user_ids:
        await publish_user_change(uid, TOPIC_NOTICES)
