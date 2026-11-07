"""Discord OAuth2 Bot Invite フロー (ADR-091 拡張)

Bot をテナントの Discord サーバーに招待し、guild_id を自動保存する。

API:
  POST /discord/oauth/start    — Invite URL を発行（認証必須）
  GET  /discord/oauth/callback — Discord からのコールバック（公開エンドポイント）

フロー:
  1. フロントが POST /start → invite_url を受け取る
  2. ユーザーが invite_url を開き Discord サーバーを選択
  3. Discord が GET /callback?guild_id=...&state=... にリダイレクト
  4. state 検証 → guild_id を tenant_discord_config に保存
  5. フロントエンドの /channels?discord_status=connected にリダイレクト
     自社用（purpose=own）は /admin/discord-config?tab=own に戻す

前提:
  Discord Developer Portal → OAuth2 → Redirects に
  https://api.salesanchor.jp/api/v1/discord/oauth/callback を登録済みであること。
"""
from __future__ import annotations

import logging
import os
import re
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    load_user_permissions,
    require_permission,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.services import oauth_state
from app.services.audit import record_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

_DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1499458730171961535")
_DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"


def _client_secret() -> str:
    # 値はログ・応答・転送先 URL に出さない（K4）
    return os.getenv("DISCORD_CLIENT_SECRET", "")

# Bot permissions integer (confirmed from Developer Portal 2026-06-16).
# 2026-10-17: +Create Instant Invite (bit 0). 805432406 -> 805432407 (PO decision, ADR-091).
# See docs/adr/ADR-091-discord-bot-scope-definition.md for full intent.
#
# Current required permissions:
#   - Manage Roles          — create Sales Anchor Staff / Partner / Member roles in auto-setup
#   - Manage Channels       — create categories and channels; set channel permission overwrites
#   - View Channels         — bot must see channels to operate or delete them (avoids 403 50001)
#   - Send Messages         — post ticket-start button in ticket channel
#   - Read Message History  — inspect existing channels during setup and operations
#   - Kick Members          — remove customers from Discord server via app (discord_remove.py)
#   - Ban Members           — ban abusive / spam customers via app
#   - Create Instant Invite — create 7-day single-use invites for viewer signups (ADR-1019 stage 4b)
#
# Approved future permissions (no API calls yet; require separate ADR before implementation):
#   - Manage Webhooks       — planned: staff configures webhooks from app
#   - Manage Messages       — planned: delete Discord messages from app (must include audit log)
#   - Embed Links           — planned: preview tracking URLs / invoice links
#   - Attach Files          — planned: share invoice PDFs / photos via bot
#   - Add Reactions         — planned: sync app reactions to Discord
#
# Intentionally excluded:
#   - Administrator         — violates least-privilege; bypasses channel permission overwrites
#   - Manage Guild          — outside bot's operational scope
#   - Thread permissions    — ADR-091: thread features are not used
#   - Voice permissions     — outside bot's operational scope
_DISCORD_PERMISSIONS = "805432407"
_DISCORD_CALLBACK_URL = os.getenv(
    "DISCORD_CALLBACK_URL",
    "https://api.salesanchor.jp/api/v1/discord/oauth/callback",
)
_FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL") or "https://app.salesanchor.jp"


def _build_invite_url(state: str) -> str:
    # scope=bot 単体は Discord の "callback-less flow" として設計されており
    # redirect_uri へのリダイレクトが発生しない（公式仕様・2017年から不変）。
    # applications.commands を追加し response_type=code を明示することで
    # フル OAuth2 Authorization Code フローが実行され、
    # redirect_uri?guild_id=GUILD_ID&code=CODE&state=STATE にリダイレクトされる。
    # 参考: MEE6 (1,950万サーバー) / Carl-bot (1,332万サーバー) が同一パターンを採用。
    params = {
        "client_id": _DISCORD_CLIENT_ID,
        "permissions": _DISCORD_PERMISSIONS,
        "scope": "bot applications.commands",
        "response_type": "code",
        "redirect_uri": _DISCORD_CALLBACK_URL,
        "state": state,
    }
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


class _ExchangeError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


async def _exchange_code_for_guild_id(code: str) -> str:
    """code を Discord で交換し、応答の guild.id を返す（公式: Advanced Bot Authorization）。"""
    secret = _client_secret()
    if not secret:
        raise _ExchangeError("discord_not_configured")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _DISCORD_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": _DISCORD_CALLBACK_URL,
                },
                auth=(_DISCORD_CLIENT_ID, secret),
            )
    except httpx.HTTPError as e:
        logger.warning("[discord_oauth] code 交換の通信失敗: %s", type(e).__name__)
        raise _ExchangeError("code_exchange_failed") from None
    if resp.status_code != 200:
        err = ""
        try:
            err = str(resp.json().get("error", ""))[:40]
        except (ValueError, AttributeError):
            pass
        logger.warning(
            "[discord_oauth] code 交換の拒否 status=%d error=%s", resp.status_code, err
        )
        raise _ExchangeError("code_exchange_failed")
    try:
        guild = resp.json().get("guild") or {}
        gid = str(guild.get("id", ""))
    except (ValueError, AttributeError):
        gid = ""
    if not re.fullmatch(r"\d{17,19}", gid):
        logger.warning("[discord_oauth] 交換の応答に guild が無い")
        raise _ExchangeError("missing_guild_in_token")
    return gid


# ---------------------------------------------------------------------------
# POST /discord/oauth/start
# ---------------------------------------------------------------------------


class DiscordOAuthStartRequest(BaseModel):
    purpose: Literal["customer", "own"] = "customer"


@router.post(
    "/discord/oauth/start",
    dependencies=[Depends(require_permission("channels.manage"))],
)
async def discord_oauth_start(
    body: DiscordOAuthStartRequest | None = None,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Discord Bot Invite URL を発行し、state を Redis に保存する。"""
    purpose = body.purpose if body else "customer"
    if purpose == "own":
        permissions = await load_user_permissions(db, tenant_id, current_user.id)
        if "tenant.profile.edit" not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"reason": "permission_denied"},
            )
    if not _client_secret():
        logger.error("[discord_oauth] DISCORD_CLIENT_SECRET 未設定のため開始しない")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "discord_not_configured"},
        )
    try:
        issued = await oauth_state.issue_state(
            tenant_id=tenant_id,
            staff_id=current_user.id,
            extra={"purpose": purpose},
        )
    except oauth_state.OAuthStateError as e:
        logger.error("[discord_oauth] state 発行失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "redis_error"},
        )

    invite_url = _build_invite_url(issued["state"])  # type: ignore[arg-type]
    logger.info("[discord_oauth] invite URL 発行 tenant=%d purpose=%s", tenant_id, purpose)
    return {
        "invite_url": invite_url,
        "state": issued["state"],
        "expires_at": issued["expires_at"],
    }


# ---------------------------------------------------------------------------
# GET /discord/oauth/callback  （公開エンドポイント: Discord からのリダイレクト）
# ---------------------------------------------------------------------------


@router.get("/discord/oauth/callback")
async def discord_oauth_callback(
    guild_id: str | None = Query(None),
    state: str | None = Query(None),
    code: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Discord からのコールバック。code を交換し、応答の guild.id を tenant_discord_config に保存する。

    このエンドポイントは Discord からのリダイレクトなので JWT 認証なし。
    tenant_id は state ペイロードから取得する（CSRF 対策: state は one-time 使用）。
    """
    channels_url = f"{_FRONTEND_BASE_URL}/channels"

    if not state:
        return RedirectResponse(f"{channels_url}?discord_status=error&reason=missing_state")

    if not guild_id:
        # ユーザーがサーバー選択をキャンセルした場合など
        return RedirectResponse(f"{channels_url}?discord_status=error&reason=missing_guild_id")

    # guild_id は Discord Snowflake（17〜19桁の数字）のみ許可（多層防御）
    if not re.fullmatch(r"\d{17,19}", guild_id):
        logger.warning("[discord_oauth] 不正な guild_id フォーマット: %s", guild_id)
        return RedirectResponse(f"{channels_url}?discord_status=error&reason=invalid_guild_id")

    # state 検証（one-time: 検証後に Redis から削除）
    try:
        payload = await oauth_state.consume_state(state)
    except oauth_state.OAuthStateError:
        logger.error("[discord_oauth] Redis 接続失敗")
        return RedirectResponse(f"{channels_url}?discord_status=error&reason=redis_error")

    if payload is None:
        logger.warning("[discord_oauth] 無効な state（期限切れ・改ざん・再利用の可能性）")
        return RedirectResponse(f"{channels_url}?discord_status=error&reason=invalid_state")

    tenant_id = payload.get("tenant_id")
    staff_id = payload.get("staff_id")
    # デプロイ前に発行した state には purpose が無い（期限 600 秒）。customer として扱う
    purpose = payload.get("purpose", "customer")
    if purpose not in ("customer", "own"):
        return RedirectResponse(f"{channels_url}?discord_status=error&reason=invalid_payload")
    own_url = f"{_FRONTEND_BASE_URL}/admin/discord-config?tab=own"
    base = own_url + "&" if purpose == "own" else channels_url + "?"
    if not tenant_id:
        return RedirectResponse(f"{base}discord_status=error&reason=invalid_payload")

    tenant_id = int(tenant_id)

    staff_id_int = int(staff_id) if staff_id else None

    # URL の guild_id は目安（hint）。Discord に code を交換させ、応答の guild.id だけを保存する。
    # 交換は state 消費の後・DB の取引を開く前（外部待ちで取引を開いたままにしない）。
    if not code:
        return RedirectResponse(f"{base}discord_status=error&reason=missing_code")
    try:
        verified = await _exchange_code_for_guild_id(code)
    except _ExchangeError as e:
        return RedirectResponse(f"{base}discord_status=error&reason={e.reason}")
    if verified != guild_id:
        logger.warning(
            "[discord_oauth] guild_id 不一致 tenant=%d purpose=%s url_guild_id=%s verified=%s",
            tenant_id, purpose, guild_id, verified,
        )
        return RedirectResponse(f"{base}discord_status=error&reason=guild_mismatch")

    # tenant context を設定（audit_logs の RLS に必要: app.tenant_id が未設定のまま
    # INSERT すると RLS ポリシー tenant_isolation_audit_logs に弾かれ 500 になる）
    # get_db の finally → clear_tenant_context が全経路（成功・例外）でリセットを担保
    from app.auth.dependencies import set_tenant_context  # noqa: PLC0415
    await set_tenant_context(db, tenant_id)

    # guild_id と接続者を upsert
    try:
        await db.execute(
            text("""
                INSERT INTO public.tenant_discord_config (tenant_id, purpose, guild_id, connected_by_staff_id)
                VALUES (:tid, :purpose, :guild_id, :staff_id)
                ON CONFLICT (tenant_id, purpose)
                DO UPDATE SET
                    guild_id = EXCLUDED.guild_id,
                    connected_by_staff_id = EXCLUDED.connected_by_staff_id,
                    updated_at = NOW()
            """),
            {"tid": tenant_id, "purpose": purpose, "guild_id": verified, "staff_id": staff_id_int},
        )
        await record_audit_log(
            db=db,
            tenant_id=tenant_id,
            user_id=staff_id_int if staff_id_int else tenant_id,
            action="update",
            table_name="tenant_discord_config",
            record_id=tenant_id,
            new_data={
                "guild_id": verified,
                "source": "discord_oauth_callback",
                "purpose": purpose,
                "verified_by": "token_exchange",
            },
        )
        await db.commit()
    except IntegrityError:
        # uq_tenant_discord_config_guild_id: 同じサーバーが既に登録されている
        await db.rollback()
        logger.warning(
            "[discord_oauth] guild_id 登録済み tenant=%d purpose=%s guild_id=%s",
            tenant_id, purpose, verified,
        )
        return RedirectResponse(f"{base}discord_status=error&reason=guild_already_registered")
    await reset_tenant_context(db, tenant_id)  # ADR-072

    logger.info(
        "[discord_oauth] guild_id 保存 tenant=%d purpose=%s guild_id=%s", tenant_id, purpose, verified
    )
    return RedirectResponse(f"{base}discord_status=connected")
