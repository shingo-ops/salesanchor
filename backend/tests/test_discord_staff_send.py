"""
Discord 返信の担当者名義送信（leads.py のテキスト・画像経路・ADR-159 便B）。

カバー:
- 送信前に staff を解決し、webhook に username=英語名の「名」・avatar_url を渡す
- アイコン未登録なら avatar_url=None
- 英語名未登録 / staff 不在 → 422 STAFF_EN_NAME_REQUIRED（送らない）
- 英語名が不正 → 422 STAFF_EN_NAME_INVALID（送らない）
- webhook 権限不足 → 409 DISCORD_WEBHOOK_PERMISSION
- 送信失敗 → 502 DISCORD_SEND_FAILED・meta_messages に行を作らない
- Bot 名義の送信関数（send_discord_dm / discord_api_request_with_file）を一切呼ばない
- 成功時 meta_messages に message_id・sent_by_staff_id を記録
"""
from __future__ import annotations

import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.routers import leads as leads_router
from app.services import discord_webhook_sender as sender
from tests.test_message_image_send import _LEAD_DDL, _META_MESSAGES_DDL

_ALL_PERMS = {"channels.view", "channels.manage", "messaging.view", "messaging.send"}
_STAFF_DDL = """
    CREATE TABLE staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        primary_email VARCHAR(255),
        given_name_en VARCHAR(100),
        avatar_token TEXT
    )
"""
_TOKEN43 = "A" * 43
_CHANNEL = "900100200"


@pytest_asyncio.fixture
async def db_session():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def set_pragma(dbapi_conn, _):
        dbapi_conn.create_function("NOW", 0, lambda: "2026-06-01 00:00:00+00:00")

    async with eng.begin() as conn:
        for ddl in (_LEAD_DDL, _META_MESSAGES_DDL, _STAFF_DDL):
            await conn.execute(text(ddl))
    Session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()
    await eng.dispose()


@pytest_asyncio.fixture
async def ctx(db_session, monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-token-test")
    monkeypatch.setenv("API_BASE_URL", "https://api.example")
    app = FastAPI()
    user = MagicMock(id=1, tenant_id=999, email="tester@example.com")

    async def override_db():
        yield db_session

    app.include_router(leads_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_tenant] = lambda: 999
    bot_text = AsyncMock(return_value="BOT")
    bot_file = AsyncMock(return_value={"id": "BOT"})
    with ExitStack() as stack:
        stack.enter_context(patch("app.auth.dependencies.load_user_permissions", new=AsyncMock(return_value=_ALL_PERMS)))
        stack.enter_context(patch("app.routers.leads.invalidate_dashboard_cache", new=AsyncMock(return_value=None)))
        stack.enter_context(patch("app.routers.leads.record_audit_log", new=AsyncMock(return_value=None)))
        stack.enter_context(patch("app.services.discord_sender.send_discord_dm", new=bot_text))
        stack.enter_context(patch("app.services.discord_rest.discord_api_request_with_file", new=bot_file))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac, db_session, bot_text, bot_file
    app.dependency_overrides.clear()


async def _seed_lead(db, *, channel: str | None = _CHANNEL):
    await db.execute(
        text(
            "INSERT INTO leads (id, tenant_id, channel_type, customer_name, discord_user_id, discord_guild_channel_id) "
            "VALUES (1, 999, 'discord', 'Cust', 'du1', :ch)"
        ),
        {"ch": channel},
    )
    await db.execute(
        text(
            "INSERT INTO meta_messages (tenant_id, lead_id, platform, sender_id, message_text, direction) "
            "VALUES (999, 1, 'discord', 'du1', 'hi', 'inbound')"
        )
    )
    await db.commit()


async def _seed_staff(db, given_name_en, avatar_token=None):
    await db.execute(
        text(
            "INSERT INTO staff (id, tenant_id, primary_email, given_name_en, avatar_token) "
            "VALUES (5, 999, 'tester@example.com', :n, :a)"
        ),
        {"n": given_name_en, "a": avatar_token},
    )
    await db.commit()


async def _outbound_count(db) -> int:
    return (await db.execute(text("SELECT COUNT(*) FROM meta_messages WHERE direction='outbound'"))).scalar()


def _post_text(ac, body="hello"):
    return ac.post("/api/v1/leads/1/messages", json={"text": body})


def _post_image(ac):
    return ac.post(
        "/api/v1/leads/1/messages/image",
        files={"image": ("a.png", b"\x89PNG" + b"\x00" * 50, "image/png")},
    )


def _assert_code(resp, status, code):
    assert resp.status_code == status, resp.text
    detail = resp.json()["detail"]
    assert detail["reason"] == code and detail["code"] == code
    assert detail["message"]


# ---------------------------------------------------------------------------
# テキスト
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_text_sends_as_staff_with_avatar(ctx):
    ac, db, bot_text, bot_file = ctx
    await _seed_lead(db)
    await _seed_staff(db, "  Shingo ", _TOKEN43)
    with patch.object(sender, "send_as_staff", new=AsyncMock(return_value="dc-100")) as send:
        resp = await _post_text(ac)
    assert resp.status_code == 201, resp.text
    assert resp.json()["message_id"] == "dc-100"
    kwargs = send.await_args.kwargs
    assert kwargs["username"] == "Shingo"
    assert kwargs["avatar_url"] == f"https://api.example/api/public/staff-avatars/{_TOKEN43}.webp"
    assert kwargs["channel_id"] == _CHANNEL and kwargs["content"] == "hello" and kwargs["file"] is None
    row = (await db.execute(text(
        "SELECT message_id, sent_by_staff_id, direction FROM meta_messages WHERE direction='outbound'"
    ))).first()
    assert tuple(row) == ("dc-100", 5, "outbound")
    bot_text.assert_not_awaited()
    bot_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_text_without_avatar_passes_none(ctx):
    ac, db, *_ = ctx
    await _seed_lead(db)
    await _seed_staff(db, "Shingo", None)
    with patch.object(sender, "send_as_staff", new=AsyncMock(return_value="dc-1")) as send:
        resp = await _post_text(ac)
    assert resp.status_code == 201, resp.text
    assert send.await_args.kwargs["avatar_url"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("given", [None, "", "   "])
async def test_text_en_name_missing_is_422_and_not_sent(ctx, given):
    ac, db, bot_text, _ = ctx
    await _seed_lead(db)
    await _seed_staff(db, given)
    with patch.object(sender, "send_as_staff", new=AsyncMock()) as send:
        resp = await _post_text(ac)
    _assert_code(resp, 422, "STAFF_EN_NAME_REQUIRED")
    send.assert_not_awaited()
    bot_text.assert_not_awaited()
    assert await _outbound_count(db) == 0


@pytest.mark.asyncio
async def test_text_staff_row_missing_is_en_name_required(ctx):
    ac, db, *_ = ctx
    await _seed_lead(db)
    with patch.object(sender, "send_as_staff", new=AsyncMock()) as send:
        resp = await _post_text(ac)
    _assert_code(resp, 422, "STAFF_EN_NAME_REQUIRED")
    send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("given", ["Discord", "x" * 81])
async def test_text_en_name_invalid_is_422_and_not_sent(ctx, given):
    ac, db, bot_text, _ = ctx
    await _seed_lead(db)
    await _seed_staff(db, given)
    with patch.object(sender, "send_as_staff", new=AsyncMock()) as send:
        resp = await _post_text(ac)
    _assert_code(resp, 422, "STAFF_EN_NAME_INVALID")
    send.assert_not_awaited()
    bot_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_text_webhook_permission_is_409(ctx):
    ac, db, bot_text, _ = ctx
    await _seed_lead(db)
    await _seed_staff(db, "Shingo")
    with patch.object(sender, "send_as_staff", new=AsyncMock(side_effect=sender.WebhookPermissionError("c"))):
        resp = await _post_text(ac)
    _assert_code(resp, 409, "DISCORD_WEBHOOK_PERMISSION")
    bot_text.assert_not_awaited()
    assert await _outbound_count(db) == 0


@pytest.mark.asyncio
async def test_text_send_failure_is_502_no_bot_fallback_no_row(ctx):
    ac, db, bot_text, bot_file = ctx
    await _seed_lead(db)
    await _seed_staff(db, "Shingo")
    with patch.object(sender, "send_as_staff", new=AsyncMock(side_effect=sender.WebhookSendError("x"))):
        resp = await _post_text(ac)
    _assert_code(resp, 502, "DISCORD_SEND_FAILED")
    bot_text.assert_not_awaited()
    bot_file.assert_not_awaited()
    assert await _outbound_count(db) == 0


@pytest.mark.asyncio
async def test_text_channel_missing_stays_409(ctx):
    ac, db, *_ = ctx
    await _seed_lead(db, channel=None)
    await _seed_staff(db, "Shingo")
    resp = await _post_text(ac)
    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# 画像
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_image_sends_as_staff_via_webhook(ctx):
    ac, db, bot_text, bot_file = ctx
    await _seed_lead(db)
    await _seed_staff(db, "Shingo", _TOKEN43)
    with patch.object(sender, "send_as_staff", new=AsyncMock(return_value="dc-img")) as send:
        resp = await _post_image(ac)
    assert resp.status_code == 201, resp.text
    assert resp.json()["message_id"] == "dc-img"
    kwargs = send.await_args.kwargs
    assert kwargs["username"] == "Shingo" and kwargs["avatar_url"].endswith(f"{_TOKEN43}.webp")
    assert kwargs["content"] is None
    assert kwargs["file"].filename == "a.png" and kwargs["file"].content_type == "image/png"
    row = (await db.execute(text(
        "SELECT message_id, sent_by_staff_id, attachment_type FROM meta_messages WHERE direction='outbound'"
    ))).first()
    assert tuple(row) == ("dc-img", 5, "image")
    bot_file.assert_not_awaited()
    bot_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_image_en_name_missing_is_422_and_not_sent(ctx):
    ac, db, _, bot_file = ctx
    await _seed_lead(db)
    await _seed_staff(db, None)
    with patch.object(sender, "send_as_staff", new=AsyncMock()) as send:
        resp = await _post_image(ac)
    _assert_code(resp, 422, "STAFF_EN_NAME_REQUIRED")
    send.assert_not_awaited()
    bot_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_image_send_failure_is_502_no_bot_fallback(ctx):
    ac, db, _, bot_file = ctx
    await _seed_lead(db)
    await _seed_staff(db, "Shingo")
    with patch.object(sender, "send_as_staff", new=AsyncMock(side_effect=sender.WebhookSendError("x"))):
        resp = await _post_image(ac)
    _assert_code(resp, 502, "DISCORD_SEND_FAILED")
    bot_file.assert_not_awaited()
    assert await _outbound_count(db) == 0


@pytest.mark.asyncio
async def test_image_webhook_permission_is_409(ctx):
    ac, db, *_ = ctx
    await _seed_lead(db)
    await _seed_staff(db, "Shingo")
    with patch.object(sender, "send_as_staff", new=AsyncMock(side_effect=sender.WebhookPermissionError("c"))):
        resp = await _post_image(ac)
    _assert_code(resp, 409, "DISCORD_WEBHOOK_PERMISSION")
