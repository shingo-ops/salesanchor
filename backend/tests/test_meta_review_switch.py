"""Meta 審査用の会社だけのログインのスイッチ（ADR-1055 What 11）のテスト。SQLite で動かす。

設計 docs/handoff/auth-new-device-approval/review-exempt-design.md の K1〜K8・K11・K12 を確かめる。
準備は backend/tests/test_new_device_approval.py と同じ形（enforce・外に出る部分の差し替え・別々の機械）。
印の会社は試験の中で tenants に1行作って meta_review_tenant = 1 にする（会社の番号を決め打ちしない）。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth import devices, passwords, self_tokens

assert sqlite3.sqlite_version_info >= (3, 35), "SQLite 3.35+ is required for RETURNING"

SECRET = "test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
ORIGIN = "https://app.salesanchor.jp"
PASSWORD = "correct horse battery staple"
AUTH = "/api/v1/auth"
SWITCH_URL = "/api/v1/super-admin/meta-review"
MARKED_TENANT = 2190
OTHER_TENANT = 2191
USER_ID = 2201
OTHER_USER_ID = 2202
SUPER_USER_ID = 2203
ADMIN_ID = 2204
OWNER_ID = 2205
EMAIL = "mr-user@example.com"
OTHER_EMAIL = "mr-other@example.com"
SUPER_USER_EMAIL = "mr-super@example.com"
ADMIN_EMAIL = "mr-admin@example.com"
OWNER_EMAIL = "mr-owner@example.com"
FLOOR = 2200  # このファイルのユーザーは id >= 2200

_T = {
    name: sa.table(name, sa.column("id"))
    for name in ("users", "auth_refresh_tokens", "user_trusted_devices", "auth_login_requests")
}

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
    router_mark = AsyncMock(side_effect=_mark)
    with patch("app.routers.auth.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.routers.auth.record_auth_failure", new=AsyncMock()), \
         patch("app.routers.auth.blacklist_token", new=AsyncMock(return_value=True)), \
         patch("app.routers.auth.record_audit_log", new=AsyncMock()), \
         patch("app.routers.auth.send_new_device_mail", new=mail), \
         patch("app.routers.auth.publish_user_change", new=publish), \
         patch("app.routers.tenant_login_requests.publish_user_change", new=publish), \
         patch("app.routers.auth._owner_user_ids", new=AsyncMock(return_value=[])), \
         patch("app.auth.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)), \
         patch("app.auth.dependencies.get_cached_jwt", new=AsyncMock(return_value=None)), \
         patch("app.auth.dependencies.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.auth.dependencies.record_auth_failure", new=AsyncMock()), \
         patch("app.auth.dependencies.cache_jwt_result", new=AsyncMock()), \
         patch("app.auth.dependencies.is_family_revoked", new=_is_revoked), \
         patch("app.auth.devices.mark_family_revoked", new=_mark), \
         patch("app.routers.super_admin_meta_review.mark_family_revoked", new=router_mark), \
         patch("app.middleware.audit.AsyncSessionLocal", new=lambda: _FakeAuditSession()):
        yield SimpleNamespace(mail=mail, publish=publish, router_mark=router_mark)


@pytest.fixture
def spies(no_redis_and_spies):
    return no_redis_and_spies


@pytest.fixture
def password_hash():
    return passwords.hash_password(PASSWORD)


@pytest.fixture
async def marked_tenant(db_session):
    """印の会社（meta_review_tenant = 1）と、印の無いほかの会社を1行ずつ作る。"""
    for tid, flag in ((MARKED_TENANT, 1), (OTHER_TENANT, 0)):
        await db_session.execute(
            text(
                "INSERT INTO tenants (id, tenant_code, tenant_name, company_name, meta_review_tenant) "
                "VALUES (:i, :c, :n, :n, :f)"
            ),
            {"i": tid, "c": f"mr-test-{tid}", "n": f"MR Test {tid}", "f": flag},
        )
    await db_session.commit()
    return MARKED_TENANT


@pytest.fixture(autouse=True)
async def cleanup(db_session):
    yield
    await db_session.rollback()
    for name in ("auth_login_requests", "auth_refresh_tokens", "user_trusted_devices"):
        await db_session.execute(sa.delete(_T[name]))
    await db_session.execute(sa.delete(_T["users"]).where(_T["users"].c.id >= FLOOR))
    await db_session.execute(text("DELETE FROM tenants WHERE id IN (:a, :b)"), {"a": MARKED_TENANT, "b": OTHER_TENANT})
    await db_session.execute(text("DROP TABLE IF EXISTS auth_events"))
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


# ── 小道具 ───────────────────────────────────────────────────

def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "origin": ORIGIN}


async def _login(client, email=EMAIL):
    return await client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD}, headers={"origin": ORIGIN})


async def _refresh(client):
    return await client.post(f"{AUTH}/refresh", headers={"origin": ORIGIN})


async def _user(
    db, hash_value, *, user_id=USER_ID, email=EMAIL, tenant_id=MARKED_TENANT,
    last_login="2026-10-01 00:00:00", is_super_admin=False,
):
    cols = {
        "id": user_id, "tenant_id": tenant_id, "username": f"u{user_id}", "email": email,
        "is_active": True, "password_argon2_hash": hash_value, "is_super_admin": is_super_admin,
        "last_login": last_login,
    }
    names = ", ".join(cols)
    marks = ", ".join(f":{k}" for k in cols)
    await db.execute(text(f"INSERT INTO users ({names}) VALUES ({marks})"), cols)
    await db.commit()


async def _set_until(db, value: datetime | None):
    await db.execute(
        text("UPDATE tenants SET meta_review_login_until = :u WHERE id = :id"),
        {"u": value, "id": MARKED_TENANT},
    )
    await db.commit()


def _future(days: float = 1) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def _past(days: float = 1) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def _row(db, sql, **params):
    return (await db.execute(text(sql), params)).first()


async def _rows(db, sql, **params):
    return (await db.execute(text(sql), params)).all()


async def _on_session(machine, db, password_hash):
    """ON の間に印の会社の人がパスワードだけで入った組。(client, access_token) を返す。"""
    await _user(db, password_hash)
    await _set_until(db, _future())
    client = machine()
    resp = await _login(client)
    assert resp.status_code == 200, resp.text
    return client, resp.json()["access_token"]


async def _super_admin_token(db, password_hash):
    await _user(db, password_hash, user_id=ADMIN_ID, email=ADMIN_EMAIL, tenant_id=OTHER_TENANT, is_super_admin=True)
    return self_tokens.create_access_token(ADMIN_ID, ADMIN_EMAIL, "pwd")


# ── K1・K2・K3・K5: ログインの判定 ─────────────────────────────

async def test_meta_review_on_login_gets_tokens(enforce, machine, db_session, password_hash, marked_tenant, spies):
    await _user(db_session, password_hash)
    await _set_until(db_session, _future())

    resp = await _login(machine())

    assert resp.status_code == 200
    assert resp.json()["access_token"]
    refresh = await _row(db_session, "SELECT trusted_device_id FROM auth_refresh_tokens")
    assert refresh.trusted_device_id is None
    assert (await _row(db_session, "SELECT count(*) AS n FROM user_trusted_devices")).n == 0
    event = _auth_event_rows()[-1]
    assert event["reason"] == "meta_review" and event["user_id"] == USER_ID
    spies.mail.assert_called_once()


@pytest.mark.parametrize("until", [None, "past"])
async def test_meta_review_off_returns_202(until, enforce, machine, db_session, password_hash, marked_tenant):
    await _user(db_session, password_hash)
    await _set_until(db_session, None if until is None else _past())

    resp = await _login(machine())

    assert resp.status_code == 202
    assert "access_token" not in resp.json()
    assert (await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens")).n == 0


async def test_meta_review_other_tenant_still_202(enforce, machine, db_session, password_hash, marked_tenant):
    await _user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL, tenant_id=OTHER_TENANT)
    await _set_until(db_session, _future())

    resp = await _login(machine(), email=OTHER_EMAIL)

    assert resp.status_code == 202


async def test_meta_review_not_for_super_admin_user(enforce, machine, db_session, password_hash, marked_tenant):
    await _user(
        db_session, password_hash, user_id=SUPER_USER_ID, email=SUPER_USER_EMAIL, is_super_admin=True
    )
    await _set_until(db_session, _future())

    resp = await _login(machine(), email=SUPER_USER_EMAIL)

    assert resp.status_code == 202


# ── K6: 14日の自動 OFF ───────────────────────────────────────

async def test_meta_review_auto_off_after_14_days(enforce, machine, db_session, password_hash, marked_tenant):
    await _user(db_session, password_hash)
    token = await _super_admin_token(db_session, password_hash)
    admin = machine()
    with patch("app.routers.super_admin_meta_review._record_auth_audit", new=AsyncMock()):
        put = await admin.put(SWITCH_URL, json={"on": True}, headers=_bearer(token))
    assert put.status_code == 200 and put.json()["is_on"] is True
    until = datetime.fromisoformat(put.json()["until"])
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    assert abs(until - (datetime.now(timezone.utc) + timedelta(days=14))) < timedelta(minutes=1)
    assert (await _login(machine())).status_code == 200

    later = datetime.now(timezone.utc) + timedelta(days=15)
    with patch("app.auth.devices._now", new=lambda: later):
        resp = await _login(machine())
        got = await admin.get(SWITCH_URL, headers=_bearer(token))

    assert resp.status_code == 202
    assert got.status_code == 200
    assert got.json()["is_on"] is False
    assert got.json()["until"] is not None  # 過ぎた値はそのまま返す（画面が自動で OFF になった日時を出す）
    assert got.json()["tenant_name"] == f"MR Test {MARKED_TENANT}"


# ── K7: OFF の後の更新は 401 ─────────────────────────────────

async def test_meta_review_refresh_after_off_401(enforce, machine, db_session, password_hash, marked_tenant):
    client, _ = await _on_session(machine, db_session, password_hash)

    ok = await _refresh(client)
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert _auth_event_rows()[-1]["reason"] == "meta_review_refresh"

    await _set_until(db_session, None)
    resp = await _refresh(client)

    assert resp.status_code == 401


# ── K8: スイッチで入った組では入口を作れない ─────────────────────

async def test_meta_review_session_cannot_enroll_passkey(enforce, machine, db_session, password_hash, marked_tenant):
    client, token = await _on_session(machine, db_session, password_hash)

    options = await client.post(f"{AUTH}/passkey/register/options", json={}, headers=_bearer(token))
    verify = await client.post(
        f"{AUTH}/passkey/register/verify",
        json={"challenge_id": "x", "credential": {}},
        headers=_bearer(token),
    )

    assert options.status_code == 403 and options.json()["detail"] == "meta_review_session_no_enroll"
    assert verify.status_code == 403 and verify.json()["detail"] == "meta_review_session_no_enroll"


async def test_meta_review_session_cannot_create_recovery_codes(enforce, machine, db_session, password_hash, marked_tenant):
    client, token = await _on_session(machine, db_session, password_hash)

    resp = await client.post(f"{AUTH}/recovery-codes", headers=_bearer(token))

    assert resp.status_code == 403 and resp.json()["detail"] == "meta_review_session_no_enroll"


async def test_meta_review_session_prompt_not_auto(enforce, machine, db_session, password_hash, marked_tenant):
    client, token = await _on_session(machine, db_session, password_hash)

    resp = await client.get(f"{AUTH}/passkey/prompt", headers=_bearer(token))

    assert resp.status_code == 200
    assert resp.json() == {"can_auto": False, "show_prompt": False}


async def test_meta_review_session_cannot_approve_tenant_request(enforce, machine, db_session, password_hash, marked_tenant):
    from app.auth.dependencies import get_current_tenant
    from app.main import app

    await _user(db_session, password_hash, user_id=OWNER_ID, email=OWNER_EMAIL)
    await _set_until(db_session, _future())
    client = machine()
    login = await _login(client, email=OWNER_EMAIL)
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    async def fake_tenant():
        return MARKED_TENANT

    async def fake_keys(db, user_id):
        return {"owner"}

    app.dependency_overrides[get_current_tenant] = fake_tenant
    try:
        with patch("app.auth.dependencies.get_user_system_keys", new=fake_keys):
            resp = await client.post(
                "/api/v1/tenant/login-requests/00000000-0000-0000-0000-000000000000/approve",
                json={"note": "電話で確認"},
                headers=_bearer(token),
            )
    finally:
        app.dependency_overrides.pop(get_current_tenant, None)

    assert resp.status_code == 403 and resp.json()["detail"] == "meta_review_session_no_enroll"


async def test_meta_review_session_cannot_enroll_after_off(enforce, machine, db_session, password_hash, marked_tenant):
    client, token = await _on_session(machine, db_session, password_hash)
    await _set_until(db_session, _past())

    resp = await client.post(f"{AUTH}/passkey/register/options", json={}, headers=_bearer(token))

    assert resp.status_code == 403 and resp.json()["detail"] == "meta_review_session_no_enroll"


async def test_meta_review_member_no_first_login_device(enforce, machine, db_session, password_hash, marked_tenant):
    await _user(db_session, password_hash, last_login=None)  # OFF（until は NULL）

    resp = await _login(machine())

    assert resp.status_code == 202
    assert (await _row(db_session, "SELECT count(*) AS n FROM user_trusted_devices")).n == 0


# ── K5・K12: 管理の口 ────────────────────────────────────────

async def test_meta_review_switch_forbidden_for_non_super_admin(enforce, machine, db_session, password_hash, marked_tenant):
    await _user(db_session, password_hash)
    token = self_tokens.create_access_token(USER_ID, EMAIL, "pwd")
    client = machine()

    got = await client.get(SWITCH_URL, headers=_bearer(token))
    put = await client.put(SWITCH_URL, json={"on": True}, headers=_bearer(token))
    logins = await client.get(f"{SWITCH_URL}/logins", headers=_bearer(token))

    assert (got.status_code, put.status_code, logins.status_code) == (403, 403, 403)
    assert (await _row(db_session, "SELECT meta_review_login_until AS u FROM tenants WHERE id = :i", i=MARKED_TENANT)).u is None


async def test_meta_review_switch_missing_tenant_409(enforce, machine, db_session, password_hash):
    token = await _super_admin_token(db_session, password_hash)

    resp = await machine().put(SWITCH_URL, json={"on": True}, headers=_bearer(token))

    assert resp.status_code == 409 and resp.json()["detail"] == "meta_review_tenant_missing"


async def test_meta_review_manual_off_revokes_deviceless_families(
    enforce, machine, db_session, password_hash, marked_tenant, spies
):
    on_client, _ = await _on_session(machine, db_session, password_hash)
    on_sid = (await _row(db_session, "SELECT family_id FROM auth_refresh_tokens")).family_id
    # 機械の付いた組（印の会社のもう1人）は残る
    await _user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL)
    now = datetime.now(timezone.utc)
    await db_session.execute(
        text(
            "INSERT INTO user_trusted_devices (id, user_id, token_hash, created_via) "
            "VALUES (9001, :u, :h, 'first_login')"
        ),
        {"u": OTHER_USER_ID, "h": b"device-hash-aaaaaaaaaaaaaaaaaaaaaaaa"},
    )
    await db_session.execute(
        text(
            "INSERT INTO auth_refresh_tokens (user_id, token_hash, family_id, family_created_at, expires_at, "
            "created_at, trusted_device_id) VALUES (:u, :h, 'device-family', :n, :e, :n, 9001)"
        ),
        {"u": OTHER_USER_ID, "h": b"refresh-hash-bbbbbbbbbbbbbbbbbbbbbbb", "n": now, "e": now + timedelta(days=30)},
    )
    await db_session.commit()
    token = await _super_admin_token(db_session, password_hash)

    with patch("app.routers.super_admin_meta_review._record_auth_audit", new=AsyncMock()) as audit:
        resp = await machine().put(SWITCH_URL, json={"on": False}, headers=_bearer(token))

    assert resp.status_code == 200 and resp.json()["is_on"] is False and resp.json()["until"] is None
    on_row = await _row(db_session, "SELECT revoked_at FROM auth_refresh_tokens WHERE family_id = :f", f=on_sid)
    assert on_row.revoked_at is not None
    device_row = await _row(db_session, "SELECT revoked_at FROM auth_refresh_tokens WHERE family_id = 'device-family'")
    assert device_row.revoked_at is None
    assert [c.args[0] for c in spies.router_mark.await_args_list] == [on_sid]
    assert audit.await_args.kwargs["new_data"]["revoked_families"] == 1
    assert (await _refresh(on_client)).status_code == 401


async def test_meta_review_switch_audited(enforce, machine, db_session, password_hash, marked_tenant):
    token = await _super_admin_token(db_session, password_hash)
    client = machine()

    with patch("app.routers.super_admin_meta_review._record_auth_audit", new=AsyncMock()) as audit:
        assert (await client.put(SWITCH_URL, json={"on": True}, headers=_bearer(token))).status_code == 200
        assert (await client.put(SWITCH_URL, json={"on": False}, headers=_bearer(token))).status_code == 200

    assert audit.await_count == 2
    events = []
    for call in audit.await_args_list:
        kwargs = call.kwargs
        assert kwargs["tenant_id"] == MARKED_TENANT and kwargs["record_id"] == MARKED_TENANT
        assert kwargs["user_id"] == ADMIN_ID and kwargs["table_name"] == "tenants" and kwargs["action"] == "update"
        events.append(kwargs["new_data"]["event"])
    assert events == ["meta_review_on", "meta_review_off"]


# ── K11: ログイン履歴 ────────────────────────────────────────

async def test_meta_review_history_lists_attempts(enforce, machine, db_session, password_hash, marked_tenant):
    await _user(db_session, password_hash)
    await _user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL, tenant_id=OTHER_TENANT)
    token = await _super_admin_token(db_session, password_hash)
    await db_session.execute(
        text(
            "CREATE TABLE auth_events (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP, "
            "user_id INTEGER, path TEXT, status_code INTEGER, reason TEXT, user_agent TEXT)"
        )
    )
    login, poll = f"{AUTH}/login", f"{AUTH}/login-requests/poll"
    mac = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0"
    rows = [
        ("2026-11-22 01:00:00", USER_ID, login, 200, "meta_review", mac),
        ("2026-11-22 02:00:00", USER_ID, login, 401, "bad_password", mac),
        ("2026-11-22 03:00:00", USER_ID, login, 202, "device_approval_required", mac),
        ("2026-11-22 04:00:00", USER_ID, poll, 200, "approved_admin", mac),
        ("2026-11-22 05:00:00", USER_ID, login, 401, "locked", mac),
        ("2026-11-22 06:00:00", OTHER_USER_ID, login, 200, "ok", mac),  # ほかの会社の人は出ない
        ("2026-11-22 07:00:00", None, login, 401, "unknown_user", mac),  # 人の付かない行は出ない
        ("2026-11-22 08:00:00", USER_ID, poll, 202, None, mac),  # 許可を待つだけの行は出ない
    ]
    for created_at, uid, path, code, reason, ua in rows:
        await db_session.execute(
            text(
                "INSERT INTO auth_events (created_at, user_id, path, status_code, reason, user_agent) "
                "VALUES (:c, :u, :p, :s, :r, :a)"
            ),
            {"c": created_at, "u": uid, "p": path, "s": code, "r": reason, "a": ua},
        )
    await db_session.commit()

    resp = await machine().get(f"{SWITCH_URL}/logins", headers=_bearer(token))

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [(i["status_code"], i["reason"]) for i in items] == [
        (401, "locked"),
        (200, "approved_admin"),
        (202, "device_approval_required"),
        (401, "bad_password"),
        (200, "meta_review"),
    ]
    assert all(i["email"] == EMAIL for i in items)
    assert items[0]["device"] == devices.describe_user_agent(mac)
