"""会話の一本化 便1: 会話を書く所と読む所を meta_messages だけにする 試験（SQLite）。

検証項目（手の記録を書き足す API は便Mで外した。ここに残るのは読む所・書く所の確かめ）:
  7. 手の記録の行（直接入れたもの。電話・inbound・original_language 'en'）が言語判定に数えられない
  8. 手の記録の行（直接入れたもの）が本文のラベル付け（priority_scoring）に入らない
  9. webhook の受信1件・echo 1件・Discord の DM 1件で、conversation_logs に0行。echo でリードが作られない
  10. migration の文字の確かめ

SQLite にはスキーマ修飾（tenant_999.）が無いので、試験の間だけ文を書き換える窓口を足す。
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from tests.conftest import (
    CONV_UNIFY_CONVERSATION_LOGS_DDL,
    CONV_UNIFY_MESSAGE_LABELS_DDL,
    CONV_UNIFY_MESSAGE_TRANSLATIONS_DDL,
    INBOX_BADGE_META_MESSAGES_DDL,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _REPO_ROOT / "migrations" / "20261108_100000_rebuild_company_stats_on_meta_messages.sql"

# meta_messages の試験で使う列（INBOX_BADGE の定義に無いもの）
_EXTRA_META_COLUMNS = (
    "contact_id INTEGER",
    "company_id INTEGER",
    "occurred_at TIMESTAMP",
    "recorded_by_user_id INTEGER",
    "original_language VARCHAR(10)",
)

@pytest_asyncio.fixture
async def env(db_session):
    """meta_messages の試験の準備（SQLite）。"""
    engine = db_session.bind

    def _strip_schema(conn, cursor, statement, parameters, context, executemany):
        if "tenant_999." in statement:
            statement = statement.replace("tenant_999.", "")
        return statement, parameters

    event.listen(engine.sync_engine, "before_cursor_execute", _strip_schema, retval=True)

    await db_session.execute(text("DROP TABLE IF EXISTS meta_messages"))
    await db_session.execute(text(INBOX_BADGE_META_MESSAGES_DDL))
    for col in _EXTRA_META_COLUMNS:
        await db_session.execute(text(f"ALTER TABLE meta_messages ADD COLUMN {col}"))
    for ddl in (
        CONV_UNIFY_MESSAGE_TRANSLATIONS_DDL,
        CONV_UNIFY_MESSAGE_LABELS_DDL,
        CONV_UNIFY_CONVERSATION_LOGS_DDL,
    ):
        await db_session.execute(text(ddl))
    await db_session.commit()

    with (
        patch("app.cache.get_avatar_urls_batch", new=AsyncMock(return_value={})),
    ):
        yield db_session

    event.remove(engine.sync_engine, "before_cursor_execute", _strip_schema)


async def _make_lead(client, name: str = "Unify Lead") -> int:
    res = await client.post("/api/v1/leads", json={"customer_name": name, "status": "lead"})
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


async def _add_auto(db, lead_id: int, *, created_at: str, direction: str = "inbound",
                    platform: str = "messenger", message_text: str = "auto", language: str | None = None,
                    message_id: str | None = None) -> int:
    res = await db.execute(
        text(
            "INSERT INTO meta_messages (tenant_id, lead_id, platform, sender_id, message_id, message_text, "
            "direction, created_at, original_language) "
            "VALUES (999, :l, :p, 'PSID-1', :mid, :t, :d, :c, :lang) RETURNING id"
        ),
        {
            "l": lead_id, "p": platform, "mid": message_id or f"auto-{created_at}-{direction}",
            "t": message_text, "d": direction, "c": created_at, "lang": language,
        },
    )
    new_id = res.scalar_one()
    await db.commit()
    return new_id


async def _rows(db, sql: str, **params):
    return (await db.execute(text(sql), params)).mappings().all()


# ---------------------------------------------------------------------------
# 7. 電話の手の記録は言語判定に数えられない
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_phone_manual_record_is_not_counted_for_language(client, env):
    from app.services.lang_judge import judge_recipient_language

    lead_id = await _make_lead(client)
    for i in range(3):
        await env.execute(
            text(
                "INSERT INTO meta_messages (tenant_id, lead_id, platform, sender_id, message_id, message_text, "
                "direction, original_language, is_manual, occurred_at) "
                "VALUES (999, :l, 'phone', 'manual:user_1', :mid, 'x', 'inbound', 'en', 1, '2026-06-01 10:00:00')"
            ),
            {"l": lead_id, "mid": f"manual_{i}"},
        )
    await _add_auto(env, lead_id, created_at="2026-06-01 09:00:00", language="ja", message_id="auto-ja")
    await env.commit()

    result = await judge_recipient_language(env, 999, lead_id)
    assert result.total_records == 1
    assert result.confident is False
    assert result.language is None


# ---------------------------------------------------------------------------
# 8. 本文のラベル付けに手の記録が入らない
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_priority_scoring_label_skips_manual_record(client, env):
    from app.services.priority_scoring import label_lead_messages

    lead_id = await _make_lead(client)
    auto_id = await _add_auto(env, lead_id, created_at="2026-06-01 09:00:00", message_text="価格はいくらですか")
    await env.execute(
        text(
            "INSERT INTO meta_messages (tenant_id, lead_id, platform, sender_id, message_id, message_text, "
            "direction, original_language, is_manual, occurred_at, created_at) "
            "VALUES (999, :l, 'phone', 'manual:user_1', 'manual_label_1', '電話で価格を確認', 'inbound', 'en', 1, "
            "'2026-06-02 10:00:00', '2026-06-02 10:00:00')"
        ),
        {"l": lead_id},
    )
    await env.commit()

    with patch("app.auth.dependencies.reset_tenant_context", new=AsyncMock()):
        saved = await label_lead_messages(env, lead_id, 999)
    assert saved == 1
    labels = await _rows(env, "SELECT message_id FROM message_labels WHERE lead_id = :l", l=lead_id)
    assert [r["message_id"] for r in labels] == [auto_id]


# ---------------------------------------------------------------------------
# 9. webhook の受信・echo と Discord の DM は conversation_logs に書かない
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def webhook_db():
    from tests import test_conv_backbone_ben1b as ben

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        for ddl in (ben.LEADS_DDL, ben.LEAD_CHANNELS_DDL, ben.TENANT_META_CONFIG_DDL, ben.TENANTS_DDL,
                    ben.META_MESSAGES_DDL, ben.META_MESSAGES_UNIQUE,
                    ben.CONVERSATION_LOGS_DDL, ben.CONVERSATION_LOGS_UNIQUE):
            await conn.execute(text(ddl))
        await conn.execute(text("INSERT INTO tenants (id, name, is_active) VALUES (999, 'Test Tenant', 1)"))
    Session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()
    await eng.dispose()


@pytest.mark.asyncio
async def test_webhook_echo_and_inbound_write_no_conversation_logs(webhook_db, monkeypatch):
    from tests import test_conv_backbone_ben1b as ben

    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("META_VERIFY_TOKEN", "test-verify-token")
    wh = ben._patch_webhook_runtime(monkeypatch, webhook_db)
    await ben._insert_tenant_meta_config(webhook_db, tenant_id=999, page_id="PAGE-A")

    writer = AsyncMock()
    monkeypatch.setattr("app.services.conv_log_writer.write_conversation_log", writer)
    persist = AsyncMock(return_value=(11, 5))
    monkeypatch.setattr(wh, "_persist_meta_message", persist)

    echo = {
        "object": "page",
        "entry": [{"id": "PAGE-A", "messaging": [{
            "sender": {"id": "PAGE-A"}, "recipient": {"id": "PSID-NEW"}, "timestamp": 1714400000,
            "message": {"mid": "mid-echo-1", "text": "Echo", "is_echo": True},
        }]}],
    }
    await wh.process_messenger_event(echo)
    # 便1.5: echo は受信の書き込み（_persist_meta_message）を呼ばず、知らない相手のリードを作る
    persist.assert_not_awaited()
    assert (await webhook_db.execute(text("SELECT COUNT(*) FROM leads"))).scalar() == 1

    inbound = {
        "object": "page",
        "entry": [{"id": "PAGE-A", "messaging": [{
            "sender": {"id": "PSID-NEW"}, "recipient": {"id": "PAGE-A"}, "timestamp": 1714400001,
            "message": {"mid": "mid-in-1", "text": "Hello"},
        }]}],
    }
    await wh.process_messenger_event(inbound)
    persist.assert_awaited_once()

    writer.assert_not_awaited()
    assert (await webhook_db.execute(text("SELECT COUNT(*) FROM conversation_logs"))).scalar() == 0


@pytest.mark.asyncio
async def test_discord_dm_writes_no_conversation_logs():
    from app.discord_gateway.dm_writer import upsert_lead_and_message

    def _result(row):
        r = MagicMock()
        r.first.return_value = row
        r.scalar.return_value = row[0] if row else None
        r.scalar_one.return_value = row[0] if row else None
        return r

    session = AsyncMock()
    session.execute.side_effect = [_result(None), _result((1,)), _result(None), _result(None), _result((10,))]

    with patch("app.services.conv_log_writer.write_conversation_log", new=AsyncMock()) as writer:
        await upsert_lead_and_message(
            session,
            tenant_id=4,
            discord_user_id="111222333",
            sender_name="テストユーザー",
            dm_channel_id="DM-CH-456",
            message_text="初めてのDM",
            discord_message_id="msg-new-001",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

    writer.assert_not_awaited()
    for call in session.execute.call_args_list:
        assert "conversation_logs" not in str(call.args[0])


# ---------------------------------------------------------------------------
# 10. migration の文字の確かめ（ファイルを文字として読むだけ）
# ---------------------------------------------------------------------------
def test_rebuild_view_migration_text():
    sql = _MIGRATION.read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW" in sql
    assert "DROP" not in sql.upper()
    assert "meta_messages" in sql
    assert "deleted_at IS NULL" in sql
    # 戻し方のコメント行を除いて、古い会話の表の名前を含まない
    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    assert "conversation_logs" not in body
    # 値を変える文は書かない（ADR-1007）
    for word in ("INSERT ", "UPDATE ", "DELETE "):
        assert word not in body
