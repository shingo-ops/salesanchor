"""パスワード再設定 API（ADR-1013 便3）のテスト。SQLite で動かす。"""

import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth import passwords, self_tokens

assert sqlite3.sqlite_version_info >= (3, 35), "SQLite 3.35+ is required for RETURNING"

try:
    from conftest import _make_noop_audit_log
except ImportError:  # pragma: no cover - conftest を import できない場合の複製
    def _make_noop_audit_log():
        import json

        async def mock_record_audit_log(db, tenant_id, user_id, action, table_name,
                                        record_id=None, old_data=None, new_data=None):
            await db.execute(
                text("""
                    INSERT INTO audit_logs (tenant_id, user_id, action, table_name, record_id, old_data, new_data)
                    VALUES (:tenant_id, :user_id, :action, :table_name, :record_id, :old_data, :new_data)
                """),
                {
                    "tenant_id": tenant_id, "user_id": user_id, "action": action,
                    "table_name": table_name, "record_id": record_id,
                    "old_data": json.dumps(old_data, default=str) if old_data else None,
                    "new_data": json.dumps(new_data, ensure_ascii=False, default=str) if new_data else None,
                },
            )
        return mock_record_audit_log

ORIGIN = "https://app.salesanchor.jp"
AUTH_PATH = "/api/v1/auth"
USER_ID = 2101
OTHER_USER_ID = 2102
EMAIL = "reset-target@example.com"
OLD_PASSWORD = "old password for the test user 1"
NEW_PASSWORD = "brand new long password 2026 ok"
TEST_USER_ID_FLOOR = 2000

_USERS = sa.table("users", sa.column("id"))
_REFRESH = sa.table("auth_refresh_tokens", sa.column("id"))
_RESET = sa.table("password_reset_tokens", sa.column("id"), sa.column("user_id"))
_AUDIT = sa.table("audit_logs", sa.column("id"), sa.column("user_id"))


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("AUTH_JWT_SECRET_PREVIOUS", raising=False)
    monkeypatch.delenv("AUTH_RP_ORIGIN", raising=False)
    monkeypatch.setenv("AUTH_PASSWORD_RESET_ALLOWLIST", EMAIL)


@pytest.fixture(autouse=True)
def no_redis():
    with patch("app.routers.auth.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.routers.auth.record_auth_failure", new=AsyncMock()), \
         patch("app.routers.auth.count_password_reset_request", new=AsyncMock(return_value=1)):
        yield


@pytest.fixture(autouse=True)
def noop_audit():
    with patch("app.routers.auth.record_audit_log", new=_make_noop_audit_log()):
        yield


@pytest.fixture
def sender():
    with patch("app.routers.auth.send_password_reset_email", new=MagicMock()) as m:
        yield m


@pytest.fixture(autouse=True)
async def cleanup(db_session):
    yield
    await db_session.rollback()
    await db_session.execute(sa.delete(_RESET).where(_RESET.c.user_id >= TEST_USER_ID_FLOOR))
    await db_session.execute(sa.delete(_AUDIT).where(_AUDIT.c.user_id >= TEST_USER_ID_FLOOR))
    await db_session.execute(sa.delete(_REFRESH))
    await db_session.execute(sa.delete(_USERS).where(_USERS.c.id >= TEST_USER_ID_FLOOR))
    await db_session.commit()


@pytest.fixture
async def http(db_session):
    from app.database import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://app.salesanchor.jp") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


async def _insert_user(db, *, user_id=USER_ID, email=EMAIL, is_active=True, hash_value=None, **extra):
    cols = {
        "id": user_id, "tenant_id": 999, "username": f"u{user_id}", "email": email,
        "is_active": is_active, "password_argon2_hash": hash_value,
    }
    cols.update(extra)
    names = ", ".join(cols)
    marks = ", ".join(f":{k}" for k in cols)
    await db.execute(text(f"INSERT INTO users ({names}) VALUES ({marks})"), cols)
    await db.commit()


async def _insert_token(db, raw, *, user_id=USER_ID, purpose="reset", expires_in=timedelta(minutes=30), used=False):
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "INSERT INTO password_reset_tokens (user_id, purpose, token_hash, expires_at, used_at, created_at) "
            "VALUES (:u, :p, :h, :e, :used, :c)"
        ),
        {
            "u": user_id, "p": purpose, "h": self_tokens._hash_token(raw),
            "e": now + expires_in, "used": now if used else None, "c": now,
        },
    )
    await db.commit()


async def _insert_refresh(db, *, user_id=USER_ID, suffix="a"):
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "INSERT INTO auth_refresh_tokens (user_id, token_hash, family_id, family_created_at, expires_at, created_at) "
            "VALUES (:u, :h, :f, :n, :e, :n)"
        ),
        {"u": user_id, "h": self_tokens._hash_token(f"refresh-{user_id}-{suffix}"), "f": f"fam-{suffix}",
         "n": now, "e": now + timedelta(days=30)},
    )
    await db.commit()


async def _scalar(db, sql, **params):
    return (await db.execute(text(sql), params)).scalar_one()


async def _row(db, sql, **params):
    return (await db.execute(text(sql), params)).first()


async def _request(http, email=EMAIL, origin=ORIGIN):
    headers = {"origin": origin} if origin else {}
    return await http.post(f"{AUTH_PATH}/password-reset/request", json={"email": email}, headers=headers)


async def _confirm(http, token, password=NEW_PASSWORD, origin=ORIGIN):
    headers = {"origin": origin} if origin else {}
    return await http.post(
        f"{AUTH_PATH}/password-reset/confirm", json={"token": token, "new_password": password}, headers=headers
    )


# ── request ──────────────────────────────────────────────────

async def test_request_allowlisted_active_user_sends(http, db_session, sender):
    await _insert_user(db_session)
    resp = await _request(http)
    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}
    rows = (await db_session.execute(text(
        "SELECT purpose, expires_at, used_at, created_at FROM password_reset_tokens WHERE user_id = :u"
    ), {"u": USER_ID})).all()
    assert len(rows) == 1 and rows[0].purpose == "reset" and rows[0].used_at is None
    span = self_tokens._as_utc(rows[0].expires_at) - self_tokens._as_utc(rows[0].created_at)
    assert timedelta(minutes=29) <= span <= timedelta(minutes=31)
    sender.assert_called_once()
    to_addr, url = sender.call_args.args
    assert to_addr == EMAIL
    assert url.startswith("https://app.salesanchor.jp/reset-password?token=")


async def test_request_empty_allowlist_firebase_sends_nothing(http, db_session, sender, monkeypatch):
    monkeypatch.setenv("AUTH_PASSWORD_RESET_ALLOWLIST", "")
    await _insert_user(db_session)
    resp = await _request(http)
    assert resp.status_code == 200 and resp.json() == {"status": "accepted"}
    assert await _scalar(db_session, "SELECT COUNT(*) FROM password_reset_tokens WHERE user_id = :u", u=USER_ID) == 0
    sender.assert_not_called()


async def test_request_unset_allowlist_sends_nothing(http, db_session, sender, monkeypatch):
    monkeypatch.delenv("AUTH_PASSWORD_RESET_ALLOWLIST", raising=False)
    await _insert_user(db_session)
    resp = await _request(http)
    assert resp.status_code == 200
    sender.assert_not_called()


async def test_request_unknown_and_inactive_get_same_response(http, db_session, sender):
    await _insert_user(db_session, is_active=False)
    ok = await _request(http)  # 許可リストに載っているが is_active=false
    unknown = await _request(http, email="nobody@example.com")
    assert ok.status_code == unknown.status_code == 200
    assert ok.json() == unknown.json() == {"status": "accepted"}
    assert await _scalar(db_session, "SELECT COUNT(*) FROM password_reset_tokens") == 0
    sender.assert_not_called()


async def test_request_self_provider_sends_without_allowlist(http, db_session, sender, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    monkeypatch.setenv("AUTH_PASSWORD_RESET_ALLOWLIST", "")
    await _insert_user(db_session)
    resp = await _request(http)
    assert resp.status_code == 200
    sender.assert_called_once()


async def test_request_fourth_is_429_even_for_unknown_email(http, db_session, sender):
    counter = {"n": 0}

    async def _count(_email):
        counter["n"] += 1
        return counter["n"]

    with patch("app.routers.auth.count_password_reset_request", new=_count):
        statuses = [(await _request(http, email="nobody@example.com")).status_code for _ in range(4)]
    assert statuses == [200, 200, 200, 429]


async def test_wrong_origin_is_403_for_both(http, db_session, sender):
    assert (await _request(http, origin="https://evil.example")).status_code == 403
    assert (await _confirm(http, "whatever", origin="https://evil.example")).status_code == 403
    assert (await _request(http, origin=None)).status_code == 403


async def test_second_request_invalidates_first_token(http, db_session, sender):
    await _insert_user(db_session)
    await _request(http)
    await _request(http)
    assert sender.call_count == 2
    first_url, second_url = sender.call_args_list[0].args[1], sender.call_args_list[1].args[1]
    first_raw, second_raw = (u.split("token=", 1)[1] for u in (first_url, second_url))
    assert (await _confirm(http, first_raw)).status_code == 400
    assert (await _confirm(http, second_raw)).status_code == 200


# ── confirm ──────────────────────────────────────────────────

async def test_confirm_success(http, db_session):
    await _insert_user(db_session, hash_value=passwords.hash_password(OLD_PASSWORD),
                       failed_login_count=5, locked_until=datetime.now(timezone.utc) + timedelta(minutes=10))
    await _insert_refresh(db_session, suffix="a")
    await _insert_refresh(db_session, suffix="b")
    await _insert_token(db_session, "good-token")

    resp = await _confirm(http, "good-token")

    assert resp.status_code == 200
    assert resp.json() == {"status": "password_updated"}
    assert "set-cookie" not in resp.headers
    assert "access_token" not in resp.text
    row = await _row(db_session,
                     "SELECT password_argon2_hash, password_changed_at, failed_login_count, locked_until "
                     "FROM users WHERE id = :id", id=USER_ID)
    assert passwords.verify_password(row.password_argon2_hash, NEW_PASSWORD) is True
    assert row.password_changed_at is not None
    assert row.failed_login_count == 0 and row.locked_until is None
    assert await _scalar(db_session,
                         "SELECT COUNT(*) FROM auth_refresh_tokens WHERE user_id = :u AND revoked_at IS NULL",
                         u=USER_ID) == 0
    assert await _scalar(db_session,
                         "SELECT COUNT(*) FROM audit_logs WHERE table_name='users' AND record_id=:uid "
                         "AND new_data LIKE '%password_reset_confirmed%'", uid=USER_ID) == 1


async def test_confirm_keeps_other_users_sessions(http, db_session):
    await _insert_user(db_session)
    await _insert_user(db_session, user_id=OTHER_USER_ID, email="other-reset@example.com")
    await _insert_refresh(db_session, user_id=OTHER_USER_ID, suffix="o")
    await _insert_token(db_session, "good-token")
    assert (await _confirm(http, "good-token")).status_code == 200
    assert await _scalar(db_session,
                         "SELECT COUNT(*) FROM auth_refresh_tokens WHERE user_id = :u AND revoked_at IS NULL",
                         u=OTHER_USER_ID) == 1


async def test_confirm_token_single_use_expired_and_garbage_same_body(http, db_session):
    await _insert_user(db_session)
    await _insert_token(db_session, "once-token")
    await _insert_token(db_session, "expired-token", expires_in=timedelta(minutes=-1))
    assert (await _confirm(http, "once-token")).status_code == 200
    second = await _confirm(http, "once-token")
    expired = await _confirm(http, "expired-token")
    garbage = await _confirm(http, "no-such-token")
    assert second.status_code == expired.status_code == garbage.status_code == 400
    assert second.json() == expired.json() == garbage.json() == {"detail": "invalid_or_expired_token"}


async def test_confirm_short_password_is_422_and_token_untouched(http, db_session):
    await _insert_user(db_session)
    await _insert_token(db_session, "good-token")
    resp = await _confirm(http, "good-token", password="short")
    assert resp.status_code == 422
    assert resp.json() == {"detail": "password_too_short"}
    assert await _scalar(db_session, "SELECT COUNT(*) FROM password_reset_tokens WHERE used_at IS NULL") == 1
    assert (await _confirm(http, "good-token")).status_code == 200


async def test_confirm_invite_token_works(http, db_session):
    await _insert_user(db_session)
    await _insert_token(db_session, "invite-token", purpose="invite", expires_in=timedelta(hours=72))
    resp = await _confirm(http, "invite-token")
    assert resp.status_code == 200
    assert await _scalar(db_session, "SELECT COUNT(*) FROM audit_logs WHERE new_data LIKE '%\"invite\"%'") == 1


async def test_confirm_inactive_user_consumes_token_and_400(http, db_session):
    await _insert_user(db_session, is_active=False)
    await _insert_token(db_session, "good-token")
    resp = await _confirm(http, "good-token")
    assert resp.status_code == 400 and resp.json() == {"detail": "invalid_or_expired_token"}
    assert await _scalar(db_session, "SELECT COUNT(*) FROM password_reset_tokens WHERE used_at IS NULL") == 0


async def test_confirm_rate_limited_is_429(http, db_session):
    with patch("app.routers.auth.check_auth_rate_limit", new=AsyncMock(return_value=True)):
        resp = await _confirm(http, "x")
    assert resp.status_code == 429


# ── 本番設定のまま（firebase・秘密なし）でも 404 にならない ─────────

async def test_endpoints_not_404_with_firebase_and_no_secret(http, db_session, sender):
    assert self_tokens.is_issuance_enabled() is False
    assert (await _request(http)).status_code == 200
    assert (await _confirm(http, "x")).status_code == 400
