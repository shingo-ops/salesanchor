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
        {"id": "BOT-1"},                                                 # 3: GET /users/@me
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},             # 4: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                      # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                        # 6: POST role_member
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},            # 7: POST category
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},        # 8: POST ch_ticket
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},# 9: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},# 10: POST ch_partner
        {"id": "MSG-1"},                                                 # 11: POST button
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

    # Discord API が 11 回呼ばれること（GET roles + GET channels + GET users/@me + roles×3 + channels×4 + button）
    assert mock_api.call_count == 11

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

    _existing_button_msg = [
        {
            "id": "MSG-EXISTING",
            "content": "サポートが必要な場合は下のボタンを押してください。",
            "components": [{"type": 1, "components": [{"type": 2, "custom_id": "ticket_open"}]}],
        }
    ]

    discord_responses = [
        existing_roles,          # GET roles
        existing_channels,       # GET channels
        {"id": "BOT-1"},         # GET /users/@me
        _existing_button_msg,    # GET messages（ボタン確認: 既存ボタンあり）
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
    # 既存ボタンを検出したため skipped（discord_id = 既存メッセージID）
    assert steps["button"]["status"] == "skipped"
    assert steps["button"]["discord_id"] == "MSG-EXISTING"

    # GET×2 + GET /users/@me×1 + GET messages×1 = 4
    assert mock_api.call_count == 4


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
        {"id": "BOT-1"},                                                 # 3: GET /users/@me
        DiscordAPIError("Missing Permissions", status_code=403),        # 4: POST role_staff 失敗
        {"id": "ROLE-PARTNER", "name": "Partner"},                      # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                        # 6: POST role_member
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},            # 7: POST category
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},        # 8: POST ch_ticket
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},# 9: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},# 10: POST ch_partner
        {"id": "MSG-1"},                                                 # 11: POST button
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
        {"id": "BOT-1"},                                                 # 3: GET /users/@me
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},             # 4: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                      # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                        # 6: POST role_member
        DiscordAPIError("Missing Permissions", status_code=403),        # 7: POST category 失敗
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

    # GET×2 + GET /users/@me×1 + role POST×3 + category POST×1 = 計7回のみ（チャンネルPOSTなし）
    assert mock_api.call_count == 7


# ---------------------------------------------------------------------------
# テスト: 権限ビット値の検証
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# テスト: 再実行時に Discord 上の既存チャンネルを名前検索でスキップ（重複作成防止）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rerun_skips_existing_category_by_name() -> None:
    """DB未保存でも Discord 上に同名カテゴリがある場合は重複作成せず skipped になること。

    シナリオ:
      1回目: category 作成成功 / ch_ticket 403失敗 → DB INSERT スキップ（Cause E fix）
      2回目（Cause D修正後）: Discord GET に category が存在 → name+type で検出 → skipped
    """
    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    # Discord 上にカテゴリのみ存在（テキストチャンネルは前回失敗で未作成）
    existing_channels = [
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},
    ]

    discord_responses = [
        [],               # 1: GET roles
        existing_channels,  # 2: GET channels
        {"id": "BOT-1"},    # 3: GET /users/@me
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},              # 4: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                       # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                         # 6: POST role_member
        # category: 名前検索でスキップ → POST なし
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},         # 7: POST ch_ticket
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0}, # 8: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},# 9: POST ch_partner
        {"id": "MSG-1"},                                                  # 10: POST button
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
    # カテゴリは重複作成されず skipped（discord_id は Discord から取得したもの）
    assert steps["category"]["status"] == "skipped"
    assert steps["category"]["discord_id"] == "CAT-1"
    # テキストチャンネルは新規作成（前回未作成）
    assert steps["ch_ticket"]["status"] == "created"
    assert steps["ch_member"]["status"] == "created"
    assert steps["ch_partner"]["status"] == "created"
    assert steps["button"]["status"] == "posted"

    # GET×2 + GET /users/@me×1 + roles×3 + ch_ticket+ch_member+ch_partner+button×1 = 10（category POSTなし）
    assert mock_api.call_count == 10

    # NOT NULL カラムが揃うため DB commit が呼ばれる
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_rerun_skips_existing_channels_by_name_and_parent() -> None:
    """DB未保存でも Discord 上に同名・同parent チャンネルがある場合は skipped になること。

    シナリオ: category + ch_ticket が既に Discord 上に存在するが DB行はない。
    ch_member / ch_partner は存在しない → 作成される。
    """
    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    # カテゴリと ch_ticket のみ Discord に存在（ch_member/ch_partner は未作成）
    existing_channels = [
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0, "parent_id": "CAT-1"},
    ]

    discord_responses = [
        [],               # 1: GET roles
        existing_channels,  # 2: GET channels
        {"id": "BOT-1"},    # 3: GET /users/@me
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},               # 4: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                        # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                          # 6: POST role_member
        # category: 名前検索 skipped
        # ch_ticket: 名前+parent_id 検索 skipped
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},  # 7: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0}, # 8: POST ch_partner
        [],               # 9: GET messages（ボタン確認: 未投稿）
        {"id": "MSG-1"},  # 10: POST button
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
    assert steps["category"]["status"] == "skipped"
    assert steps["category"]["discord_id"] == "CAT-1"
    assert steps["ch_ticket"]["status"] == "skipped"
    assert steps["ch_ticket"]["discord_id"] == "CH-TICKET"
    assert steps["ch_member"]["status"] == "created"
    assert steps["ch_partner"]["status"] == "created"
    # 既存チャンネルにボタンが未存在 → 新規投稿
    assert steps["button"]["status"] == "posted"
    assert steps["button"]["discord_id"] == "MSG-1"

    # GET×2 + GET /users/@me×1 + roles×3 + ch_member+ch_partner + GET messages + POST button = 10
    assert mock_api.call_count == 10

    mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# テスト: 初回実行 + チャンネル作成403 → 500 でなく 200 partial（Cause E 回帰テスト）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_run_channel_403_returns_200_partial_not_500() -> None:
    """初回実行（DB行なし）でチャンネル作成が403失敗しても 500 にならず 200 partial を返すこと。

    本番再現シナリオ（2026-06-14 VPS確認）:
      - カテゴリ作成: 成功
      - ch_ticket / ch_member / ch_partner: 403 Missing Permissions
      - DB行なし → ticket_button_channel_id NOT NULL 違反を防ぐため INSERT をスキップ
    """
    from app.services.discord_rest import DiscordAPIError

    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    discord_responses = [
        [],                                                               # 1: GET roles
        [],                                                               # 2: GET channels
        {"id": "BOT-1"},                                                  # 3: GET /users/@me
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},              # 4: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                       # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                         # 6: POST role_member
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},             # 7: POST category 成功
        DiscordAPIError("Missing Permissions", status_code=403),         # 8: POST ch_ticket 失敗
        DiscordAPIError("Missing Permissions", status_code=403),         # 9: POST ch_member 失敗
        DiscordAPIError("Missing Permissions", status_code=403),         # 10: POST ch_partner 失敗
        # button は ch_ticket 失敗のため呼ばれない
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
    assert steps["category"]["status"] == "created"
    assert steps["ch_ticket"]["status"] == "failed"
    assert steps["ch_member"]["status"] == "failed"
    assert steps["ch_partner"]["status"] == "failed"
    assert steps["button"]["status"] == "failed"

    # NOT NULL カラムが揃わないため DB commit は呼ばれない
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_first_run_all_channels_403_returns_200_partial_not_500() -> None:
    """初回実行でカテゴリ含む全チャンネル作成が403失敗しても 500 にならず 200 partial を返すこと。"""
    from app.services.discord_rest import DiscordAPIError

    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    discord_responses = [
        [],                                                               # 1: GET roles
        [],                                                               # 2: GET channels
        {"id": "BOT-1"},                                                  # 3: GET /users/@me
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},              # 4: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                       # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                         # 6: POST role_member
        DiscordAPIError("Missing Permissions", status_code=403),         # 7: POST category 失敗
        # チャンネル作成は全スキップ（category失敗フロー）
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

    steps = {s["step"]: s for s in body["steps"]}
    assert steps["category"]["status"] == "failed"
    assert steps["ch_ticket"]["status"] == "failed"
    assert steps["button"]["status"] == "failed"

    # カテゴリも NOT NULL → DB commit は呼ばれない
    mock_db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# テスト: カテゴリ作成に Bot member overwrite が含まれること（Cause F 回帰テスト）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_category_includes_bot_member_overwrite() -> None:
    """カテゴリ作成時の permission_overwrites に Bot ユーザー (type=1) の VIEW_CHANNEL allow が含まれること。

    背景 (Cause F, 2026-06-15):
      カテゴリに @everyone deny VIEW_CHANNEL のみ設定すると、Bot 自身も VIEW_CHANNEL を
      失い、カテゴリ内のチャンネルに permission_overwrites を設定できず 403 になる。
      GET /users/@me で取得した bot_user_id を type=1 member overwrite で明示的に許可する。
    """
    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    discord_responses = [
        [],                                                              # 1: GET roles
        [],                                                              # 2: GET channels
        {"id": "BOT-USER-123"},                                          # 3: GET /users/@me
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},             # 4: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                      # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                        # 6: POST role_member
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},            # 7: POST category
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},        # 8: POST ch_ticket
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},# 9: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},# 10: POST ch_partner
        {"id": "MSG-1"},                                                 # 11: POST button
    ]

    with ExitStack() as stack:
        mock_api = _common_patches(stack)
        mock_api.side_effect = discord_responses

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"

    # 7番目の呼び出し（index=6）がカテゴリ作成 POST /guilds/GUILD-1/channels
    category_call = mock_api.call_args_list[6]
    overwrites = category_call.kwargs["json"]["permission_overwrites"]
    by_type = {ow["type"]: ow for ow in overwrites}

    # type=0 (@everyone): VIEW_CHANNEL deny が存在する
    assert 0 in by_type
    assert int(by_type[0]["deny"]) & 1024  # VIEW_CHANNEL = 1024

    # type=1 (member overwrite): bot_user_id = "BOT-USER-123" かつ VIEW_CHANNEL allow
    assert 1 in by_type, "Bot member overwrite (type=1) が存在すること"
    assert by_type[1]["id"] == "BOT-USER-123"
    assert int(by_type[1]["allow"]) & 1024  # VIEW_CHANNEL


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


# ---------------------------------------------------------------------------
# テスト: button 冪等化（_ensure_ticket_button_step）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_existing_channel_without_button_posts_button() -> None:
    """既存 ticket-start チャンネルにボタンが無い場合、ボタンを投稿すること。"""
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
        existing_roles,    # GET roles
        existing_channels, # GET channels
        {"id": "BOT-1"},   # GET /users/@me
        [],                # GET messages（ボタン未存在）
        {"id": "MSG-NEW"}, # POST button
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
    assert steps["ch_ticket"]["status"] == "skipped"
    # ボタン未存在 → 投稿される
    assert steps["button"]["status"] == "posted"
    assert steps["button"]["discord_id"] == "MSG-NEW"

    # GET×2 + GET /users/@me×1 + GET messages×1 + POST button×1 = 5
    assert mock_api.call_count == 5


@pytest.mark.asyncio
async def test_existing_channel_with_button_skips_button() -> None:
    """既存 ticket-start チャンネルにボタンが既にある場合、重複投稿しないこと。"""
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
    existing_button_messages = [
        {
            "id": "MSG-EXISTING",
            "content": "サポートが必要な場合は下のボタンを押してください。",
            "components": [
                {"type": 1, "components": [{"type": 2, "custom_id": "ticket_open"}]}
            ],
        }
    ]

    discord_responses = [
        existing_roles,           # GET roles
        existing_channels,        # GET channels
        {"id": "BOT-1"},          # GET /users/@me
        existing_button_messages, # GET messages（ボタン既存）
        # POST button は呼ばれない
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
    assert steps["ch_ticket"]["status"] == "skipped"
    # 既存ボタン検出 → 重複投稿しない
    assert steps["button"]["status"] == "skipped"
    assert steps["button"]["discord_id"] == "MSG-EXISTING"

    # POST button が呼ばれないこと（GET×2 + GET /users/@me×1 + GET messages×1 = 4）
    assert mock_api.call_count == 4


@pytest.mark.asyncio
async def test_button_post_403_returns_descriptive_error() -> None:
    """ボタン投稿が 403 Missing Permissions で失敗した場合、ロール順を示すエラーを返すこと。"""
    from app.services.discord_rest import DiscordAPIError

    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)

    discord_responses = [
        [],                                                              # 1: GET roles
        [],                                                              # 2: GET channels
        {"id": "BOT-1"},                                                 # 3: GET /users/@me
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},             # 4: POST role_staff
        {"id": "ROLE-PARTNER", "name": "Partner"},                      # 5: POST role_partner
        {"id": "ROLE-MEMBER", "name": "Member"},                        # 6: POST role_member
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},            # 7: POST category
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},        # 8: POST ch_ticket (created)
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},# 9: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},# 10: POST ch_partner
        DiscordAPIError("Missing Permissions", status_code=403),        # 11: POST button 403
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

    steps = {s["step"]: s for s in body["steps"]}
    assert steps["button"]["status"] == "failed"
    # 403 エラーにはロール順に関するガイドが含まれる
    assert steps["button"]["error"] is not None
    assert "SEND_MESSAGES" in steps["button"]["error"]
    assert "上位" in steps["button"]["error"]


@pytest.mark.asyncio
async def test_button_read_403_returns_descriptive_error() -> None:
    """ボタン確認のメッセージ取得が 403 で失敗した場合、権限不足エラーを返すこと。"""
    from app.services.discord_rest import DiscordAPIError

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
        existing_roles,    # GET roles
        existing_channels, # GET channels
        {"id": "BOT-1"},   # GET /users/@me
        DiscordAPIError("Missing Permissions", status_code=403),  # GET messages 403
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

    steps = {s["step"]: s for s in body["steps"]}
    assert steps["button"]["status"] == "failed"
    assert steps["button"]["error"] is not None
    assert "チャンネル権限" in steps["button"]["error"] or "VIEW_CHANNEL" in steps["button"]["error"]
