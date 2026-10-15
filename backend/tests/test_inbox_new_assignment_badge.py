"""
受信箱「新規」バッジ（担当になったが、まだ開いていない）の Acceptance Criteria テスト。

設計: docs/handoff/inbox-new-assignment-badge/design.md
対象:
- migrations/20261015_090000_add_leads_assignment_opened_at.sql （A1, A2）
- backend/app/services/tenant.py の leads CREATE TABLE （A11）
- backend/app/routers/leads.py の update_lead （A3, A4）
- backend/app/routers/leads.py の mark_lead_messages_read （A5, A6, A7, A10）
- backend/app/routers/meta_inbox.py の list_conversations （A8, A9）

`test_conversations.py` と同じ構成（最小 FastAPI app + SQLite + dependency
override）で構築する。PostgreSQL 専用の `DO $$ ... pg_namespace` ループは
SQLite では動かないため、その事実を記録するテストと、列追加・既存行の
埋め直しの「冪等性」だけを同じ SQL 文で検証するテストを分けて用意する
（design.md の指示: 「無理に通さない」）。

実行:
    pytest backend/tests/test_inbox_new_assignment_badge.py -v
"""

from __future__ import annotations

import os
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# DATABASE_URL を SQLite に必ず差し替え（モジュール import 順の罠回避）
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
from app.routers import meta_inbox

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "migrations" / "20261015_090000_add_leads_assignment_opened_at.sql"
TENANT_SERVICE_PATH = REPO_ROOT / "backend" / "app" / "services" / "tenant.py"

_ALL_PERMS = {"leads.view", "leads.update", "leads.create", "messaging.view", "messaging.send"}


# ---------------------------------------------------------------------------
# fixtures（test_conversations.py と同じ作法）
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    """SQLite に leads（+ assignment_opened_at） + meta_messages を最小スキーマで作成する。

    NOW() は呼び出しごとに異なる値を返す（単調増加のダミー時刻）。固定値だと
    「2回目に開いても時刻が変わらない」(A7) が、ガード条件を外しても偶然
    グリーンになってしまい、検証として機能しないため。
    """
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    counter = {"n": 0}

    @event.listens_for(eng.sync_engine, "connect")
    def _setup(dbapi_conn, _):
        def _fake_now():
            counter["n"] += 1
            return f"2026-10-15T12:00:{counter['n']:02d}"
        dbapi_conn.create_function("NOW", 0, _fake_now)
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    async with eng.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL DEFAULT 999,
                lead_code VARCHAR(20),
                customer_name VARCHAR(255) NOT NULL,
                company_name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(50),
                channel_type VARCHAR(30),
                initiative VARCHAR(10),
                type VARCHAR(50),
                status VARCHAR(50) DEFAULT 'lead',
                temperature VARCHAR(20),
                estimated_scale VARCHAR(20),
                customer_type VARCHAR(50),
                response_speed VARCHAR(20),
                monthly_forecast NUMERIC(15, 2),
                amount NUMERIC(15, 2),
                currency VARCHAR(10) DEFAULT 'JPY',
                expected_close_date DATE,
                prospect_rank VARCHAR(10),
                assigned_to INTEGER,
                assignment_opened_at TIMESTAMP,
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
        """))
        # update_lead は（商談カルテ選択肢を一切触らなくても）最後に必ず
        # sales_form_selections / sales_form_options を読みに行くため、空でも実体が必要。
        await conn.execute(text("""
            CREATE TABLE tenant_sales_form_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                label VARCHAR(100),
                value VARCHAR(100),
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """))
        await conn.execute(text("""
            CREATE TABLE lead_sales_form_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                option_id INTEGER NOT NULL,
                other_text VARCHAR(500)
            )
        """))
        await conn.execute(text("""
            CREATE TABLE meta_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                lead_id INTEGER,
                platform VARCHAR(20) NOT NULL DEFAULT 'messenger',
                sender_id VARCHAR(100) NOT NULL,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


def _mock_user(user_id: int, tenant_id: int):
    u = MagicMock()
    u.id = user_id
    u.tenant_id = tenant_id
    u.email = f"tester{user_id}@example.com"
    return u


def _build_app(db_session, *, user_id: int, tenant_id: int):
    app = FastAPI()

    async def override_db():
        yield db_session

    async def override_user():
        return _mock_user(user_id, tenant_id)

    async def override_tenant():
        return tenant_id

    app.include_router(leads_router.router, prefix="/api/v1")
    app.include_router(meta_inbox.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_current_tenant] = override_tenant
    return app


@asynccontextmanager
async def _client(db_session, *, user_id: int = 10, tenant_id: int = 999):
    """指定ユーザーとして振る舞う AsyncClient（leads + meta_inbox router 搭載）。"""
    app = _build_app(db_session, user_id=user_id, tenant_id=tenant_id)
    transport = ASGITransport(app=app)
    with ExitStack() as stack:
        stack.enter_context(patch(
            "app.auth.dependencies.load_user_permissions",
            new=AsyncMock(return_value=_ALL_PERMS),
        ))
        stack.enter_context(patch(
            "app.routers.leads.record_audit_log",
            new=AsyncMock(return_value=None),
        ))
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


async def _insert_lead(
    db_session,
    *,
    lead_id: int,
    tenant_id: int = 999,
    customer_name: str = "Customer",
    assigned_to: int | None = None,
    assignment_opened_at: str | None = None,
):
    await db_session.execute(
        text("""
            INSERT INTO leads (id, tenant_id, customer_name, assigned_to, assignment_opened_at)
            VALUES (:id, :tenant_id, :customer_name, :assigned_to, :assignment_opened_at)
        """),
        {
            "id": lead_id, "tenant_id": tenant_id, "customer_name": customer_name,
            "assigned_to": assigned_to, "assignment_opened_at": assignment_opened_at,
        },
    )
    await db_session.commit()


async def _insert_message(
    db_session,
    *,
    lead_id: int,
    tenant_id: int = 999,
    platform: str = "messenger",
    direction: str = "inbound",
    message_text: str = "Hello",
    sender_id: str = "PSID-1",
):
    await db_session.execute(
        text("""
            INSERT INTO meta_messages (tenant_id, lead_id, platform, sender_id, message_text, direction)
            VALUES (:tenant_id, :lead_id, :platform, :sender_id, :message_text, :direction)
        """),
        {
            "tenant_id": tenant_id, "lead_id": lead_id, "platform": platform,
            "sender_id": sender_id, "message_text": message_text, "direction": direction,
        },
    )
    await db_session.commit()


async def _get_lead(db_session, lead_id: int):
    result = await db_session.execute(
        text("SELECT * FROM leads WHERE id = :id"), {"id": lead_id},
    )
    return result.mappings().first()


# ---------------------------------------------------------------------------
# A1 / A2: マイグレーションの列追加・既存行の埋め直し・冪等性
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_migration_do_block_is_postgresql_only_syntax_error_on_sqlite():
    """事実の記録: マイグレーション本体の `DO $$ ... pg_namespace` ループは
    PostgreSQL 専用構文であり、SQLite ではそのまま実行できない。
    （design.md の指示により、動かないという事実をテストとして残す。無理に通さない）
    """
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "DO $$" in migration_sql
    assert "pg_namespace" in migration_sql

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        with pytest.raises(Exception):
            async with eng.begin() as conn:
                await conn.execute(text(migration_sql))
    finally:
        await eng.dispose()


@pytest.mark.asyncio
async def test_sqlite_alter_table_does_not_support_add_column_if_not_exists():
    """事実の記録: SQLite の `ALTER TABLE` 文法自体に `ADD COLUMN IF NOT EXISTS` は
    存在しない（`IF NOT EXISTS` は `CREATE TABLE`/`CREATE INDEX` 専用。PostgreSQL は
    `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` を独自拡張として持つが SQLite には無い）。
    実際に SQLite へ投げて構文エラーになることを確認する（design.md の指示により、
    動かないという事実をテストとして残す。無理に通さない）。
    """
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        with pytest.raises(Exception):
            async with eng.begin() as conn:
                await conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY)"))
                await conn.execute(text("ALTER TABLE t ADD COLUMN IF NOT EXISTS x TIMESTAMP"))
    finally:
        await eng.dispose()


@pytest.mark.asyncio
async def test_a1_a2_backfill_update_is_idempotent():
    """A1: 既存の担当付き行の埋め直し。
    A2: 同じ UPDATE を2回流しても結果が同じ（冪等）。

    列追加（`ADD COLUMN IF NOT EXISTS`）そのものの2回実行は SQLite の ALTER TABLE
    文法に存在しないため検証できない（上のテストで確認済み）。そのため列は最初から
    用意し、マイグレーション本体にある「既存行の埋め直し」の UPDATE 文
    （`WHERE assigned_to IS NOT NULL AND assignment_opened_at IS NULL`）の冪等性を、
    同じ SQL 文を2回実行して検証する。
    """
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS assignment_opened_at" in migration_sql
    backfill_sql = text(
        "UPDATE leads SET assignment_opened_at = CURRENT_TIMESTAMP "
        "WHERE assigned_to IS NOT NULL AND assignment_opened_at IS NULL"
    )
    assert "WHERE assigned_to IS NOT NULL AND assignment_opened_at IS NULL" in migration_sql

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        async with eng.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE leads (id INTEGER PRIMARY KEY, assigned_to INTEGER, assignment_opened_at TIMESTAMP)"
            ))
            await conn.execute(text("INSERT INTO leads (id, assigned_to) VALUES (1, 10)"))  # 担当あり
            await conn.execute(text("INSERT INTO leads (id, assigned_to) VALUES (2, NULL)"))  # 担当なし

        # 1回目（A1: 担当付きの既存行が埋まる）
        async with eng.begin() as conn:
            result1 = await conn.execute(backfill_sql)
            rows = (await conn.execute(
                text("SELECT id, assigned_to, assignment_opened_at FROM leads ORDER BY id")
            )).mappings().all()
        by_id = {r["id"]: r for r in rows}
        assert result1.rowcount == 1
        assert by_id[1]["assignment_opened_at"] is not None  # 担当付きは埋まる
        assert by_id[2]["assignment_opened_at"] is None      # 担当なしは埋めない
        first_value = by_id[1]["assignment_opened_at"]

        # 2回目（A2: 冪等性。対象行が無いため rowcount=0、値も変わらない）
        async with eng.begin() as conn:
            result2 = await conn.execute(backfill_sql)
            rows2 = (await conn.execute(
                text("SELECT id, assigned_to, assignment_opened_at FROM leads ORDER BY id")
            )).mappings().all()
        by_id2 = {r["id"]: r for r in rows2}
        assert result2.rowcount == 0
        assert by_id2[1]["assignment_opened_at"] == first_value
        assert by_id2[2]["assignment_opened_at"] is None
    finally:
        await eng.dispose()


# ---------------------------------------------------------------------------
# A11: migration と tenant.py の両方に新列があること（静的チェック）
# ---------------------------------------------------------------------------


def test_a11_both_migration_and_tenant_service_have_new_column():
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "assignment_opened_at" in migration_sql

    tenant_py = TENANT_SERVICE_PATH.read_text(encoding="utf-8")
    leads_block_start = tenant_py.index("CREATE TABLE IF NOT EXISTS {schema}.leads")
    leads_block_end = tenant_py.index(");", leads_block_start)
    leads_block = tenant_py[leads_block_start:leads_block_end]
    assert "assignment_opened_at" in leads_block


# ---------------------------------------------------------------------------
# A3 / A4: 担当変更で assignment_opened_at がリセットされる（同じ担当者では戻らない）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a3_assignment_change_resets_opened_at(db_session):
    await _insert_lead(db_session, lead_id=1, assigned_to=10, assignment_opened_at="2026-01-01T00:00:00")

    async with _client(db_session, user_id=10) as ac:
        resp = await ac.patch("/api/v1/leads/1", json={"assigned_to": 20})
        assert resp.status_code == 200, resp.text

    row = await _get_lead(db_session, 1)
    assert row["assigned_to"] == 20
    assert row["assignment_opened_at"] is None


@pytest.mark.asyncio
async def test_a4_same_assignee_resave_keeps_opened_at(db_session):
    await _insert_lead(db_session, lead_id=1, assigned_to=10, assignment_opened_at="2026-01-01T00:00:00")

    async with _client(db_session, user_id=10) as ac:
        resp = await ac.patch("/api/v1/leads/1", json={"assigned_to": 10, "notes": "same assignee"})
        assert resp.status_code == 200, resp.text

    row = await _get_lead(db_session, 1)
    assert row["assigned_to"] == 10
    assert row["assignment_opened_at"] == "2026-01-01T00:00:00"


# ---------------------------------------------------------------------------
# A5 / A6 / A7 / A10: mark-read の opened フラグ
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a5_mark_read_opened_sets_timestamp_only_for_the_assignee(db_session):
    await _insert_lead(db_session, lead_id=1, assigned_to=10, assignment_opened_at=None)   # 自分担当
    await _insert_lead(db_session, lead_id=2, assigned_to=99, assignment_opened_at=None)   # 他人担当

    async with _client(db_session, user_id=10) as ac:
        r1 = await ac.post("/api/v1/leads/1/messages/mark-read", json={"opened": True})
        assert r1.status_code == 200, r1.text
        r2 = await ac.post("/api/v1/leads/2/messages/mark-read", json={"opened": True})
        assert r2.status_code == 200, r2.text

    row1 = await _get_lead(db_session, 1)
    row2 = await _get_lead(db_session, 2)
    assert row1["assignment_opened_at"] is not None   # 自分担当 → 入る
    assert row2["assignment_opened_at"] is None        # 他人担当 → 入らない（R3）


@pytest.mark.asyncio
async def test_a6_mark_read_without_opened_does_not_set_timestamp(db_session):
    await _insert_lead(db_session, lead_id=1, assigned_to=10, assignment_opened_at=None)

    async with _client(db_session, user_id=10) as ac:
        r_missing = await ac.post("/api/v1/leads/1/messages/mark-read")  # body なし（既存呼び出し相当）
        assert r_missing.status_code == 200, r_missing.text
        r_false = await ac.post("/api/v1/leads/1/messages/mark-read", json={"opened": False})
        assert r_false.status_code == 200, r_false.text

    row = await _get_lead(db_session, 1)
    assert row["assignment_opened_at"] is None  # 一括既読で消えないこと（K5 相当）


@pytest.mark.asyncio
async def test_a7_mark_read_opened_twice_keeps_first_timestamp(db_session):
    await _insert_lead(db_session, lead_id=1, assigned_to=10, assignment_opened_at=None)

    async with _client(db_session, user_id=10) as ac:
        r1 = await ac.post("/api/v1/leads/1/messages/mark-read", json={"opened": True})
        assert r1.status_code == 200
        first = (await _get_lead(db_session, 1))["assignment_opened_at"]
        assert first is not None

        r2 = await ac.post("/api/v1/leads/1/messages/mark-read", json={"opened": True})
        assert r2.status_code == 200
        second = (await _get_lead(db_session, 1))["assignment_opened_at"]

    assert first == second  # NOW() は呼び出しごとに違う値を返すため、ガードが効いていないと赤になる


@pytest.mark.asyncio
async def test_a10_existing_mark_read_caller_without_opened_field_still_works(db_session):
    """既存の呼び出し（body `{}`）が壊れていないこと。"""
    await _insert_lead(db_session, lead_id=1, assigned_to=10, assignment_opened_at=None)
    await _insert_message(db_session, lead_id=1, direction="inbound")

    async with _client(db_session, user_id=10) as ac:
        resp = await ac.post("/api/v1/leads/1/messages/mark-read", json={})
        assert resp.status_code == 200, resp.text
        assert resp.json()["marked_count"] == 1


# ---------------------------------------------------------------------------
# A8 / A9: 会話一覧の is_new_assignment と assigned_to 非公開
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a8_a9_is_new_assignment_and_assigned_to_not_leaked(db_session):
    await _insert_lead(db_session, lead_id=1, assigned_to=10, assignment_opened_at=None)   # 自分・未開封
    await _insert_lead(db_session, lead_id=2, assigned_to=99, assignment_opened_at=None)   # 他人担当
    await _insert_lead(db_session, lead_id=3, assigned_to=None, assignment_opened_at=None)  # 担当なし
    for lid in (1, 2, 3):
        await _insert_message(db_session, lead_id=lid)

    async with _client(db_session, user_id=10) as ac:
        resp = await ac.get("/api/v1/conversations")
        assert resp.status_code == 200, resp.text

    convs = {c["lead_id"]: c for c in resp.json()["conversations"]}
    assert convs[1]["is_new_assignment"] is True
    assert convs[2]["is_new_assignment"] is False
    assert convs[3]["is_new_assignment"] is False
    for conv in convs.values():
        assert "assigned_to" not in conv  # A9: 他人の担当者IDを返さない
