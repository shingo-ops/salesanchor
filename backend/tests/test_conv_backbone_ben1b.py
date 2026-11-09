"""便1b: conversation_logs の背骨必須化 テスト。

検証項目:
  1. write_conversation_log(lead_id=None) は ValueError を返す
  2. echo の未知 PSID は、便1.5 以降は meta_messages に outbound で書く（リードは作る・conversation_logs には書かない）
  3. echo の既知 PSID は、便1.5 以降は meta_messages に outbound で書く（lead は増やさない・conversation_logs には書かない）
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from tests import test_message_send as ms


LEADS_DDL = """
    CREATE TABLE leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        lead_code VARCHAR(20),
        customer_name VARCHAR(255) NOT NULL,
        amount NUMERIC(15,2),
        currency VARCHAR(10) DEFAULT 'JPY',
        expected_close_date DATE,
        channel_type VARCHAR(30),
        initiative VARCHAR(10),
        type VARCHAR(50),
        status VARCHAR(50),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

LEAD_CHANNELS_DDL = """
    CREATE TABLE lead_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
        platform VARCHAR(30) NOT NULL,
        external_id VARCHAR(255) NOT NULL,
        display_name VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (platform, external_id)
    )
"""

TENANT_META_CONFIG_DDL = """
    CREATE TABLE tenant_meta_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        page_id VARCHAR(50) NOT NULL,
        page_name VARCHAR(200) NOT NULL,
        page_access_token_encrypted BLOB NOT NULL,
        instagram_business_account_id VARCHAR(50),
        is_active BOOLEAN NOT NULL DEFAULT 1
    )
"""

TENANTS_DDL = """
    CREATE TABLE tenants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT 1
    )
"""

META_MESSAGES_DDL = ms._META_MESSAGES_DDL

# 共通の meta_messages 定義（test_message_send）をそのまま使う
META_MESSAGES_UNIQUE = ms._META_MESSAGES_MSGID_INDEX_DDL

CONVERSATION_LOGS_DDL = """
    CREATE TABLE conversation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        lead_id INTEGER NOT NULL,
        contact_id INTEGER,
        company_id INTEGER,
        channel_type VARCHAR(30) NOT NULL,
        channel_identity VARCHAR(255),
        direction VARCHAR(10) NOT NULL,
        sender VARCHAR(255),
        content_text TEXT,
        external_message_id VARCHAR(255),
        raw_payload TEXT,
        occurred_at TIMESTAMP NOT NULL
    )
"""

CONVERSATION_LOGS_UNIQUE = """
    CREATE UNIQUE INDEX uq_conversation_logs_external_message_id
    ON conversation_logs (external_message_id)
    WHERE external_message_id IS NOT NULL
"""


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _setup(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    async with eng.begin() as conn:
        await conn.execute(text(LEADS_DDL))
        await conn.execute(text(LEAD_CHANNELS_DDL))
        await conn.execute(text(TENANT_META_CONFIG_DDL))
        await conn.execute(text(TENANTS_DDL))
        await conn.execute(text(META_MESSAGES_DDL))
        await conn.execute(text(META_MESSAGES_UNIQUE))
        await conn.execute(text(CONVERSATION_LOGS_DDL))
        await conn.execute(text(CONVERSATION_LOGS_UNIQUE))
        await conn.execute(
            text("INSERT INTO tenants (id, name, is_active) VALUES (999, 'Test Tenant', 1)")
        )

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def webhook_env(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("META_VERIFY_TOKEN", "test-verify-token")


async def _insert_tenant_meta_config(
    db_session,
    *,
    tenant_id: int = 999,
    page_id: str = "PAGE-1",
    ig_business_account_id: str | None = None,
):
    await db_session.execute(
        text("""
            INSERT INTO tenant_meta_config (
                tenant_id, page_id, page_name, page_access_token_encrypted,
                instagram_business_account_id, is_active
            )
            VALUES (
                :tenant_id, :page_id, :page_name, :token, :ig, 1
            )
        """),
        {
            "tenant_id": tenant_id,
            "page_id": page_id,
            "page_name": "Test Page",
            "token": b"encrypted-bytes",
            "ig": ig_business_account_id,
        },
    )
    await db_session.commit()


@asynccontextmanager
async def _session_scope(session):
    yield session


def _patch_webhook_runtime(monkeypatch, db_session):
    from app.routers import webhook as wh

    monkeypatch.setattr(wh, "AsyncSessionLocal", lambda: _session_scope(db_session))
    monkeypatch.setattr(wh, "set_tenant_context", AsyncMock())
    monkeypatch.setattr(wh, "reset_tenant_context", AsyncMock())
    monkeypatch.setattr(wh, "clear_tenant_context", AsyncMock())
    monkeypatch.setattr(wh, "send_discord_notification", AsyncMock())
    monkeypatch.setattr(wh, "enqueue_inbound_translation", MagicMock())
    monkeypatch.setattr(
        "app.services.conv_log_writer._get_company_id_for_lead",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.services.conv_log_writer._get_contact_id_for_lead",
        AsyncMock(return_value=None),
    )
    return wh


@pytest.mark.asyncio
async def test_writer_rejects_none_lead():
    from app.services.conv_log_writer import write_conversation_log

    db = AsyncMock()

    with (
        patch("app.services.conv_log_writer._get_company_id_for_lead", new=AsyncMock()) as company_mock,
        patch("app.services.conv_log_writer._get_contact_id_for_lead", new=AsyncMock()) as contact_mock,
        pytest.raises(ValueError, match="lead_id 必須"),
    ):
        await write_conversation_log(
            db,
            tenant_id=999,
            lead_id=None,
            channel_type="messenger",
            direction="inbound",
            occurred_at=datetime(2026, 7, 3, 0, 0, tzinfo=timezone.utc),
        )

    company_mock.assert_not_called()
    contact_mock.assert_not_called()


@pytest.mark.asyncio
async def test_echo_unknown_psid_creates_outbound_lead(db_session, webhook_env, monkeypatch):
    wh = _patch_webhook_runtime(monkeypatch, db_session)
    await _insert_tenant_meta_config(db_session, tenant_id=999, page_id="PAGE-A")

    body = {
        "object": "page",
        "entry": [{
            "id": "PAGE-A",
            "messaging": [{
                "sender": {"id": "PAGE-A"},
                "recipient": {"id": "PSID-00001234"},
                "timestamp": 1714400000,
                "message": {"mid": "mid-echo-unknown", "text": "Echo", "is_echo": True},
            }],
        }],
    }

    await wh.process_messenger_event(body)

    # 便1.5: echo は知らない相手のリード（outbound）を作り、meta_messages に outbound で書く
    res = await db_session.execute(
        text("SELECT channel_type, initiative FROM leads")
    )
    leads = res.fetchall()
    assert len(leads) == 1
    assert leads[0][0] == "messenger"
    assert leads[0][1] == "outbound"

    res = await db_session.execute(text("SELECT COUNT(*) FROM lead_channels"))
    assert res.scalar() == 1

    res = await db_session.execute(
        text("SELECT direction, recipient_id FROM meta_messages")
    )
    msgs = res.fetchall()
    assert len(msgs) == 1
    assert msgs[0][0] == "outbound"
    assert msgs[0][1] == "PSID-00001234"

    # conversation_logs には書かない
    res = await db_session.execute(text("SELECT COUNT(*) FROM conversation_logs"))
    assert res.scalar() == 0


@pytest.mark.asyncio
async def test_echo_known_psid_uses_existing_lead(db_session, webhook_env, monkeypatch):
    wh = _patch_webhook_runtime(monkeypatch, db_session)
    await _insert_tenant_meta_config(db_session, tenant_id=999, page_id="PAGE-A")

    await db_session.execute(text("""
        INSERT INTO leads (id, tenant_id, lead_code, customer_name, channel_type, initiative, type, status)
        VALUES (42, 999, 'LD-00042', 'Existing Lead', 'messenger', 'inbound', 'Inbound', 'lead')
    """))
    await db_session.execute(text("""
        INSERT INTO lead_channels (lead_id, platform, external_id)
        VALUES (42, 'messenger', 'PSID-EXISTING')
    """))
    await db_session.commit()

    body = {
        "object": "page",
        "entry": [{
            "id": "PAGE-A",
            "messaging": [{
                "sender": {"id": "PAGE-A"},
                "recipient": {"id": "PSID-EXISTING"},
                "timestamp": 1714400001,
                "message": {"mid": "mid-echo-known", "text": "Echo", "is_echo": True},
            }],
        }],
    }

    await wh.process_messenger_event(body)

    res = await db_session.execute(text("SELECT COUNT(*) FROM leads"))
    assert res.scalar() == 1

    # 便1.5: echo は既存リードの meta_messages に outbound で書く
    res = await db_session.execute(
        text("SELECT lead_id, direction FROM meta_messages WHERE message_id = 'mid-echo-known'")
    )
    msgs = res.fetchall()
    assert len(msgs) == 1
    assert msgs[0][0] == 42
    assert msgs[0][1] == "outbound"

    # conversation_logs には書かない
    res = await db_session.execute(text(
        "SELECT COUNT(*) FROM conversation_logs WHERE external_message_id = 'mid-echo-known'"
    ))
    assert res.scalar() == 0
