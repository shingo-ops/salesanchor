"""Discord Auto Setup ウィザード API のテスト群。

カバー:
- 全ステップ正常作成（happy path）
- 冪等動作: 2回目実行でロール・チャンネルがスキップされること
- 部分失敗: Discord API が 403 を返すと status="partial"
- guild_id 未設定 → 422
- Bot トークン未設定 → 503
- 権限ビット値の正確性（member-announcements / ticket-start）

設計方針:
  DB レイヤーはモックで置換（public. スキーマ修飾は SQLite 非対応のため）。
  Discord API レイヤーは discord_api_request をパッチして制御。

実行:
    pytest backend/tests/test_discord_auto_setup.py -v
"""
from __future__ import annotations

import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ["DISCORD_BOT_TOKEN_999"] = "test-bot-token"

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.routers import discord_auto_setup as auto_setup_router

_ALL_PERMS = {"tenant.profile.edit", "tenant.profile.view"}


# ---------------------------------------------------------------------------
# テスト用ヘルパー
# ---------------------------------------------------------------------------


def _mock_user() -> MagicMock:
    u = MagicMock()
    u.id = 1
    u.tenant_id = 999
    u.email = "admin@example.com"
    return u


def _execute_result(row=None, *, is_mapping: bool = False) -> MagicMock:
    """db.execute() の戻り値モックを生成する。"""
    result = MagicMock()
    if is_mapping:
        result.mappings.return_value.first.return_value = row
    else:
        result.first.return_value = row
    return result


def _make_mock_db(
    guild_id: str | None = "GUILD-1",
    existing_config: dict | None = None,
) -> AsyncMock:
    """テスト用モック DB セッションを生成する。

    router 内の execute() 呼び出し順:
      1. SELECT guild_id FROM public.tenant_discord_config
      2. SELECT ... FROM public.tenant_discord_ticket_config
      3. INSERT ... ON CONFLICT (upsert)
    """
    mock_db = AsyncMock()

    guild_row = (guild_id,) if guild_id else None

    cfg_row: MagicMock | None = None
    if existing_config is not None:
        cfg_row = MagicMock()
        cfg_row.__getitem__ = lambda self, k: existing_config.get(k)  # type: ignore
        cfg_row.get = lambda k, default=None: existing_config.get(k, default)  # type: ignore

    mock_db.execute = AsyncMock(side_effect=[
        _execute_result(guild_row),           # guild_id query
        _execute_result(cfg_row, is_mapping=True),  # config query
        MagicMock(),                           # upsert
    ])
    mock_db.commit = AsyncMock()
    return mock_db


def _build_app(mock_db: AsyncMock, tenant_id: int = 999) -> FastAPI:
    app = FastAPI()

    async def override_db():
        yield mock_db

    async def override_user():
        return _mock_user()

    async def override_tenant():
        return tenant_id

    app.include_router(auto_setup_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_current_tenant] = override_tenant
    return app


def _common_patches(stack: ExitStack) -> AsyncMock:
    """共通パッチ: 認証・監査ログ・テナントコンテキストをスキップ。"""
    stack.enter_context(patch(
        "app.auth.dependencies.load_user_permissions",
        new=AsyncMock(return_value=_ALL_PERMS),
    ))
    stack.enter_context(patch(
        "app.routers.discord_auto_setup.record_audit_log",
        new=AsyncMock(return_value=None),
    ))
    stack.enter_context(patch(
        "app.routers.discord_auto_setup.reset_tenant_context",
        new=AsyncMock(return_value=None),
    ))
    mock_api = AsyncMock()
    stack.enter_context(patch(
        "app.routers.discord_auto_setup.discord_api_request",
        new=mock_api,
    ))
    return mock_api


# ---------------------------------------------------------------------------
# テスト: happy path（全ステップ新規作成）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_all_created() -> None:
    """全8ステップが正常作成され status=completed になること。"""
    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    # discord_api_request の呼び出し順に応じた応答リスト
    discord_responses = [
        [],                                                              # 1: GET roles
        [],                                                              # 2: GET channels
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},             # 3: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                      # 4: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                        # 5: POST role_member
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},            # 6: POST category
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},        # 7: POST ch_ticket
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},# 8: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},# 9: POST ch_partner
        {"id": "MSG-1"},                                                 # 10: POST button
    ]

    with ExitStack() as stack:
        mock_api = _common_patches(stack)
        mock_api.side_effect = discord_responses

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["error_hint"] is None
    assert "role_order_guide_url" in body

    steps = {s["step"]: s for s in body["steps"]}
    assert steps["role_staff"] == {"step": "role_staff", "status": "created", "discord_id": "ROLE-STAFF", "error": None}
    assert steps["role_partner"]["status"] == "created"
    assert steps["role_member"]["status"] == "created"
    assert steps["category"]["status"] == "created"
    assert steps["category"]["discord_id"] == "CAT-1"
    assert steps["ch_ticket"]["status"] == "created"
    assert steps["ch_member"]["status"] == "created"
    assert steps["ch_partner"]["status"] == "created"
    assert steps["button"]["status"] == "posted"
    assert steps["button"]["discord_id"] == "MSG-1"

    # Discord API が 10 回呼ばれること
    assert mock_api.call_count == 10

    # DB commit が呼ばれること（ADR-072）
    mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# テスト: 冪等動作（2回目はスキップ）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotent_skips_existing() -> None:
    """既存のロール・チャンネルがある場合はスキップされ status=completed になること。"""
    existing_config = {
        "ticket_category_id": "CAT-1",
        "ticket_button_channel_id": "CH-TICKET",
        "staff_role_id": "ROLE-STAFF",
        "small_channel_id": "CH-MEMBER",
        "large_channel_id": "CH-PARTNER",
        "small_role_name": "Member",
        "large_role_name": "Partner",
    }
    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=existing_config)
    app = _build_app(mock_db)

    # Discord API 上にも既存オブジェクトが存在する
    existing_roles = [
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},
        {"id": "ROLE-PARTNER", "name": "Partner"},
        {"id": "ROLE-MEMBER", "name": "Member"},
    ]
    existing_channels = [
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},
    ]

    discord_responses = [
        existing_roles,     # GET roles
        existing_channels,  # GET channels
        # ch_ticket が skipped のためボタン投稿は発生しない
    ]

    with ExitStack() as stack:
        mock_api = _common_patches(stack)
        mock_api.side_effect = discord_responses

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"

    steps = {s["step"]: s for s in body["steps"]}
    assert steps["role_staff"]["status"] == "skipped"
    assert steps["role_staff"]["discord_id"] == "ROLE-STAFF"
    assert steps["role_partner"]["status"] == "skipped"
    assert steps["role_member"]["status"] == "skipped"
    assert steps["category"]["status"] == "skipped"
    assert steps["category"]["discord_id"] == "CAT-1"
    assert steps["ch_ticket"]["status"] == "skipped"
    assert steps["ch_member"]["status"] == "skipped"
    assert steps["ch_partner"]["status"] == "skipped"
    # ch_ticket が skipped のため button も skipped
    assert steps["button"]["status"] == "skipped"

    # GET×2 のみ（ボタン投稿なし）
    assert mock_api.call_count == 2


# ---------------------------------------------------------------------------
# テスト: 部分失敗（role_staff 作成403）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_partial_failure_on_role() -> None:
    """ロール作成が失敗しても後続ステップを継続し status=partial になること。"""
    from app.services.discord_rest import DiscordAPIError

    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    discord_responses = [
        [],                                                              # 1: GET roles
        [],                                                              # 2: GET channels
        DiscordAPIError("Missing Permissions", status_code=403),        # 3: POST role_staff 失敗
        {"id": "ROLE-PARTNER", "name": "Partner"},                      # 4: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                        # 5: POST role_member
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},            # 6: POST category
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},        # 7: POST ch_ticket
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},# 8: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},# 9: POST ch_partner
        {"id": "MSG-1"},                                                 # 10: POST button
    ]

    with ExitStack() as stack:
        mock_api = _common_patches(stack)
        mock_api.side_effect = discord_responses

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "partial"
    assert body["error_hint"] is not None

    steps = {s["step"]: s for s in body["steps"]}
    assert steps["role_staff"]["status"] == "failed"
    assert steps["role_staff"]["error"] is not None
    # 後続ステップは継続
    assert steps["role_partner"]["status"] == "created"
    assert steps["role_member"]["status"] == "created"
    assert steps["button"]["status"] == "posted"


# ---------------------------------------------------------------------------
# テスト: guild_id 未設定 → 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_guild_id_returns_422() -> None:
    """tenant_discord_config に guild_id がない場合は 422 を返すこと。"""
    mock_db = _make_mock_db(guild_id=None)
    app = _build_app(mock_db)

    with ExitStack() as stack:
        _common_patches(stack)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    assert resp.status_code == 422
    assert "未接続" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# テスト: Bot トークン未設定 → 503
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_bot_token_returns_503() -> None:
    """DISCORD_BOT_TOKEN_{tenant_id} が未設定の場合は 503 を返すこと。"""
    # テナント 998 にはトークンが設定されていない
    mock_db = _make_mock_db(guild_id="GUILD-998")
    app = _build_app(mock_db, tenant_id=998)

    with ExitStack() as stack:
        _common_patches(stack)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    assert resp.status_code == 503
    assert "Bot トークン" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# テスト: カテゴリ作成失敗 → チャンネル作成がスキップされること
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_category_failure_blocks_channels() -> None:
    """カテゴリ作成が失敗した場合、チャンネル作成・ボタン投稿が全て failed になること。

    ルート直下へのチャンネル作成 POST は発生しないこと。
    """
    from app.services.discord_rest import DiscordAPIError

    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    discord_responses = [
        [],                                                              # 1: GET roles
        [],                                                              # 2: GET channels
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},             # 3: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                      # 4: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                        # 5: POST role_member
        DiscordAPIError("Missing Permissions", status_code=403),        # 6: POST category 失敗
        # POST チャンネルは呼ばれない
    ]

    with ExitStack() as stack:
        mock_api = _common_patches(stack)
        mock_api.side_effect = discord_responses

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "partial"
    assert body["error_hint"] is not None

    steps = {s["step"]: s for s in body["steps"]}
    assert steps["category"]["status"] == "failed"
    # チャンネル・ボタンは全て failed（ルート直下作成防止）
    assert steps["ch_ticket"]["status"] == "failed"
    assert "カテゴリ" in steps["ch_ticket"]["error"]
    assert steps["ch_member"]["status"] == "failed"
    assert steps["ch_partner"]["status"] == "failed"
    assert steps["button"]["status"] == "failed"

    # GET×2 + role POST×3 + category POST×1 = 計6回のみ（チャンネルPOSTなし）
    assert mock_api.call_count == 6


# ---------------------------------------------------------------------------
# テスト: 権限ビット値の検証
# ---------------------------------------------------------------------------


def test_member_announcements_overwrites_bits() -> None:
    """member-announcements の権限ビットが設計通りであること（design.md §2 参照）。"""
    from app.routers.discord_auto_setup import _member_announcements_overwrites

    _VIEW = 1024
    _SEND = 2048
    _READ = 65536

    overwrites = _member_announcements_overwrites(
        guild_id="GUILD-1",
        member_role_id="MEMBER-ROLE",
        partner_role_id="PARTNER-ROLE",
        staff_role_id="STAFF-ROLE",
    )
    by_id = {ow["id"]: ow for ow in overwrites}

    # @everyone: 全deny
    assert int(by_id["GUILD-1"]["allow"]) == 0
    assert int(by_id["GUILD-1"]["deny"]) == _VIEW | _SEND | _READ

    # Member: view+read 許可・send 禁止
    assert int(by_id["MEMBER-ROLE"]["allow"]) == _VIEW | _READ
    assert int(by_id["MEMBER-ROLE"]["deny"]) == _SEND

    # Partner: view+read 許可・send 禁止（Large顧客は Partner ロールのみの場合あり）
    assert int(by_id["PARTNER-ROLE"]["allow"]) == _VIEW | _READ
    assert int(by_id["PARTNER-ROLE"]["deny"]) == _SEND

    # Staff: 全許可
    assert int(by_id["STAFF-ROLE"]["allow"]) == _VIEW | _SEND | _READ
    assert int(by_id["STAFF-ROLE"]["deny"]) == 0


def test_ticket_ch_overwrites_bits() -> None:
    """ticket-start の権限ビットが設計通りであること。"""
    from app.routers.discord_auto_setup import _ticket_ch_overwrites

    _VIEW = 1024
    _SEND = 2048
    _READ = 65536

    overwrites = _ticket_ch_overwrites("GUILD-1", "STAFF-ROLE")
    by_id = {ow["id"]: ow for ow in overwrites}

    # @everyone: view+read 許可・send 禁止
    assert int(by_id["GUILD-1"]["allow"]) == _VIEW | _READ
    assert int(by_id["GUILD-1"]["deny"]) == _SEND

    # Staff: send 許可
    assert int(by_id["STAFF-ROLE"]["allow"]) == _SEND


def test_partner_announcements_overwrites_bits() -> None:
    """partner-announcements の権限ビットが設計通りであること。"""
    from app.routers.discord_auto_setup import _partner_announcements_overwrites

    _VIEW = 1024
    _SEND = 2048
    _READ = 65536

    overwrites = _partner_announcements_overwrites(
        guild_id="GUILD-1",
        partner_role_id="PARTNER-ROLE",
        staff_role_id="STAFF-ROLE",
    )
    by_id = {ow["id"]: ow for ow in overwrites}

    # @everyone: 全deny
    assert int(by_id["GUILD-1"]["allow"]) == 0
    assert int(by_id["GUILD-1"]["deny"]) == _VIEW | _SEND | _READ

    # Partner: view+read 許可・send 禁止
    assert int(by_id["PARTNER-ROLE"]["allow"]) == _VIEW | _READ
    assert int(by_id["PARTNER-ROLE"]["deny"]) == _SEND

    # Staff: 全許可
    assert int(by_id["STAFF-ROLE"]["allow"]) == _VIEW | _SEND | _READ
    assert int(by_id["STAFF-ROLE"]["deny"]) == 0
