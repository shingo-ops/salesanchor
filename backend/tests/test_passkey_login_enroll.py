"""ログイン直後のパスキー登録（ADR-1013 便6）のテスト。SQLite で動かす。py_webauthn の照合は差し替える。"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth import passkeys, self_tokens
from app.auth.dependencies import get_current_user

SECRET = "test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
ORIGIN = "https://app.salesanchor.jp"
AUTH_PATH = "/api/v1/auth"
USER_ID = 2201
OTHER_USER_ID = 2202
EMAIL = "enroll-user@example.com"
TEST_USER_ID_FLOOR = 2200

_USERS = sa.table("users", sa.column("id"))
_CREDS = sa.table("webauthn_credentials", sa.column("id"))
_SKIPS = sa.table("passkey_enroll_prompt_skips", sa.column("id"))


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        self.data[key] = value

    async def getdel(self, key):
        return self.data.pop(key, None)


@pytest.fixture(autouse=True)
def enroll_env(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    monkeypatch.setenv("AUTH_JWT_SECRET", SECRET)
    monkeypatch.delenv("AUTH_JWT_SECRET_PREVIOUS", raising=False)
    monkeypatch.delenv("AUTH_RP_ORIGIN", raising=False)
    monkeypatch.delenv("AUTH_RP_ID", raising=False)


@pytest.fixture(autouse=True)
def no_redis_limits():
    with patch("app.routers.auth.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.routers.auth.record_auth_failure", new=AsyncMock()), \
         patch("app.routers.auth.blacklist_token", new=AsyncMock(return_value=True)):
        yield


@pytest.fixture
def redis():
    fake = FakeRedis()
    with patch("app.auth.passkeys.get_redis", return_value=fake):
        yield fake


@pytest.fixture
def audit():
    mock = AsyncMock()
    with patch("app.routers.auth.record_audit_log", new=mock):
        yield mock


@pytest.fixture(autouse=True)
async def cleanup_enroll(db_session):
    yield
    await db_session.rollback()
    await db_session.execute(sa.delete(_SKIPS))
    await db_session.execute(sa.delete(_CREDS))
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
    async with AsyncClient(transport=transport, base_url=ORIGIN) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def as_user():
    from app.main import app

    holder = {"user": SimpleNamespace(id=USER_ID, email=EMAIL, tenant_id=999)}
    app.dependency_overrides[get_current_user] = lambda: holder["user"]
    yield holder
    app.dependency_overrides.pop(get_current_user, None)


async def _insert_user(db, user_id=USER_ID, email=EMAIL):
    await db.execute(
        text(
            "INSERT INTO users (id, tenant_id, username, email, is_active) "
            "VALUES (:id, 999, :un, :email, TRUE)"
        ),
        {"id": user_id, "un": f"u{user_id}", "email": email},
    )
    await db.commit()


async def _insert_cred(db, n, user_id=USER_ID):
    await db.execute(
        text(
            "INSERT INTO public.webauthn_credentials (user_id, credential_id, public_key, sign_count) "
            "VALUES (:uid, :cid, :pk, 0)"
        ),
        {"uid": user_id, "cid": f"cred-enroll-{n:04d}".encode(), "pk": b"public-key"},
    )
    await db.commit()


async def _insert_skip(db, days_ago, user_id=USER_ID):
    at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    await db.execute(
        text("INSERT INTO public.passkey_enroll_prompt_skips (user_id, skipped_at) VALUES (:uid, :at)"),
        {"uid": user_id, "at": at.replace(tzinfo=None)},
    )
    await db.commit()


def _token(amr, age_seconds=0, user_id=USER_ID):
    """age_seconds 前に発行された合図を作る。"""

    class _FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) - timedelta(seconds=age_seconds)

    with patch("app.auth.self_tokens.datetime", _FakeDatetime):
        return self_tokens.create_access_token(user_id, EMAIL, amr)


def _headers(token=None, origin=ORIGIN):
    h = {"origin": origin}
    if token:
        h["authorization"] = f"Bearer {token}"
    return h


async def _prompt(http, token):
    return await http.get(f"{AUTH_PATH}/passkey/prompt", headers=_headers(token))


# ── T1 パスワード直後 ─────────────────────────────────────────


async def test_t1_fresh_password_login_can_auto_and_show_prompt(http, db_session, as_user):
    await _insert_user(db_session)
    resp = await _prompt(http, _token("pwd"))
    assert resp.status_code == 200
    assert resp.json() == {"can_auto": True, "show_prompt": True}


# ── T2 合図の種類・古さ ───────────────────────────────────────


@pytest.mark.parametrize(
    "token_args",
    [
        {"amr": None},
        {"amr": "webauthn"},
        {"amr": "pwd", "age_seconds": 301},
    ],
)
async def test_t2_not_fresh_is_rejected(http, db_session, as_user, redis, token_args):
    await _insert_user(db_session)
    token = _token(**token_args)
    resp = await _prompt(http, token)
    assert resp.status_code == 200
    assert resp.json() == {"can_auto": False, "show_prompt": False}

    opts = await http.post(
        f"{AUTH_PATH}/passkey/register/options", json={"auto": True}, headers=_headers(token)
    )
    assert opts.status_code == 403
    assert opts.json()["detail"] == "auto_not_allowed"

    skip = await http.post(f"{AUTH_PATH}/passkey/prompt/skip", headers=_headers(token))
    assert skip.status_code == 403
    assert skip.json()["detail"] == "auto_not_allowed"


# ── T3 auto=false / 本文なしは今のまま ────────────────────────


async def test_t3_options_without_auto_unchanged(http, db_session, as_user, redis):
    await _insert_user(db_session)
    token = _token(None)
    for kwargs in ({"json": {"auto": False}}, {}):
        resp = await http.post(f"{AUTH_PATH}/passkey/register/options", headers=_headers(token), **kwargs)
        assert resp.status_code == 200
        cid = resp.json()["challenge_id"]
        assert f"passkey_chal:reg:{USER_ID}:{cid}" in redis.data


async def test_t3_auto_options_store_reg_auto(http, db_session, as_user, redis):
    await _insert_user(db_session)
    resp = await http.post(
        f"{AUTH_PATH}/passkey/register/options", json={"auto": True}, headers=_headers(_token("pwd"))
    )
    assert resp.status_code == 200
    cid = resp.json()["challenge_id"]
    assert f"passkey_chal:reg_auto:{USER_ID}:{cid}" in redis.data


# ── T4 スキップ 6 か月 3 回 ───────────────────────────────────


async def test_t4_skip_limit(http, db_session, as_user):
    await _insert_user(db_session)
    token = _token("pwd")
    await _insert_skip(db_session, 1)
    await _insert_skip(db_session, 2)
    assert (await _prompt(http, token)).json()["show_prompt"] is True

    skip = await http.post(f"{AUTH_PATH}/passkey/prompt/skip", headers=_headers(token))
    assert skip.status_code == 204
    assert (await _prompt(http, token)).json()["show_prompt"] is False


async def test_t4_old_skips_not_counted(http, db_session, as_user):
    await _insert_user(db_session)
    for _ in range(3):
        await _insert_skip(db_session, 181)
    resp = await _prompt(http, _token("pwd"))
    assert resp.json()["show_prompt"] is True


# ── T5 パスキー保有数 ─────────────────────────────────────────


async def test_t5_has_passkey_and_limit(http, db_session, as_user):
    await _insert_user(db_session)
    token = _token("pwd")
    await _insert_cred(db_session, 0)
    assert (await _prompt(http, token)).json() == {"can_auto": True, "show_prompt": False}
    for n in range(1, passkeys.MAX_PASSKEYS_PER_USER):
        await _insert_cred(db_session, n)
    assert (await _prompt(http, token)).json() == {"can_auto": False, "show_prompt": False}


# ── T6 verify の要求 ──────────────────────────────────────────


def _verified():
    return SimpleNamespace(
        credential_id=b"cred-new-enroll01",
        credential_public_key=b"pk",
        sign_count=0,
        credential_device_type=SimpleNamespace(),
        credential_backed_up=False,
        aaguid="",
    )


@pytest.mark.parametrize("kind,auto", [("reg_auto", True), ("reg", False)])
async def test_t6_verify_requirements(http, db_session, as_user, redis, audit, kind, auto):
    await _insert_user(db_session)
    cid = await passkeys.store_challenge(kind, str(USER_ID), b"challenge-bytes")
    parsed = SimpleNamespace(response=SimpleNamespace(transports=[]))
    with patch("app.routers.auth.parse_registration_credential_json", return_value=parsed), \
         patch("app.routers.auth.verify_registration_response", return_value=_verified()) as verify:
        resp = await http.post(
            f"{AUTH_PATH}/passkey/register/verify",
            json={"challenge_id": cid, "credential": {"id": "x"}, "label": ""},
            headers=_headers(_token("pwd")),
        )
    assert resp.status_code == 201, resp.text
    kwargs = verify.call_args.kwargs
    if auto:
        assert kwargs["require_user_presence"] is False
        assert kwargs["require_user_verification"] is False
    else:
        assert kwargs["require_user_verification"] is True
        assert "require_user_presence" not in kwargs
    assert audit.await_args_list[-1].kwargs["new_data"]["auto"] is auto


# ── T7 他人・取り違え ─────────────────────────────────────────


async def test_t7_other_users_challenge_rejected(http, db_session, as_user, redis, audit):
    await _insert_user(db_session)
    cid = await passkeys.store_challenge("reg_auto", str(OTHER_USER_ID), b"challenge-bytes")
    with patch("app.routers.auth.parse_registration_credential_json"), \
         patch("app.routers.auth.verify_registration_response") as verify:
        resp = await http.post(
            f"{AUTH_PATH}/passkey/register/verify",
            json={"challenge_id": cid, "credential": {"id": "x"}},
            headers=_headers(_token("pwd")),
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "challenge_expired"
    verify.assert_not_called()


async def test_t7_login_challenge_not_taken_as_registration(http, db_session, as_user, redis, audit):
    await _insert_user(db_session)
    cid = await passkeys.store_challenge("login", str(USER_ID), b"challenge-bytes")
    resp = await http.post(
        f"{AUTH_PATH}/passkey/register/verify",
        json={"challenge_id": cid, "credential": {"id": "x"}},
        headers=_headers(_token("pwd")),
    )
    assert resp.status_code == 400
