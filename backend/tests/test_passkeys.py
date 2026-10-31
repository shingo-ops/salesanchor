"""パスキー（ADR-1013 便5）のテスト。SQLite で動かす。py_webauthn の照合は差し替え、実物の暗号は使わない。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidJSONStructure
from webauthn.helpers.structs import CredentialDeviceType

from app.auth import passkeys
from app.auth.dependencies import get_current_user

SECRET = "test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
ORIGIN = "https://app.salesanchor.jp"
AUTH_PATH = "/api/v1/auth"
USER_ID = 2101
OTHER_USER_ID = 2102
EMAIL = "passkey-user@example.com"
OTHER_EMAIL = "passkey-other@example.com"
TEST_USER_ID_FLOOR = 2100
CRED_ID = b"cred-id-aaaaaaaa"
NEW_CRED_ID = b"cred-id-new-0001"

_USERS = sa.table("users", sa.column("id"))
_REFRESH = sa.table("auth_refresh_tokens", sa.column("id"))
_CREDS = sa.table("webauthn_credentials", sa.column("id"))


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.ttl = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        self.data[key] = value
        self.ttl[key] = ex

    async def getdel(self, key):
        return self.data.pop(key, None)


@pytest.fixture(autouse=True)
def passkey_env(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    monkeypatch.setenv("AUTH_JWT_SECRET", SECRET)
    monkeypatch.delenv("AUTH_JWT_SECRET_PREVIOUS", raising=False)
    monkeypatch.delenv("AUTH_RP_ORIGIN", raising=False)
    monkeypatch.delenv("AUTH_RP_ID", raising=False)
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)


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


def events(audit_mock):
    return [c.kwargs["new_data"]["event"] for c in audit_mock.await_args_list]


@pytest.fixture(autouse=True)
async def cleanup_passkeys(db_session):
    yield
    await db_session.rollback()
    await db_session.execute(sa.delete(_CREDS))
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


@pytest.fixture
def as_user():
    from app.main import app

    holder = {"user": SimpleNamespace(id=USER_ID, email=EMAIL, tenant_id=999)}
    app.dependency_overrides[get_current_user] = lambda: holder["user"]
    yield holder
    app.dependency_overrides.pop(get_current_user, None)


async def _insert_user(db, user_id=USER_ID, email=EMAIL, is_active=True):
    await db.execute(
        text(
            "INSERT INTO users (id, tenant_id, username, email, is_active) "
            "VALUES (:id, 999, :un, :email, :act)"
        ),
        {"id": user_id, "un": f"u{user_id}", "email": email, "act": is_active},
    )
    await db.commit()


async def _insert_cred(db, user_id=USER_ID, cred_id=CRED_ID, sign_count=5, label=None):
    row = (
        await db.execute(
            text(
                "INSERT INTO public.webauthn_credentials (user_id, credential_id, public_key, sign_count, label) "
                "VALUES (:uid, :cid, :pk, :sc, :label) RETURNING id"
            ),
            {"uid": user_id, "cid": cred_id, "pk": b"public-key", "sc": sign_count, "label": label},
        )
    ).one()
    await db.commit()
    return row.id


async def _row(db, sql, **params):
    return (await db.execute(text(sql), params)).first()


def _headers(origin=ORIGIN):
    return {"origin": origin} if origin else {}


def _login_credential(user_id=USER_ID, raw_id=CRED_ID):
    return SimpleNamespace(
        raw_id=raw_id,
        response=SimpleNamespace(user_handle=passkeys.user_handle(user_id)),
    )


async def _login_options(http, redis):
    resp = await http.post(f"{AUTH_PATH}/passkey/login/options", headers=_headers())
    assert resp.status_code == 200
    return resp.json()["challenge_id"]


def _verified(new_sign_count):
    return SimpleNamespace(new_sign_count=new_sign_count, credential_backed_up=True)


async def _login_verify(http, challenge_id, credential=None):
    return await http.post(
        f"{AUTH_PATH}/passkey/login/verify",
        json={"challenge_id": challenge_id, "credential": credential or {"id": "x"}},
        headers=_headers(),
    )


@pytest.fixture
def login_patches():
    """parse / verify を差し替える。verify の返り値は holder["verified"] で変える。"""
    holder = {
        "parsed": _login_credential(),
        "verified": _verified(6),
        "verify_calls": [],
    }

    def fake_verify(**kwargs):
        holder["verify_calls"].append(kwargs)
        result = holder["verified"]
        if isinstance(result, Exception):
            raise result
        return result

    with patch("app.routers.auth.parse_authentication_credential_json", side_effect=lambda c: holder["parsed"]), \
         patch("app.routers.auth.verify_authentication_response", side_effect=fake_verify):
        yield holder


# ── T1 login/options ──────────────────────────────────────────

async def test_login_options_returns_challenge_and_stores_it_for_300_seconds(http, redis):
    resp = await http.post(f"{AUTH_PATH}/passkey/login/options", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["challenge_id"]
    assert body["options"]["rpId"] == "app.salesanchor.jp"
    keys = [k for k in redis.data if k.startswith("passkey_chal:login:-:")]
    assert len(keys) == 1 and keys[0].endswith(body["challenge_id"])
    assert redis.ttl[keys[0]] == 300


# ── T2 login/verify 成功 ──────────────────────────────────────

async def test_login_verify_success_issues_webauthn_token(http, db_session, redis, login_patches):
    await _insert_user(db_session)
    cid = await _insert_cred(db_session, sign_count=5)
    chal = await _login_options(http, redis)

    resp = await _login_verify(http, chal)

    assert resp.status_code == 200
    from jose import jwt

    claims = jwt.get_unverified_claims(resp.json()["access_token"])
    assert claims["amr"] == ["webauthn"] and claims["sub"] == str(USER_ID)
    cookie = resp.headers["set-cookie"].lower()
    assert "sa_refresh=" in cookie and "httponly" in cookie
    assert "samesite=strict" in cookie and "path=/api/v1/auth" in cookie
    row = await _row(db_session, "SELECT sign_count, last_used_at FROM webauthn_credentials WHERE id = :id", id=cid)
    assert row.sign_count == 6 and row.last_used_at is not None
    user = await _row(db_session, "SELECT last_login FROM users WHERE id = :id", id=USER_ID)
    assert user.last_login is not None


# ── T3 challenge は 1 回限り ──────────────────────────────────

async def test_login_challenge_is_single_use(http, db_session, redis, login_patches):
    await _insert_user(db_session)
    await _insert_cred(db_session, sign_count=5)
    chal = await _login_options(http, redis)

    assert (await _login_verify(http, chal)).status_code == 200
    assert (await _login_verify(http, chal)).status_code == 401


# ── T4 使用回数 ───────────────────────────────────────────────

@pytest.mark.parametrize("stored,received,status,rejected", [
    (5, 5, 401, 1),
    (5, 3, 401, 1),
    (0, 0, 200, 0),
])
async def test_login_sign_count_rule(http, db_session, redis, audit, login_patches, stored, received, status, rejected):
    await _insert_user(db_session)
    await _insert_cred(db_session, sign_count=stored)
    login_patches["verified"] = _verified(received)
    chal = await _login_options(http, redis)

    resp = await _login_verify(http, chal)

    assert resp.status_code == status
    assert events(audit).count("passkey_sign_count_rejected") == rejected


# ── T4b 署名の照合失敗は使用回数の拒否にしない ────────────────

async def test_login_signature_failure_is_401_without_sign_count_audit(http, db_session, redis, audit, login_patches):
    await _insert_user(db_session)
    await _insert_cred(db_session, sign_count=5)
    login_patches["verified"] = InvalidAuthenticationResponse("bad signature")
    chal = await _login_options(http, redis)

    resp = await _login_verify(http, chal)

    assert resp.status_code == 401
    assert "passkey_sign_count_rejected" not in events(audit)
    assert login_patches["verify_calls"][0]["credential_current_sign_count"] == 0


# ── T5 持ち主・存在・停止 ─────────────────────────────────────

async def test_login_verify_rejections_share_one_response(http, db_session, redis, login_patches):
    await _insert_user(db_session)
    await _insert_user(db_session, user_id=OTHER_USER_ID, email=OTHER_EMAIL, is_active=False)
    await _insert_cred(db_session, sign_count=5)
    await _insert_cred(db_session, user_id=OTHER_USER_ID, cred_id=NEW_CRED_ID, sign_count=5)
    bodies = []

    # 表に無い credential
    login_patches["parsed"] = _login_credential(raw_id=b"unknown-cred-id!")
    resp = await _login_verify(http, await _login_options(http, redis))
    bodies.append((resp.status_code, resp.json()))

    # is_active=false の人
    login_patches["parsed"] = _login_credential(user_id=OTHER_USER_ID, raw_id=NEW_CRED_ID)
    resp = await _login_verify(http, await _login_options(http, redis))
    bodies.append((resp.status_code, resp.json()))

    # user_handle が別の人
    login_patches["parsed"] = _login_credential(user_id=OTHER_USER_ID, raw_id=CRED_ID)
    resp = await _login_verify(http, await _login_options(http, redis))
    bodies.append((resp.status_code, resp.json()))

    # user_handle が無い
    login_patches["parsed"] = SimpleNamespace(raw_id=CRED_ID, response=SimpleNamespace(user_handle=None))
    resp = await _login_verify(http, await _login_options(http, redis))
    bodies.append((resp.status_code, resp.json()))

    assert all(b == (401, {"detail": "invalid_credentials"}) for b in bodies)


# ── T5b 壊れた入力で 500 にしない ─────────────────────────────

async def test_login_verify_broken_user_handle_is_401(http, db_session, redis):
    await _insert_user(db_session)
    await _insert_cred(db_session)
    chal = await _login_options(http, redis)
    credential = {
        "id": bytes_to_base64url(CRED_ID),
        "rawId": bytes_to_base64url(CRED_ID),
        "type": "public-key",
        "response": {
            "clientDataJSON": bytes_to_base64url(b"{}"),
            "authenticatorData": bytes_to_base64url(b"auth-data"),
            "signature": bytes_to_base64url(b"sig"),
            "userHandle": "A",
        },
    }

    resp = await _login_verify(http, chal, credential)

    assert resp.status_code == 401


async def test_register_verify_broken_credential_is_400(http, redis, as_user):
    chal = await passkeys.store_challenge("reg", str(USER_ID), b"challenge-bytes")
    credential = {
        "id": "x",
        "rawId": "A",
        "type": "public-key",
        "response": {"clientDataJSON": "A", "attestationObject": "A"},
    }

    resp = await http.post(
        f"{AUTH_PATH}/passkey/register/verify",
        json={"challenge_id": chal, "credential": credential},
        headers=_headers(),
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "passkey_invalid"


# ── T6 firebase では 404 ──────────────────────────────────────

async def test_login_routes_are_404_when_provider_is_firebase(http, redis, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")

    options = await http.post(f"{AUTH_PATH}/passkey/login/options", headers=_headers())
    verify = await _login_verify(http, "x")

    assert options.status_code == 404
    assert verify.status_code == 404


# ── T7 Origin ─────────────────────────────────────────────────

@pytest.mark.parametrize("origin", ["https://evil.example.com", None])
async def test_all_write_routes_reject_bad_origin(http, redis, as_user, origin):
    headers = _headers(origin)
    cred = {"challenge_id": "c", "credential": {}}

    responses = [
        await http.post(f"{AUTH_PATH}/passkey/register/options", headers=headers),
        await http.post(f"{AUTH_PATH}/passkey/register/verify", json=cred, headers=headers),
        await http.post(f"{AUTH_PATH}/passkey/login/options", headers=headers),
        await http.post(f"{AUTH_PATH}/passkey/login/verify", json=cred, headers=headers),
        await http.delete(f"{AUTH_PATH}/passkeys/1", headers=headers),
    ]

    assert [r.status_code for r in responses] == [403] * 5


# ── T8 register ───────────────────────────────────────────────

@pytest.fixture
def register_patches():
    holder = {
        "verified": SimpleNamespace(
            credential_id=NEW_CRED_ID,
            credential_public_key=b"new-public-key",
            sign_count=0,
            credential_device_type=CredentialDeviceType.MULTI_DEVICE,
            credential_backed_up=True,
            aaguid="00000000-0000-0000-0000-000000000000",
        ),
        "parse_error": None,
    }

    def fake_parse(credential):
        if holder["parse_error"]:
            raise holder["parse_error"]
        return SimpleNamespace(response=SimpleNamespace(transports=[SimpleNamespace(value="internal")]))

    with patch("app.routers.auth.parse_registration_credential_json", side_effect=fake_parse), \
         patch("app.routers.auth.verify_registration_response", side_effect=lambda **kw: holder["verified"]):
        yield holder


async def _register(http, redis, label="  work iPhone  ", owner=USER_ID):
    chal = await passkeys.store_challenge("reg", str(owner), b"challenge-bytes")
    return await http.post(
        f"{AUTH_PATH}/passkey/register/verify",
        json={"challenge_id": chal, "credential": {"id": "x"}, "label": label},
        headers=_headers(),
    )


async def test_register_verify_inserts_row_and_audits(http, db_session, redis, audit, as_user, register_patches):
    await _insert_user(db_session)

    resp = await _register(http, redis)

    assert resp.status_code == 201
    body = resp.json()
    assert body["label"] == "work iPhone"
    row = await _row(
        db_session,
        "SELECT user_id, credential_id, transports, backup_eligible, backup_state, aaguid, label "
        "FROM webauthn_credentials WHERE id = :id",
        id=body["id"],
    )
    assert row.user_id == USER_ID and bytes(row.credential_id) == NEW_CRED_ID
    assert row.transports == '["internal"]'
    assert row.backup_eligible and row.backup_state
    assert row.aaguid == "00000000-0000-0000-0000-000000000000" and row.label == "work iPhone"
    assert events(audit).count("passkey_registered") == 1


async def test_register_verify_duplicate_credential_is_409(http, db_session, redis, as_user, register_patches):
    await _insert_user(db_session)
    await _insert_cred(db_session, cred_id=NEW_CRED_ID)

    resp = await _register(http, redis)

    assert resp.status_code == 409 and resp.json()["detail"] == "passkey_exists"


async def test_register_options_limit_is_409(http, db_session, redis, as_user):
    await _insert_user(db_session)
    for i in range(passkeys.MAX_PASSKEYS_PER_USER):
        await _insert_cred(db_session, cred_id=f"cred-limit-{i:04d}".encode())

    resp = await http.post(f"{AUTH_PATH}/passkey/register/options", headers=_headers())

    assert resp.status_code == 409 and resp.json()["detail"] == "passkey_limit"


async def test_register_options_returns_challenge(http, db_session, redis, as_user):
    await _insert_user(db_session)

    resp = await http.post(f"{AUTH_PATH}/passkey/register/options", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["options"]["rp"]["id"] == "app.salesanchor.jp"
    assert any(k.startswith(f"passkey_chal:reg:{USER_ID}:") for k in redis.data)


async def test_register_verify_other_owner_challenge_is_400(http, db_session, redis, as_user, register_patches):
    await _insert_user(db_session)

    resp = await _register(http, redis, owner=OTHER_USER_ID)

    assert resp.status_code == 400 and resp.json()["detail"] == "challenge_expired"


async def test_register_verify_parse_error_is_400(http, db_session, redis, as_user, register_patches):
    await _insert_user(db_session)
    register_patches["parse_error"] = InvalidJSONStructure("bad")

    resp = await _register(http, redis)

    assert resp.status_code == 400 and resp.json()["detail"] == "passkey_invalid"


# ── T9 一覧・削除 ─────────────────────────────────────────────

async def test_list_returns_only_own_passkeys(http, db_session, as_user):
    await _insert_user(db_session)
    await _insert_user(db_session, user_id=OTHER_USER_ID, email=OTHER_EMAIL)
    await _insert_cred(db_session, label="mine")
    await _insert_cred(db_session, user_id=OTHER_USER_ID, cred_id=NEW_CRED_ID, label="theirs")

    resp = await http.get(f"{AUTH_PATH}/passkeys")

    assert resp.status_code == 200
    assert [i["label"] for i in resp.json()["items"]] == ["mine"]


async def test_delete_other_users_passkey_is_404_and_keeps_row(http, db_session, audit, as_user):
    await _insert_user(db_session)
    await _insert_user(db_session, user_id=OTHER_USER_ID, email=OTHER_EMAIL)
    other = await _insert_cred(db_session, user_id=OTHER_USER_ID, cred_id=NEW_CRED_ID)

    resp = await http.delete(f"{AUTH_PATH}/passkeys/{other}", headers=_headers())

    assert resp.status_code == 404
    assert (await _row(db_session, "SELECT id FROM webauthn_credentials WHERE id = :id", id=other)) is not None
    assert events(audit) == []


async def test_delete_own_passkey_is_204_and_audited(http, db_session, audit, as_user):
    await _insert_user(db_session)
    mine = await _insert_cred(db_session)

    resp = await http.delete(f"{AUTH_PATH}/passkeys/{mine}", headers=_headers())

    assert resp.status_code == 204
    assert (await _row(db_session, "SELECT id FROM webauthn_credentials WHERE id = :id", id=mine)) is None
    assert events(audit).count("passkey_deleted") == 1


# ── T10 Redis が無いとき ──────────────────────────────────────

async def test_options_are_503_without_redis(http, db_session, as_user):
    await _insert_user(db_session)
    with patch("app.auth.passkeys.get_redis", return_value=None):
        login = await http.post(f"{AUTH_PATH}/passkey/login/options", headers=_headers())
        register = await http.post(f"{AUTH_PATH}/passkey/register/options", headers=_headers())

    assert login.status_code == 503 and login.json()["detail"] == "unavailable"
    assert register.status_code == 503 and register.json()["detail"] == "unavailable"


# ── 部品 ──────────────────────────────────────────────────────

@pytest.mark.parametrize("stored,received,expected", [
    (5, 5, True), (5, 3, True), (5, 6, False), (0, 0, False), (0, 1, False), (3, 0, True),
])
def test_sign_count_rejected(stored, received, expected):
    assert passkeys.sign_count_rejected(stored, received) is expected


def test_user_handle_is_8_byte_big_endian_without_email():
    assert passkeys.user_handle(1) == b"\x00\x00\x00\x00\x00\x00\x00\x01"
