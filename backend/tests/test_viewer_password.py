"""閲覧専用ページのパスワード変更・再発行の試験（ADR-1019 段4a-1・設計 D1/D2）。

Redis はメモリ上の FakeRedis、DB は表の動きを真似る StatefulDb（実 DB には接続しない）。
メールは send_viewer_password_reset_email を mock して宛先と URL だけを捕まえる。
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app import cache
from app.auth import self_tokens, viewer_tokens
from app.auth.passwords import hash_password, verify_password
from app.database import get_db
from app.routers import viewer as viewer_router
from app.tasks import viewer_inventory_cache as vic
from tests.test_viewer_api import SECRET, FakeRedis

PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "another-long-passphrase-42"
_HASH = hash_password(PASSWORD)
CHANGE = "/api/v1/viewer/password"
REQUEST = "/api/v1/viewer/password-reset/request"
CONFIRM = "/api/v1/viewer/password-reset/confirm"
INVENTORY = "/api/v1/viewer/inventory"
LOGIN = "/api/v1/viewer/login"


@pytest.fixture(autouse=True)
def viewer_env(monkeypatch):
    monkeypatch.setenv("AUTH_VIEWER_JWT_SECRET", SECRET)
    monkeypatch.setenv("AUTH_JWT_SECRET", "a" * 48)


@pytest.fixture
def redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_redis", fake)
    return fake


class _Result:
    def __init__(self, row=None) -> None:
        self._row = row

    def first(self):
        return self._row


class StatefulDb:
    """viewer_accounts・viewer_login_tokens・viewer_login_events の動きだけを真似る。"""

    def __init__(self) -> None:
        self.accounts: dict[int, SimpleNamespace] = {}
        self.tokens: list[dict] = []
        self.events: list[dict] = []
        self.commits = 0

    def add(self, vid=1, email="a@x.com", status="active", must_change=False, hashed=_HASH, trial_expires_at=None):
        self.accounts[vid] = SimpleNamespace(
            id=vid,
            email=email,
            status=status,
            password_argon2_hash=hashed,
            password_must_change=must_change,
            password_changed_at=None,
            trial_expires_at=trial_expires_at,
        )
        return self.accounts[vid]

    def add_token(self, vid, raw, purpose="password_reset", expires_in=timedelta(minutes=30)):
        self.tokens.append(
            {
                "viewer_account_id": vid,
                "token_sha256": hashlib.sha256(raw.encode()).digest(),
                "purpose": purpose,
                "expires_at": datetime.now(timezone.utc) + expires_in,
            }
        )

    async def execute(self, stmt, params=None):
        sql = " ".join(str(stmt).split())
        p = params or {}
        if sql.startswith("INSERT INTO public.viewer_login_events"):
            self.events.append(dict(p))
            return _Result()
        if sql.startswith("INSERT INTO public.viewer_login_tokens"):
            assert len(p["h"]) == 32
            self.tokens.append(
                {
                    "viewer_account_id": p["id"],
                    "token_sha256": p["h"],
                    "purpose": "password_reset",
                    "expires_at": p["exp"],
                }
            )
            return _Result()
        if sql.startswith("DELETE FROM public.viewer_login_tokens WHERE viewer_account_id"):
            self.tokens = [
                t
                for t in self.tokens
                if not (t["viewer_account_id"] == p["id"] and t["purpose"] == "password_reset")
            ]
            return _Result()
        if sql.startswith("DELETE FROM public.viewer_login_tokens WHERE token_sha256"):
            for t in self.tokens:
                if t["token_sha256"] == p["h"] and t["purpose"] == "password_reset" and t["expires_at"] > p["now"]:
                    self.tokens.remove(t)
                    return _Result(SimpleNamespace(viewer_account_id=t["viewer_account_id"]))
            return _Result()
        if sql.startswith("UPDATE public.viewer_accounts SET password_argon2_hash"):
            a = self.accounts[p["id"]]
            a.password_argon2_hash = p["h"]
            a.password_must_change = False
            a.password_changed_at = p["now"]
            return _Result()
        if "FROM public.viewer_accounts WHERE lower(email)" in sql:
            return _Result(next((a for a in self.accounts.values() if a.email.lower() == p["email"]), None))
        if "FROM public.viewer_accounts WHERE id" in sql:
            return _Result(self.accounts.get(p["id"]))
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.commits += 1


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


def _headers(ip="10.0.0.1", **extra):
    return {"Origin": self_tokens.rp_origin(), "X-Real-IP": ip, "User-Agent": "pytest-agent", **extra}


def _auth(token):
    return {"Authorization": f"Bearer {token}", "X-Real-IP": "10.0.0.1", "User-Agent": "pytest-agent"}


def _token_with_iat(vid, iat):
    claims = {
        "iss": viewer_tokens.VIEWER_ISSUER,
        "sub": f"viewer:{vid}",
        "iat": iat,
        "exp": iat + viewer_tokens.VIEWER_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(claims, SECRET, algorithm="HS256")


def _fresh_token(vid=1):
    return viewer_tokens.create_viewer_access_token(vid)[0]


@pytest.fixture
def mail():
    with patch.object(viewer_router, "send_viewer_password_reset_email", new=MagicMock()) as m:
        yield m


def _raw_from_mail(m, call=-1):
    url = m.call_args_list[call].args[1]
    assert url.startswith(f"{self_tokens.rp_origin()}/viewer/#reset=")
    return url.split("#reset=", 1)[1]


# ── POST /password ────────────────────────────────────────────


async def test_must_change_viewer_changes_password_then_inventory_is_200(redis):
    redis.store[vic.CACHE_KEY] = "{}"
    db = StatefulDb()
    db.add(must_change=True)
    token = _fresh_token()
    async with _Client(db) as http:
        before = await http.get(INVENTORY, headers=_auth(token))
        resp = await http.post(
            CHANGE, json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}, headers=_auth(token)
        )
        body = resp.json()
        after = await http.get(INVENTORY, headers=_auth(body["access_token"]))
    assert before.status_code == 403 and before.json()["detail"] == "password_change_required"
    assert resp.status_code == 200 and body["must_change_password"] is False and body["token_type"] == "bearer"
    assert after.status_code == 200
    assert verify_password(db.accounts[1].password_argon2_hash, NEW_PASSWORD)
    assert db.accounts[1].password_must_change is False


async def test_change_password_rejections_401_422_422(redis):
    db = StatefulDb()
    db.add()
    token = _fresh_token()
    async with _Client(db) as http:
        wrong = await http.post(
            CHANGE, json={"current_password": "not-the-password-1", "new_password": NEW_PASSWORD}, headers=_auth(token)
        )
        short = await http.post(
            CHANGE, json={"current_password": PASSWORD, "new_password": "short"}, headers=_auth(token)
        )
        common = await http.post(
            CHANGE, json={"current_password": PASSWORD, "new_password": "passwordpassword"}, headers=_auth(token)
        )
        same = await http.post(
            CHANGE, json={"current_password": PASSWORD, "new_password": PASSWORD}, headers=_auth(token)
        )
    assert (wrong.status_code, wrong.json()["detail"]) == (401, "viewer_invalid_current_password")
    assert (short.status_code, short.json()["detail"]) == (422, "password_too_short")
    assert common.status_code == 422 and common.json()["detail"] == "password_too_common"
    assert (same.status_code, same.json()["detail"]) == (422, "password_same_as_current")
    assert verify_password(db.accounts[1].password_argon2_hash, PASSWORD)  # 変わっていない


async def test_change_password_null_hash_is_401(redis):
    db = StatefulDb()
    db.add(hashed=None)
    async with _Client(db) as http:
        resp = await http.post(
            CHANGE,
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            headers=_auth(_fresh_token()),
        )
    assert resp.status_code == 401 and resp.json()["detail"] == "viewer_invalid_current_password"


async def test_change_password_locked_ip_gets_429(redis):
    db = StatefulDb()
    db.add()
    async with _Client(db) as http:
        for _ in range(10):
            await cache.record_auth_failure("10.0.0.1")
        resp = await http.post(
            CHANGE,
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            headers=_auth(_fresh_token()),
        )
    assert resp.status_code == 429 and resp.json()["detail"] == "viewer_too_many_attempts"


async def test_token_issued_before_password_change_gets_401(redis):
    redis.store[vic.CACHE_KEY] = "{}"
    db = StatefulDb()
    db.add()
    old = _token_with_iat(1, int(time.time()) - 5)
    async with _Client(db) as http:
        ok_before = await http.get(INVENTORY, headers=_auth(old))
        changed = await http.post(
            CHANGE, json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}, headers=_auth(old)
        )
        old_after = await http.get(INVENTORY, headers=_auth(old))
        new_after = await http.get(INVENTORY, headers=_auth(changed.json()["access_token"]))
    assert ok_before.status_code == 200 and changed.status_code == 200
    assert old_after.status_code == 401
    assert new_after.status_code == 200


async def test_iat_floor_comparison_boundaries(redis):
    """password_changed_at が XX:XX:XX.700 のとき、同じ秒の iat は通り、1 秒前は 401。"""
    redis.store[vic.CACHE_KEY] = "{}"
    db = StatefulDb()
    acct = db.add()
    base = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=700000)
    acct.password_changed_at = base
    iat_ok = int(base.replace(microsecond=0).timestamp())
    async with _Client(db) as http:
        same_second = await http.get(INVENTORY, headers=_auth(_token_with_iat(1, iat_ok)))
        earlier = await http.get(INVENTORY, headers=_auth(_token_with_iat(1, iat_ok - 1)))
    assert same_second.status_code == 200
    assert earlier.status_code == 401


async def test_token_in_change_response_works_immediately(redis):
    """応答のトークンで、すぐ（同じ秒でも）inventory が 200。:now をトークン作成より前に取っているため。"""
    redis.store[vic.CACHE_KEY] = "{}"
    db = StatefulDb()
    db.add()
    async with _Client(db) as http:
        for _ in range(3):
            resp = await http.post(
                CHANGE,
                json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
                headers=_auth(_fresh_token()),
            )
            assert resp.status_code == 200
            got = await http.get(INVENTORY, headers=_auth(resp.json()["access_token"]))
            assert got.status_code == 200
            db.accounts[1].password_argon2_hash = _HASH  # 次の周回のために戻す


# ── 再発行 request ────────────────────────────────────────────


async def test_reset_mail_goes_only_to_trial_and_active(redis, mail):
    now = datetime.now(timezone.utc)
    db = StatefulDb()
    db.add(1, "active@x.com", "active")
    db.add(2, "trial@x.com", "trial", trial_expires_at=now + timedelta(days=3))
    db.add(3, "expired@x.com", "trial", trial_expires_at=now - timedelta(days=3))
    db.add(4, "pending@x.com", "pending")
    db.add(5, "suspended@x.com", "suspended")
    emails = ["active@x.com", "trial@x.com", "expired@x.com", "pending@x.com", "suspended@x.com", "nobody@x.com"]
    async with _Client(db) as http:
        resps = [await http.post(REQUEST, json={"email": e}, headers=_headers()) for e in emails]
    assert all(r.status_code == 200 and r.json() == {"status": "accepted"} for r in resps)
    assert [c.args[0] for c in mail.call_args_list] == ["active@x.com", "trial@x.com", "expired@x.com"]


async def test_reset_request_event_and_token_row_use_real_ip(redis, mail):
    db = StatefulDb()
    db.add()
    async with _Client(db) as http:
        await http.post(REQUEST, json={"email": " A@x.com "}, headers=_headers("10.7.0.1"))
    assert [(e["viewer_id"], e["event_type"], e["ip"]) for e in db.events] == [(1, "password_reset_requested", "10.7.0.1")]
    raw = _raw_from_mail(mail)
    assert [t["token_sha256"] for t in db.tokens] == [hashlib.sha256(raw.encode()).digest()]
    assert raw not in str(db.tokens)  # 鍵そのものは保存しない


async def test_fourth_request_for_same_email_sends_no_mail(redis, mail):
    db = StatefulDb()
    db.add()
    async with _Client(db) as http:
        codes = [(await http.post(REQUEST, json={"email": "a@x.com"}, headers=_headers())).status_code for _ in range(5)]
    assert codes == [200] * 5
    assert mail.call_count == 3
    assert any(k.startswith("viewer_pw_reset_req:") for k in redis.store)
    assert not any(k.startswith("pw_reset_req:") for k in redis.store)  # アプリ側とは別のキー


async def test_reset_request_invalid_email_is_200_without_mail(redis, mail):
    async with _Client(StatefulDb()) as http:
        resp = await http.post(REQUEST, json={"email": "not an email"}, headers=_headers())
    assert resp.status_code == 200 and resp.json() == {"status": "accepted"} and mail.call_count == 0


async def test_new_reset_request_invalidates_previous_token(redis, mail):
    db = StatefulDb()
    db.add()
    async with _Client(db) as http:
        await http.post(REQUEST, json={"email": "a@x.com"}, headers=_headers())
        first = _raw_from_mail(mail)
        await http.post(REQUEST, json={"email": "a@x.com"}, headers=_headers())
        second = _raw_from_mail(mail)
        old = await http.post(CONFIRM, json={"token": first, "new_password": NEW_PASSWORD}, headers=_headers())
        new = await http.post(CONFIRM, json={"token": second, "new_password": NEW_PASSWORD}, headers=_headers())
    assert first != second
    assert (old.status_code, old.json()["detail"]) == (400, "viewer_reset_invalid_or_expired")
    assert new.status_code == 200


# ── 再発行 confirm ────────────────────────────────────────────


async def test_confirm_updates_password_once_and_returns_no_login_token(redis):
    db = StatefulDb()
    db.add(must_change=True)
    db.add_token(1, "raw-token-1")
    async with _Client(db) as http:
        ok = await http.post(CONFIRM, json={"token": "raw-token-1", "new_password": NEW_PASSWORD}, headers=_headers())
        again = await http.post(CONFIRM, json={"token": "raw-token-1", "new_password": NEW_PASSWORD}, headers=_headers())
    assert ok.status_code == 200 and ok.json() == {"status": "password_updated"}  # 12時間トークンは返さない
    assert (again.status_code, again.json()["detail"]) == (400, "viewer_reset_invalid_or_expired")
    assert verify_password(db.accounts[1].password_argon2_hash, NEW_PASSWORD)
    assert db.accounts[1].password_must_change is False and db.accounts[1].password_changed_at is not None


async def test_confirm_token_expires_after_30_minutes(redis):
    db = StatefulDb()
    db.add()
    db.add_token(1, "fresh", expires_in=timedelta(minutes=29))
    db.add_token(1, "stale", expires_in=timedelta(seconds=-1))
    async with _Client(db) as http:
        stale = await http.post(CONFIRM, json={"token": "stale", "new_password": NEW_PASSWORD}, headers=_headers())
        fresh = await http.post(CONFIRM, json={"token": "fresh", "new_password": NEW_PASSWORD}, headers=_headers())
    assert stale.status_code == 400 and fresh.status_code == 200


async def test_request_token_lives_30_minutes(redis, mail):
    db = StatefulDb()
    db.add()
    async with _Client(db) as http:
        await http.post(REQUEST, json={"email": "a@x.com"}, headers=_headers())
    remaining = db.tokens[0]["expires_at"] - datetime.now(timezone.utc)
    assert timedelta(minutes=29) < remaining <= timedelta(minutes=30)


async def test_signup_code_token_cannot_confirm_reset(redis):
    db = StatefulDb()
    db.add()
    db.add_token(1, "signup-raw", purpose="signup_code")
    async with _Client(db) as http:
        resp = await http.post(CONFIRM, json={"token": "signup-raw", "new_password": NEW_PASSWORD}, headers=_headers())
    assert resp.status_code == 400 and len(db.tokens) == 1  # 申込コードは消費されない


async def test_confirm_policy_failure_does_not_consume_token(redis):
    db = StatefulDb()
    db.add()
    db.add_token(1, "raw-token-2")
    async with _Client(db) as http:
        bad = await http.post(CONFIRM, json={"token": "raw-token-2", "new_password": "short"}, headers=_headers())
        good = await http.post(CONFIRM, json={"token": "raw-token-2", "new_password": NEW_PASSWORD}, headers=_headers())
    assert (bad.status_code, bad.json()["detail"]) == (422, "password_too_short")
    assert good.status_code == 200


async def test_confirm_for_suspended_account_consumes_token_but_fails(redis):
    db = StatefulDb()
    db.add(status="suspended")
    db.add_token(1, "raw-token-3")
    async with _Client(db) as http:
        resp = await http.post(CONFIRM, json={"token": "raw-token-3", "new_password": NEW_PASSWORD}, headers=_headers())
    assert resp.status_code == 400 and db.tokens == [] and verify_password(db.accounts[1].password_argon2_hash, PASSWORD)


async def test_old_login_token_is_401_after_reset(redis):
    redis.store[vic.CACHE_KEY] = "{}"
    db = StatefulDb()
    db.add()
    db.add_token(1, "raw-token-4")
    old = _token_with_iat(1, int(time.time()) - 5)
    async with _Client(db) as http:
        before = await http.get(INVENTORY, headers=_auth(old))
        await http.post(CONFIRM, json={"token": "raw-token-4", "new_password": NEW_PASSWORD}, headers=_headers())
        after = await http.get(INVENTORY, headers=_auth(old))
    assert before.status_code == 200 and after.status_code == 401


async def test_confirm_failure_counts_toward_ip_lock(redis):
    db = StatefulDb()
    db.add()
    async with _Client(db) as http:
        codes = [
            (await http.post(CONFIRM, json={"token": f"nope{i}", "new_password": NEW_PASSWORD}, headers=_headers("10.8.0.1"))).status_code
            for i in range(10)
        ]
        locked = await http.post(CONFIRM, json={"token": "nope", "new_password": NEW_PASSWORD}, headers=_headers("10.8.0.1"))
    assert codes == [400] * 10 and locked.status_code == 429


async def test_get_viewer_page_does_not_touch_reset_token_then_confirm_works(redis):
    """再発行のリンクを GET で何度開いても鍵に触れない（メールのリンク先読みで鍵が消えない）こと。"""
    db = StatefulDb()
    db.add()
    db.add_token(1, "raw-token-5")
    async with _Client(db) as http:
        for _ in range(2):
            await http.get("/viewer/", headers={"X-Real-IP": "10.0.0.1"})
        assert len(db.tokens) == 1
        resp = await http.post(CONFIRM, json={"token": "raw-token-5", "new_password": NEW_PASSWORD}, headers=_headers())
    assert resp.status_code == 200


# ── Origin・ログイン記録 ───────────────────────────────────────


async def test_request_and_confirm_403_when_origin_differs(redis):
    bad = {"Origin": "https://evil.example", "X-Real-IP": "10.0.0.1"}
    async with _Client(StatefulDb()) as http:
        req = await http.post(REQUEST, json={"email": "a@x.com"}, headers=bad)
        conf = await http.post(CONFIRM, json={"token": "t", "new_password": NEW_PASSWORD}, headers=bad)
    assert (req.status_code, req.json()["detail"]) == (403, "forbidden_origin")
    assert (conf.status_code, conf.json()["detail"]) == (403, "forbidden_origin")


async def test_login_events_for_change_request_and_done(redis, mail):
    db = StatefulDb()
    db.add()
    async with _Client(db) as http:
        await http.post(
            CHANGE,
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            headers={**_auth(_fresh_token()), "X-Real-IP": "10.5.0.1"},
        )
        await http.post(REQUEST, json={"email": "a@x.com"}, headers=_headers("10.5.0.2"))
        raw = _raw_from_mail(mail)
        await http.post(CONFIRM, json={"token": raw, "new_password": PASSWORD + "-2"}, headers=_headers("10.5.0.3"))
    assert [(e["viewer_id"], e["event_type"], e["ip"]) for e in db.events] == [
        (1, "password_changed", "10.5.0.1"),
        (1, "password_reset_requested", "10.5.0.2"),
        (1, "password_reset_done", "10.5.0.3"),
    ]
    assert all(e["ua"] == "pytest-agent" for e in db.events)
