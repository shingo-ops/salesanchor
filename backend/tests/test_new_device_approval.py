"""知らない機械からのログインを、いつもの機械で許可するまで止める仕組み（ADR-1055 段A）のテスト。SQLite で動かす。

設計書 docs/handoff/auth-new-device-approval/design.md §6 の K1〜K9 と D4・D5・D11・A2（off は今と同じ）を確かめる。
段W（web push）の項目は含めない。記録（K9）は、middleware が書く先 app.middleware.audit.AsyncSessionLocal を
受けた SQL と値を覚えるだけの偽物に差し替えて確かめる（SQLite に auth_events は無い）。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import text

from app.auth import devices, geo, passwords, recovery_codes, self_tokens

assert sqlite3.sqlite_version_info >= (3, 35), "SQLite 3.35+ is required for RETURNING"

SECRET = "test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
ORIGIN = "https://app.salesanchor.jp"
PASSWORD = "correct horse battery staple"
USER_ID = 2101
OTHER_USER_ID = 2102
ADMIN_ID = 2103
EMAIL = "nd-user@example.com"
OTHER_EMAIL = "nd-other@example.com"
ADMIN_EMAIL = "nd-admin@example.com"
AUTH = "/api/v1/auth"
FLOOR = 2100  # このファイルのユーザーは id >= 2100

_T = {
    name: sa.table(name, sa.column("id"))
    for name in (
        "users",
        "auth_refresh_tokens",
        "user_trusted_devices",
        "auth_login_requests",
        "user_recovery_codes",
        "password_reset_tokens",
    )
}


# ── 足場 ─────────────────────────────────────────────────────

AUDIT_SINK: list[tuple[str, dict]] = []
REVOKED_SIDS: set[str] = set()


class _FakeAuditSession:
    """AuditMiddleware が使う DB セッションの偽物。受けた SQL と値を覚えるだけ。"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, stmt, params=None):
        AUDIT_SINK.append((str(stmt), dict(params or {})))

    async def commit(self):
        return None


def _auth_event_rows() -> list[dict]:
    return [p for s, p in AUDIT_SINK if "auth_events" in s]


@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    monkeypatch.setenv("AUTH_JWT_SECRET", SECRET)
    monkeypatch.delenv("AUTH_JWT_SECRET_PREVIOUS", raising=False)
    monkeypatch.delenv("AUTH_RP_ORIGIN", raising=False)
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("AUTH_DEVICE_APPROVAL", raising=False)
    monkeypatch.delenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", raising=False)
    monkeypatch.setenv("GEOIP_DB_PATH", "")


@pytest.fixture
def enforce(monkeypatch):
    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")


@pytest.fixture(autouse=True)
def no_redis_and_spies():
    """Redis・メール・合図・監査の外に出る部分を差し替える。公開の spies を返す。"""
    AUDIT_SINK.clear()
    REVOKED_SIDS.clear()

    async def _mark(sid):
        REVOKED_SIDS.add(sid)

    async def _is_revoked(sid):
        return sid in REVOKED_SIDS

    mail = MagicMock()
    publish = AsyncMock()
    with patch("app.routers.auth.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.routers.auth.record_auth_failure", new=AsyncMock()), \
         patch("app.routers.auth.blacklist_token", new=AsyncMock(return_value=True)), \
         patch("app.routers.auth.record_audit_log", new=AsyncMock()), \
         patch("app.routers.auth.send_new_device_mail", new=mail), \
         patch("app.routers.auth.publish_user_change", new=publish), \
         patch("app.routers.super_admin_login_requests.publish_user_change", new=publish), \
         patch("app.auth.dependencies._init_firebase"), \
         patch("app.auth.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)), \
         patch("app.auth.dependencies.get_cached_jwt", new=AsyncMock(return_value=None)), \
         patch("app.auth.dependencies.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.auth.dependencies.record_auth_failure", new=AsyncMock()), \
         patch("app.auth.dependencies.cache_jwt_result", new=AsyncMock()), \
         patch("app.auth.dependencies.is_family_revoked", new=_is_revoked), \
         patch("app.auth.devices.mark_family_revoked", new=_mark), \
         patch("app.middleware.audit.AsyncSessionLocal", new=lambda: _FakeAuditSession()):
        yield SimpleNamespace(mail=mail, publish=publish)


@pytest.fixture
def spies(no_redis_and_spies):
    return no_redis_and_spies


@pytest.fixture
def password_hash():
    return passwords.hash_password(PASSWORD)


async def _insert_user(
    db, hash_value, *, user_id=USER_ID, email=EMAIL, last_login="2026-10-01 00:00:00", is_super_admin=False
):
    cols = {
        "id": user_id, "tenant_id": 999, "username": f"u{user_id}", "email": email,
        "is_active": True, "password_argon2_hash": hash_value, "is_super_admin": is_super_admin,
        "last_login": last_login,
    }
    names = ", ".join(cols)
    marks = ", ".join(f":{k}" for k in cols)
    await db.execute(text(f"INSERT INTO users ({names}) VALUES ({marks})"), cols)
    await db.commit()


@pytest.fixture(autouse=True)
async def cleanup(db_session):
    yield
    await db_session.rollback()
    for name in ("user_recovery_codes", "auth_login_requests", "auth_refresh_tokens", "user_trusted_devices", "password_reset_tokens"):
        await db_session.execute(sa.delete(_T[name]))
    await db_session.execute(sa.delete(_T["users"]).where(_T["users"].c.id >= FLOOR))
    await db_session.commit()


@pytest.fixture
async def machine(db_session):
    """別々の機械（Cookie の入れ物が別のクライアント）を作る関数。"""
    from app.database import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    clients: list[AsyncClient] = []

    def make() -> AsyncClient:
        client = AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN)
        clients.append(client)
        return client

    yield make
    for c in clients:
        await c.aclose()
    app.dependency_overrides.pop(get_db, None)


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "origin": ORIGIN}


async def _login(client, password=PASSWORD, email=EMAIL, origin=ORIGIN):
    headers = {"origin": origin} if origin else {}
    return await client.post(f"{AUTH}/login", json={"email": email, "password": password}, headers=headers)


async def _poll(client):
    return await client.post(f"{AUTH}/login-requests/poll", headers={"origin": ORIGIN})


async def _row(db, sql, **params):
    return (await db.execute(text(sql), params)).first()


async def _rows(db, sql, **params):
    return (await db.execute(text(sql), params)).all()


def _set_cookies(resp) -> list[str]:
    return [c.lower() for c in resp.headers.get_list("set-cookie")]


async def _first_machine(machine, db, hash_value, **user_kwargs):
    """最初のログインでいつもの機械になった機械 A を用意する（enforce）。(client, access_token) を返す。"""
    await _insert_user(db, hash_value, last_login=None, **user_kwargs)
    a = machine()
    resp = await _login(a, email=user_kwargs.get("email", EMAIL))
    assert resp.status_code == 200, resp.text
    return a, resp.json()["access_token"]


async def _pending_from_new_machine(machine, db, email=EMAIL):
    """知らない機械 B のログイン（202）。(client, request_id, match_number) を返す。"""
    b = machine()
    resp = await _login(b, email=email)
    assert resp.status_code == 202, resp.text
    row = await _row(db, "SELECT id FROM auth_login_requests ORDER BY created_at DESC")
    return b, str(row.id), resp.json()["match_number"]


# ── A2: off（既定）は今のログインと同じ ──────────────────────────

async def test_a2_off_login_is_unchanged_but_carries_sid(machine, db_session, password_hash):
    await _insert_user(db_session, password_hash, last_login=None)
    client = machine()

    resp = await _login(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["token_type"] == "bearer"
    claims = jwt.get_unverified_claims(body["access_token"])
    assert claims["sid"]
    cookies = _set_cookies(resp)
    assert any(c.startswith("sa_refresh=") for c in cookies)
    assert not any(c.startswith("sa_device=") or c.startswith("sa_login_pending=") for c in cookies)
    # 機械の行は増えない・依頼も作らない
    assert (await _row(db_session, "SELECT count(*) AS n FROM user_trusted_devices")).n == 0
    assert (await _row(db_session, "SELECT count(*) AS n FROM auth_login_requests")).n == 0
    refresh = await _row(db_session, "SELECT trusted_device_id, family_id FROM auth_refresh_tokens")
    assert refresh.trusted_device_id is None and refresh.family_id == claims["sid"]


async def test_a2_off_unknown_cookie_machine_is_not_stopped(machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    client = machine()
    client.cookies.set("sa_device", "x" * 43, domain="app.salesanchor.jp", path="/api/v1/auth")

    assert (await _login(client)).status_code == 200


# ── K1: 知らない機械は 202 で止まる ─────────────────────────────

async def test_k1_unknown_machine_gets_202_without_tokens(enforce, machine, db_session, password_hash, spies):
    await _insert_user(db_session, password_hash)
    client = machine()

    resp = await _login(client)

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "device_approval_required"
    assert len(body["match_number"]) == 2 and body["match_number"].isdigit()
    assert body["expires_in"] == 1800
    assert body["has_trusted_device"] is False and body["has_recovery_codes"] is False
    assert "access_token" not in body
    cookies = _set_cookies(resp)
    assert not any(c.startswith("sa_refresh=") for c in cookies)
    pending = [c for c in cookies if c.startswith("sa_login_pending=")]
    assert len(pending) == 1
    for flag in ("httponly", "secure", "samesite=strict", "path=/api/v1/auth/login-requests"):
        assert flag in pending[0]
    assert (await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens")).n == 0
    req = await _row(db_session, "SELECT status, user_id, match_number FROM auth_login_requests")
    assert req.status == "pending" and req.user_id == USER_ID and req.match_number == body["match_number"]
    # 記録: 202 は auth_pending
    event = _auth_event_rows()[-1]
    assert event["event_type"] == "auth_pending"
    assert event["reason"] == "device_approval_required"
    assert event["user_id"] == USER_ID and event["is_new_device"] is True


async def test_k1_pending_cookie_value_is_not_stored_raw(enforce, machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    client = machine()
    resp = await _login(client)
    raw = resp.cookies.get("sa_login_pending")

    assert raw
    row = await _row(db_session, "SELECT pending_token_hash FROM auth_login_requests")
    assert bytes(row.pending_token_hash) == devices.hash_value(raw)


async def test_request_limit_is_5_per_hour(enforce, machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    client = machine()
    for _ in range(5):
        assert (await _login(client)).status_code == 202

    resp = await _login(client)

    assert resp.status_code == 429
    assert resp.json()["detail"] == "too_many_requests"


# ── D5: 一度もログインしていない人の最初のログイン ─────────────────

async def test_d5_first_login_registers_first_trusted_device(enforce, machine, db_session, password_hash, spies):
    await _insert_user(db_session, password_hash, last_login=None)
    client = machine()

    resp = await _login(client)

    assert resp.status_code == 200
    cookies = _set_cookies(resp)
    device_cookie = [c for c in cookies if c.startswith("sa_device=")]
    assert len(device_cookie) == 1
    for flag in ("httponly", "secure", "samesite=strict", "path=/api/v1/auth", "max-age=15552000"):
        assert flag in device_cookie[0]
    dev = await _row(db_session, "SELECT created_via, user_id FROM user_trusted_devices")
    assert dev.created_via == "first_login" and dev.user_id == USER_ID
    refresh = await _row(db_session, "SELECT trusted_device_id FROM auth_refresh_tokens")
    assert refresh.trusted_device_id is not None
    spies.mail.assert_called_once()
    assert _auth_event_rows()[-1]["reason"] == "first_login"


async def test_d5_known_user_with_no_device_is_not_first_login(enforce, machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)  # last_login あり
    assert (await _login(machine())).status_code == 202


async def test_d5_never_logged_in_but_has_device_row_is_stopped(enforce, machine, db_session, password_hash):
    await _insert_user(db_session, password_hash, last_login=None)
    await db_session.execute(
        text(
            "INSERT INTO user_trusted_devices (user_id, token_hash, created_via, revoked_at) "
            "VALUES (:u, :h, 'cli', :r)"
        ),
        {"u": USER_ID, "h": devices.hash_value("a" * 43), "r": datetime.now(timezone.utc)},
    )
    await db_session.commit()

    assert (await _login(machine())).status_code == 202


# ── K2: 知らせ ──────────────────────────────────────────────────

async def test_k2_request_publishes_to_user_and_sends_one_mail(enforce, machine, db_session, password_hash, spies):
    await _insert_user(db_session, password_hash)
    await _insert_user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL)

    resp = await _login(machine())

    assert resp.status_code == 202
    spies.publish.assert_awaited_once()
    assert spies.publish.await_args.args[0] == USER_ID
    assert spies.publish.await_args.args[1] == "auth.login_request"
    spies.mail.assert_called_once()
    assert spies.mail.call_args.args[0] == EMAIL
    kwargs = spies.mail.call_args.kwargs
    assert kwargs["when"] and kwargs["device"]


def test_k2_hub_delivers_user_channel_only_to_that_user():
    from app.realtime.hub import Connection, _targets

    mine = Connection(tenant_id=1, is_super_admin=False, user_id=7)
    other = Connection(tenant_id=1, is_super_admin=False, user_id=8)
    anonymous = Connection(tenant_id=1, is_super_admin=True)

    assert _targets("rt:u:7", mine) is True
    assert _targets("rt:u:7", other) is False
    assert _targets("rt:u:7", anonymous) is False
    assert _targets("rt:u:x", mine) is False


async def test_k2_publish_user_change_uses_user_channel_and_minimal_payload():
    from app.realtime import publisher

    client = MagicMock()
    client.publish = AsyncMock()
    with patch.object(publisher, "_get_async", return_value=client):
        await publisher.publish_user_change(7, "auth.login_request")

    client.publish.assert_awaited_once()
    channel, payload = client.publish.await_args.args
    assert channel == "rt:u:7"
    assert set(__import__("json").loads(payload)) == {"topic", "origin"}


def test_k2_mail_has_no_link_and_includes_time_device_location():
    from app.services import auth_mail

    sent = []

    class _Smtp:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): ...
        def login(self, *a): ...
        def send_message(self, msg): sent.append(msg)

    settings = SimpleNamespace(host="h", port=587, user="u", password="p", mail_from="from@example.com")
    with patch.object(auth_mail, "smtp_settings", return_value=settings), patch.object(auth_mail.smtplib, "SMTP", _Smtp):
        auth_mail.send_new_device_mail("to@example.com", when="2026-11-01 10:00", device="iPhone・Safari", location="Tokyo, Japan")

    assert len(sent) == 1
    body = sent[0].get_payload()[0].get_payload(decode=True).decode("utf-8")
    assert "http" not in body.lower()
    assert "2026-11-01 10:00" in body and "iPhone・Safari" in body and "Tokyo, Japan" in body
    assert "IP Geolocation by DB-IP" in body


# ── K3: 許可して入る ─────────────────────────────────────────────

async def test_k3_correct_number_approves_and_waiting_machine_gets_tokens(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)

    pending = await a.get("/api/v1/login-approvals/pending", headers=_bearer(tok_a))
    assert pending.status_code == 200
    items = pending.json()["items"]
    assert [i["id"] for i in items] == [rid] and number in items[0]["candidates"] and len(items[0]["candidates"]) == 3

    approved = await a.post(f"{AUTH}/login-requests/{rid}/approve", json={"number": number}, headers=_bearer(tok_a))
    assert approved.status_code == 200 and approved.json()["status"] == "approved"

    done = await _poll(b)
    assert done.status_code == 200
    body = done.json()
    assert body["status"] == "completed" and body["access_token"]
    cookies = _set_cookies(done)
    assert any(c.startswith("sa_device=") for c in cookies) and any(c.startswith("sa_refresh=") for c in cookies)
    assert (await _row(db_session, "SELECT count(*) AS n FROM user_trusted_devices")).n == 2
    new_dev = await _row(db_session, "SELECT created_via FROM user_trusted_devices ORDER BY id DESC")
    assert new_dev.created_via == "device_approval"
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "completed"
    assert _auth_event_rows()[-1]["reason"] == "approved_device"
    # last_login が入る
    assert (await _row(db_session, "SELECT last_login FROM users WHERE id = :i", i=USER_ID)).last_login is not None
    # K5: 許可済みの印で再ログインすると 200
    assert (await _login(b)).status_code == 200


async def test_k3_poll_twice_issues_only_once(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    await a.post(f"{AUTH}/login-requests/{rid}/approve", json={"number": number}, headers=_bearer(tok_a))

    first = await _poll(b)
    second = await _poll(b)

    assert first.json().get("access_token")
    assert not second.json().get("access_token")
    rows = await _rows(db_session, "SELECT family_id FROM auth_refresh_tokens WHERE user_id = :u", u=USER_ID)
    assert len(rows) == 2  # A の最初の組 + B の組1つだけ


async def test_k3_other_users_request_is_404_and_unchanged(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    await _insert_user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL)
    b, rid, number = await _pending_from_new_machine(machine, db_session, email=OTHER_EMAIL)

    approve = await a.post(f"{AUTH}/login-requests/{rid}/approve", json={"number": number}, headers=_bearer(tok_a))
    reject = await a.post(f"{AUTH}/login-requests/{rid}/reject", headers=_bearer(tok_a))

    assert approve.status_code == 404 and reject.status_code == 404
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"
    # 他人の依頼は一覧にも出ない
    listed = await a.get("/api/v1/login-approvals/pending", headers=_bearer(tok_a))
    assert listed.json()["items"] == []
    assert (await a.post(f"{AUTH}/login-requests/not-a-uuid/approve", json={"number": "11"}, headers=_bearer(tok_a))).status_code == 404


async def test_k3_token_without_sid_is_403(enforce, machine, db_session, password_hash):
    a, _ = await _first_machine(machine, db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    old_style = self_tokens.create_access_token(USER_ID, EMAIL, "pwd")  # sid なし（本便より前の発行）

    resp = await a.post(f"{AUTH}/login-requests/{rid}/approve", json={"number": number}, headers=_bearer(old_style))

    assert resp.status_code == 403 and resp.json()["detail"] == "session_upgrade_required"
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"


async def test_k3_revoked_device_session_cannot_approve(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    await db_session.execute(text("UPDATE user_trusted_devices SET revoked_at = :n"), {"n": datetime.now(timezone.utc)})
    await db_session.commit()

    resp = await a.post(f"{AUTH}/login-requests/{rid}/approve", json={"number": number}, headers=_bearer(tok_a))

    assert resp.status_code == 403 and resp.json()["detail"] == "device_not_trusted"
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"


async def test_d1_wrong_number_rejects_only_that_request_and_logs_nobody_out(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    wrong = "00" if number != "00" else "01"

    resp = await a.post(f"{AUTH}/login-requests/{rid}/approve", json={"number": wrong}, headers=_bearer(tok_a))

    assert resp.status_code == 200
    assert resp.json() == {"status": "rejected", "reason": "wrong_number"}
    req = await _row(db_session, "SELECT status, reject_reason FROM auth_login_requests")
    assert req.status == "rejected" and req.reject_reason == "wrong_number"
    assert (await _poll(b)).json()["status"] == "rejected"
    # A のログインは生きている
    assert (await a.get(f"{AUTH}/devices", headers=_bearer(tok_a))).status_code == 200
    assert any(e["reason"] == "wrong_number" and e["user_id"] == USER_ID for e in _auth_event_rows())


async def test_k3_expired_request_poll_returns_expired(enforce, machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    await db_session.execute(text("UPDATE auth_login_requests SET expires_at = :p"), {"p": datetime.now(timezone.utc) - timedelta(minutes=1)})
    await db_session.commit()

    resp = await _poll(b)

    assert resp.json()["status"] == "expired"
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "expired"


# ── K4: 「私ではない」 ───────────────────────────────────────────

async def test_k4_reject_revokes_other_sessions_and_keeps_current(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    # 同じ機械 A の別の組（別のタブ・別のログイン）
    second = await _login(a)
    assert second.status_code == 200
    tok_second = second.json()["access_token"]
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    assert (await a.get(f"{AUTH}/devices", headers=_bearer(tok_second))).status_code == 200

    resp = await a.post(f"{AUTH}/login-requests/{rid}/reject", headers=_bearer(tok_a))

    assert resp.status_code == 200 and resp.json()["status"] == "rejected"
    assert (await _poll(b)).json()["status"] == "rejected"
    # 押した組は残り、他の組は失効し、その古いアクセストークンは次の要求で 401
    assert (await a.get(f"{AUTH}/devices", headers=_bearer(tok_a))).status_code == 200
    assert (await a.get(f"{AUTH}/devices", headers=_bearer(tok_second))).status_code == 401
    live = await _rows(db_session, "SELECT family_id FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert len(live) == 1


async def test_k4_approve_after_reject_is_404(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    assert (await a.post(f"{AUTH}/login-requests/{rid}/reject", headers=_bearer(tok_a))).status_code == 200

    resp = await a.post(f"{AUTH}/login-requests/{rid}/approve", json={"number": number}, headers=_bearer(tok_a))

    assert resp.status_code == 404
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "rejected"


# ── K5 / D4: 締切 ───────────────────────────────────────────────

async def _login_off_and_family_created_at(machine, db):
    client = machine()
    resp = await _login(client)
    assert resp.status_code == 200
    row = await _row(db, "SELECT family_created_at FROM auth_refresh_tokens")
    return client, self_tokens._as_utc(row.family_created_at)


async def test_d4_family_before_cutoff_is_bootstrapped_on_refresh(machine, db_session, password_hash, monkeypatch):
    await _insert_user(db_session, password_hash)
    client, created = await _login_off_and_family_created_at(machine, db_session)
    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", (created + timedelta(seconds=1)).isoformat())

    resp = await client.post(f"{AUTH}/refresh", headers={"origin": ORIGIN})

    assert resp.status_code == 200
    assert any(c.startswith("sa_device=") for c in _set_cookies(resp))
    dev = await _row(db_session, "SELECT created_via FROM user_trusted_devices")
    assert dev.created_via == "bootstrap"
    live = await _row(db_session, "SELECT trusted_device_id FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert live.trusted_device_id is not None
    assert _auth_event_rows()[-1]["reason"] == "bootstrap"
    # 2回目の更新は印のある組として通る
    assert (await client.post(f"{AUTH}/refresh", headers={"origin": ORIGIN})).status_code == 200


async def test_d4_family_created_exactly_at_cutoff_is_401(machine, db_session, password_hash, monkeypatch):
    await _insert_user(db_session, password_hash)
    client, created = await _login_off_and_family_created_at(machine, db_session)
    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", created.isoformat())

    resp = await client.post(f"{AUTH}/refresh", headers={"origin": ORIGIN})

    assert resp.status_code == 401
    assert (await _row(db_session, "SELECT count(*) AS n FROM user_trusted_devices")).n == 0
    assert (await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens WHERE revoked_at IS NULL")).n == 0


async def test_d4_without_cutoff_enforce_refresh_of_deviceless_family_is_401(machine, db_session, password_hash, monkeypatch):
    await _insert_user(db_session, password_hash)
    client, _ = await _login_off_and_family_created_at(machine, db_session)
    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")

    assert (await client.post(f"{AUTH}/refresh", headers={"origin": ORIGIN})).status_code == 401


async def test_a2_off_refresh_of_deviceless_family_still_works(machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    client, _ = await _login_off_and_family_created_at(machine, db_session)

    resp = await client.post(f"{AUTH}/refresh", headers={"origin": ORIGIN})

    assert resp.status_code == 200
    assert (await _row(db_session, "SELECT count(*) AS n FROM user_trusted_devices")).n == 0
    assert jwt.get_unverified_claims(resp.json()["access_token"])["sid"]


async def test_refresh_of_revoked_device_family_is_401(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    await db_session.execute(text("UPDATE user_trusted_devices SET revoked_at = :n"), {"n": datetime.now(timezone.utc)})
    await db_session.commit()

    assert (await a.post(f"{AUTH}/refresh", headers={"origin": ORIGIN})).status_code == 401


# ── K6: 予備の合言葉 ─────────────────────────────────────────────

def test_k6_code_format_normalize_and_aliases():
    assert recovery_codes.format_code("ABCD", "EFGHJKMNPQ") == "ABCD-EFGHJ-KMNPQ"
    assert recovery_codes.normalize("abcd-efghj-kmnpq") == ("ABCD", "EFGHJKMNPQ")
    assert recovery_codes.normalize("ABCDEFGHJKMNPQ") == ("ABCD", "EFGHJKMNPQ")
    assert recovery_codes.normalize("OIL0-0000-000000") is not None  # O→0, I/L→1
    assert recovery_codes.normalize("short") is None
    assert recovery_codes.normalize("ABCD-EFGHJ-KMNP!") is None
    assert recovery_codes.normalize(None) is None


async def test_k6_generate_10_hashed_codes_and_use_once(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)

    created = await a.post(f"{AUTH}/recovery-codes", headers=_bearer(tok_a))

    assert created.status_code == 200
    codes = created.json()["codes"]
    assert len(codes) == 10 and len(set(codes)) == 10
    assert (await a.get(f"{AUTH}/recovery-codes/status", headers=_bearer(tok_a))).json() == {"remaining": 10}
    # 生の値は DB に無い（見出しと argon2 だけ）
    rows = await _rows(db_session, "SELECT code_id, code_hash FROM user_recovery_codes")
    assert len(rows) == 10
    for code in codes:
        head, _, rest = code.partition("-")
        body = rest.replace("-", "")
        assert all(body not in (r.code_hash or "") and body != r.code_id for r in rows)
    assert all(r.code_hash.startswith("$argon2") for r in rows)

    b, rid, number = await _pending_from_new_machine(machine, db_session)
    ok = await b.post(f"{AUTH}/login-requests/recovery", json={"code": codes[0].lower()}, headers={"origin": ORIGIN})
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert (await _row(db_session, "SELECT status, decided_via FROM auth_login_requests")).decided_via == "recovery_code"
    assert (await _row(db_session, "SELECT created_via FROM user_trusted_devices ORDER BY id DESC")).created_via == "recovery_code"
    assert _auth_event_rows()[-1]["reason"] == "approved_recovery"
    assert (await a.get(f"{AUTH}/recovery-codes/status", headers=_bearer(tok_a))).json() == {"remaining": 9}

    # 同じ合言葉の2回目は失敗し、口座の失敗回数が1増える
    c = machine()
    assert (await _login(c)).status_code == 202
    again = await c.post(f"{AUTH}/login-requests/recovery", json={"code": codes[0]}, headers={"origin": ORIGIN})
    assert again.status_code == 400 and again.json()["detail"] == "recovery_code_wrong"
    assert (await _row(db_session, "SELECT failed_login_count FROM users WHERE id = :i", i=USER_ID)).failed_login_count == 1


async def test_k6_regenerate_revokes_old_unused_codes(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    first = (await a.post(f"{AUTH}/recovery-codes", headers=_bearer(tok_a))).json()["codes"]
    second = (await a.post(f"{AUTH}/recovery-codes", headers=_bearer(tok_a))).json()["codes"]

    assert set(first).isdisjoint(second)
    assert (await a.get(f"{AUTH}/recovery-codes/status", headers=_bearer(tok_a))).json() == {"remaining": 10}
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    old = await b.post(f"{AUTH}/login-requests/recovery", json={"code": first[0]}, headers={"origin": ORIGIN})
    assert old.status_code == 400
    assert (await _row(db_session, "SELECT count(*) AS n FROM user_recovery_codes WHERE revoked_at IS NOT NULL")).n == 10


async def test_k6_five_wrong_codes_reject_the_request(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    await a.post(f"{AUTH}/recovery-codes", headers=_bearer(tok_a))
    b, rid, number = await _pending_from_new_machine(machine, db_session)

    for i in range(5):
        resp = await b.post(f"{AUTH}/login-requests/recovery", json={"code": "AAAA-AAAAA-AAAAA"}, headers={"origin": ORIGIN})
        assert resp.status_code == 400
    assert resp.json()["detail"] == "request_closed"
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "rejected"
    assert (await _poll(b)).json()["status"] == "rejected"


async def test_k6_recovery_without_pending_cookie_is_400(enforce, machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    resp = await machine().post(f"{AUTH}/login-requests/recovery", json={"code": "AAAA-AAAAA-AAAAA"}, headers={"origin": ORIGIN})
    assert resp.status_code == 400 and resp.json()["detail"] == "request_not_found"


# ── K7: 管理者の許可 ─────────────────────────────────────────────

async def _admin_setup(db, password_hash):
    await _insert_user(db, password_hash)  # 依頼する人
    await _insert_user(db, password_hash, user_id=ADMIN_ID, email=ADMIN_EMAIL, is_super_admin=True)
    return self_tokens.create_access_token(ADMIN_ID, ADMIN_EMAIL, "pwd")


async def test_k7_admin_approves_and_waiting_machine_gets_in(enforce, machine, db_session, password_hash):
    admin_token = await _admin_setup(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    admin = machine()

    listed = await admin.get("/api/v1/super-admin/login-requests?status=pending", headers=_bearer(admin_token))
    assert listed.status_code == 200 and [i["id"] for i in listed.json()["items"]] == [rid]

    with patch("app.routers.super_admin_login_requests._record_auth_audit", new=AsyncMock()) as audit:
        resp = await admin.post(
            f"/api/v1/super-admin/login-requests/{rid}/approve", json={"note": "対面で確認"}, headers=_bearer(admin_token)
        )
    assert resp.status_code == 200
    row = await _row(db_session, "SELECT status, decided_by_user_id, decided_note, decided_via FROM auth_login_requests")
    assert (row.status, row.decided_by_user_id, row.decided_note, row.decided_via) == ("approved", ADMIN_ID, "対面で確認", "admin")
    audit.assert_awaited_once()
    kwargs = audit.await_args.kwargs
    assert kwargs["tenant_id"] == 999 and kwargs["user_id"] == ADMIN_ID and kwargs["record_id"] is None
    assert kwargs["table_name"] == "auth_login_requests" and kwargs["action"] == "update"
    assert kwargs["new_data"]["request_id"] == rid and kwargs["new_data"]["target_user_id"] == USER_ID
    assert "対面" not in str(kwargs["new_data"])

    done = await _poll(b)
    assert done.json()["access_token"]
    assert _auth_event_rows()[-1]["reason"] == "approved_admin"
    assert (await _row(db_session, "SELECT created_via FROM user_trusted_devices ORDER BY id DESC")).created_via == "admin_approval"


async def test_k7_admin_guards(enforce, machine, db_session, password_hash):
    admin_token = await _admin_setup(db_session, password_hash)
    user_token = self_tokens.create_access_token(USER_ID, EMAIL, "pwd")
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    admin = machine()
    url = f"/api/v1/super-admin/login-requests/{rid}/approve"

    # super admin 以外 403
    assert (await admin.post(url, json={"note": "x"}, headers=_bearer(user_token))).status_code == 403
    # note 無し・空は 422
    assert (await admin.post(url, json={}, headers=_bearer(admin_token))).status_code == 422
    assert (await admin.post(url, json={"note": ""}, headers=_bearer(admin_token))).status_code == 422
    # 出どころ違いは 403
    bad_origin = {"Authorization": f"Bearer {admin_token}", "origin": "https://evil.example"}
    assert (await admin.post(url, json={"note": "x"}, headers=bad_origin)).status_code == 403
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"


async def test_k7_admin_cannot_approve_own_request(enforce, machine, db_session, password_hash):
    admin_token = await _admin_setup(db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session, email=ADMIN_EMAIL)

    resp = await machine().post(
        f"/api/v1/super-admin/login-requests/{rid}/approve", json={"note": "自分"}, headers=_bearer(admin_token)
    )

    assert resp.status_code == 403
    assert (await _row(db_session, "SELECT status FROM auth_login_requests")).status == "pending"


# ── K8: 機械の一覧と取り消し ──────────────────────────────────────

async def test_k8_list_and_revoke_device(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    b, rid, number = await _pending_from_new_machine(machine, db_session)
    await a.post(f"{AUTH}/login-requests/{rid}/approve", json={"number": number}, headers=_bearer(tok_a))
    tok_b = (await _poll(b)).json()["access_token"]

    listed = await a.get(f"{AUTH}/devices", headers=_bearer(tok_a))

    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 2
    assert sum(1 for i in items if i["is_current"]) == 1
    for item in items:
        assert item["created_at"] and item["label"] and "created_via" in item and "location" in item
    other = [i for i in items if not i["is_current"]][0]

    gone = await a.delete(f"{AUTH}/devices/{other['id']}", headers=_bearer(tok_a))

    assert gone.status_code == 204
    # 結び付いた組は revoked、その機械のアクセストークンは次の要求で 401
    assert (await b.get(f"{AUTH}/devices", headers=_bearer(tok_b))).status_code == 401
    assert (await b.post(f"{AUTH}/refresh", headers={"origin": ORIGIN})).status_code == 401
    assert (await a.get(f"{AUTH}/devices", headers=_bearer(tok_a))).status_code == 200


async def test_k8_other_users_device_is_404(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    await _insert_user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL, last_login=None)
    o = machine()
    assert (await _login(o, email=OTHER_EMAIL)).status_code == 200
    other_dev = await _row(db_session, "SELECT id FROM user_trusted_devices WHERE user_id = :u", u=OTHER_USER_ID)

    resp = await a.delete(f"{AUTH}/devices/{other_dev.id}", headers=_bearer(tok_a))

    assert resp.status_code == 404
    assert (await _row(db_session, "SELECT revoked_at FROM user_trusted_devices WHERE id = :i", i=other_dev.id)).revoked_at is None


# ── K9: 記録 ───────────────────────────────────────────────────

async def test_k9_events_have_user_reason_and_no_secrets(enforce, machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    client = machine()

    await _login(client, password="wrong password!!")
    await _login(client, email="nobody@example.com")
    await _login(client)  # 知らない機械 → 202

    events = _auth_event_rows()
    reasons = [(e["reason"], e["user_id"]) for e in events]
    assert ("bad_password", USER_ID) in reasons
    assert ("unknown_user", None) in reasons
    assert ("device_approval_required", USER_ID) in reasons
    dumped = " ".join(str(e) for e in events)
    assert "wrong password" not in dumped and PASSWORD not in dumped


async def test_k9_login_success_records_user_and_is_new_device(machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)

    resp = await _login(machine())

    assert resp.status_code == 200
    event = _auth_event_rows()[-1]
    assert event["event_type"] == "auth_success" and event["reason"] == "ok" and event["user_id"] == USER_ID


async def test_k9_known_device_login_records_not_new_device(enforce, machine, db_session, password_hash):
    a, _ = await _first_machine(machine, db_session, password_hash)

    resp = await _login(a)

    assert resp.status_code == 200
    event = _auth_event_rows()[-1]
    assert event["is_new_device"] is False and event["reason"] == "ok"
    assert (await _row(db_session, "SELECT last_used_at FROM user_trusted_devices")).last_used_at is not None


async def test_k9_middleware_reads_request_state_set_inside_the_route():
    """(e) middleware から、口の中で入れた request.state が読める（starlette の request.state は scope["state"] を共有する）。"""
    from app.middleware.audit import AuditMiddleware

    small = FastAPI()
    small.add_middleware(AuditMiddleware)

    @small.post("/api/v1/auth/probe", status_code=202)
    async def probe(request: Request):
        request.state.auth_audit = {
            "user_id": 42, "reason": "device_approval_required", "is_new_device": True, "event_type": "auth_pending",
        }
        return {"ok": True}

    @small.post("/api/v1/auth/plain")
    async def plain():
        return {"ok": True}

    with patch("app.middleware.audit.AsyncSessionLocal", new=lambda: _FakeAuditSession()):
        async with AsyncClient(transport=ASGITransport(app=small), base_url="http://test") as c:
            assert (await c.post("/api/v1/auth/probe")).status_code == 202
            assert (await c.post("/api/v1/auth/plain")).status_code == 200

    first, second = _auth_event_rows()[-2:]
    assert (first["event_type"], first["user_id"], first["reason"], first["is_new_device"]) == (
        "auth_pending", 42, "device_approval_required", True,
    )
    # 口が何も入れなければ今まで通り（auth_success・列は NULL）
    assert (second["event_type"], second["user_id"], second["reason"], second["is_new_device"]) == (
        "auth_success", None, None, None,
    )


# ── D8: 組の失効（Redis の印） ──────────────────────────────────────

async def test_d8_revoke_user_sessions_returns_families_and_keeps_excluded(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    second = await _login(a)
    sid_a = jwt.get_unverified_claims(tok_a)["sid"]
    sid_2 = jwt.get_unverified_claims(second.json()["access_token"])["sid"]

    revoked = await devices.revoke_user_sessions(db_session, USER_ID, except_family_id=sid_a)
    await db_session.commit()

    assert revoked == [sid_2]
    assert sid_2 in REVOKED_SIDS and sid_a not in REVOKED_SIDS


async def test_d8_family_revoked_marker_uses_key_and_ttl():
    from app import cache

    client = MagicMock()
    client.set = AsyncMock()
    client.exists = AsyncMock(return_value=1)
    with patch.object(cache, "get_redis", return_value=client):
        await cache.mark_family_revoked("sid-1")
        assert await cache.is_family_revoked("sid-1") is True

    client.set.assert_awaited_once_with("auth:fam_revoked:sid-1", "1", ex=900)
    client.exists.assert_awaited_once_with("auth:fam_revoked:sid-1")


async def test_d8_redis_down_fails_open():
    from app import cache

    with patch.object(cache, "get_redis", return_value=None):
        await cache.mark_family_revoked("sid-1")
        assert await cache.is_family_revoked("sid-1") is False


async def test_d8_password_reset_confirm_revokes_all_families(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    sid_a = jwt.get_unverified_claims(tok_a)["sid"]
    await db_session.execute(
        text(
            "INSERT INTO password_reset_tokens (user_id, purpose, token_hash, expires_at) "
            "VALUES (:u, 'reset', :h, :e)"
        ),
        {"u": USER_ID, "h": self_tokens._hash_token("reset-token-raw"), "e": datetime.now(timezone.utc) + timedelta(minutes=30)},
    )
    await db_session.commit()

    resp = await machine().post(
        f"{AUTH}/password-reset/confirm",
        json={"token": "reset-token-raw", "new_password": NEW_PASSWORD_RESET},
        headers={"origin": ORIGIN},
    )

    assert resp.status_code == 200
    assert sid_a in REVOKED_SIDS
    assert (await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens WHERE revoked_at IS NULL")).n == 0
    # 新しい組は出さない（動きは今と同じ）
    assert (await a.get(f"{AUTH}/devices", headers=_bearer(tok_a))).status_code == 401


# ── password change（off と enforce） ───────────────────────────────

NEW_PASSWORD = "brand new long password 2026 ok"
NEW_PASSWORD_RESET = "reset new long password 2026 ok"


async def _change(client, token, current=PASSWORD):
    return await client.post(
        f"{AUTH}/password/change",
        json={"current_password": current, "new_password": NEW_PASSWORD},
        headers=_bearer(token),
    )


async def test_password_change_off_issues_family_without_device_and_accepts_sidless_token(machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    client = machine()
    token = (await _login(client)).json()["access_token"]

    resp = await _change(client, token)

    assert resp.status_code == 200
    body = resp.json()
    assert jwt.get_unverified_claims(body["access_token"])["sid"]
    live = await _row(db_session, "SELECT trusted_device_id FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert live.trusted_device_id is None
    assert (await _row(db_session, "SELECT count(*) AS n FROM user_trusted_devices")).n == 0
    # sid の無い古いトークンでも通る（off は今まで通り）
    old = self_tokens.create_access_token(USER_ID, EMAIL, "pwd")
    row = await _row(db_session, "SELECT password_argon2_hash FROM users WHERE id = :i", i=USER_ID)
    assert passwords.verify_password(row.password_argon2_hash, NEW_PASSWORD)
    await db_session.execute(
        text("UPDATE users SET password_argon2_hash = :h, password_changed_at = NULL WHERE id = :i"),
        {"h": passwords.hash_password(PASSWORD), "i": USER_ID},
    )
    await db_session.commit()
    assert (await _change(client, old)).status_code == 200


async def test_password_change_enforce_inherits_device(enforce, machine, db_session, password_hash):
    a, tok_a = await _first_machine(machine, db_session, password_hash)
    dev = await _row(db_session, "SELECT id FROM user_trusted_devices")

    resp = await _change(a, tok_a)

    assert resp.status_code == 200
    live = await _row(db_session, "SELECT trusted_device_id FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert live.trusted_device_id == dev.id
    # 新しいトークンでそのまま承認の口が使える
    assert (await a.get(f"{AUTH}/devices", headers=_bearer(resp.json()["access_token"]))).status_code == 200


async def test_password_change_enforce_sidless_token_is_403_and_password_unchanged(enforce, machine, db_session, password_hash):
    await _insert_user(db_session, password_hash)
    old = self_tokens.create_access_token(USER_ID, EMAIL, "pwd")

    resp = await _change(machine(), old)

    assert resp.status_code == 403 and resp.json()["detail"] == "session_upgrade_required"
    row = await _row(db_session, "SELECT password_argon2_hash FROM users WHERE id = :i", i=USER_ID)
    assert passwords.verify_password(row.password_argon2_hash, PASSWORD)


async def test_password_change_enforce_deviceless_family_after_cutoff_is_403(machine, db_session, password_hash, monkeypatch):
    await _insert_user(db_session, password_hash)
    client = machine()
    token = (await _login(client)).json()["access_token"]  # off: 機械なしの組
    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "2020-01-01T00:00:00+00:00")

    resp = await _change(client, token)

    assert resp.status_code == 403 and resp.json()["detail"] == "device_not_trusted"
    row = await _row(db_session, "SELECT password_argon2_hash FROM users WHERE id = :i", i=USER_ID)
    assert passwords.verify_password(row.password_argon2_hash, PASSWORD)
    assert (await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens WHERE revoked_at IS NULL")).n == 1


async def test_password_change_enforce_deviceless_family_before_cutoff_registers_bootstrap(machine, db_session, password_hash, monkeypatch):
    await _insert_user(db_session, password_hash)
    client = machine()
    token = (await _login(client)).json()["access_token"]
    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())

    resp = await _change(client, token)

    assert resp.status_code == 200
    assert any(c.startswith("sa_device=") for c in _set_cookies(resp))
    assert (await _row(db_session, "SELECT created_via FROM user_trusted_devices")).created_via == "bootstrap"
    live = await _row(db_session, "SELECT trusted_device_id FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert live.trusted_device_id is not None


# ── 部品 ─────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "ua, expected",
    [
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1", "iPhone・Safari"),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36", "Mac・Chrome"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36 Edg/120.0", "Windows・Edge"),
        ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36", "Android・Chrome"),
        ("", "不明な機械"),
        (None, "不明な機械"),
    ],
)
def test_describe_user_agent(ua, expected):
    assert devices.describe_user_agent(ua) == expected


def test_geo_lookup_returns_none_without_database(monkeypatch):
    monkeypatch.setenv("GEOIP_DB_PATH", "")
    assert geo.lookup("8.8.8.8") is None
    monkeypatch.setenv("GEOIP_DB_PATH", "/nonexistent/dbip.mmdb")
    assert geo.lookup("8.8.8.8") is None
    assert geo.lookup("192.168.0.1") is None  # 私用の IP
    assert geo.lookup("not-an-ip") is None
    assert geo.lookup(None) is None


def test_bootstrap_cutoff_parsing(monkeypatch):
    assert devices.bootstrap_cutoff() is None
    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "2026-11-01T12:00:00Z")
    assert devices.bootstrap_cutoff() == datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "garbage")
    assert devices.bootstrap_cutoff() is None


def test_device_approval_mode_defaults_to_off(monkeypatch):
    assert devices.approval_mode() == "off"
    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "ENFORCE")
    assert devices.approval_mode() == "enforce"
    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "whatever")
    assert devices.approval_mode() == "off"
