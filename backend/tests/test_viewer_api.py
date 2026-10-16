"""閲覧専用ページの API（login・logout・inventory）の試験（ADR-1019 段2・設計 D1/D2）。

Redis は mock（メモリ上の FakeRedis を app.cache._redis に差す）。DB は大半が mock（FakeDb）で、
実際の表に対する SQL の確かめは PG の1関数（CI 専用・CREATE TABLE は書かず migration を流す）。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app import cache
from app.auth import self_tokens, viewer_tokens
from app.auth.passwords import hash_password
from app.database import get_db
from app.routers import viewer as viewer_router
from app.tasks import viewer_inventory_cache as vic
from tests.rls_bootstrap import _ensure_public_users
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

SECRET = "v" * 48
PASSWORD = "correct-horse-battery"
_HASH = hash_password(PASSWORD)
NOW = datetime.now(timezone.utc)
LOGIN = "/api/v1/viewer/login"
LOGOUT = "/api/v1/viewer/logout"
INVENTORY = "/api/v1/viewer/inventory"


@pytest.fixture(autouse=True)
def viewer_env(monkeypatch):
    monkeypatch.setenv("AUTH_VIEWER_JWT_SECRET", SECRET)
    monkeypatch.setenv("AUTH_JWT_SECRET", "a" * 48)


class _Pipe:
    def __init__(self, redis: "FakeRedis") -> None:
        self.redis = redis
        self.ops: list = []

    def setex(self, key, ttl, value):
        self.ops.append(("set", key, value, ttl))

    def delete(self, key):
        self.ops.append(("del", key))

    async def execute(self):
        for op in self.ops:
            if op[0] == "set":
                self.redis.store[op[1]] = op[2]
                self.redis.ttls[op[1]] = op[3]
            else:
                self.redis.store.pop(op[1], None)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict = {}
        self.ttls: dict = {}

    async def get(self, key):
        return self.store.get(key)

    async def exists(self, key):
        return 1 if key in self.store else 0

    async def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    async def expire(self, key, ttl):
        self.ttls[key] = ttl

    async def delete(self, key):
        self.store.pop(key, None)

    def pipeline(self):
        return _Pipe(self)


class _Result:
    def __init__(self, row) -> None:
        self._row = row

    def first(self):
        return self._row


def make_viewer(vid=1, email="a@x.com", status="active", must_change=False, hashed=_HASH, trial_expires_at=None):
    return SimpleNamespace(
        id=vid,
        email=email,
        status=status,
        password_argon2_hash=hashed,
        password_must_change=must_change,
        password_changed_at=None,
        trial_expires_at=trial_expires_at,
    )


class FakeDb:
    def __init__(self, *viewers) -> None:
        self.viewers = list(viewers)
        self.events: list[dict] = []
        self.commits = 0

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        if "INSERT INTO public.viewer_login_events" in sql:
            self.events.append(dict(params))
            return _Result(None)
        if "FROM public.viewer_accounts WHERE lower(email)" in sql:
            return _Result(next((v for v in self.viewers if v.email.lower() == params["email"]), None))
        if "FROM public.viewer_accounts WHERE id" in sql:
            return _Result(next((v for v in self.viewers if v.id == params["id"]), None))
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.commits += 1


@pytest.fixture
def redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_redis", fake)
    return fake


def _headers(ip="10.0.0.1", **extra):
    return {"Origin": self_tokens.rp_origin(), "X-Real-IP": ip, "User-Agent": "pytest-agent", **extra}


def _bearer(vid=1):
    token, _ = viewer_tokens.create_viewer_access_token(vid)
    return token, {"Authorization": f"Bearer {token}"}


class _Client:
    def __init__(self, db) -> None:
        self.db = db

    async def __aenter__(self):
        from app.main import app

        async def _db():
            yield self.db

        app.dependency_overrides[get_db] = _db
        self.http = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        return self.http

    async def __aexit__(self, *exc):
        from app.main import app

        await self.http.aclose()
        app.dependency_overrides.pop(get_db, None)


async def _login(http, email="a@x.com", password=PASSWORD, ip="10.0.0.1", headers=None):
    return await http.post(LOGIN, json={"email": email, "password": password}, headers=headers or _headers(ip))


# ── 守り手・ソース ──────────────────────────────────────────────


def test_viewer_modules_do_not_use_app_jwt_cache():
    for module in (viewer_router, vic):
        source = inspect.getsource(module)
        assert "cache_jwt_result" not in source and "get_cached_jwt" not in source


async def test_app_user_token_gets_401_on_viewer_inventory(redis):
    token = self_tokens.create_access_token(1, "u@example.com", "pwd")
    async with _Client(FakeDb()) as http:
        resp = await http.get(INVENTORY, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ── inventory ─────────────────────────────────────────────────


async def test_inventory_503_when_no_key(redis):
    _, auth = _bearer()
    async with _Client(FakeDb(make_viewer())) as http:
        resp = await http.get(INVENTORY, headers=auth)
    assert resp.status_code == 503 and resp.json()["detail"] == "viewer_inventory_not_ready"


async def test_inventory_503_when_redis_is_none(monkeypatch):
    monkeypatch.setattr(cache, "_redis", None)
    _, auth = _bearer()
    async with _Client(FakeDb(make_viewer())) as http:
        resp = await http.get(INVENTORY, headers=auth)
    assert resp.status_code == 503


async def test_inventory_503_when_redis_get_raises(monkeypatch, redis):
    redis.get = AsyncMock(side_effect=RuntimeError("down"))
    _, auth = _bearer()
    async with _Client(FakeDb(make_viewer())) as http:
        resp = await http.get(INVENTORY, headers=auth)
    assert resp.status_code == 503


async def test_inventory_returns_cached_json_as_is(redis):
    body = json.dumps(
        {"updated_at": "2026-10-16T00:00:00+00:00", "fresh_window_hours": 24, "rows": [{"a": "日本語"}]},
        ensure_ascii=False,
    )
    redis.store[vic.CACHE_KEY] = body
    _, auth = _bearer()
    async with _Client(FakeDb(make_viewer())) as http:
        resp = await http.get(INVENTORY, headers=auth)
    assert resp.status_code == 200
    assert resp.content.decode() == body
    assert resp.headers["cache-control"] == "no-store"
    assert resp.headers["content-type"].startswith("application/json")


async def test_inventory_403_when_password_change_required(redis):
    redis.store[vic.CACHE_KEY] = "{}"
    _, auth = _bearer()
    async with _Client(FakeDb(make_viewer(must_change=True))) as http:
        resp = await http.get(INVENTORY, headers=auth)
    assert resp.status_code == 403 and resp.json()["detail"] == "password_change_required"


async def test_inventory_403_when_suspended(redis):
    redis.store[vic.CACHE_KEY] = "{}"
    _, auth = _bearer()
    async with _Client(FakeDb(make_viewer(status="suspended"))) as http:
        resp = await http.get(INVENTORY, headers=auth)
    assert resp.status_code == 403 and resp.json()["detail"] == "viewer_suspended"


# ── logout ────────────────────────────────────────────────────


async def test_logout_503_when_blacklist_fails(redis):
    _, auth = _bearer()
    with patch.object(viewer_router, "blacklist_token", new=AsyncMock(return_value=False)):
        async with _Client(FakeDb(make_viewer())) as http:
            resp = await http.post(LOGOUT, headers=auth)
    assert resp.status_code == 503 and resp.json()["detail"] == "logout_unavailable"


async def test_logout_uses_remaining_lifetime_then_token_is_rejected(redis):
    token, auth = _bearer()
    seen: list[int] = []
    real = cache.blacklist_token

    async def spy(tok, ttl=3600):
        seen.append(ttl)
        return await real(tok, ttl=ttl)

    redis.store[vic.CACHE_KEY] = "{}"
    async with _Client(FakeDb(make_viewer())) as http:
        with patch.object(viewer_router, "blacklist_token", new=spy):
            resp = await http.post(LOGOUT, headers=auth)
        assert resp.status_code == 200 and resp.json() == {"ok": True}
        after = await http.get(INVENTORY, headers=auth)
    assert len(seen) == 1 and abs(seen[0] - viewer_tokens.VIEWER_TOKEN_TTL_SECONDS) <= 5
    assert after.status_code == 401


async def test_logout_allowed_before_password_change(redis):
    _, auth = _bearer()
    async with _Client(FakeDb(make_viewer(must_change=True))) as http:
        resp = await http.post(LOGOUT, headers=auth)
    assert resp.status_code == 200


# ── login ─────────────────────────────────────────────────────


async def test_login_403_when_origin_differs(redis):
    async with _Client(FakeDb(make_viewer())) as http:
        resp = await _login(http, headers={"Origin": "https://evil.example", "X-Real-IP": "10.0.0.1"})
    assert resp.status_code == 403 and resp.json()["detail"] == "forbidden_origin"


async def test_login_failures_look_the_same(redis):
    db = FakeDb(make_viewer(vid=1, email="a@x.com"), make_viewer(vid=2, email="p@x.com", status="pending"))
    async with _Client(db) as http:
        unknown = await _login(http, email="nobody@x.com")
        wrong = await _login(http, email="a@x.com", password="wrong-password")
        pending = await _login(http, email="p@x.com")
    assert {unknown.status_code, wrong.status_code, pending.status_code} == {401}
    assert unknown.json() == wrong.json() == pending.json() == {"detail": "viewer_invalid_credentials"}


async def test_login_null_hash_is_failure(redis):
    async with _Client(FakeDb(make_viewer(hashed=None))) as http:
        resp = await _login(http)
    assert resp.status_code == 401


async def test_login_suspended_and_expired_trial_with_correct_password(redis):
    db = FakeDb(
        make_viewer(vid=1, email="s@x.com", status="suspended"),
        make_viewer(vid=2, email="t@x.com", status="trial", trial_expires_at=NOW - timedelta(days=1)),
        make_viewer(vid=3, email="n@x.com", status="trial", trial_expires_at=None),
    )
    async with _Client(db) as http:
        suspended = await _login(http, email="s@x.com")
        expired = await _login(http, email="t@x.com")
        no_expiry = await _login(http, email="n@x.com")
    assert (suspended.status_code, suspended.json()["detail"]) == (403, "viewer_suspended")
    assert (expired.status_code, expired.json()["detail"]) == (403, "viewer_trial_expired")
    assert (no_expiry.status_code, no_expiry.json()["detail"]) == (403, "viewer_trial_expired")
    assert [e["event_type"] for e in db.events] == ["login_failed"] * 3
    assert not any(k.startswith("viewer_login_fail:") for k in redis.store)  # 失敗の回数には数えない


async def test_login_suspended_with_wrong_password_is_plain_401(redis):
    async with _Client(FakeDb(make_viewer(status="suspended"))) as http:
        resp = await _login(http, password="wrong-password")
    assert resp.status_code == 401


async def test_login_success_returns_token_and_must_change_flag(redis):
    db = FakeDb(make_viewer(must_change=True))
    async with _Client(db) as http:
        resp = await _login(http)
    body = resp.json()
    assert resp.status_code == 200
    assert body["must_change_password"] is True and body["token_type"] == "bearer"
    claims = viewer_tokens.decode_viewer_token(body["access_token"])
    assert claims["sub"] == "viewer:1"
    assert datetime.fromisoformat(body["expires_at"]) == datetime.fromtimestamp(claims["exp"], timezone.utc)


async def test_login_trims_and_lowercases_email(redis):
    async with _Client(FakeDb(make_viewer(email="a@x.com"))) as http:
        resp = await _login(http, email=" A@x.com ")
    assert resp.status_code == 200 and resp.json()["must_change_password"] is False


async def test_login_success_clears_email_failure_count(redis):
    db = FakeDb(make_viewer())
    async with _Client(db) as http:
        await _login(http, password="wrong-password")
        assert any(k.startswith("viewer_login_fail:") for k in redis.store)
        resp = await _login(http)
    assert resp.status_code == 200
    assert not any(k.startswith("viewer_login_fail:") for k in redis.store)


async def test_login_fail_open_when_redis_is_none(monkeypatch):
    monkeypatch.setattr(cache, "_redis", None)
    async with _Client(FakeDb(make_viewer())) as http:
        ok = await _login(http)
        bad = await _login(http, password="wrong-password")
    assert (ok.status_code, bad.status_code) == (200, 401)


# ── 回数制限 ──────────────────────────────────────────────────


async def test_rate_limit_by_ip(redis):
    async with _Client(FakeDb(make_viewer())) as http:
        codes = [(await _login(http, email=f"u{i}@x.com", password="x", ip="10.9.9.9")).status_code for i in range(10)]
        eleventh = await _login(http, email="a@x.com", ip="10.9.9.9")
    assert codes == [401] * 10
    assert eleventh.status_code == 429 and eleventh.json()["detail"] == "viewer_too_many_attempts"


async def test_rate_limit_by_email_across_ips(redis):
    async with _Client(FakeDb(make_viewer())) as http:
        codes = [
            (await _login(http, email="a@x.com", password="wrong-password", ip=f"10.1.0.{i}")).status_code
            for i in range(10)
        ]
        eleventh = await _login(http, email="a@x.com", ip="10.1.0.200")  # 正しいパスワードでも止まる
    assert codes == [401] * 10
    assert eleventh.status_code == 429 and eleventh.json()["detail"] == "viewer_too_many_attempts"


# ── ログイン記録（mock） ────────────────────────────────────────


async def test_login_events_for_success_and_failure_not_for_unknown(redis):
    db = FakeDb(make_viewer(vid=7))
    async with _Client(db) as http:
        await _login(http, email="nobody@x.com", ip="10.2.0.1")
        await _login(http, password="wrong-password", ip="10.2.0.2")
        await _login(http, ip="10.2.0.3")
    assert [(e["viewer_id"], e["event_type"], e["ip"]) for e in db.events] == [
        (7, "login_failed", "10.2.0.2"),
        (7, "login_succeeded", "10.2.0.3"),
    ]
    assert all(e["ua"] == "pytest-agent" for e in db.events)


async def test_client_ip_ignores_x_forwarded_for(redis):
    db = FakeDb(make_viewer())
    async with _Client(db) as http:
        await _login(http, headers=_headers("10.3.0.1", **{"X-Forwarded-For": "6.6.6.6"}))
    assert db.events[0]["ip"] == "10.3.0.1"


# ── 実際の表に対する SQL（CI 専用） ──────────────────────────────


@pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")
def test_pg_login_records_events_in_real_table(pg, monkeypatch):  # noqa: F811
    conn, _, async_url = pg
    monkeypatch.setattr(cache, "_redis", FakeRedis())

    async def _prepare():
        engine = create_async_engine(async_url, echo=False)
        try:
            async with engine.begin() as aconn:
                await _ensure_public_users(aconn)
        finally:
            await engine.dispose()

    asyncio.run(_prepare())
    cur = conn.cursor()
    cur.execute((MIGRATIONS / "20261016_150000_add_viewer_accounts.sql").read_text())
    cur.execute(
        "INSERT INTO public.viewer_accounts (email, line_name, status, password_argon2_hash, password_must_change) "
        "VALUES ('A@x.com', 'n', 'active', %s, true) RETURNING id",
        (_HASH,),
    )
    vid = cur.fetchone()[0]

    async def _run():
        from app.main import app

        engine = create_async_engine(async_url, echo=False)

        async def _db():
            async with AsyncSession(engine, expire_on_commit=False) as session:
                yield session

        app.dependency_overrides[get_db] = _db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
                unknown = await _login(http, email="nobody@x.com", ip="10.4.0.1")
                wrong = await _login(http, password="wrong-password", ip="10.4.0.2")
                ok = await _login(http, email=" a@X.com ", ip="10.4.0.3")
                return unknown.status_code, wrong.status_code, ok.status_code, ok.json()
        finally:
            app.dependency_overrides.pop(get_db, None)
            await engine.dispose()

    unknown, wrong, ok, body = asyncio.run(_run())
    assert (unknown, wrong, ok) == (401, 401, 200)
    assert body["must_change_password"] is True
    cur.execute("SELECT viewer_id, event_type, client_ip, user_agent FROM public.viewer_login_events ORDER BY id")
    rows = cur.fetchall()
    assert [(r[0], r[1], r[2]) for r in rows] == [
        (vid, "login_failed", "10.4.0.2"),
        (vid, "login_succeeded", "10.4.0.3"),
    ]
