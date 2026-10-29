"""自社ログインの心臓部（ADR-1013 便2）のテスト。SQLite で動かす。"""

import base64
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import text
from starlette.requests import Request

from app.auth import passwords, self_tokens

# RETURNING のために SQLite 3.35 以上が必要（満たさなければ skip ではなく失敗させる）
assert sqlite3.sqlite_version_info >= (3, 35), "SQLite 3.35+ is required for RETURNING"

SECRET = "test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
OTHER_SECRET = "other-secret-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
ORIGIN = "https://app.salesanchor.jp"
PASSWORD = "correct horse battery staple"
USER_ID = 2001
EMAIL = "self-login@example.com"
AUTH_PATH = "/api/v1/auth"
TEST_USER_ID_FLOOR = 2000  # このファイルのユーザーは id >= 2000（既存テストの 999 とぶつからない）

_USERS = sa.table("users", sa.column("id"))
_REFRESH = sa.table("auth_refresh_tokens", sa.column("id"))


@pytest.fixture(autouse=True)
def self_auth_env(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    monkeypatch.setenv("AUTH_JWT_SECRET", SECRET)
    monkeypatch.delenv("AUTH_JWT_SECRET_PREVIOUS", raising=False)
    monkeypatch.delenv("AUTH_RP_ORIGIN", raising=False)
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)


@pytest.fixture(autouse=True)
def no_redis():
    with patch("app.routers.auth.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.routers.auth.record_auth_failure", new=AsyncMock()), \
         patch("app.routers.auth.blacklist_token", new=AsyncMock(return_value=True)):
        yield


@pytest.fixture
def password_hash():
    return passwords.hash_password(PASSWORD)


async def _insert_user(db, *, hash_value, is_active=True, user_id=USER_ID, email=EMAIL, **extra):
    cols = {
        "id": user_id, "tenant_id": 999, "username": f"u{user_id}", "email": email,
        "is_active": is_active, "password_argon2_hash": hash_value,
    }
    cols.update(extra)
    names = ", ".join(cols)
    marks = ", ".join(f":{k}" for k in cols)
    await db.execute(text(f"INSERT INTO users ({names}) VALUES ({marks})"), cols)
    await db.commit()


@pytest.fixture(autouse=True)
async def cleanup_self_auth(db_session):
    """このテストが commit した行を、テスト後に消す（SQLAlchemy の delete 構文）。"""
    yield
    await db_session.rollback()
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


async def _login(http, password=PASSWORD, email=EMAIL, origin=ORIGIN):
    headers = {"origin": origin} if origin else {}
    return await http.post(f"{AUTH_PATH}/login", json={"email": email, "password": password}, headers=headers)


async def _row(db, sql, **params):
    return (await db.execute(text(sql), params)).first()


# ── 1. パスワード ────────────────────────────────────────────

def test_hash_then_verify_true_and_wrong_false(password_hash):
    assert passwords.verify_password(password_hash, PASSWORD) is True
    assert passwords.verify_password(password_hash, "wrong") is False


def test_verify_broken_hash_returns_false_without_exception():
    assert passwords.verify_password("not-a-hash", PASSWORD) is False


def test_verify_none_hash_returns_false():
    assert passwords.verify_password(None, PASSWORD) is False


def test_needs_rehash_false_for_current_parameters(password_hash):
    assert passwords.needs_rehash(password_hash) is False


# ── 2. login 成功 ────────────────────────────────────────────

async def test_login_success_returns_token_and_cookie(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash, failed_login_count=3)

    resp = await _login(http)

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    claims = jwt.get_unverified_claims(body["access_token"])
    assert claims["iss"] == "salesanchor" and claims["sub"] == str(USER_ID) and claims["amr"] == ["pwd"]
    cookie = resp.headers["set-cookie"].lower()
    assert "sa_refresh=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie
    row = await _row(db_session, "SELECT last_login, failed_login_count FROM users WHERE id = :id", id=USER_ID)
    assert row.last_login is not None
    assert row.failed_login_count == 0


# ── 3. 失敗の文言は 1 種類 ─────────────────────────────────────

async def test_all_failure_kinds_return_same_401(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    await _insert_user(db_session, hash_value=password_hash, user_id=2002, email="inactive@example.com", is_active=False)
    await _insert_user(db_session, hash_value=None, user_id=2003, email="nopass@example.com")

    responses = [
        await _login(http, password="wrong"),
        await _login(http, email="ghost@example.com"),
        await _login(http, email="inactive@example.com"),
        await _login(http, email="nopass@example.com"),
    ]

    assert [r.status_code for r in responses] == [401, 401, 401, 401]
    assert {r.json()["detail"] for r in responses} == {"invalid_credentials"}


# ── 4. 口座ロック ────────────────────────────────────────────

async def test_ten_failures_lock_then_expiry_allows_login(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)

    for _ in range(self_tokens.LOGIN_FAIL_LIMIT):
        assert (await _login(http, password="wrong")).status_code == 401
    row = await _row(db_session, "SELECT locked_until, failed_login_count FROM users WHERE id = :id", id=USER_ID)
    assert row.locked_until is not None
    assert row.failed_login_count == 0
    assert (await _login(http)).status_code == 401  # 正しいパスワードでもロック中

    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.execute(text("UPDATE users SET locked_until = :t WHERE id = :id"), {"t": past, "id": USER_ID})
    await db_session.commit()
    assert (await _login(http)).status_code == 200


# ── 5・6. 無効時 404・Origin 403 ──────────────────────────────

async def test_login_and_refresh_404_when_provider_firebase(http, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")

    assert (await _login(http)).status_code == 404
    assert (await http.post(f"{AUTH_PATH}/refresh", headers={"origin": ORIGIN})).status_code == 404


async def test_login_and_refresh_403_when_origin_wrong_or_missing(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)

    assert (await _login(http, origin="https://salesanchor.jp")).status_code == 403
    assert (await _login(http, origin=None)).status_code == 403
    assert (await http.post(f"{AUTH_PATH}/refresh", headers={"origin": "https://evil.example"})).status_code == 403
    assert (await http.post(f"{AUTH_PATH}/refresh")).status_code == 403


# ── 7. refresh ───────────────────────────────────────────────

def _set_refresh_cookie_on(http, cookie):
    http.cookies.clear()
    http.cookies.set("sa_refresh", cookie, domain="app.salesanchor.jp", path=self_tokens.REFRESH_COOKIE_PATH)


async def _refresh(http, cookie):
    _set_refresh_cookie_on(http, cookie)
    return await http.post(f"{AUTH_PATH}/refresh", headers={"origin": ORIGIN})


async def _login_cookie(http):
    resp = await _login(http)
    assert resp.status_code == 200
    return resp.cookies.get("sa_refresh")


async def test_refresh_rotates_and_old_cookie_is_rejected(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    first = await _login_cookie(http)

    ok = await _refresh(http, first)

    assert ok.status_code == 200
    assert "amr" not in jwt.get_unverified_claims(ok.json()["access_token"])
    second = ok.cookies.get("sa_refresh")
    assert second and second != first
    assert (await _refresh(http, first)).status_code == 401


async def test_reused_cookie_revokes_whole_family(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    first = await _login_cookie(http)
    second = (await _refresh(http, first)).cookies.get("sa_refresh")
    assert second

    assert (await _refresh(http, first)).status_code == 401  # 使い回し

    assert (await _refresh(http, second)).status_code == 401
    live = await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert live.n == 0


async def test_second_refresh_with_same_cookie_revokes_family(http, db_session, password_hash):
    """同時タブの仕様の固定: 2 本目は使い回し扱いで組ごと失効する。"""
    await _insert_user(db_session, hash_value=password_hash)
    first = await _login_cookie(http)

    assert (await _refresh(http, first)).status_code == 200
    assert (await _refresh(http, first)).status_code == 401

    total = await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens")
    live = await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert total.n == 2
    assert live.n == 0


async def test_refresh_rejected_after_absolute_30_days(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    cookie = await _login_cookie(http)
    old = datetime.now(timezone.utc) - timedelta(days=31)
    await db_session.execute(
        text("UPDATE auth_refresh_tokens SET family_created_at = :t, expires_at = :e"),
        {"t": old, "e": old + self_tokens.REFRESH_ABSOLUTE_TTL},
    )
    await db_session.commit()

    assert (await _refresh(http, cookie)).status_code == 401


async def test_refresh_expiry_is_not_extended_by_rotation(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    first = await _login_cookie(http)
    assert (await _refresh(http, first)).status_code == 200

    rows = await _row(
        db_session,
        "SELECT count(*) AS total, count(DISTINCT expires_at) AS distinct_expiry FROM auth_refresh_tokens",
    )
    assert rows.total == 2
    assert rows.distinct_expiry == 1


async def test_refresh_rejected_when_password_changed_after_issue(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    cookie = await _login_cookie(http)
    await db_session.execute(
        text("UPDATE users SET password_changed_at = :t WHERE id = :id"),
        {"t": datetime.now(timezone.utc) + timedelta(minutes=1), "id": USER_ID},
    )
    await db_session.commit()

    assert (await _refresh(http, cookie)).status_code == 401


async def test_refresh_without_cookie_is_401(http):
    resp = await http.post(f"{AUTH_PATH}/refresh", headers={"origin": ORIGIN})
    assert resp.status_code == 401


# ── 8. logout ────────────────────────────────────────────────

async def test_logout_revokes_refresh_and_clears_cookie(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    login = await _login(http)
    cookie = login.cookies.get("sa_refresh")
    assert cookie

    _set_refresh_cookie_on(http, cookie)
    resp = await http.post(
        f"{AUTH_PATH}/logout",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert resp.status_code == 200
    set_cookie = resp.headers["set-cookie"].lower()
    assert "sa_refresh=" in set_cookie and "max-age=0" in set_cookie
    live = await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert live.n == 0
    assert (await _refresh(http, cookie)).status_code == 401


async def test_logout_clear_cookie_has_same_attributes_as_set_cookie(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    login = await _login(http)
    cookie = login.cookies.get("sa_refresh")
    _set_refresh_cookie_on(http, cookie)

    resp = await http.post(
        f"{AUTH_PATH}/logout",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    set_cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "max-age=0" in set_cookie
    assert self_tokens.cookie_secure() is True
    assert "secure" in set_cookie


# ── 9. get_current_user の自社トークン ───────────────────────────

def _request():
    return Request({"type": "http", "headers": [], "client": ("203.0.113.9", 1234)})


async def _current_user(db, token):
    from app.auth.dependencies import get_current_user

    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with patch("app.auth.dependencies._init_firebase"), \
         patch("app.auth.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)), \
         patch("app.auth.dependencies.get_cached_jwt", new=AsyncMock(return_value=None)), \
         patch("app.auth.dependencies.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.auth.dependencies.record_auth_failure", new=AsyncMock()), \
         patch("app.auth.dependencies.cache_jwt_result", new=AsyncMock()):
        return await get_current_user(_request(), cred, db)


def _token(secret=SECRET, *, email=EMAIL, iat_offset=0, kid_secret=None, user_id=USER_ID):
    now = int(datetime.now(timezone.utc).timestamp()) + iat_offset
    claims = {"iss": "salesanchor", "sub": str(user_id), "email": email, "jti": "j1", "iat": now, "exp": now + 900}
    headers = {"kid": self_tokens._kid(kid_secret or secret)}
    return jwt.encode(claims, secret, algorithm="HS256", headers=headers)


async def test_get_current_user_accepts_self_token(db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)

    user = await _current_user(db_session, _token())

    assert user.id == USER_ID and user.email == EMAIL


async def test_get_current_user_rejects_token_signed_with_other_key(db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)

    with pytest.raises(HTTPException) as exc:
        await _current_user(db_session, _token(OTHER_SECRET, kid_secret=SECRET))
    assert exc.value.status_code == 401


async def test_get_current_user_accepts_previous_key(db_session, password_hash, monkeypatch):
    await _insert_user(db_session, hash_value=password_hash)
    monkeypatch.setenv("AUTH_JWT_SECRET_PREVIOUS", OTHER_SECRET)

    user = await _current_user(db_session, _token(OTHER_SECRET))

    assert user.id == USER_ID


async def test_get_current_user_rejects_email_mismatch(db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)

    with pytest.raises(HTTPException) as exc:
        await _current_user(db_session, _token(email="someone-else@example.com"))
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_token_issued_before_password_change(db_session, password_hash):
    changed = datetime.now(timezone.utc)
    await _insert_user(db_session, hash_value=password_hash, password_changed_at=changed)

    with pytest.raises(HTTPException) as exc:
        await _current_user(db_session, _token(iat_offset=-60))
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_self_token_without_secret(db_session, password_hash, monkeypatch):
    await _insert_user(db_session, hash_value=password_hash)
    token = _token()
    monkeypatch.delenv("AUTH_JWT_SECRET")

    with pytest.raises(HTTPException) as exc:
        await _current_user(db_session, token)
    assert exc.value.status_code == 401


def _token_with_iat(iat, *, has_iat=True):
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {"iss": "salesanchor", "sub": str(USER_ID), "email": EMAIL, "jti": "j1", "exp": now + 900}
    if has_iat:
        claims["iat"] = iat
    return jwt.encode(claims, SECRET, algorithm="HS256", headers={"kid": self_tokens._kid(SECRET)})


@pytest.mark.parametrize("token", [
    _token_with_iat(None, has_iat=False),
    _token_with_iat("not-a-number"),
    _token_with_iat(10**30),
], ids=["no-iat", "string-iat", "huge-iat"])
async def test_get_current_user_rejects_invalid_iat_with_401(db_session, password_hash, token):
    await _insert_user(db_session, hash_value=password_hash)

    with pytest.raises(HTTPException) as exc:
        await _current_user(db_session, token)
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_alg_none(db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    now = int(datetime.now(timezone.utc).timestamp())

    def b64(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    header = {"alg": "none", "typ": "JWT", "kid": self_tokens._kid(SECRET)}
    claims = {"iss": "salesanchor", "sub": str(USER_ID), "email": EMAIL, "jti": "j", "iat": now, "exp": now + 900}
    forged = f"{b64(header)}.{b64(claims)}."

    with pytest.raises(HTTPException) as exc:
        await _current_user(db_session, forged)
    assert exc.value.status_code == 401


# ── 10. 設定検査 ─────────────────────────────────────────────

def test_validate_settings_accepts_valid_self_config():
    assert self_tokens.validate_settings() is None


def test_validate_settings_accepts_default_firebase_without_secret(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
    monkeypatch.delenv("AUTH_JWT_SECRET")
    assert self_tokens.validate_settings() is None


def test_validate_settings_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "okta")
    with pytest.raises(RuntimeError):
        self_tokens.validate_settings()


def test_validate_settings_rejects_self_without_secret(monkeypatch):
    monkeypatch.delenv("AUTH_JWT_SECRET")
    with pytest.raises(RuntimeError):
        self_tokens.validate_settings()


def test_validate_settings_rejects_short_secret_without_leaking_it(monkeypatch):
    monkeypatch.setenv("AUTH_JWT_SECRET", "short-secret-value")
    with pytest.raises(RuntimeError) as exc:
        self_tokens.validate_settings()
    assert "short-secret-value" not in str(exc.value)


def test_validate_settings_rejects_short_previous_secret(monkeypatch):
    monkeypatch.setenv("AUTH_JWT_SECRET_PREVIOUS", "tiny")
    with pytest.raises(RuntimeError):
        self_tokens.validate_settings()


# ── 10. パスワード変更（便4a） ────────────────────────────────

NEW_PASSWORD = "brand new long password 2026 ok"


@pytest.fixture
def as_user():
    """get_current_user を差し替える（認証そのものは §9 で確かめ済み）。"""
    from types import SimpleNamespace

    from app.auth.dependencies import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=USER_ID)
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def noop_audit():
    with patch("app.routers.auth.record_audit_log", new=AsyncMock()):
        yield


async def _change(http, current=PASSWORD, new=NEW_PASSWORD, origin=ORIGIN):
    headers = {"origin": origin} if origin else {}
    return await http.post(
        f"{AUTH_PATH}/password/change", json={"current_password": current, "new_password": new}, headers=headers
    )


async def test_password_change_success_issues_new_token_and_revokes_old_refresh(
    http, db_session, password_hash, as_user
):
    await _insert_user(db_session, hash_value=password_hash)
    old_cookie = await _login_cookie(http)

    resp = await _change(http)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "password_updated"
    # 新アクセストークンで保護された口（get_current_user）が通る
    user = await _current_user(db_session, body["access_token"])
    assert user.id == USER_ID
    # 今の端末には新しい更新用 Cookie が出る
    new_cookie = resp.cookies.get("sa_refresh")
    assert new_cookie and new_cookie != old_cookie
    assert (await _refresh(http, new_cookie)).status_code == 200
    # 古い更新用トークンは即時に失効
    assert (await _refresh(http, old_cookie)).status_code == 401
    row = await _row(db_session, "SELECT password_argon2_hash, password_changed_at FROM users WHERE id = :id", id=USER_ID)
    assert passwords.verify_password(row.password_argon2_hash, NEW_PASSWORD) is True
    assert self_tokens._as_utc(row.password_changed_at).microsecond == 0


async def test_password_change_rejects_old_access_token_when_cache_is_empty(
    http, db_session, password_hash, as_user
):
    """保持（Redis の 300 秒）が空の状態では、変更前のアクセストークンは 401（保持中は最大 300 秒通る＝F31）。"""
    await _insert_user(db_session, hash_value=password_hash)
    # iat は秒単位なので、変更時刻（秒に切り捨て）より確実に前にする
    old_token = _token(iat_offset=-5)
    assert (await _current_user(db_session, old_token)).id == USER_ID

    assert (await _change(http)).status_code == 200

    with pytest.raises(HTTPException) as exc:
        await _current_user(db_session, old_token)
    assert exc.value.status_code == 401


async def test_password_change_wrong_current_counts_failure_and_returns_400(
    http, db_session, password_hash, as_user
):
    await _insert_user(db_session, hash_value=password_hash)

    resp = await _change(http, current="not the right password")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_credentials"
    row = await _row(db_session, "SELECT failed_login_count FROM users WHERE id = :id", id=USER_ID)
    assert row.failed_login_count == 1


async def test_password_change_short_new_password_is_422(http, db_session, password_hash, as_user):
    await _insert_user(db_session, hash_value=password_hash)

    resp = await _change(http, new="x" * 14)

    assert resp.status_code == 422
    assert resp.json()["detail"] == "password_too_short"


async def test_password_change_wrong_origin_is_403(http, db_session, password_hash, as_user):
    await _insert_user(db_session, hash_value=password_hash)

    assert (await _change(http, origin="https://salesanchor.jp")).status_code == 403
    assert (await _change(http, origin=None)).status_code == 403


async def test_password_change_user_without_hash_is_400(http, db_session, as_user):
    await _insert_user(db_session, hash_value=None)

    resp = await _change(http)

    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_credentials"


async def test_password_change_firebase_revokes_refresh_but_issues_nothing(
    http, db_session, password_hash, as_user, monkeypatch
):
    await _insert_user(db_session, hash_value=password_hash)
    cookie = await _login_cookie(http)
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)

    resp = await _change(http)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "password_updated"
    assert body["access_token"] is None
    assert "sa_refresh" not in resp.headers.get("set-cookie", "")
    live = await _row(
        db_session,
        "SELECT COUNT(*) AS n FROM auth_refresh_tokens WHERE user_id = :id AND revoked_at IS NULL",
        id=USER_ID,
    )
    assert live.n == 0
    assert cookie
