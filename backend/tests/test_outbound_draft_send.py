"""
段階A: draft_id 経由 outbound 送信の統合テスト（Meta / DB モック付き）

E-1 で要求される証明:
- K1 コード証明: draft_id 指定時、Meta send API に英語(final_text)が渡る
- K2 コード証明: meta_messages INSERT の message_text が英語(final_text)
- K3/K4 コード証明: is_edited が final_text vs draft_text の差異で正しく計算される
- 400 系: 未確認 / 別リード / 不存在 draft_id
- K6 コード証明: draft_id なし経路では text ペイロードがそのまま通る

実行:
    pytest backend/tests/test_outbound_draft_send.py -v
"""
from __future__ import annotations

import os
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.routers import leads as leads_router
from app.services import encryption

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_LEAD_DDL = """
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL DEFAULT 999,
        lead_code VARCHAR(20),
        customer_name VARCHAR(200),
        company_name VARCHAR(200),
        email VARCHAR(255),
        phone VARCHAR(50),
        channel_type VARCHAR(30),
        initiative VARCHAR(10),
        type VARCHAR(50),
        status VARCHAR(50),
        temperature VARCHAR(20),
        estimated_scale VARCHAR(20),
        customer_type VARCHAR(20),
        response_speed VARCHAR(20),
        monthly_forecast NUMERIC(15,2),
        prospect_rank VARCHAR(20),
        assigned_to INTEGER,
        converted_deal_id INTEGER,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        next_action VARCHAR(500),
        next_action_date DATE,
        challenge TEXT,
        meeting_memo TEXT,
        meeting_impression VARCHAR(50),
        cs_memo TEXT,
        sales_form VARCHAR(50),
        competitor_check BOOLEAN NOT NULL DEFAULT 0,
        per_order_amount NUMERIC(15, 2),
        monthly_frequency NUMERIC(10, 2),
        nickname VARCHAR(255),
        country VARCHAR(100),
        target_titles VARCHAR(500),
        messenger_link VARCHAR(1000),
        discord_id VARCHAR(255),
        instagram_link VARCHAR(1000),
        whatsapp_link VARCHAR(1000),
        discord_user_id VARCHAR(50),
        discord_dm_channel_id VARCHAR(50),
        discord_role_sync_status VARCHAR(20),
        discord_role_sync_at TIMESTAMP,
        discord_guild_channel_id VARCHAR(50)
    )
"""

_META_MESSAGES_DDL = """
    CREATE TABLE IF NOT EXISTS meta_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        lead_id INTEGER,
        platform VARCHAR(20) NOT NULL DEFAULT 'messenger',
        sender_id VARCHAR(100),
        sender_name VARCHAR(200),
        message_text TEXT,
        direction VARCHAR(10) NOT NULL DEFAULT 'inbound',
        raw_payload TEXT,
        message_id VARCHAR(100),
        recipient_id VARCHAR(100),
        messaging_type VARCHAR(20),
        message_tag VARCHAR(50),
        sent_by_staff_id INTEGER,
        error_code VARCHAR(50),
        error_message TEXT,
        seen_at TIMESTAMP,
        seen_by_staff_id INTEGER,
        page_id VARCHAR(50),
        attachment_url TEXT,
        attachment_type VARCHAR(20),
        original_language VARCHAR(10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_TENANT_META_CONFIG_DDL = """
    CREATE TABLE IF NOT EXISTS tenant_meta_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        page_id VARCHAR(50) NOT NULL,
        page_name VARCHAR(200) NOT NULL,
        page_access_token_encrypted BLOB NOT NULL,
        page_token_expires_at TIMESTAMP,
        instagram_business_account_id VARCHAR(50),
        instagram_username VARCHAR(100),
        subscribed_fields TEXT,
        connected_by_staff_id INTEGER,
        connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_token_refreshed_at TIMESTAMP,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        deactivated_at TIMESTAMP,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_STAFF_DDL = """
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL DEFAULT 999,
        primary_email VARCHAR(255) NOT NULL
    )
"""

_OUTBOUND_DRAFT_DDL = """
    CREATE TABLE IF NOT EXISTS outbound_translation_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        lead_id INTEGER,
        original_text TEXT,
        draft_text TEXT NOT NULL,
        confidence REAL,
        flagged_terms TEXT,
        model VARCHAR(100),
        confirmed_at TIMESTAMP,
        final_text TEXT,
        meta_message_id INTEGER,
        is_edited BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_AUDIT_LOGS_DDL = """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER,
        user_id INTEGER,
        action VARCHAR(100),
        record_id INTEGER,
        old_data TEXT,
        new_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_MESSAGE_TRANSLATIONS_DDL = """
    CREATE TABLE IF NOT EXISTS message_translations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        meta_message_id INTEGER,
        source_lang VARCHAR(10),
        target_lang VARCHAR(10),
        original_text TEXT,
        translated_text TEXT,
        model VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _setup(dbapi_conn, _):
        dbapi_conn.create_function(
            "NOW", 0,
            lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
        )
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    @event.listens_for(eng.sync_engine, "before_cursor_execute", retval=True)
    def _ilike(conn, cursor, stmt, params, ctx, many):
        if "ILIKE" in stmt:
            stmt = stmt.replace(" ILIKE ", " LIKE ").replace("\nILIKE ", "\nLIKE ")
        if " FOR UPDATE" in stmt:
            stmt = stmt.replace(" FOR UPDATE", "")
        return stmt, params

    async with eng.begin() as conn:
        for ddl in (
            _LEAD_DDL, _META_MESSAGES_DDL, _TENANT_META_CONFIG_DDL,
            _STAFF_DDL, _OUTBOUND_DRAFT_DDL, _AUDIT_LOGS_DDL,
            _MESSAGE_TRANSLATIONS_DDL,
        ):
            await conn.execute(text(ddl))

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def fernet_env(monkeypatch):
    encryption.reset_cache()
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("METADATA_FERNET_KEY", key)
    yield
    encryption.reset_cache()


def _mock_user(email: str = "tester@example.com"):
    u = MagicMock()
    u.id = 1
    u.tenant_id = 999
    u.email = email
    return u


def _build_app(db_session, tenant_id: int = 999):
    app = FastAPI()

    async def _db():
        yield db_session

    async def _user():
        return _mock_user()

    async def _tenant():
        return tenant_id

    app.include_router(leads_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_current_tenant] = _tenant
    return app


@pytest_asyncio.fixture
async def app_client(db_session, fernet_env):
    app = _build_app(db_session)
    transport = ASGITransport(app=app)
    with ExitStack() as stack:
        stack.enter_context(patch(
            "app.auth.dependencies.load_user_permissions",
            new=AsyncMock(return_value={
                "channels.view", "channels.manage",
                "messaging.view", "messaging.send",
            }),
        ))
        stack.enter_context(patch(
            "app.routers.leads.invalidate_dashboard_cache",
            new=AsyncMock(return_value=None),
        ))
        stack.enter_context(patch(
            "app.routers.leads.record_audit_log",
            new=AsyncMock(return_value=None),
        ))
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


async def _insert_lead(db, *, lead_id: int, tenant_id: int = 999,
                       channel_type: str = "messenger"):
    await db.execute(text("""
        INSERT INTO leads (id, tenant_id, lead_code, customer_name, channel_type, status)
        VALUES (:id, :tid, :code, 'Alice', :ch, 'lead')
    """), {"id": lead_id, "tid": tenant_id, "code": f"LD-{lead_id:05d}", "ch": channel_type})
    await db.commit()


async def _insert_inbound(db, *, lead_id: int, tenant_id: int = 999,
                          minutes_ago: int = 60, platform: str = "messenger",
                          sender_id: str = "PSID-1"):
    when = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    await db.execute(text("""
        INSERT INTO meta_messages
            (tenant_id, lead_id, platform, sender_id, message_text, direction, created_at)
        VALUES (:tid, :lid, :pl, :sid, 'Hi', 'inbound', :w)
    """), {
        "tid": tenant_id, "lid": lead_id, "pl": platform,
        "sid": sender_id, "w": when.strftime("%Y-%m-%d %H:%M:%S+00:00"),
    })
    await db.commit()


async def _insert_meta_config(db, *, tenant_id: int = 999, page_id: str = "page-1"):
    encrypted = encryption.encrypt("page-token-plain")
    await db.execute(text("""
        INSERT INTO tenant_meta_config
            (tenant_id, page_id, page_name, page_access_token_encrypted, is_active, connected_at)
        VALUES (:tid, :pid, 'Page', :tok, 1, :now)
    """), {
        "tid": tenant_id, "pid": page_id,
        "tok": encrypted.encode("ascii"),
        "now": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00"),
    })
    await db.commit()


async def _insert_draft(
    db, *, draft_id: int, tenant_id: int = 999, lead_id: int = 1,
    draft_text: str = "Hello (AI draft)",
    final_text: str | None = None,
    confirmed: bool = True,
) -> int:
    confirmed_at = (
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
        if confirmed else None
    )
    await db.execute(text("""
        INSERT INTO outbound_translation_drafts
            (id, tenant_id, lead_id, original_text, draft_text, final_text,
             confidence, model, confirmed_at)
        VALUES (:id, :tid, :lid, 'こんにちは', :dt, :ft, 0.99, 'gemini-pro', :ca)
    """), {
        "id": draft_id, "tid": tenant_id, "lid": lead_id,
        "dt": draft_text, "ft": final_text, "ca": confirmed_at,
    })
    await db.commit()
    return draft_id


async def _get_outbound_message(db, *, lead_id: int, tenant_id: int = 999):
    res = await db.execute(text("""
        SELECT message_text FROM meta_messages
        WHERE lead_id=:lid AND tenant_id=:tid AND direction='outbound'
        ORDER BY id DESC LIMIT 1
    """), {"lid": lead_id, "tid": tenant_id})
    row = res.first()
    return row[0] if row else None


async def _get_draft(db, *, draft_id: int, tenant_id: int = 999):
    res = await db.execute(text("""
        SELECT meta_message_id, is_edited FROM outbound_translation_drafts
        WHERE id=:did AND tenant_id=:tid
    """), {"did": draft_id, "tid": tenant_id})
    return res.first()


# ---------------------------------------------------------------------------
# E-1 K1コード証明: Meta send API に final_text(英語) が渡る
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_id_sends_final_text_to_meta(app_client, db_session):
    """
    K1コード証明:
    confirmed な draft_id を指定すると、send_messenger_message に
    text=final_text（英語）が渡ることをアサート。
    """
    await _insert_lead(db_session, lead_id=1)
    await _insert_inbound(db_session, lead_id=1, minutes_ago=60)
    await _insert_meta_config(db_session)
    await _insert_draft(
        db_session, draft_id=10, lead_id=1,
        draft_text="Hello (AI draft)",
        final_text="Hello, nice to meet you! (edited)",
        confirmed=True,
    )

    captured = {}

    async def fake_send(**kwargs):
        captured.update(kwargs)
        return {"recipient_id": kwargs["recipient_id"], "message_id": "mid-k1"}

    with patch("app.routers.leads.meta_graph.send_messenger_message",
               new=AsyncMock(side_effect=fake_send)):
        resp = await app_client.post(
            "/api/v1/leads/1/messages",
            json={"text": "こんにちは", "draft_id": 10},
        )

    assert resp.status_code == 201
    # ★K1コード証明: Metaに渡るtextはfinal_text（英語）
    assert captured["text"] == "Hello, nice to meet you! (edited)", \
        f"Meta に渡った text が英語でない: {captured.get('text')!r}"


# ---------------------------------------------------------------------------
# E-1 K2コード証明: meta_messages INSERT の message_text が英語
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_id_inserts_english_to_meta_messages(app_client, db_session):
    """
    K2コード証明:
    confirmed な draft_id 指定時、meta_messages に INSERT される
    message_text が final_text（英語）であること。
    """
    await _insert_lead(db_session, lead_id=2)
    await _insert_inbound(db_session, lead_id=2, minutes_ago=60)
    await _insert_meta_config(db_session)
    await _insert_draft(
        db_session, draft_id=20, lead_id=2,
        draft_text="Good morning.",
        final_text="Good morning, how can I help you?",
        confirmed=True,
    )

    async def fake_send(**kwargs):
        return {"recipient_id": kwargs["recipient_id"], "message_id": "mid-k2"}

    with patch("app.routers.leads.meta_graph.send_messenger_message",
               new=AsyncMock(side_effect=fake_send)):
        resp = await app_client.post(
            "/api/v1/leads/2/messages",
            json={"text": "おはようございます", "draft_id": 20},
        )

    assert resp.status_code == 201
    stored_text = await _get_outbound_message(db_session, lead_id=2)
    # ★K2コード証明: meta_messagesに保存されるのはfinal_text（英語）
    assert stored_text == "Good morning, how can I help you?", \
        f"meta_messages に保存されたテキストが英語でない: {stored_text!r}"


# ---------------------------------------------------------------------------
# E-1 K4コード証明: is_edited=false（無編集）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_id_is_edited_false_when_unmodified(app_client, db_session):
    """
    K4コード証明:
    final_text == draft_text（無編集）の場合 is_edited=false が記録される。
    """
    await _insert_lead(db_session, lead_id=3)
    await _insert_inbound(db_session, lead_id=3, minutes_ago=60)
    await _insert_meta_config(db_session)
    await _insert_draft(
        db_session, draft_id=30, lead_id=3,
        draft_text="Thank you.",
        final_text="Thank you.",  # 同じ = 無編集
        confirmed=True,
    )

    async def fake_send(**kwargs):
        return {"recipient_id": kwargs["recipient_id"], "message_id": "mid-k4a"}

    with patch("app.routers.leads.meta_graph.send_messenger_message",
               new=AsyncMock(side_effect=fake_send)):
        resp = await app_client.post(
            "/api/v1/leads/3/messages",
            json={"text": "ありがとう", "draft_id": 30},
        )

    assert resp.status_code == 201
    row = await _get_draft(db_session, draft_id=30)
    assert row is not None
    assert row[1] == 0 or row[1] is False or row[1] == False, \
        f"is_edited が True になっている（無編集のはず）: {row[1]!r}"  # noqa: E712
    assert row[0] is not None, "meta_message_id が NULL のまま（UPDATE されていない）"


# ---------------------------------------------------------------------------
# E-1 K3コード証明: is_edited=true（手編集あり）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_id_is_edited_true_when_modified(app_client, db_session):
    """
    K3コード証明:
    final_text != draft_text（手編集あり）の場合 is_edited=true が記録される。
    """
    await _insert_lead(db_session, lead_id=4)
    await _insert_inbound(db_session, lead_id=4, minutes_ago=60)
    await _insert_meta_config(db_session)
    await _insert_draft(
        db_session, draft_id=40, lead_id=4,
        draft_text="Hello.",
        final_text="Hello! Great to hear from you.",  # 手編集あり
        confirmed=True,
    )

    async def fake_send(**kwargs):
        return {"recipient_id": kwargs["recipient_id"], "message_id": "mid-k3"}

    with patch("app.routers.leads.meta_graph.send_messenger_message",
               new=AsyncMock(side_effect=fake_send)):
        resp = await app_client.post(
            "/api/v1/leads/4/messages",
            json={"text": "こんにちは", "draft_id": 40},
        )

    assert resp.status_code == 201
    row = await _get_draft(db_session, draft_id=40)
    assert row is not None
    assert row[1] == 1 or row[1] is True or row[1] == True, \
        f"is_edited が False のまま（手編集があるはず）: {row[1]!r}"  # noqa: E712
    assert row[0] is not None, "meta_message_id が NULL のまま"


# ---------------------------------------------------------------------------
# E-1 400系: 未確認 draft_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_id_unconfirmed_returns_400(app_client, db_session):
    """confirmed_at=NULL の draft_id → 400。Meta は呼ばない。"""
    await _insert_lead(db_session, lead_id=5)
    await _insert_inbound(db_session, lead_id=5, minutes_ago=60)
    await _insert_meta_config(db_session)
    await _insert_draft(
        db_session, draft_id=50, lead_id=5,
        draft_text="Hello.",
        final_text=None,
        confirmed=False,  # ← 未確認
    )

    with patch("app.routers.leads.meta_graph.send_messenger_message",
               new=AsyncMock()) as mocked:
        resp = await app_client.post(
            "/api/v1/leads/5/messages",
            json={"text": "こんにちは", "draft_id": 50},
        )

    assert resp.status_code == 400
    assert mocked.await_count == 0


# ---------------------------------------------------------------------------
# E-1 400系: 別リード draft_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_id_wrong_lead_returns_400(app_client, db_session):
    """lead_id が異なる draft_id → 400。Meta は呼ばない。"""
    await _insert_lead(db_session, lead_id=6)
    await _insert_inbound(db_session, lead_id=6, minutes_ago=60)
    await _insert_meta_config(db_session)
    # lead_id=999（別リード）で draft を作成
    await _insert_draft(
        db_session, draft_id=60, lead_id=999,
        draft_text="Hello.", final_text="Hello!", confirmed=True,
    )

    with patch("app.routers.leads.meta_graph.send_messenger_message",
               new=AsyncMock()) as mocked:
        resp = await app_client.post(
            "/api/v1/leads/6/messages",  # lead_id=6 でリクエスト
            json={"text": "こんにちは", "draft_id": 60},
        )

    assert resp.status_code == 400
    assert mocked.await_count == 0


# ---------------------------------------------------------------------------
# E-1 400系: 不存在 draft_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_id_not_found_returns_400(app_client, db_session):
    """存在しない draft_id → 400。Meta は呼ばない。"""
    await _insert_lead(db_session, lead_id=7)
    await _insert_inbound(db_session, lead_id=7, minutes_ago=60)
    await _insert_meta_config(db_session)

    with patch("app.routers.leads.meta_graph.send_messenger_message",
               new=AsyncMock()) as mocked:
        resp = await app_client.post(
            "/api/v1/leads/7/messages",
            json={"text": "こんにちは", "draft_id": 9999},
        )

    assert resp.status_code == 400
    assert mocked.await_count == 0


# ---------------------------------------------------------------------------
# E-1 K6コード証明: draft_id なし → 従来パス（text ペイロードがそのまま通る）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_draft_id_sends_payload_text_unchanged(app_client, db_session):
    """
    K6コード証明:
    draft_id なし通常送信では、ペイロードの text がそのまま
    send_messenger_message に渡る（翻訳差し替えは起きない）。
    """
    await _insert_lead(db_session, lead_id=8)
    await _insert_inbound(db_session, lead_id=8, minutes_ago=60)
    await _insert_meta_config(db_session)

    captured = {}

    async def fake_send(**kwargs):
        captured.update(kwargs)
        return {"recipient_id": kwargs["recipient_id"], "message_id": "mid-k6"}

    with patch("app.routers.leads.meta_graph.send_messenger_message",
               new=AsyncMock(side_effect=fake_send)):
        resp = await app_client.post(
            "/api/v1/leads/8/messages",
            json={"text": "通常送信テスト"},  # draft_id なし
        )

    assert resp.status_code == 201
    # ★K6コード証明: 翻訳差し替えなし＝ペイロードのtextがそのまま渡る
    assert captured["text"] == "通常送信テスト", \
        f"通常送信なのに text が変わっている: {captured.get('text')!r}"
