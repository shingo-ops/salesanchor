"""閲覧ページの申込（POST /signup）・申込コード・招待リンクの試験（ADR-1019 段4b・設計 D5）。

DB の形（既存に合わせた2本立て）:
  - FakeDb（test_viewer_api.py と同じく SQL 文字列で応答する状態つきの偽物）と FakeRedis: 全項目をローカルで流せる。
  - 実 PG（pg fixture・CI 専用・test_viewer_discord_trial.py の形）: 1・3・4・9 の「実際の表に書けること」だけ。
Discord は create_viewer_invite の中の discord_api_request を patch する（9 の時間切れだけ httpx の送信を patch して本体を通す）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app import cache
from app.auth import self_tokens
from app.auth.viewer_signup_code import (
    SIGNUP_CODE_ALPHABET,
    format_signup_code,
    generate_signup_code,
    normalize_signup_code,
    signup_code_sha256,
)
from app.database import get_db
from app.services import discord_rest, viewer_invite
from app.services.discord_rest import DiscordAPIError
from tests.test_super_admin_viewers import _account, _prepare, needs_ci_pg
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_viewer_api import FakeRedis

SIGNUP = "/api/v1/viewer/signup"
SECRET = "v" * 48
KEYS = {"signup_code", "expires_at", "invite_url"}


@pytest.fixture(autouse=True)
def viewer_env(monkeypatch):
    monkeypatch.setenv("AUTH_VIEWER_JWT_SECRET", SECRET)
    monkeypatch.setenv("AUTH_JWT_SECRET", "a" * 48)
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-bot-token")


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


class FakeSignupDb:
    """申込が使う SQL だけに答える、状態つきの偽 DB。commit までを「保存」とみなす必要は無いので即時反映。"""

    def __init__(self, *, users=(), viewers=(), channel_id: str | None = "2001") -> None:
        self.users = [u.lower() for u in users]
        self.viewers: list[dict] = [dict(id=i + 1, **v) for i, v in enumerate(viewers)]
        self.tokens: list[dict] = []
        self.events: list[dict] = []
        self.channel_id = channel_id
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        if "FROM public.users" in sql:
            return _Result((1,) if params["email"] in self.users else None)
        if "FROM public.viewer_discord_config" in sql:
            return _Result((self.channel_id,) if self.channel_id is not None else None)
        if "SELECT id, status FROM public.viewer_accounts" in sql:
            row = next((v for v in self.viewers if v["email"].lower() == params["email"]), None)
            return _Result(SimpleNamespace(id=row["id"], status=row["status"]) if row else None)
        if "INSERT INTO public.viewer_accounts" in sql:
            new = dict(
                id=len(self.viewers) + 1, email=params["email"], line_name=params["line_name"],
                inventory_issue=params["issue"], status="pending",
            )
            self.viewers.append(new)
            return _Result(SimpleNamespace(id=new["id"]))
        if "DELETE FROM public.viewer_login_tokens" in sql:
            self.tokens = [t for t in self.tokens if t["id"] != params["id"]]
            return _Result()
        if "INSERT INTO public.viewer_login_tokens" in sql:
            self.tokens.append(dict(params))
            return _Result()
        if "INSERT INTO public.viewer_login_events" in sql:
            self.events.append(dict(params))
            return _Result()
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def _headers(ip="10.0.0.1", **extra):
    return {"Origin": self_tokens.rp_origin(), "X-Real-IP": ip, "User-Agent": "pytest-agent", **extra}


def _body(email="a@x.com", **extra):
    return {"email": email, "line_name": "太郎", **extra}


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


def _invite_patch(result=None, side_effect=None):
    return patch.object(
        viewer_invite,
        "discord_api_request",
        new=AsyncMock(return_value=result if result is not None else {"code": "abc123"}, side_effect=side_effect),
    )


async def _post(db, body, headers=None, ip="10.0.0.1"):
    async with _Client(db) as http:
        return await http.post(SIGNUP, json=body, headers=headers or _headers(ip))


def _hash_of(signup_code: str) -> bytes:
    return signup_code_sha256(normalize_signup_code(signup_code))


# ── 12. コードの生成 ────────────────────────────────────────────


def test_generate_signup_code_shape_and_roundtrip():
    for _ in range(50):
        code = generate_signup_code()
        assert len(code) == 16 and set(code) <= set(SIGNUP_CODE_ALPHABET)
        assert normalize_signup_code(code) == code
        shown = format_signup_code(code)
        assert len(shown) == 19 and shown.count("-") == 3
        assert normalize_signup_code(shown) == code


# ── 1・2・3. 新規・同じ人・再申込（FakeDb） ──────────────────────


async def test_new_signup_creates_pending_row_token_and_event(redis):
    db = FakeSignupDb()
    body = {"email": " A@X.com ", "line_name": "  太郎  ", "inventory_issue": "  困る  "}
    with _invite_patch() as invite:
        resp = await _post(db, body, ip="10.9.9.9")
    assert resp.status_code == 200 and set(resp.json()) == KEYS
    assert resp.json()["invite_url"] == "https://discord.gg/abc123"
    assert len(db.viewers) == 1
    v = db.viewers[0]
    assert (v["email"], v["line_name"], v["inventory_issue"], v["status"]) == ("a@x.com", "太郎", "困る", "pending")
    assert len(db.tokens) == 1
    assert db.tokens[0]["h"] == _hash_of(resp.json()["signup_code"])
    exp = db.tokens[0]["exp"]
    assert abs((exp - (datetime.now(timezone.utc) + timedelta(days=7))).total_seconds()) < 60
    assert [(e["event_type"], e["ip"]) for e in db.events] == [("signup", "10.9.9.9")]
    assert invite.await_count == 1 and db.commits == 1


async def test_same_person_with_spaces_and_case_is_a_resubmission(redis):
    db = FakeSignupDb()
    with _invite_patch():
        r1 = await _post(db, _body(email=" A@x.com "))
        r2 = await _post(db, _body(email="a@x.com"))
    assert r1.status_code == r2.status_code == 200
    assert len(db.viewers) == 1 and len(db.tokens) == 1


async def test_pending_resubmission_replaces_the_old_code_and_keeps_fields(redis):
    db = FakeSignupDb(viewers=[dict(email="a@x.com", line_name="最初", inventory_issue=None, status="pending")])
    with _invite_patch():
        r1 = await _post(db, _body(line_name="別名"))
        r2 = await _post(db, _body(line_name="別名"))
    assert r1.json()["signup_code"] != r2.json()["signup_code"]
    assert [t["h"] for t in db.tokens] == [_hash_of(r2.json()["signup_code"])]
    assert db.viewers[0]["line_name"] == "最初"


# ── 4. 登録済み・users にある email（FakeDb） ────────────────────


@pytest.mark.parametrize("status", ["trial", "active", "suspended", "verified"])
async def test_non_pending_viewer_gets_a_throwaway_code(redis, status):
    db = FakeSignupDb(viewers=[dict(email="a@x.com", line_name="x", inventory_issue=None, status=status)])
    with _invite_patch() as invite:
        resp = await _post(db, _body())
    assert resp.status_code == 200 and set(resp.json()) == KEYS
    assert resp.json()["invite_url"] == "https://discord.gg/abc123"  # 5 以外は招待を作る（形から分からない）
    assert db.tokens == [] and db.events == [] and len(db.viewers) == 1 and db.commits == 0
    assert invite.await_count == 1


async def test_email_in_app_users_gets_a_throwaway_code(redis):
    db = FakeSignupDb(users=["boss@example.com"])
    with _invite_patch():
        resp = await _post(db, _body(email="BOSS@example.com"))
    assert resp.status_code == 200 and set(resp.json()) == KEYS
    assert db.viewers == [] and db.tokens == []


# ── 5. 隠し欄 ─────────────────────────────────────────────────


async def test_honeypot_creates_nothing_and_never_calls_discord(redis):
    db = FakeSignupDb()
    with _invite_patch() as invite:
        resp = await _post(db, _body(website="http://spam"))
    assert resp.status_code == 200 and set(resp.json()) == KEYS and resp.json()["invite_url"] is None
    assert db.viewers == [] and db.tokens == [] and invite.await_count == 0


# ── 6. 回数制限 ───────────────────────────────────────────────


async def test_fourth_signup_for_the_same_email_is_429(redis):
    db = FakeSignupDb()
    with _invite_patch():
        codes = [(await _post(db, _body(), ip=f"10.0.1.{i}")).status_code for i in range(4)]
    assert codes == [200, 200, 200, 429]


async def test_eleventh_signup_from_the_same_ip_is_429(redis):
    db = FakeSignupDb()
    with _invite_patch():
        codes = [(await _post(db, _body(email=f"u{i}@x.com"))).status_code for i in range(11)]
    assert codes == [200] * 10 + [429]


# ── 7. 入力の検査 ─────────────────────────────────────────────


async def test_wrong_origin_is_403(redis):
    resp = await _post(FakeSignupDb(), _body(), headers={"Origin": "https://evil.example", "X-Real-IP": "10.0.0.1"})
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        {"email": "", "line_name": "x"},
        {"email": "not-an-email", "line_name": "x"},
        {"email": "a@x.com", "line_name": "   "},
        {"email": "a@x.com", "line_name": "あ" * 101},
        {"email": "a@x.com", "line_name": "x", "inventory_issue": "a" * 1001},
    ],
)
async def test_invalid_input_is_422(redis, body):
    db = FakeSignupDb()
    resp = await _post(db, body)
    assert resp.status_code == 422 and db.viewers == []


async def test_discord_user_id_in_body_is_ignored(redis):
    db = FakeSignupDb()
    with _invite_patch():
        resp = await _post(db, _body(discord_user_id="123456789"))
    assert resp.status_code == 200
    assert "discord_user_id" not in db.viewers[0] and "123456789" not in json.dumps(db.tokens, default=str)


# ── 8. 招待の呼び出し ─────────────────────────────────────────


async def test_invite_call_shape(redis):
    db = FakeSignupDb(channel_id="2001")
    with _invite_patch(result={"code": "zzz9"}) as invite:
        url = await viewer_invite.create_viewer_invite(db)
    assert url == "https://discord.gg/zzz9"
    kwargs = invite.await_args.kwargs
    assert kwargs["method"] == "POST" and kwargs["path"] == "/channels/2001/invites"
    assert kwargs["json"] == {"max_age": 604800, "max_uses": 1, "unique": True}
    assert kwargs["max_retries"] == 1 and kwargs["expected_statuses"] == (200,)
    assert db.rollbacks == 1


# ── 9. 招待の失敗でも申込は成功 ──────────────────────────────


@pytest.mark.parametrize("status", [403, 429, 500])
async def test_invite_api_errors_still_return_200_with_null(redis, status):
    db = FakeSignupDb()
    with _invite_patch(side_effect=DiscordAPIError("x", status_code=status)) as invite:
        resp = await _post(db, _body())
    assert resp.status_code == 200 and resp.json()["invite_url"] is None
    assert invite.await_count == 1 and len(db.tokens) == 1


async def test_invite_timeout_goes_through_the_real_helper_with_one_call(redis):
    db = FakeSignupDb()
    send = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
    fake_client = AsyncMock()
    fake_client.request = send
    fake_cls = MagicMock()
    fake_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
    fake_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    # テスト用の HTTP クライアントは本物のまま、discord_rest が見る httpx だけを差し替える
    fake_httpx = SimpleNamespace(AsyncClient=fake_cls, RequestError=httpx.RequestError)
    with patch.object(discord_rest, "httpx", fake_httpx):
        resp = await _post(db, _body())
    assert resp.status_code == 200 and resp.json()["invite_url"] is None
    assert send.await_count == 1 and len(db.tokens) == 1


async def test_missing_discord_config_row_returns_null(redis):
    db = FakeSignupDb(channel_id=None)
    with _invite_patch() as invite:
        resp = await _post(db, _body())
    assert resp.status_code == 200 and resp.json()["invite_url"] is None
    assert invite.await_count == 0 and len(db.tokens) == 1


async def test_invite_failure_log_has_no_secrets(redis, caplog):
    db = FakeSignupDb()
    with _invite_patch(side_effect=DiscordAPIError("body with a@x.com", status_code=403)):
        with caplog.at_level("WARNING"):
            resp = await _post(db, _body())
    text = caplog.text
    assert "viewer invite" in text and "403" in text
    assert "a@x.com" not in text and resp.json()["signup_code"] not in text


# ── 10. Redis が使えないとき ──────────────────────────────────


async def test_without_redis_signup_succeeds_but_no_invite(monkeypatch):
    monkeypatch.setattr(cache, "_redis", None)
    db = FakeSignupDb()
    with _invite_patch() as invite:
        resp = await _post(db, _body())
    assert resp.status_code == 200 and resp.json()["invite_url"] is None
    assert invite.await_count == 0 and len(db.tokens) == 1


async def test_redis_that_raises_counts_as_unavailable(monkeypatch):
    broken = FakeRedis()
    broken.incr = AsyncMock(side_effect=RuntimeError("down"))
    monkeypatch.setattr(cache, "_redis", broken)
    assert await cache.count_viewer_signup("ip", "1.2.3.4") is None
    with _invite_patch() as invite:
        resp = await _post(FakeSignupDb(), _body())
    assert resp.status_code == 200 and invite.await_count == 0


async def test_count_keys_are_hashed_and_expire(redis):
    assert await cache.count_viewer_signup("email", "a@x.com") == 1
    key = "viewer_signup_email:" + hashlib.sha256(b"a@x.com").hexdigest()
    assert key in redis.store and redis.ttls[key] == cache.VIEWER_SIGNUP_WINDOW


# ── 11. discord_api_request の max_retries ───────────────────


async def test_default_retries_are_still_five():
    resp = httpx.Response(500, text="err")
    send = AsyncMock(return_value=resp)
    with patch.object(httpx.AsyncClient, "request", send), patch.object(discord_rest.asyncio, "sleep", new=AsyncMock()):
        with pytest.raises(DiscordAPIError):
            await discord_rest.discord_api_request(method="GET", path="/x", bot_token="t")
    assert send.await_count == 5


async def test_max_retries_one_calls_once():
    send = AsyncMock(return_value=httpx.Response(500, text="err"))
    with patch.object(httpx.AsyncClient, "request", send):
        with pytest.raises(DiscordAPIError) as exc:
            await discord_rest.discord_api_request(method="GET", path="/x", bot_token="t", max_retries=1)
    assert send.await_count == 1 and exc.value.status_code == 500


# ── 実 PG（CI 専用）: 1・3・4・9 ─────────────────────────────


def _prep(conn, async_url, *, with_config=True):
    cur = _prepare(conn, async_url)
    if with_config:
        cur.execute(
            "INSERT INTO public.viewer_discord_config (id, guild_id, reception_channel_id, "
            "ticket_category_id, staff_role_id) VALUES (1, '1001', '2001', '2002', '2003')"
        )
    return cur


def _pg_post(async_url, body, headers=None):
    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            from app.main import app

            async def _db():
                async with AsyncSession(engine, expire_on_commit=False) as session:
                    yield session

            app.dependency_overrides[get_db] = _db
            try:
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
                    return await http.post(SIGNUP, json=body, headers=headers or _headers())
            finally:
                app.dependency_overrides.pop(get_db, None)
        finally:
            await engine.dispose()

    return asyncio.run(_go())


@needs_ci_pg
def test_pg_new_signup_writes_row_token_and_event(pg, monkeypatch):  # noqa: F811
    monkeypatch.setattr(cache, "_redis", FakeRedis())
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    with _invite_patch():
        resp = _pg_post(async_url, {"email": " A@X.com ", "line_name": "  太郎 ", "discord_user_id": "999"}, _headers("10.7.7.7"))
    assert resp.status_code == 200
    cur.execute("SELECT id, email, line_name, inventory_issue, status, discord_user_id FROM public.viewer_accounts")
    rows = cur.fetchall()
    assert len(rows) == 1 and rows[0][1:] == ("a@x.com", "太郎", None, "pending", None)
    cur.execute("SELECT token_sha256, expires_at FROM public.viewer_login_tokens WHERE purpose='signup_code' AND viewer_account_id=%s", (rows[0][0],))
    tokens = cur.fetchall()
    assert len(tokens) == 1 and bytes(tokens[0][0]) == _hash_of(resp.json()["signup_code"])
    assert abs((tokens[0][1] - (datetime.now(timezone.utc) + timedelta(days=7))).total_seconds()) < 120
    cur.execute("SELECT event_type, client_ip FROM public.viewer_login_events WHERE viewer_id=%s", (rows[0][0],))
    assert cur.fetchall() == [("signup", "10.7.7.7")]


@needs_ci_pg
def test_pg_pending_resubmission_replaces_code(pg, monkeypatch):  # noqa: F811
    monkeypatch.setattr(cache, "_redis", FakeRedis())
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    with _invite_patch():
        r1 = _pg_post(async_url, {"email": "a@x.com", "line_name": "x"})
        r2 = _pg_post(async_url, {"email": " A@x.com", "line_name": "y"})
    assert r1.json()["signup_code"] != r2.json()["signup_code"]
    cur.execute("SELECT count(*) FROM public.viewer_accounts")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT token_sha256 FROM public.viewer_login_tokens")
    assert [bytes(r[0]) for r in cur.fetchall()] == [_hash_of(r2.json()["signup_code"])]


@needs_ci_pg
def test_pg_registered_emails_get_throwaway_codes(pg, monkeypatch):  # noqa: F811
    monkeypatch.setattr(cache, "_redis", FakeRedis())
    conn, _, async_url = pg
    cur = _prep(conn, async_url)
    for i, status in enumerate(("trial", "active", "suspended", "verified")):
        _account(cur, f"s{i}@x.com", status, expires_in_days=5 if status == "trial" else None)
    with _invite_patch():
        for i in range(4):
            resp = _pg_post(async_url, {"email": f"S{i}@x.com", "line_name": "x"})
            assert resp.status_code == 200 and set(resp.json()) == KEYS
        resp = _pg_post(async_url, {"email": "TEST@example.com", "line_name": "x"})  # public.users にある email
        assert resp.status_code == 200 and set(resp.json()) == KEYS
    cur.execute("SELECT count(*) FROM public.viewer_accounts")
    assert cur.fetchone()[0] == 4
    cur.execute("SELECT count(*) FROM public.viewer_login_tokens")
    assert cur.fetchone()[0] == 0


@needs_ci_pg
def test_pg_missing_config_row_still_returns_200_with_code(pg, monkeypatch):  # noqa: F811
    monkeypatch.setattr(cache, "_redis", FakeRedis())
    conn, _, async_url = pg
    cur = _prep(conn, async_url, with_config=False)
    resp = _pg_post(async_url, {"email": "a@x.com", "line_name": "x"})
    assert resp.status_code == 200 and resp.json()["invite_url"] is None
    cur.execute("SELECT count(*) FROM public.viewer_login_tokens")
    assert cur.fetchone()[0] == 1
