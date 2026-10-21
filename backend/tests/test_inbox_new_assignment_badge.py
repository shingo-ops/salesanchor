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

from .conftest import (
    INBOX_BADGE_GENERIC_SINGLE_COLUMN_DDL,
    INBOX_BADGE_MINIMAL_LEADS_DDL,
    INBOX_BADGE_SQLITE_DDL,
    INBOX_BADGE_TENANT_LEADS_CREATE_TABLE_MARKER,
)

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
        # leads / tenant_sales_form_options / lead_sales_form_selections /
        # meta_messages の DDL は conftest.py の INBOX_BADGE_SQLITE_DDL に集約
        # している（check_test_schema_dup.py の対象除外ファイルに寄せるため）。
        # update_lead は（商談カルテ選択肢を一切触らなくても）最後に必ず
        # sales_form_selections / sales_form_options を読みに行くため、空でも実体が必要。
        for ddl in INBOX_BADGE_SQLITE_DDL:
            await conn.execute(text(ddl))

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
    """事実の記録（一般的な SQLite の制約）: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
    は PostgreSQL 独自拡張であり SQLite の ALTER TABLE 文法には存在しない
    （`IF NOT EXISTS` は `CREATE TABLE`/`CREATE INDEX` 専用）。

    現在のマイグレーション本体はこの構文を使わず、`information_schema.columns` で
    列の有無を調べてから `ADD COLUMN`（`IF NOT EXISTS` 無し）する方式に変更済み
    （レビュー 2026-10-15 指摘の再実行時欠陥の修正）。本テストはそれでも一般的な
    事実として記録しておく（design.md の指示により、動かないという事実を残す）。
    """
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        with pytest.raises(Exception):
            async with eng.begin() as conn:
                await conn.execute(text(INBOX_BADGE_GENERIC_SINGLE_COLUMN_DDL))
                await conn.execute(text("ALTER TABLE t ADD COLUMN IF NOT EXISTS x TIMESTAMP"))
    finally:
        await eng.dispose()


@pytest.mark.asyncio
async def test_a1_a2_column_guard_backfill_is_idempotent_across_redeploys():
    """A1: 列がまだ無いときだけ列を追加し、既存の担当付き行を埋める。
    A2: 2回目以降（列が既に存在する）は丸ごとスキップし、1回目以降に新しく担当が付いた
    行（＝まだ開いていない・NULL のまま）を壊さない。

    これは 2026-10-15 のレビューで指摘された本番上の欠陥そのものの再現テストである:
    旧マイグレーションは `UPDATE ... WHERE assignment_opened_at IS NULL` を毎デプロイで
    再実行し、「担当になったがまだ開いていない」行（＝バッジを出すべき行）まで埋めて
    しまっていた。現在のマイグレーションは `information_schema.columns` で列の存在を
    確認し、存在すれば `CONTINUE` で完全にスキップする。

    `DO $$` ループ自体は SQLite で動かせないため（上のテストで確認済み）、
    同じ「列が無いときだけ ALTER+UPDATE、あれば完全スキップ」という分岐ロジックを
    Python 側で再現して検証する。
    """
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "information_schema.columns" in migration_sql
    assert "CONTINUE" in migration_sql
    assert "ADD COLUMN assignment_opened_at" in migration_sql
    assert "WHERE assigned_to IS NOT NULL" in migration_sql
    # 旧版の欠陥（再実行ごとにバッジが消える原因）が実行コード側に復活していないことの確認。
    # コメント（審査での指摘の経緯説明）に同じ文字列が出てくるため、DO $$ 本体
    # （実行コード）だけを取り出して検査する。
    do_block = migration_sql[migration_sql.index("DO $$"):]
    assert "assignment_opened_at IS NULL" not in do_block

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def _column_exists(conn) -> bool:
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM pragma_table_info('leads') WHERE name = 'assignment_opened_at'"
        ))
        return (result.scalar_one() or 0) > 0

    async def _run_migration_once():
        """マイグレーション本体の分岐（列が無いときだけ実行・あれば CONTINUE）を再現する。"""
        async with eng.begin() as conn:
            if await _column_exists(conn):
                return  # CONTINUE 相当（何もしない）
            await conn.execute(text("ALTER TABLE leads ADD COLUMN assignment_opened_at TIMESTAMP"))
            await conn.execute(text(
                "UPDATE leads SET assignment_opened_at = CURRENT_TIMESTAMP WHERE assigned_to IS NOT NULL"
            ))

    try:
        async with eng.begin() as conn:
            await conn.execute(text(INBOX_BADGE_MINIMAL_LEADS_DDL))
            await conn.execute(text("INSERT INTO leads (id, assigned_to) VALUES (1, 10)"))  # 既存の担当付き行
            await conn.execute(text("INSERT INTO leads (id, assigned_to) VALUES (2, NULL)"))  # 担当なし

        # 1回目（列がまだ無い）: A1 相当。列が追加され、既存の担当付き行が埋まる
        await _run_migration_once()
        async with eng.begin() as conn:
            rows = (await conn.execute(
                text("SELECT id, assigned_to, assignment_opened_at FROM leads ORDER BY id")
            )).mappings().all()
        by_id = {r["id"]: r for r in rows}
        assert by_id[1]["assignment_opened_at"] is not None
        assert by_id[2]["assignment_opened_at"] is None

        # 本番相当の経過: 1回目以降に新しく担当が付いた行（まだ開いていない＝NULL）
        async with eng.begin() as conn:
            await conn.execute(text(
                "INSERT INTO leads (id, assigned_to, assignment_opened_at) VALUES (3, 20, NULL)"
            ))

        # 2回目（毎デプロイで再実行される想定）: A2 相当。列は既にあるので丸ごとスキップ
        await _run_migration_once()
        async with eng.begin() as conn:
            rows2 = (await conn.execute(
                text("SELECT id, assigned_to, assignment_opened_at FROM leads ORDER BY id")
            )).mappings().all()
        by_id2 = {r["id"]: r for r in rows2}
        assert by_id2[1]["assignment_opened_at"] == by_id[1]["assignment_opened_at"]  # 既存行は変化なし
        assert by_id2[2]["assignment_opened_at"] is None
        assert by_id2[3]["assignment_opened_at"] is None  # 旧版の欠陥ポイント。消えてはいけない
    finally:
        await eng.dispose()


# ---------------------------------------------------------------------------
# A11: migration と tenant.py の両方に新列があること（静的チェック）
# ---------------------------------------------------------------------------


def test_a11_both_migration_and_tenant_service_have_new_column():
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "assignment_opened_at" in migration_sql

    tenant_py = TENANT_SERVICE_PATH.read_text(encoding="utf-8")
    leads_block_start = tenant_py.index(INBOX_BADGE_TENANT_LEADS_CREATE_TABLE_MARKER)
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
    # 4件目: 自分担当だが既に開封済み（レビュー指摘: 3ケースだけでは不足）
    await _insert_lead(db_session, lead_id=4, assigned_to=10, assignment_opened_at="2026-01-01T00:00:00")
    for lid in (1, 2, 3, 4):
        await _insert_message(db_session, lead_id=lid)

    async with _client(db_session, user_id=10) as ac:
        resp = await ac.get("/api/v1/conversations")
        assert resp.status_code == 200, resp.text

    convs = {c["lead_id"]: c for c in resp.json()["conversations"]}
    assert convs[1]["is_new_assignment"] is True
    assert convs[2]["is_new_assignment"] is False
    assert convs[3]["is_new_assignment"] is False
    assert convs[4]["is_new_assignment"] is False  # 自分担当だが開封済みなので false
    for conv in convs.values():
        assert "assigned_to" not in conv  # A9: 他人の担当者IDを返さない


@pytest.mark.asyncio
async def test_assignment_cleared_to_null_resets_opened_at(db_session):
    """担当を外す（assigned_to を NULL にする）遷移でも reset が走ることを確認する
    （レビュー指摘: assigned_to を NULL にする遷移が未検証だった）。"""
    await _insert_lead(db_session, lead_id=1, assigned_to=10, assignment_opened_at="2026-01-01T00:00:00")

    async with _client(db_session, user_id=10) as ac:
        resp = await ac.patch("/api/v1/leads/1", json={"assigned_to": None})
        assert resp.status_code == 200, resp.text

    row = await _get_lead(db_session, 1)
    assert row["assigned_to"] is None
    assert row["assignment_opened_at"] is None
