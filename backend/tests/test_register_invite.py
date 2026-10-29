"""register と担当者の追加の初回設定メール（ADR-1013 便4a）のテスト。SQLite で動かす。

self のとき: purpose=invite の鍵が 1 行・送信関数の呼び出し 1 回。
firebase のとき: 鍵 0 行・送信 0 回。
"""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth import self_tokens

ORIGIN = "https://app.salesanchor.jp"
REGISTER_PATH = "/api/v1/auth/register"
EMAIL = "Invitee-Reg@Example.com"
TENANT_CODE = "tenant-invite-reg"
TENANT_ID = 4701
ADMIN_ID = 4700
SECRET = "test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

_INVITES = sa.table("password_reset_tokens", sa.column("id"), sa.column("user_id"))
_USERS = sa.table("users", sa.column("id"), sa.column("email"))
_TENANTS = sa.table("tenants", sa.column("id"))


@pytest.fixture(autouse=True)
def provider_self(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    monkeypatch.setenv("AUTH_JWT_SECRET", SECRET)
    monkeypatch.delenv("AUTH_RP_ORIGIN", raising=False)


@pytest.fixture
def provider_firebase(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)


@pytest.fixture(autouse=True)
def stubs():
    with patch("app.routers.auth.record_audit_log", new=AsyncMock()), \
         patch("app.routers.auth.invalidate_user_permissions", new=AsyncMock()):
        yield


@pytest.fixture
def sender():
    with patch("app.routers.auth.send_invite_email", new=MagicMock()) as m:
        yield m


@pytest.fixture(autouse=True)
async def cleanup(db_session):
    yield
    await db_session.rollback()
    mine = sa.select(_USERS.c.id).where(sa.func.lower(_USERS.c.email) == EMAIL.lower())
    await db_session.execute(sa.delete(_INVITES).where(_INVITES.c.user_id.in_(mine)))
    await db_session.execute(sa.delete(_USERS).where(sa.func.lower(_USERS.c.email) == EMAIL.lower()))
    await db_session.execute(sa.delete(_TENANTS).where(_TENANTS.c.id == TENANT_ID))
    await db_session.commit()


@pytest.fixture
async def http(db_session):
    from types import SimpleNamespace

    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app

    # 試験の土台の tenants は最小定義。ORM が読む列を、無ければ足す
    for column, ddl in (("created_at", "TIMESTAMP"), ("updated_at", "TIMESTAMP"), ("settings", "TEXT")):
        have = {r[1] for r in (await db_session.execute(text("PRAGMA table_info(tenants)"))).all()}
        if column not in have:
            await db_session.execute(text(f"ALTER TABLE tenants ADD COLUMN {column} {ddl}"))
    await db_session.execute(
        text("INSERT INTO tenants (id, tenant_code, tenant_name, is_active) VALUES (:i, :c, 'T', 1)"),
        {"i": TENANT_ID, "c": TENANT_CODE},
    )
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_super_admin] = lambda: SimpleNamespace(id=ADMIN_ID, is_super_admin=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://app.salesanchor.jp") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_super_admin, None)


async def _register(http, origin=ORIGIN):
    headers = {"origin": origin} if origin else {}
    return await http.post(
        REGISTER_PATH,
        json={"email": EMAIL, "username": "invitee", "full_name": "I", "tenant_code": TENANT_CODE},
        headers=headers,
    )


async def _invite_rows(db):
    return (
        await db.execute(
            text(
                "SELECT t.purpose, t.expires_at, t.created_at, u.password_argon2_hash AS h, u.email AS email "
                "FROM password_reset_tokens t JOIN users u ON u.id = t.user_id WHERE lower(u.email) = :e"
            ),
            {"e": EMAIL.lower()},
        )
    ).all()


async def test_register_self_creates_invite_key_and_sends_one_mail(http, db_session, sender):
    resp = await _register(http)

    assert resp.status_code == 201, resp.text
    rows = await _invite_rows(db_session)
    assert len(rows) == 1
    assert rows[0].purpose == "invite"
    assert rows[0].h is None  # パスワードは NULL のまま
    assert rows[0].email == EMAIL.lower()
    lifetime = self_tokens._as_utc(rows[0].expires_at) - self_tokens._as_utc(rows[0].created_at)
    assert lifetime == timedelta(hours=72)
    assert sender.call_count == 1
    to_addr, url = sender.call_args.args
    assert to_addr == EMAIL.lower()
    assert url.startswith(f"{ORIGIN}/reset-password?token=")


async def test_register_firebase_creates_user_only(http, db_session, sender, provider_firebase):
    resp = await _register(http)

    assert resp.status_code == 201, resp.text
    assert await _invite_rows(db_session) == []
    user = (await db_session.execute(text("SELECT id FROM users WHERE lower(email) = :e"), {"e": EMAIL.lower()})).first()
    assert user is not None
    assert sender.call_count == 0


async def test_register_wrong_origin_is_403(http, db_session, sender):
    assert (await _register(http, origin="https://salesanchor.jp")).status_code == 403
    assert (await _register(http, origin=None)).status_code == 403
    assert sender.call_count == 0


async def test_register_duplicate_email_is_409_without_mail(http, db_session, sender):
    assert (await _register(http)).status_code == 201
    sender.reset_mock()

    assert (await _register(http)).status_code == 409
    assert sender.call_count == 0
    assert len(await _invite_rows(db_session)) == 1


async def test_invite_key_is_accepted_by_password_reset_confirm(http, db_session, sender):
    """初回設定の鍵は再設定の confirm でそのまま使える（リンクは再設定ページと同じ）。"""
    assert (await _register(http)).status_code == 201
    raw = sender.call_args.args[1].split("token=", 1)[1]

    with patch("app.routers.auth.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.routers.auth.record_auth_failure", new=AsyncMock()):
        resp = await http.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": raw, "new_password": "brand new long password 2026 ok"},
            headers={"origin": ORIGIN},
        )

    assert resp.status_code == 200, resp.text
    row = (await db_session.execute(text("SELECT password_argon2_hash FROM users WHERE lower(email) = :e"), {"e": EMAIL.lower()})).first()
    assert row.password_argon2_hash is not None
