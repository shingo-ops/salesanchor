"""自社用 Discord サーバーの今の姿の読み取り（discord-server-management 便2・設計 §4-6）。

API:
  POST /api/v1/admin/discord/own-server/snapshot — 自社用サーバーのロールとチャンネルを読み、
    public.discord_server_snapshots に 1 行入れる

約束:
  - 読むだけ。Discord の物を作らない・変えない・消さない（呼ぶのは GET だけ）
  - サーバーの番号は記録に入れない。@everyone（番号がサーバーの番号と同じ）は "@everyone" と書く
  - 人の名前・書き込みは入れない。人ごとの上書き（type=1）は外し、数だけ残す
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
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
from app.auth.system_roles import TENANT_HIDDEN_SYSTEM_KEYS
from app.cache import get_redis
from app.database import get_db
from app.models import User
from app.routers.roles import _visible_role_sql, _visible_text
from app.services.audit import record_audit_log
from app.services.discord_blueprint import (
    APP_ROLE_KEY_PREFIX,
    NOTICE_ROOMS,
    Blueprint,
    blueprint_path,
    build_plan,
    load_blueprint,
)
from app.services.discord_blueprint_apply import apply_plan
from app.services.discord_rest import DiscordAPIError, discord_api_request
from app.services.staff_join import RECEPTION_CHANNEL_KEY, ensure_reception_button

logger = logging.getLogger(__name__)
router = APIRouter()

SNAPSHOT_VERSION = 1
EVERYONE = "@everyone"
# Discord のロールとチャンネルの項目（Context7 /discord/discord-api-docs の Role Structure・Channel Structure）
_ROLE_FIELDS = ("name", "color", "colors", "hoist", "mentionable", "permissions", "position", "managed")
_CHANNEL_FIELDS = ("type", "name", "position", "topic", "nsfw")


class OwnServerSnapshotResponse(BaseModel):
    snapshot_id: int
    role_count: int
    channel_count: int


def _ref(discord_id: Any, guild_id: str) -> str:
    """番号を文字にする。サーバーの番号と同じなら @everyone と書く（記録にサーバーの番号を残さない）。"""
    value = str(discord_id)
    return EVERYONE if value == guild_id else value


def build_snapshot_body(
    roles: list[dict[str, Any]], channels: list[dict[str, Any]], guild_id: str
) -> dict[str, Any]:
    """Discord の返事から、記録に入れる形を作る。"""
    out_roles: list[dict[str, Any]] = []
    for role in roles:
        item: dict[str, Any] = {"discord_id": _ref(role.get("id"), guild_id)}
        for field in _ROLE_FIELDS:
            item[field] = role.get(field)
        out_roles.append(item)
    out_channels: list[dict[str, Any]] = []
    for ch in channels:
        item = {"discord_id": str(ch.get("id"))}
        for field in _CHANNEL_FIELDS:
            item[field] = ch.get(field)
        parent = ch.get("parent_id")
        item["parent_id"] = str(parent) if parent is not None else None
        overwrites = ch.get("permission_overwrites") or []
        item["permission_overwrites"] = [
            {
                "target": _ref(ow.get("id"), guild_id),
                "allow": str(ow.get("allow", "0")),
                "deny": str(ow.get("deny", "0")),
            }
            for ow in overwrites
            if ow.get("type") == 0
        ]
        item["member_overwrite_count"] = sum(1 for ow in overwrites if ow.get("type") == 1)
        out_channels.append(item)
    return {"version": SNAPSHOT_VERSION, "roles": out_roles, "channels": out_channels}


def _insert_sql(db: AsyncSession) -> str:
    """PostgreSQL では JSONB に CAST する。SQLite（試験）では素の文字で入れる（backend/app/routers/meta_inbox.py:152-158 と同じ分け方）。"""
    bind = db.get_bind() if hasattr(db, "get_bind") else getattr(db, "bind", None)
    name = getattr(getattr(bind, "dialect", None), "name", "") or ""
    body_expr = "CAST(:body AS JSONB)" if name.startswith("postgresql") else ":body"
    return (
        "INSERT INTO public.discord_server_snapshots (tenant_id, purpose, body, taken_by)"
        f" VALUES (:tid, 'own', {body_expr}, :uid) RETURNING id"
    )


@router.post(
    "/admin/discord/own-server/snapshot",
    response_model=OwnServerSnapshotResponse,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def take_own_server_snapshot(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> OwnServerSnapshotResponse:
    """自社用サーバーのロールとチャンネルを読み、記録に 1 行入れる。"""
    result = await db.execute(
        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
        {"tid": tenant_id},
    )
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(
            status_code=422,
            detail="自社用サーバーが未登録です。先に Bot を招待してください。",
        )
    guild_id = str(row[0])

    bot_token: str | None = os.environ.get("DISCORD_BOT_TOKEN") or None
    if not bot_token:
        raise HTTPException(
            status_code=503,
            detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。",
        )

    try:
        roles: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/roles",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
        channels: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/channels",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
    except DiscordAPIError as exc:
        logger.warning("[discord_own_server] snapshot read failed tenant=%d: %s", tenant_id, exc)
        raise HTTPException(status_code=502, detail="Discord から読み取れませんでした。") from exc

    body = build_snapshot_body(roles, channels, guild_id)
    inserted = await db.execute(
        text(_insert_sql(db)),
        {"tid": tenant_id, "body": json.dumps(body, ensure_ascii=False), "uid": current_user.id},
    )
    snapshot_id = int(inserted.scalar_one())
    role_count = len(body["roles"])
    channel_count = len(body["channels"])
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="create",
        table_name="discord_server_snapshots",
        record_id=snapshot_id,
        new_data={"role_count": role_count, "channel_count": channel_count},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    logger.info(
        "[discord_own_server] snapshot tenant=%d id=%d roles=%d channels=%d",
        tenant_id, snapshot_id, role_count, channel_count,
    )
    return OwnServerSnapshotResponse(
        snapshot_id=snapshot_id, role_count=role_count, channel_count=channel_count
    )


# ---------------------------------------------------------------- 確認（設計図と今のサーバーの差・便3a）

class PlanRow(BaseModel):
    kind: str
    key: str
    name: str
    field: str | None = None
    before: str | None = None
    after: str | None = None
    reason: str | None = None


class DeleteCandidate(BaseModel):
    kind: str
    discord_id: str
    name: str | None = None
    parent_name: str | None = None
    target: str | None = None


class AppRoleState(BaseModel):
    role_id: int
    name: str
    state: str
    reason: str | None = None


class OwnServerPlanResponse(BaseModel):
    plan_digest: str
    changes: list[PlanRow]
    blocked: list[PlanRow]
    delete_candidates: list[DeleteCandidate]
    app_roles: list[AppRoleState] = []


@router.get(
    "/admin/discord/own-server/plan",
    response_model=OwnServerPlanResponse,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def check_own_server_plan(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> OwnServerPlanResponse:
    """設計図と今の自社用サーバーを比べて、差を返す。読むだけ（DB にも Discord にも書かない）。"""
    guild_id, blueprint, bot_token = await _load_own_context(db, tenant_id)
    plan = await _read_and_plan(db, guild_id, blueprint, bot_token)
    return OwnServerPlanResponse(
        plan_digest=plan["plan_digest"],
        changes=plan["changes"],
        blocked=plan["blocked"],
        delete_candidates=plan["delete_candidates"],
        app_roles=plan.get("app_roles", []),
    )


async def _load_own_context(db: AsyncSession, tenant_id: int) -> tuple[str, Blueprint, str]:
    """自社用サーバーの番号・設計図・Bot の鍵を用意する（確認と反映で同じ手順）。"""
    result = await db.execute(
        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
        {"tid": tenant_id},
    )
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(
            status_code=422,
            detail="自社用サーバーが未登録です。先に Bot を招待してください。",
        )
    guild_id = str(row[0])

    path = blueprint_path(tenant_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="設計図がまだありません。")
    try:
        blueprint = load_blueprint(path)
    except (ValueError, OSError) as exc:
        logger.warning("[discord_own_server] blueprint invalid tenant=%d: %s", tenant_id, exc)
        raise HTTPException(status_code=422, detail="設計図の形が正しくありません。") from exc

    bot_token: str | None = os.environ.get("DISCORD_BOT_TOKEN") or None
    if not bot_token:
        raise HTTPException(
            status_code=503,
            detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。",
        )
    return guild_id, blueprint, bot_token


async def _read_and_plan(db: AsyncSession, guild_id: str, blueprint: Blueprint, bot_token: str) -> dict[str, Any]:
    """Discord を GET で 4 回読み、アプリの役割を DB から読み、設計図との差（build_plan の戻り値）を返す。"""
    try:
        roles: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/roles",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
        channels: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/channels",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
        me: dict[str, Any] = await discord_api_request(
            method="GET",
            path="/users/@me",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or {}
        member: dict[str, Any] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/members/{me.get('id')}",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or {}
    except DiscordAPIError as exc:
        logger.warning("[discord_own_server] plan read failed: %s", exc)
        raise HTTPException(status_code=502, detail="Discord から読み取れませんでした。") from exc

    bot_role_ids = [str(r) for r in (member.get("roles") or [])]
    # アプリの役割（第2段 2a-2）。管理者の隠しロールは見る人が誰でも Discord の対象にしない
    app_result = await db.execute(
        _visible_text(f"SELECT id, name, color, discord_role_id FROM roles WHERE {_visible_role_sql()} ORDER BY id"),
        {"show_hidden": False, "hidden_keys": sorted(TENANT_HIDDEN_SYSTEM_KEYS)},
    )
    app_roles = [dict(r) for r in app_result.mappings().all()]
    # 知らせの送り先（第2段 2c）。表が無い会社（新しい会社）はつなぎの段を出さない
    notice_links: list[dict[str, Any]] | None = None
    if await _notice_table_exists(db):
        notice_result = await db.execute(
            text("SELECT blueprint_key, event_types, is_active FROM notification_channels ORDER BY id")
        )
        notice_links = [dict(r) for r in notice_result.mappings().all()]
    return build_plan(blueprint, roles, channels, guild_id, bot_role_ids, app_roles=app_roles, notice_links=notice_links)


# ---------------------------------------------------------------- 反映（便3b）

class OwnServerApplyRequest(BaseModel):
    plan_digest: str


class ApplyResultRow(BaseModel):
    kind: str
    key: str
    name: str
    field: str | None = None
    status: str
    reason: str | None = None
    discord_id: str | None = None
    discord_status: int | None = None


class OwnServerApplyResponse(BaseModel):
    run_id: int
    success_count: int
    blocked_count: int
    failed_count: int
    results: list[ApplyResultRow]


_APP_ROLE_WRITE_KINDS = ("create_role", "link_role")


async def _write_back_app_roles(db: AsyncSession, results: list[dict[str, Any]]) -> int:
    """反映で作った・見つけたロールの番号をアプリの役割に書く（第2段 2a-2）。書いた数を返す。

    既に番号がある役割は書き換えない。その番号を「消した番号の表」から外す（つなぎ直したロールを外さないため）。
    """
    written = 0
    for x in results:
        key = str(x.get("key") or "")
        if (x.get("status") != "success" or x.get("kind") not in _APP_ROLE_WRITE_KINDS
                or not key.startswith(APP_ROLE_KEY_PREFIX) or not x.get("discord_id")):
            continue
        role_id = int(key[len(APP_ROLE_KEY_PREFIX):])
        res = await db.execute(
            text("UPDATE roles SET discord_role_id = :did WHERE id = :rid AND discord_role_id IS NULL"),
            {"did": str(x["discord_id"]), "rid": role_id},
        )
        written += int(res.rowcount or 0)
        await db.execute(
            text("DELETE FROM discord_retired_roles WHERE discord_role_id = :did"),
            {"did": str(x["discord_id"])},
        )
    return written


def _apply_insert_sql(db: AsyncSession) -> str:
    """反映の記録を入れる文。PostgreSQL では JSONB に CAST し、SQLite（試験）では素の文字（_insert_sql と同じ分け方）。"""
    bind = db.get_bind() if hasattr(db, "get_bind") else getattr(db, "bind", None)
    name = getattr(getattr(bind, "dialect", None), "name", "") or ""
    result_expr = "CAST(:result AS JSONB)" if name.startswith("postgresql") else ":result"
    return (
        "INSERT INTO public.discord_server_apply_runs"
        " (tenant_id, purpose, plan_digest, started_at, finished_at, applied_by, result)"
        f" VALUES (:tid, 'own', :digest, :started, :finished, :uid, {result_expr}) RETURNING id"
    )


async def _notice_table_exists(db: AsyncSession) -> bool:
    """今のテナントに notification_channels があるか。PostgreSQL は to_regclass で見る（無い表を読んで取引を壊さない）。SQLite（試験）は在る。"""
    bind = db.get_bind() if hasattr(db, "get_bind") else getattr(db, "bind", None)
    name = getattr(getattr(bind, "dialect", None), "name", "") or ""
    if not name.startswith("postgresql"):
        return True
    found = await db.execute(text("SELECT to_regclass('notification_channels') IS NOT NULL"))
    return bool(found.scalar())


async def _write_notice_links(db: AsyncSession, tenant_id: int, results: list[dict[str, Any]],
                              webhook_urls: dict[str, str]) -> int:
    """反映で作った webhook を知らせの送り先の行にする（第2段 2c）。書いた数を返す。URL は記録・ログに出さない。"""
    written = 0
    for x in results:
        key = str(x.get("key") or "")
        event = NOTICE_ROOMS.get(key)
        if x.get("status") != "success" or x.get("kind") != "link_notice" or event is None or key not in webhook_urls:
            continue
        res = await db.execute(
            text(
                "INSERT INTO notification_channels (tenant_id, channel_name, webhook_url, event_types, blueprint_key)"
                " VALUES (:tid, :name, :url, :events, :bkey)"
                " ON CONFLICT (blueprint_key) WHERE blueprint_key IS NOT NULL DO NOTHING"
            ),
            {"tid": tenant_id, "name": str(x.get("name") or key), "url": webhook_urls[key],
             "events": json.dumps([event]), "bkey": key},
        )
        written += int(res.rowcount or 0)
    return written


@router.post(
    "/admin/discord/own-server/apply",
    response_model=OwnServerApplyResponse,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def apply_own_server_plan(
    body: OwnServerApplyRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> OwnServerApplyResponse:
    """確認した差を自社用サーバーに反映する。作る・変えるだけで、消さない。"""
    guild_id, blueprint, bot_token = await _load_own_context(db, tenant_id)

    # 同時に 1 本だけ反映する
    r = get_redis()
    if r is None:
        raise HTTPException(
            status_code=503,
            detail="同時に反映しないための仕組みにつながりません。少し待ってからやり直してください。",
        )
    lock_key = f"discord_own_apply:{tenant_id}"
    if not await r.set(lock_key, "1", nx=True, ex=600):
        raise HTTPException(status_code=409, detail="反映が動いています。終わってから確認し直してください。")

    try:
        started_at = datetime.now(timezone.utc)
        plan = await _read_and_plan(db, guild_id, blueprint, bot_token)
        if plan["plan_digest"] != body.plan_digest:
            raise HTTPException(
                status_code=409,
                detail="確認したあとにサーバーか設計図が変わりました。確認し直してください。",
            )

        webhook_urls: dict[str, str] = {}
        results = await apply_plan(plan, guild_id, bot_token, webhook_urls=webhook_urls)
        app_roles_written = await _write_back_app_roles(db, results)
        notice_links_written = await _write_notice_links(db, tenant_id, results, webhook_urls)

        inserted = await db.execute(
            text(_apply_insert_sql(db)),
            {
                "tid": tenant_id,
                "digest": plan["plan_digest"],
                "started": started_at,
                "finished": datetime.now(timezone.utc),
                "uid": current_user.id,
                "result": json.dumps({"rows": results}, ensure_ascii=False),
            },
        )
        run_id = int(inserted.scalar_one())
        counts = {s: sum(1 for x in results if x["status"] == s) for s in ("success", "blocked", "failed")}
        await record_audit_log(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            action="create",
            table_name="discord_server_apply_runs",
            record_id=run_id,
            new_data={**counts, "app_roles_written": app_roles_written, "notice_links_written": notice_links_written},
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072

        # 受付の部屋が設計図にあるときだけ、ボタン付きの投稿を置く（設計 §4-5）。DB の記録・監査ログには足さない
        response_rows = list(results)
        reception = next((c for c in blueprint.channels if c.key == RECEPTION_CHANNEL_KEY), None)
        if reception is not None:
            try:
                button = await ensure_reception_button(guild_id, bot_token, tenant_id)
            except Exception as exc:  # noqa: BLE001 - 部屋やロールの反映は済んでいるため適用は失敗にしない
                logger.warning("[discord_own_server] reception button failed kind=%s", type(exc).__name__)
                button = {"status": "discord_error"}
            button_status = str(button.get("status"))
            posted_ok = button_status in ("posted", "exists")
            response_rows.append({
                "kind": "post_button",
                "key": RECEPTION_CHANNEL_KEY,
                "name": reception.name,
                "field": None,
                "status": "success" if posted_ok else "failed",
                "reason": None if button_status == "posted" else button_status,
                "discord_id": button.get("message_id") if button_status == "posted" else None,
                "discord_status": None,
            })
        response_counts = {s: sum(1 for x in response_rows if x["status"] == s) for s in ("success", "blocked", "failed")}

        logger.info(
            "[discord_own_server] apply tenant=%d run=%d success=%d blocked=%d failed=%d",
            tenant_id, run_id, response_counts["success"], response_counts["blocked"], response_counts["failed"],
        )
        return OwnServerApplyResponse(
            run_id=run_id,
            success_count=response_counts["success"],
            blocked_count=response_counts["blocked"],
            failed_count=response_counts["failed"],
            results=[ApplyResultRow(**x) for x in response_rows],
        )
    finally:
        try:
            await r.delete(lock_key)
        except Exception as exc:  # noqa: BLE001 - 鍵は 10 分で自然に消える
            logger.warning("[discord_own_server] apply lock release failed tenant=%d: %s", tenant_id, exc)
