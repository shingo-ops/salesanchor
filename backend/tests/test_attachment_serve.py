"""serve_lead_attachment エンドポイントのユニットテスト（attachment-storage 便4）。

実 DB・実ファイルシステム・Discord CDN には接続しない。
SQLite インメモリ + tmp_path でテーブルとファイルを用意する。

テスト対象: GET /api/v1/leads/{lead_id}/attachments/{attachment_id}
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_DATABASE_URL", os.environ["DATABASE_URL"])

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch


# ---------------------------------------------------------------------------
# テスト用 DB / アプリセットアップ
# ---------------------------------------------------------------------------

TENANT_A = 1
TENANT_B = 2
ALL_PERMS = {"messaging.view"}


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _setup(dbapi_conn, _):
        dbapi_conn.create_function("NOW", 0, lambda: "2026-09-02 00:00:00+00:00")
        # SQLite は FOR UPDATE 非対応
        pass

    @event.listens_for(eng.sync_engine, "before_cursor_execute", retval=True)
    def _rewrite(conn, cursor, statement, parameters, context, executemany):
        if "public.users" in statement:
            statement = statement.replace("public.users", "users")
        if "public.permissions" in statement:
            statement = statement.replace("public.permissions", "permissions")
        if " FOR UPDATE" in statement:
            statement = statement.replace(" FOR UPDATE", "")
        return statement, parameters

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """lead_attachments テーブルを持つ SQLite セッション。"""
    async with engine.begin() as conn:
        # users / permissions / tenants は conftest から読まれるが、
        # このテストは self-contained なので最低限だけ定義する。
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                is_superadmin INTEGER NOT NULL DEFAULT 0
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tenant_id INTEGER NOT NULL,
                permission TEXT NOT NULL
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS lead_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                lead_id INTEGER NOT NULL,
                message_id TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL DEFAULT 'discord',
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                content_type TEXT,
                original_filename TEXT,
                created_at TEXT DEFAULT '2026-09-02 00:00:00+00:00',
                updated_at TEXT DEFAULT '2026-09-02 00:00:00+00:00'
            )
        """))
        await conn.execute(text("""
            INSERT INTO users (id, email, password_hash) VALUES (1, 'test@example.com', 'x')
        """))

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db, tmp_path, monkeypatch):
    """ATTACHMENT_ROOT を tmp_path に向けた HTTPクライアント。"""
    monkeypatch.setenv("ATTACHMENT_ROOT", str(tmp_path))

    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.database import get_db
    from app.main import app
    from app.models import User

    mock_user = User()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.is_active = True
    mock_user.is_superadmin = False
    mock_user.tenant_id = TENANT_A

    async def override_db():
        yield db

    async def override_user():
        return mock_user

    async def override_tenant():
        return TENANT_A

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_current_tenant] = override_tenant

    transport = ASGITransport(app=app)
    # 権限モックは conftest.py の bypass_permissions（autouse=True）が
    # 全テストに自動適用するため、ここでは patch しない。
    # 自前で patch すると load_user_permissions の引数数が合わず TypeError になる。
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

async def _insert_attachment(db: AsyncSession, *, tenant_id: int, lead_id: int, message_id: str, file_path: str) -> int:
    """lead_attachments に1行 INSERT して採番された id を返す。"""
    result = await db.execute(
        text("""
            INSERT INTO lead_attachments
                (tenant_id, lead_id, message_id, platform, file_path, file_size, content_type, original_filename)
            VALUES
                (:tenant_id, :lead_id, :message_id, 'discord', :file_path, 1024, 'image/png', 'test.png')
            RETURNING id
        """),
        {"tenant_id": tenant_id, "lead_id": lead_id, "message_id": message_id, "file_path": file_path},
    )
    row = result.first()
    await db.commit()
    return int(row[0])


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_serve_not_found_attachment_id(client, db):
    """存在しない attachment_id で 404 が返ること。"""
    resp = await client.get("/api/v1/leads/1/attachments/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "attachment_not_found"


@pytest.mark.asyncio
async def test_serve_other_tenant_returns_404(client, db, tmp_path):
    """他テナント（TENANT_B）の attachment_id に対して 404 が返ること（RLS の確認）。"""
    # TENANT_B の行を INSERT
    attachment_id = await _insert_attachment(
        db,
        tenant_id=TENANT_B,
        lead_id=1,
        message_id="msg-other-tenant",
        file_path="tenant_002/lead_1/msg-other-tenant.png",
    )
    # クライアントは TENANT_A でログイン中 → 他テナントの行は見えない
    resp = await client.get(f"/api/v1/leads/1/attachments/{attachment_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "attachment_not_found"


@pytest.mark.asyncio
async def test_serve_missing_file_returns_404(client, db, tmp_path):
    """DB に行があっても実体ファイルが無い場合に 404 が返ること。"""
    attachment_id = await _insert_attachment(
        db,
        tenant_id=TENANT_A,
        lead_id=10,
        message_id="msg-no-file",
        file_path="tenant_001/lead_10/msg-no-file.png",
    )
    # ファイルは作らない（実体なし）
    resp = await client.get(f"/api/v1/leads/10/attachments/{attachment_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "attachment_file_missing"


@pytest.mark.asyncio
async def test_serve_success_returns_file(client, db, tmp_path):
    """正常時に 200 と正しい media_type が返ること。"""
    # 実体ファイルを tmp_path に配置
    file_dir = tmp_path / "tenant_001" / "lead_20"
    file_dir.mkdir(parents=True)
    file_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    file_path = file_dir / "msg-ok.png"
    file_path.write_bytes(file_content)

    attachment_id = await _insert_attachment(
        db,
        tenant_id=TENANT_A,
        lead_id=20,
        message_id="msg-ok",
        file_path="tenant_001/lead_20/msg-ok.png",
    )

    resp = await client.get(f"/api/v1/leads/20/attachments/{attachment_id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.content == file_content
