"""会話の一本化 便1: 会話を書く所と読む所を meta_messages だけにする 試験（SQLite）。

検証項目（カード 9-3）:
  1. 手の記録を作ると meta_messages に1行（is_manual TRUE・sender_id manual:user_<id>・
     message_id manual_ で始まる・created_at = occurred_at）、conversation_logs に0行
  2. 手の記録が会話の流れの API（GET /leads/{id}/messages）に出る（K3）
  3. 過去の時刻で記録した手の記録が、流れのその時刻の位置に並ぶ。あとで時刻を直すと直した位置に並ぶ
  4. 消した手の記録が流れに出ない
  5. 手の記録が最新の行でも、最新の窓口・24時間の窓・未読に戻す行・受信箱の一覧が、手の記録の無いときと同じ
  6. 自動連携の行の id を手の記録の変更・削除の API に渡すと 404
  7. 電話の手の記録（inbound・original_language 'en'）が言語判定に数えられない
  8. 本文のラベル付け（priority_scoring）に手の記録が入らない
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

from tests.conftest import INBOX_BADGE_META_MESSAGES_DDL

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _REPO_ROOT / "migrations" / "20261108_100000_rebuild_company_stats_on_meta_messages.sql"

# 手の記録の作成が入れる列（INBOX_BADGE の定義に無いもの）
_EXTRA_META_COLUMNS = (
    "contact_id INTEGER",
    "company_id INTEGER",
    "occurred_at TIMESTAMP",
    "recorded_by_user_id INTEGER",
    "original_language VARCHAR(10)",
)

_MESSAGE_TRANSLATIONS_DDL = """
    CREATE TABLE IF NOT EXISTS message_translations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT NOT NULL,
        target_language VARCHAR(10),
        translated_text TEXT
    )
"""

_MESSAGE_LABELS_DDL = """
    CREATE TABLE IF NOT EXISTS message_labels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER,
        message_id INTEGER,
        lead_id INTEGER,
        label TEXT,
        confidence REAL,
        direction TEXT,
        source TEXT
    )
"""

_CONVERSATION_LOGS_DDL = """
    CREATE TABLE IF NOT EXISTS conversation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL DEFAULT 999,
        lead_id INTEGER,
        channel_type TEXT,
        direction TEXT,
        content_text TEXT,
        external_message_id TEXT,
        occurred_at TIMESTAMP,
        deleted_at TIMESTAMP
    )
"""


@pytest_asyncio.fixture
async def env(db_session):
    """手の記録の作成・読み出しを SQLite で通すための準備。"""
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
    for ddl in (_MESSAGE_TRANSLATIONS_DDL, _MESSAGE_LABELS_DDL, _CONVERSATION_LOGS_DDL):
        await db_session.execute(text(ddl))
    await db_session.commit()

    from app.routers import conv_logs as conv_logs_router

    real_fetch = conv_logs_router._fetch_conv_log

    async def fetch_with_datetimes(db, tenant_id, log_id):
        # SQLite は日時を文字で返す（PostgreSQL は日時）。監査用の isoformat() が通るよう日時にそろえる
        row = await real_fetch(db, tenant_id, log_id)
        if row is not None:
            for key in ("occurred_at", "deleted_at"):
                if isinstance(row[key], str):
                    row[key] = datetime.fromisoformat(row[key])
        return row

    with (
        patch("app.routers.conv_logs.record_audit_log", new=AsyncMock()),
        patch("app.routers.conv_logs._fire_translation", new=AsyncMock()),
        patch("app.routers.conv_logs._fetch_conv_log", new=fetch_with_datetimes),
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


async def _record_manual(client, lead_id: int, *, content: str = "電話で確認", occurred: str,
                         channel: str = "phone", direction: str = "inbound") -> int:
    res = await client.post(
        f"/api/v1/leads/{lead_id}/conv-logs",
        json={"channel_type": channel, "direction": direction, "content_text": content, "occurred_at": occurred},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def _rows(db, sql: str, **params):
    return (await db.execute(text(sql), params)).mappings().all()


# ---------------------------------------------------------------------------
# 1. 手の記録は meta_messages に1行だけ
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_manual_record_goes_to_meta_messages_only(client, env):
    lead_id = await _make_lead(client)
    log_id = await _record_manual(client, lead_id, occurred="2026-06-01T10:00:00+00:00")

    rows = await _rows(env, "SELECT * FROM meta_messages WHERE id = :i", i=log_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["is_manual"] in (1, True)
    assert row["sender_id"].startswith("manual:user_")
    assert row["message_id"].startswith("manual_")
    assert row["platform"] == "phone"
    assert row["lead_id"] == lead_id
    assert row["created_at"] == row["occurred_at"]

    logs = await _rows(env, "SELECT * FROM conversation_logs")
    assert logs == []


# ---------------------------------------------------------------------------
# 2. 会話の流れに出る（K3）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_manual_record_shows_in_conversation_flow(client, env):
    lead_id = await _make_lead(client)
    await _add_auto(env, lead_id, created_at="2026-06-01 09:00:00", message_text="auto-1")
    await _record_manual(client, lead_id, content="手の記録A", occurred="2026-06-02T10:00:00+00:00")

    res = await client.get(f"/api/v1/leads/{lead_id}/messages")
    assert res.status_code == 200, res.text
    texts = [m["message_text"] for m in res.json()["messages"]]
    assert "手の記録A" in texts
    assert "auto-1" in texts


# ---------------------------------------------------------------------------
# 3. 並ぶ位置は記録した時刻。あとで直すと直した位置に動く
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_manual_record_is_placed_by_its_time(client, env):
    lead_id = await _make_lead(client)
    await _add_auto(env, lead_id, created_at="2026-06-02 09:00:00", message_text="auto-late")
    await _add_auto(env, lead_id, created_at="2026-06-01 09:00:00", message_text="auto-early",
                    direction="outbound")
    log_id = await _record_manual(client, lead_id, content="過去の手の記録", occurred="2026-06-01T12:00:00+00:00")

    res = await client.get(f"/api/v1/leads/{lead_id}/messages")
    order = [m["message_text"] for m in res.json()["messages"]]
    assert order == ["auto-early", "過去の手の記録", "auto-late"]

    patched = await client.patch(
        f"/api/v1/leads/{lead_id}/conv-logs/{log_id}",
        json={"occurred_at": "2026-06-03T12:00:00+00:00"},
    )
    assert patched.status_code == 200, patched.text
    res = await client.get(f"/api/v1/leads/{lead_id}/messages")
    order = [m["message_text"] for m in res.json()["messages"]]
    assert order == ["auto-early", "auto-late", "過去の手の記録"]


# ---------------------------------------------------------------------------
# 4. 消した手の記録は流れに出ない
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_deleted_manual_record_is_not_in_flow(client, env):
    lead_id = await _make_lead(client)
    await _add_auto(env, lead_id, created_at="2026-06-01 09:00:00", message_text="auto-1")
    log_id = await _record_manual(client, lead_id, content="消す記録", occurred="2026-06-02T10:00:00+00:00")

    deleted = await client.delete(f"/api/v1/leads/{lead_id}/conv-logs/{log_id}")
    assert deleted.status_code == 204

    res = await client.get(f"/api/v1/leads/{lead_id}/messages")
    texts = [m["message_text"] for m in res.json()["messages"]]
    assert "消す記録" not in texts
    assert texts == ["auto-1"]


# ---------------------------------------------------------------------------
# 5. 手の記録が最新でも、窓口・24時間の窓・未読・受信箱が変わらない
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_manual_latest_row_does_not_change_destination_window_unread_inbox(client, env):
    lead_id = await _make_lead(client)
    await _add_auto(env, lead_id, created_at="2026-06-01 09:00:00", platform="messenger",
                    message_text="customer hello")

    async def snapshot():
        msgs = (await client.get(f"/api/v1/leads/{lead_id}/messages")).json()
        inbox = (await client.get("/api/v1/conversations")).json()["conversations"]
        conv = next(c for c in inbox if c["lead_id"] == lead_id)
        return {
            "platform": msgs["lead"]["platform"],
            "window": msgs["messaging_window"],
            "inbox_platform": conv["platform"],
            "inbox_last_text": conv["last_message_text"],
            "inbox_unread": conv["unread_count"],
        }

    before = await snapshot()
    assert before["platform"] == "messenger"
    assert before["inbox_unread"] == 1

    # 手の記録（電話）を、一番新しい行として足す
    await _record_manual(client, lead_id, content="電話で話した", occurred="2026-06-09T10:00:00+00:00")
    after = await snapshot()
    assert after == before

    # 未読に戻す: 戻す行は自動連携の最新の受信（手の記録ではない）
    await client.post(f"/api/v1/leads/{lead_id}/messages/mark-read")
    unmarked = await client.post(f"/api/v1/leads/{lead_id}/messages/mark-unread")
    assert unmarked.status_code == 200, unmarked.text
    assert unmarked.json()["unmarked_count"] == 1
    # 未読に戻ったのは自動連携の受信。手の記録の行は戻さない
    auto_row = await _rows(env, "SELECT seen_at FROM meta_messages WHERE message_text = 'customer hello'")
    manual_row = await _rows(env, "SELECT seen_at FROM meta_messages WHERE message_text = '電話で話した'")
    assert auto_row[0]["seen_at"] is None
    assert manual_row[0]["seen_at"] is not None


# ---------------------------------------------------------------------------
# 6. 自動連携の行の id を手の記録の API に渡すと 404
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_auto_row_id_is_404_for_manual_api(client, env):
    lead_id = await _make_lead(client)
    auto_id = await _add_auto(env, lead_id, created_at="2026-06-01 09:00:00")

    patched = await client.patch(
        f"/api/v1/leads/{lead_id}/conv-logs/{auto_id}", json={"content_text": "書き換え"}
    )
    assert patched.status_code == 404
    deleted = await client.delete(f"/api/v1/leads/{lead_id}/conv-logs/{auto_id}")
    assert deleted.status_code == 404

    rows = await _rows(env, "SELECT message_text, deleted_at FROM meta_messages WHERE id = :i", i=auto_id)
    assert rows[0]["message_text"] == "auto"
    assert rows[0]["deleted_at"] is None


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
    await _record_manual(client, lead_id, content="電話で価格を確認", occurred="2026-06-02T10:00:00+00:00")

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
    # echo では何も書かず、リードも作らない（受信の書き込みも呼ばれない）
    persist.assert_not_awaited()
    assert (await webhook_db.execute(text("SELECT COUNT(*) FROM leads"))).scalar() == 0

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
