"""自社用 Discord サーバーのスタッフのロールを、アプリの登録どおりに付け外しする（discord-server-management 第2段 2b）。

設計: docs/handoff/discord-server-management/design.md S2-3 D2-3・D2-7・D2-8。
見る相手はアプリに登録したスタッフ（Discord の番号のある人）と discord_retired_members の人だけ。
全員の一覧（List Guild Members）は読まない。Bot が管理するロール（アプリの役割につないだ番号・
消した役割の番号・「スタッフ」）だけを付け外しする。手作りのロールには触らない。
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

from sqlalchemy import text

from app.auth.dependencies import reset_tenant_context, set_tenant_context
from app.services.discord_blueprint import blueprint_path, load_blueprint
from app.services.discord_rest import DiscordAPIError, discord_api_request

logger = logging.getLogger(__name__)

# 設計図の「スタッフ」のロールの key（tenant_*.json）
STAFF_ROLE_KEY = "staff"
_LOCK_TTL_SEC = 120
_DISCORD_ID = re.compile(r"^[0-9]+$")
# 試験では conftest が False にする（書いたあとの 1 回が本物の DB・Discord へ行かないように）
SCHEDULE_ENABLED = True
_pending: set[asyncio.Task[Any]] = set()


def _lock_key(tenant_id: int) -> str:
    return f"discord:own_staff_sync:{tenant_id}"


def _transient(exc: DiscordAPIError) -> bool:
    """次の点検でやり直す失敗か（つながらない・429・5xx）。"""
    code = exc.status_code
    return code is None or code == 429 or code >= 500


async def _find_staff_role_id(guild_id: str, token: str, tenant_id: int) -> tuple[str | None, str | None]:
    """「スタッフ」の番号を返す。見つからなければ (None, 止める理由)。設計 D2-3 手順2。"""
    path = blueprint_path(tenant_id)
    if not path.exists():
        return None, "blueprint_missing"
    bp = load_blueprint(path)
    role = next((r for r in bp.roles if r.key == STAFF_ROLE_KEY), None)
    if role is None:
        return None, "staff_role_not_in_blueprint"
    if role.discord_id:
        return str(role.discord_id), None
    roles = await discord_api_request(method="GET", path=f"/guilds/{guild_id}/roles", bot_token=token) or []
    hits = [str(r.get("id")) for r in roles if r.get("name") == role.name]
    if len(hits) == 1:
        return hits[0], None
    return None, ("staff_role_missing" if not hits else "staff_role_ambiguous")


async def _send(result: dict[str, Any], counter: str, method: str, path: str, token: str) -> bool:
    """1 つ送る。次の点検でやり直す失敗のときだけ False。404 は済んだものとして True。"""
    try:
        await discord_api_request(method=method, path=path, bot_token=token)
    except DiscordAPIError as exc:
        if exc.status_code == 404:
            return True
        result["failed"] += 1
        logger.warning("[own-staff-sync] %s %s failed status=%s", method, path, exc.status_code)
        return not _transient(exc)
    result[counter] += 1
    return True


async def _reconcile(
    guild_id: str,
    discord_user_id: str,
    desired: set[str],
    managed: set[str],
    token: str,
    result: dict[str, Any],
    *,
    kick: bool = False,
) -> bool:
    """1 人分を合わせる。辞めた人の表の行を消してよければ True。"""
    member_path = f"/guilds/{guild_id}/members/{discord_user_id}"
    try:
        member = await discord_api_request(method="GET", path=member_path, bot_token=token)
    except DiscordAPIError as exc:
        if exc.status_code == 404:
            result["skipped"] += 1
            return True
        result["failed"] += 1
        logger.warning("[own-staff-sync] GET %s failed status=%s", member_path, exc.status_code)
        return not _transient(exc)
    current = {str(r) for r in (member or {}).get("roles", [])}
    ok = True
    for role_id in sorted(desired - current):
        ok = await _send(result, "added", "PUT", f"{member_path}/roles/{role_id}", token) and ok
    for role_id in sorted((current & managed) - desired):
        ok = await _send(result, "removed", "DELETE", f"{member_path}/roles/{role_id}", token) and ok
    if kick and ok:
        ok = await _send(result, "kicked", "DELETE", member_path, token)
    return ok


async def _sync_with_db(db: Any, tenant_id: int, token: str, result: dict[str, Any]) -> None:
    await set_tenant_context(db, tenant_id)
    row = (await db.execute(
        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
        {"tid": tenant_id},
    )).first()
    if not row or not row[0]:
        result["reason"] = "no_own_server"
        return
    guild_id = str(row[0])

    staff_rows = (await db.execute(text(
        "SELECT user_id, discord_user_id, status FROM staff"
        " WHERE discord_user_id IS NOT NULL AND discord_user_id <> ''"
    ))).all()
    links = (await db.execute(text(
        "SELECT ur.user_id, r.discord_role_id FROM user_roles ur JOIN roles r ON r.id = ur.role_id"
        " WHERE r.discord_role_id IS NOT NULL"
    ))).all()
    app_role_ids = {str(r[0]) for r in (await db.execute(
        text("SELECT discord_role_id FROM roles WHERE discord_role_id IS NOT NULL")
    )).all()}
    retired_role_ids = {str(r[0]) for r in (await db.execute(
        text("SELECT discord_role_id FROM discord_retired_roles")
    )).all()}
    retired_rows = (await db.execute(text("SELECT discord_user_id, kick FROM discord_retired_members"))).all()

    # 先に片付け: 辞めた人の表の番号が今の staff にもある（登録し直した）なら、行を消して staff として扱う
    staff_ids = {str(s[1]) for s in staff_rows}
    for r in retired_rows:
        if str(r[0]) in staff_ids:
            await db.execute(
                text("DELETE FROM discord_retired_members WHERE discord_user_id = :did"), {"did": str(r[0])}
            )
    retired = [(str(r[0]), bool(r[1])) for r in retired_rows if str(r[0]) not in staff_ids]
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    try:
        staff_role_id, reason = await _find_staff_role_id(guild_id, token, tenant_id)
    except DiscordAPIError as exc:
        staff_role_id, reason = None, f"discord_error_{exc.status_code}"
    if staff_role_id is None:
        result["reason"] = reason
        logger.warning("[own-staff-sync] tenant=%s stopped reason=%s", tenant_id, reason)
        return

    managed = app_role_ids | retired_role_ids | {staff_role_id}
    desired_by_user: dict[int, set[str]] = {}
    for user_id, role_id in links:
        desired_by_user.setdefault(int(user_id), set()).add(str(role_id))

    for user_id, discord_user_id, status in staff_rows:
        did = str(discord_user_id)
        if not _DISCORD_ID.match(did):
            result["skipped"] += 1
            continue
        desired = (desired_by_user.get(int(user_id), set()) | {staff_role_id}) if status == "active" else set()
        await _reconcile(guild_id, did, desired, managed, token, result)

    done: list[str] = []
    for did, kick in retired:
        if not _DISCORD_ID.match(did):
            result["skipped"] += 1
            done.append(did)
            continue
        if await _reconcile(guild_id, did, set(), managed, token, result, kick=kick):
            done.append(did)
    for did in done:
        await db.execute(text("DELETE FROM discord_retired_members WHERE discord_user_id = :did"), {"did": did})
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072


async def sync_own_server_staff_roles(
    tenant_id: int,
    *,
    redis_client: Any = None,
    session_factory: Any = None,
) -> dict[str, Any]:
    """1 テナントの自社サーバーを 1 回点検して合わせる。数えた結果を返し、記録にも出す。"""
    result: dict[str, Any] = {
        "tenant_id": tenant_id, "added": 0, "removed": 0, "kicked": 0, "failed": 0, "skipped": 0, "reason": None,
    }
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        result["reason"] = "no_token"
        return result
    if session_factory is None:
        from app.database import AsyncSessionLocal  # noqa: PLC0415

        session_factory = AsyncSessionLocal

    locked = False
    if redis_client is not None:
        try:
            locked = bool(await redis_client.set(_lock_key(tenant_id), "1", nx=True, ex=_LOCK_TTL_SEC))
        except Exception as exc:  # noqa: BLE001
            # Redis が使えないときは鍵なしで進める（PUT・DELETE は何度送っても同じ結果＝設計 D2-8）
            logger.warning("[own-staff-sync] lock unavailable tenant=%s: %s", tenant_id, type(exc).__name__)
            redis_client = None
        else:
            if not locked:
                result["reason"] = "locked"
                return result
    try:
        async with session_factory() as db:
            await _sync_with_db(db, tenant_id, token, result)
    finally:
        if locked and redis_client is not None:
            await redis_client.delete(_lock_key(tenant_id))
    logger.info(
        "[own-staff-sync] tenant=%s added=%s removed=%s kicked=%s failed=%s skipped=%s reason=%s",
        tenant_id, result["added"], result["removed"], result["kicked"], result["failed"], result["skipped"],
        result["reason"],
    )
    return result


async def _run_quietly(tenant_id: int, redis_client: Any) -> None:
    try:
        await sync_own_server_staff_roles(tenant_id, redis_client=redis_client)
    except Exception as exc:  # noqa: BLE001
        logger.error("[own-staff-sync] tenant=%s failed: %s: %s", tenant_id, type(exc).__name__, exc)


def schedule_own_staff_sync(tenant_id: int) -> None:
    """書いた所の commit のあとに呼ぶ。待たずに裏で 1 回点検する（先例 backend/app/routers/leads.py:728 の create_task）。"""
    if not SCHEDULE_ENABLED or not os.environ.get("DISCORD_BOT_TOKEN"):
        return
    from app.cache import get_redis  # noqa: PLC0415

    task = asyncio.create_task(_run_quietly(tenant_id, get_redis()))
    _pending.add(task)
    task.add_done_callback(_pending.discard)
