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
os.environ["DISCORD_BOT_TOKEN"] = "test-bot-token"

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
    # サーバー名義（webhook）投稿は別テストで検証。ここでは Bot 名義の投稿経路に固定する
    stack.enter_context(patch(
        "app.routers.discord_auto_setup.fetch_guild_identity",
        new=AsyncMock(return_value=None),
    ))
    mock_api = AsyncMock()
    stack.enter_context(patch(
        "app.routers.discord_auto_setup.discord_api_request",
        new=mock_api,
    ))
    return mock_api


_CAT_DM = "\U0001F4E9\uff5cDM"
_CAT_MEMBER = "\U0001F340\uff5cStock Information"
_CAT_LARGE = "\U0001F352\uff5cStock Information"


def _migrated_channels() -> list[dict]:
    """新構成（📩｜DM / 🍀 / 🍒）が構築済みの Discord チャンネル一覧。"""
    return [
        {"id": "CAT-1", "name": _CAT_DM, "type": 4},
        {"id": "CAT-MEMBER", "name": _CAT_MEMBER, "type": 4},
        {"id": "CAT-LARGE", "name": _CAT_LARGE, "type": 4},
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0, "parent_id": "CAT-MEMBER"},
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0, "parent_id": "CAT-LARGE"},
    ]


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
        {"id": "CAT-MEMBER", "name": "\U0001F340\uff5cStock Information", "type": 4},  # POST category_stock_member
        {"id": "CAT-LARGE", "name": "\U0001F352\uff5cStock Information", "type": 4},   # POST category_stock_large
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

    # Discord API が 13 回呼ばれること（GET×3 + roles×3 + categories×3 + channels×3 + button）
    assert mock_api.call_count == 13

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
    existing_channels = _migrated_channels()

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
        {"id": "CAT-MEMBER", "name": "\U0001F340\uff5cStock Information", "type": 4},  # POST category_stock_member
        {"id": "CAT-LARGE", "name": "\U0001F352\uff5cStock Information", "type": 4},   # POST category_stock_large
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
    """DISCORD_BOT_TOKEN が未設定の場合は 503 を返すこと（ADR-146 B方式: 共通 Token）。"""
    mock_db = _make_mock_db(guild_id="GUILD-998")
    app = _build_app(mock_db, tenant_id=998)

    with ExitStack() as stack:
        _common_patches(stack)
        # B方式: 共通 DISCORD_BOT_TOKEN を空にして 503 を確認（patch.dict がテスト後に自動復元）
        stack.enter_context(patch.dict(os.environ, {"DISCORD_BOT_TOKEN": ""}))
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
    """DM カテゴリ作成が失敗した場合、ticket-start・ボタンが failed になること。

    ルート直下へのチャンネル作成 POST は発生しない。在庫アナウンスは別カテゴリのため継続する。
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
        DiscordAPIError("Missing Permissions", status_code=403),        # 7: POST category(DM) 失敗
        {"id": "CAT-MEMBER", "name": _CAT_MEMBER, "type": 4},           # 8: POST category_stock_member
        {"id": "CAT-LARGE", "name": _CAT_LARGE, "type": 4},             # 9: POST category_stock_large
        # ticket-start は DM カテゴリ無しのため POST されない
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},  # 10: POST ch_member
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},# 11: POST ch_partner
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
    # ticket-start・ボタンは failed（ルート直下作成防止）
    assert steps["ch_ticket"]["status"] == "failed"
    assert "カテゴリ" in steps["ch_ticket"]["error"]
    assert steps["button"]["status"] == "failed"
    assert steps["ch_member"]["status"] == "created"
    assert steps["ch_partner"]["status"] == "created"

    # GET×3 + role×3 + category×3 + ch_member/ch_partner×2 = 11（ticket-start の POST なし）
    assert mock_api.call_count == 11
    created_names = [
        c.kwargs["json"]["name"]
        for c in mock_api.call_args_list
        if c.kwargs.get("method") == "POST" and c.kwargs["path"].endswith("/channels")
    ]
    assert "ticket-start" not in created_names


# ---------------------------------------------------------------------------
# テスト: 権限ビット値の検証
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# テスト: 再実行時に Discord 上の既存チャンネルを名前検索でスキップ（重複作成防止）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rerun_skips_existing_category_by_name() -> None:
    """DB未保存でも Discord 上に旧「Sales Anchor」カテゴリがある場合は重複作成せず名前変更になること。

    シナリオ:
      1回目: category 作成成功 / ch_ticket 403失敗 → DB INSERT スキップ（Cause E fix）
      2回目: Discord GET に旧 category が存在 → name+type で検出 → 📩｜DM へ名前変更
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
        {},                                                               # 7: PATCH category 名前変更
        {"id": "CAT-MEMBER", "name": _CAT_MEMBER, "type": 4},            # 8: POST stock member
        {"id": "CAT-LARGE", "name": _CAT_LARGE, "type": 4},              # 9: POST stock large
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
    # 旧「Sales Anchor」は重複作成されず名前変更で引き継ぐ（discord_id は Discord から取得したもの）
    assert steps["category"]["status"] == "updated"
    assert steps["category"]["discord_id"] == "CAT-1"
    # テキストチャンネルは新規作成（前回未作成）
    assert steps["ch_ticket"]["status"] == "created"
    assert steps["ch_member"]["status"] == "created"
    assert steps["ch_partner"]["status"] == "created"
    assert steps["button"]["status"] == "posted"

    patch_call = mock_api.call_args_list[6]
    assert patch_call.kwargs["method"] == "PATCH"
    assert patch_call.kwargs["path"] == "/channels/CAT-1"
    assert patch_call.kwargs["json"] == {"name": _CAT_DM}

    # GET×3 + roles×3 + PATCH×1 + categories×2 + channels×3 + button×1 = 13（DM カテゴリ POSTなし）
    assert mock_api.call_count == 13

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
        {},                                                               # 7: PATCH category 名前変更
        {"id": "CAT-MEMBER", "name": _CAT_MEMBER, "type": 4},            # 8: POST stock member
        {"id": "CAT-LARGE", "name": _CAT_LARGE, "type": 4},              # 9: POST stock large
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
    assert steps["category"]["status"] == "updated"
    assert steps["category"]["discord_id"] == "CAT-1"
    assert steps["ch_ticket"]["status"] == "skipped"
    assert steps["ch_ticket"]["discord_id"] == "CH-TICKET"
    assert steps["ch_member"]["status"] == "created"
    assert steps["ch_partner"]["status"] == "created"
    # 既存チャンネルにボタンが未存在 → 新規投稿
    assert steps["button"]["status"] == "posted"
    assert steps["button"]["discord_id"] == "MSG-1"

    # GET×3 + roles×3 + PATCH + categories×2 + ch_member+ch_partner + GET messages + POST button = 13
    assert mock_api.call_count == 13

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
        {"id": "CAT-MEMBER", "name": "\U0001F340\uff5cStock Information", "type": 4},  # POST category_stock_member
        {"id": "CAT-LARGE", "name": "\U0001F352\uff5cStock Information", "type": 4},   # POST category_stock_large
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
        DiscordAPIError("Missing Permissions", status_code=403),         # 8: POST stock member 失敗
        DiscordAPIError("Missing Permissions", status_code=403),         # 9: POST stock large 失敗
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
    assert steps["ch_member"]["status"] == "failed"
    assert steps["ch_partner"]["status"] == "failed"
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
        {"id": "CAT-MEMBER", "name": "\U0001F340\uff5cStock Information", "type": 4},  # POST category_stock_member
        {"id": "CAT-LARGE", "name": "\U0001F352\uff5cStock Information", "type": 4},   # POST category_stock_large
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
    existing_channels = _migrated_channels()

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
    existing_channels = _migrated_channels()
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
        {"id": "CAT-MEMBER", "name": "\U0001F340\uff5cStock Information", "type": 4},  # POST category_stock_member
        {"id": "CAT-LARGE", "name": "\U0001F352\uff5cStock Information", "type": 4},   # POST category_stock_large
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
    existing_channels = _migrated_channels()

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


# ---------------------------------------------------------------------------
# テスト: 顧客向け文言は bot_texts（英語）から供給される
# ---------------------------------------------------------------------------

async def test_auto_setup_posts_english_button_and_default_welcome() -> None:
    """ボタン投稿ペイロードと初回 INSERT の welcome_template が bot_texts の英語既定であること。"""
    from app.discord_gateway import bot_texts

    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=None)
    app = _build_app(mock_db)
    discord_responses = [
        [], [], {"id": "BOT-1"},
        {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},
        {"id": "ROLE-PARTNER", "name": "Partner"},
        {"id": "ROLE-MEMBER", "name": "Member"},
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},
        {"id": "CAT-MEMBER", "name": _CAT_MEMBER, "type": 4},
        {"id": "CAT-LARGE", "name": _CAT_LARGE, "type": 4},
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0},
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0},
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0},
        {"id": "MSG-1"},
    ]

    with ExitStack() as stack:
        mock_api = _common_patches(stack)
        mock_api.side_effect = discord_responses
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    assert resp.status_code == 200, resp.text
    button_payload = mock_api.call_args_list[12].kwargs["json"]
    assert button_payload == bot_texts.ticket_button_payload()
    assert button_payload["content"] == "Need help? Click the button below to open a private support ticket."
    assert button_payload["components"][0]["components"][0]["label"] == "Open a ticket"
    assert button_payload["components"][0]["components"][0]["custom_id"] == "ticket_open"

    upsert_params = mock_db.execute.await_args_list[2].args[1]
    assert upsert_params["welcome_template"] == bot_texts.DEFAULT_WELCOME_TEMPLATE


# ---------------------------------------------------------------------------
# テスト: カテゴリ3分割（📩｜DM / 🍀｜Stock Information / 🍒｜Stock Information）
# ---------------------------------------------------------------------------


class _FakeDiscord:
    """状態を持つ Discord REST フェイク（POST/PATCH を反映し、再実行を模擬する）。"""

    def __init__(self, channels: list[dict], roles: list[dict] | None = None) -> None:
        self.channels = channels
        self.roles = roles if roles is not None else [
            {"id": "ROLE-STAFF", "name": "Sales Anchor Staff"},
            {"id": "ROLE-PARTNER", "name": "Partner"},
            {"id": "ROLE-MEMBER", "name": "Member"},
        ]
        self.calls: list[tuple[str, str, dict | None]] = []
        self._seq = 0

    async def request(self, *, method, path, bot_token, json=None, expected_statuses=None):
        self.calls.append((method, path, json))
        if method == "GET" and path.endswith("/roles"):
            return list(self.roles)
        if method == "GET" and path.endswith("/channels"):
            return [dict(c) for c in self.channels]
        if method == "GET" and path == "/users/@me":
            return {"id": "BOT-1"}
        if method == "GET" and "/messages" in path:
            return []
        if method == "POST" and path.endswith("/messages"):
            return {"id": "MSG-1"}
        if method == "POST" and path.endswith("/channels"):
            self._seq += 1
            created = {"id": f"NEW-{self._seq}", "name": json["name"], "type": json["type"],
                       "parent_id": json.get("parent_id")}
            self.channels.append(created)
            return created
        if method == "PATCH" and path.startswith("/channels/"):
            target = next(c for c in self.channels if c["id"] == path.split("/")[-1])
            target.update({k: v for k, v in json.items() if k in ("name", "parent_id")})
            return dict(target)
        raise AssertionError(f"unexpected call {method} {path}")

    def methods(self, method: str) -> list[tuple[str, dict | None]]:
        return [(p, j) for m, p, j in self.calls if m == method]


async def _run_setup(fake: _FakeDiscord, existing_config: dict | None) -> dict:
    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config=existing_config)
    app = _build_app(mock_db)
    with ExitStack() as stack:
        mock_api = _common_patches(stack)
        mock_api.side_effect = fake.request
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_name(fake: _FakeDiscord, name: str) -> list[dict]:
    return [c for c in fake.channels if c["name"] == name]


@pytest.mark.asyncio
async def test_fresh_setup_creates_three_categories_with_channels_under_each() -> None:
    """新規セットアップで3カテゴリが作られ、チャンネルが指定カテゴリ配下に作成されること。"""
    fake = _FakeDiscord(channels=[])
    body = await _run_setup(fake, None)

    assert body["status"] == "completed"
    dm = _by_name(fake, _CAT_DM)[0]["id"]
    member = _by_name(fake, _CAT_MEMBER)[0]["id"]
    large = _by_name(fake, _CAT_LARGE)[0]["id"]
    assert _by_name(fake, "Sales Anchor") == []
    assert _by_name(fake, "ticket-start")[0]["parent_id"] == dm
    assert _by_name(fake, "member-announcements")[0]["parent_id"] == member
    assert _by_name(fake, "partner-announcements")[0]["parent_id"] == large
    assert fake.methods("PATCH") == []
    assert fake.methods("DELETE") == []
    steps = {s["step"]: s for s in body["steps"]}
    assert steps["category"]["discord_id"] == dm


@pytest.mark.asyncio
async def test_rerun_migrates_legacy_setup_rename_and_move_without_delete() -> None:
    """旧構成（Sales Anchor 配下に3チャンネル）を再実行で 名前変更＋アナウンス移動 に作り替えること。"""
    fake = _FakeDiscord(channels=[
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0, "parent_id": "CAT-1"},
    ])
    config = {
        "ticket_category_id": "CAT-1",
        "ticket_button_channel_id": "CH-TICKET",
        "staff_role_id": "ROLE-STAFF",
        "small_channel_id": "CH-MEMBER",
        "large_channel_id": "CH-PARTNER",
        "small_role_name": "Member",
        "large_role_name": "Partner",
    }
    body = await _run_setup(fake, config)

    assert body["status"] == "completed"
    by_id = {c["id"]: c for c in fake.channels}
    member = _by_name(fake, _CAT_MEMBER)[0]["id"]
    large = _by_name(fake, _CAT_LARGE)[0]["id"]
    # 既存カテゴリは同じ ID のまま改名（ticket_category_id 不変・ticket-start は DM 配下に残る）
    assert by_id["CAT-1"]["name"] == _CAT_DM
    assert by_id["CH-TICKET"]["parent_id"] == "CAT-1"
    # member(小口)=🍀 / partner(大口)=🍒
    assert by_id["CH-MEMBER"]["parent_id"] == member
    assert by_id["CH-PARTNER"]["parent_id"] == large
    # チャンネルは1つも失われない・DELETE なし・権限は同期しない
    assert {"CH-TICKET", "CH-MEMBER", "CH-PARTNER", "CAT-1"} <= set(by_id)
    assert fake.methods("DELETE") == []
    moves = [j for p, j in fake.methods("PATCH") if "parent_id" in j]
    assert len(moves) == 2
    assert all(j["lock_permissions"] is False for j in moves)
    steps = {s["step"]: s for s in body["steps"]}
    assert steps["category"]["status"] == "updated"
    assert steps["ch_member"] == {"step": "ch_member", "status": "updated", "discord_id": "CH-MEMBER", "error": None}
    assert steps["ch_partner"]["status"] == "updated"
    assert steps["ch_ticket"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_rerun_twice_is_idempotent_no_duplicates() -> None:
    """移行後にもう一度実行しても、カテゴリ・チャンネルの重複や追加の PATCH が発生しないこと。"""
    fake = _FakeDiscord(channels=[
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0, "parent_id": "CAT-1"},
    ])
    config = {
        "ticket_category_id": "CAT-1",
        "ticket_button_channel_id": "CH-TICKET",
        "staff_role_id": "ROLE-STAFF",
        "small_channel_id": "CH-MEMBER",
        "large_channel_id": "CH-PARTNER",
        "small_role_name": "Member",
        "large_role_name": "Partner",
    }
    await _run_setup(fake, config)
    count_after_first = len(fake.channels)
    calls_after_first = len(fake.calls)

    body = await _run_setup(fake, config)

    assert len(fake.channels) == count_after_first
    new_calls = fake.calls[calls_after_first:]
    assert [m for m, _, _ in new_calls if m in ("PATCH", "DELETE")] == []
    steps = {s["step"]: s for s in body["steps"]}
    for name in ("category", "category_stock_member", "category_stock_large", "ch_member", "ch_partner"):
        assert steps[name]["status"] == "skipped", name
    for name in (_CAT_DM, _CAT_MEMBER, _CAT_LARGE, "ticket-start"):
        assert len(_by_name(fake, name)) == 1


@pytest.mark.asyncio
async def test_rerun_without_stored_ids_finds_legacy_announcements_and_moves_them() -> None:
    """DB に small/large が未保存でも、旧カテゴリ配下の同名チャンネルを検出して重複作成せず移動すること。"""
    fake = _FakeDiscord(channels=[
        {"id": "CAT-1", "name": "Sales Anchor", "type": 4},
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0, "parent_id": "CAT-1"},
    ])
    body = await _run_setup(fake, None)

    assert body["status"] == "completed"
    assert len(_by_name(fake, "member-announcements")) == 1
    assert len(_by_name(fake, "partner-announcements")) == 1
    assert _by_name(fake, "member-announcements")[0]["parent_id"] == _by_name(fake, _CAT_MEMBER)[0]["id"]
    assert _by_name(fake, "partner-announcements")[0]["parent_id"] == _by_name(fake, _CAT_LARGE)[0]["id"]


@pytest.mark.asyncio
async def test_move_failure_is_reported_and_nothing_deleted() -> None:
    """移動が 403 で失敗しても status=partial で報告し、チャンネルは削除されないこと。"""
    from app.services.discord_rest import DiscordAPIError

    fake = _FakeDiscord(channels=[
        {"id": "CAT-1", "name": _CAT_DM, "type": 4},
        {"id": "CH-TICKET", "name": "ticket-start", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-MEMBER", "name": "member-announcements", "type": 0, "parent_id": "CAT-1"},
        {"id": "CH-PARTNER", "name": "partner-announcements", "type": 0, "parent_id": "CAT-1"},
    ])
    original_call = fake.request

    async def failing(**kwargs):
        if kwargs["method"] == "PATCH" and "parent_id" in (kwargs.get("json") or {}):
            raise DiscordAPIError("Missing Permissions", status_code=403)
        return await original_call(**kwargs)

    mock_db = _make_mock_db(guild_id="GUILD-1", existing_config={
        "ticket_category_id": "CAT-1", "ticket_button_channel_id": "CH-TICKET",
        "staff_role_id": "ROLE-STAFF", "small_channel_id": "CH-MEMBER",
        "large_channel_id": "CH-PARTNER", "small_role_name": "Member", "large_role_name": "Partner",
    })
    app = _build_app(mock_db)
    with ExitStack() as stack:
        mock_api = _common_patches(stack)
        mock_api.side_effect = failing
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/admin/discord/auto-setup")

    body = resp.json()
    assert body["status"] == "partial"
    steps = {s["step"]: s for s in body["steps"]}
    assert steps["ch_member"]["status"] == "failed"
    assert steps["ch_member"]["discord_id"] == "CH-MEMBER"
    assert steps["category"]["status"] == "skipped"  # 既に 📩｜DM のため改名なし
    assert {"CH-TICKET", "CH-MEMBER", "CH-PARTNER"} <= {c["id"] for c in fake.channels}
    assert fake.methods("DELETE") == []


def test_category_names_are_po_specified() -> None:
    """カテゴリ名が PO 指定の文字列（全角縦線 U+FF5C）であること。"""
    from app.discord_gateway import bot_texts

    assert bot_texts.CATEGORY_DM == "\U0001F4E9\uff5cDM"
    assert bot_texts.CATEGORY_STOCK_MEMBER == "\U0001F340\uff5cStock Information"
    assert bot_texts.CATEGORY_STOCK_LARGE == "\U0001F352\uff5cStock Information"
