"""スタッフ自己登録の招待 API（ADR-1068 1回目）の試験。SQLite で動かす。

会社の分離（RLS）は SQLite では示せない（set_tenant_context が何もしない）ため、
PostgreSQL の試験 tests/test_staff_join_invites_rls.py で別に示す。
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text

from app.routers.staff import EMAIL_UNAVAILABLE_DETAIL

pytestmark = pytest.mark.asyncio

ADMIN_BASE = "/api/v1/staff/join-invites"
PUBLIC_BASE = "/api/v1/public/staff-join"
ORIGIN = "https://app.salesanchor.jp"
TENANT = 999
ACTOR_ID = 999  # conftest の client が返す操作者（mock user）
ROLE_STAFF = 1
ROLE_ACTOR = 2
BODY = {
    "surname_jp": "山田", "given_name_jp": "太郎",
    "surname_en": "Yamada", "given_name_en": "Taro",
    "primary_email": "staffjoin-new1@example.com",
}


@pytest.fixture(autouse=True)
async def seed(db_session):
    await db_session.execute(text(
        "INSERT OR REPLACE INTO tenants (id, tenant_code, tenant_name, company_name, is_active) "
        "VALUES (:t, 't999', 'テスト株式会社', '', 1)"
    ), {"t": TENANT})
    # 操作者 999 の行は conftest が入れている（setup_test_db）。有効に戻しておく
    await db_session.execute(text(
        "INSERT OR IGNORE INTO users (id, tenant_id, username, email, is_active) "
        "VALUES (:u, :t, 'actor', 'staffjoin-actor@example.com', 1)"
    ), {"u": ACTOR_ID, "t": TENANT})
    await db_session.execute(text("UPDATE users SET is_active = 1 WHERE id = :u"), {"u": ACTOR_ID})
    await db_session.execute(text(
        "INSERT INTO roles (id, tenant_id, name, color, priority, is_system) VALUES (1, 999, 'staff', '#888888', 0, FALSE)"
    ))
    await db_session.execute(text(
        "INSERT INTO roles (id, tenant_id, name, color, priority, is_system) VALUES (2, 999, 'actor', '#000000', 1000, FALSE)"
    ))
    await db_session.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (999, 2)"))
    await db_session.commit()
    yield
    await db_session.rollback()
    await db_session.execute(text("UPDATE users SET is_active = 1 WHERE id = :u"), {"u": ACTOR_ID})
    await db_session.execute(text("DELETE FROM users WHERE email LIKE 'staffjoin-%@example.com' AND id <> :u"), {"u": ACTOR_ID})
    await db_session.commit()


@pytest.fixture(autouse=True)
def no_redis():
    with patch("app.routers.staff_join.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.routers.staff_join.record_auth_failure", new=AsyncMock()), \
         patch("app.routers.staff_join.create_reception_invite", new=AsyncMock(return_value=None)):
        yield


@pytest.fixture
def mail_guard():
    """メールが一切出ないこと（送信関数・SMTP のどれも呼ばれない）を確かめるための差し替え。"""
    with patch("app.routers.staff.send_invite_email", new=MagicMock()) as invite, \
         patch("app.routers.auth.send_password_reset_email", new=MagicMock()) as reset, \
         patch("smtplib.SMTP", new=MagicMock()) as smtp, \
         patch("smtplib.SMTP_SSL", new=MagicMock()) as smtp_ssl:
        yield {"invite": invite, "reset": reset, "smtp": smtp, "smtp_ssl": smtp_ssl}


def _key_of(url: str) -> str:
    assert "#k=" in url
    return url.split("#k=", 1)[1]


async def _create(client, role_id: int = ROLE_STAFF):
    res = await client.post(ADMIN_BASE, json={"role_id": role_id})
    assert res.status_code == 201, res.text
    return res.json()


async def _scalar(db, sql: str, **params):
    return (await db.execute(text(sql), params)).scalar()


async def _invite_row(db, invite_id: int):
    return (await db.execute(
        text("SELECT * FROM staff_join_invites WHERE id = :i"), {"i": invite_id}
    )).mappings().first()


# ── 作成 ──

async def test_create_returns_url_once_and_sends_nothing(client, db_session, mail_guard):
    body = await _create(client)

    url = body["url"]
    assert url.startswith("https://app.salesanchor.jp/staff-join#k=999.")
    key = _key_of(url)
    assert re.fullmatch(r"999\.[A-Za-z0-9_-]{43}", key)
    row = await _invite_row(db_session, body["id"])
    assert row["status"] == "open"
    assert row["role_id"] == ROLE_STAFF
    assert row["created_by"] == ACTOR_ID
    assert bytes(row["token_hash"]) == hashlib.sha256(key.encode()).digest()  # 生の値は保存しない
    # 72 時間
    expires = datetime.fromisoformat(str(row["expires_at"]))
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    assert timedelta(hours=71, minutes=55) < expires - datetime.now(timezone.utc) <= timedelta(hours=72)
    # メールは出ない
    for name, mock in mail_guard.items():
        assert not mock.called, name
    # 一覧には鍵も URL も出ない
    listed = await client.get(ADMIN_BASE)
    assert listed.status_code == 200, listed.text
    assert [i["id"] for i in listed.json()] == [body["id"]]
    assert key not in listed.text and "url" not in listed.json()[0] and "token" not in listed.text
    assert listed.json()[0]["role_name"] == "staff"


async def test_create_rejects_role_at_or_above_my_priority(client, db_session):
    res = await client.post(ADMIN_BASE, json={"role_id": ROLE_ACTOR})  # 自分の最大 priority と同じ
    assert res.status_code == 403
    res = await client.post(ADMIN_BASE, json={"role_id": 424242})
    assert res.status_code == 400
    assert await _scalar(db_session, "SELECT COUNT(*) FROM staff_join_invites") == 0


# ── 作り直し・取り消し・期限 ──

async def test_reissue_makes_old_key_unusable(client, db_session):
    first = await _create(client)
    old_key = _key_of(first["url"])
    assert (await client.get(f"{PUBLIC_BASE}/{old_key}")).status_code == 200

    again = await client.post(f"{ADMIN_BASE}/{first['id']}/reissue")
    assert again.status_code == 200, again.text
    new_key = _key_of(again.json()["url"])
    assert new_key != old_key

    assert (await client.get(f"{PUBLIC_BASE}/{old_key}")).status_code == 404
    assert (await client.post(f"{PUBLIC_BASE}/{old_key}", json=BODY)).status_code == 404
    info = await client.get(f"{PUBLIC_BASE}/{new_key}")
    assert info.status_code == 200, info.text
    assert info.json()["tenant_name"] == "テスト株式会社"
    assert info.json()["role_name"] == "staff"
    # 行は 1 本のまま（古い鍵の行は残らない）
    assert await _scalar(db_session, "SELECT COUNT(*) FROM staff_join_invites") == 1


async def test_expired_key_is_404(client, db_session):
    body = await _create(client)
    key = _key_of(body["url"])
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(tzinfo=None)
    await db_session.execute(text("UPDATE staff_join_invites SET expires_at = :e"), {"e": past})
    await db_session.commit()

    assert (await client.get(f"{PUBLIC_BASE}/{key}")).status_code == 404
    assert (await client.post(f"{PUBLIC_BASE}/{key}", json=BODY)).status_code == 404
    assert await _scalar(db_session, "SELECT COUNT(*) FROM staff") == 0


async def test_revoked_key_is_404_and_cannot_be_operated_again(client, db_session):
    body = await _create(client)
    key = _key_of(body["url"])
    res = await client.post(f"{ADMIN_BASE}/{body['id']}/revoke")
    assert res.status_code == 200, res.text
    assert (await _invite_row(db_session, body["id"]))["status"] == "revoked"

    assert (await client.get(f"{PUBLIC_BASE}/{key}")).status_code == 404
    assert (await client.post(f"{PUBLIC_BASE}/{key}", json=BODY)).status_code == 404
    assert (await client.post(f"{ADMIN_BASE}/{body['id']}/revoke")).status_code == 409
    assert (await client.post(f"{ADMIN_BASE}/{body['id']}/reissue")).status_code == 409
    assert (await client.get(ADMIN_BASE)).json() == []  # 取り消し済みは一覧に出ない


# ── 申込 ──

async def test_submit_creates_inactive_user_pending_staff_and_submitted_invite(client, db_session, mail_guard):
    body = await _create(client)
    key = _key_of(body["url"])
    with patch("app.routers.staff_join.create_reception_invite",
               new=AsyncMock(return_value="https://discord.gg/abcdef")):
        res = await client.post(f"{PUBLIC_BASE}/{key}", json=BODY)

    assert res.status_code == 200, res.text
    out = res.json()
    assert re.fullmatch(r"[0-9A-Z]{4}(-[0-9A-Z]{4}){3}", out["registration_code"])
    assert out["discord_invite_url"] == "https://discord.gg/abcdef"

    user = (await db_session.execute(text(
        "SELECT id, tenant_id, is_active FROM users WHERE email = 'staffjoin-new1@example.com'"
    ))).mappings().first()
    assert user is not None and user["tenant_id"] == TENANT
    assert not user["is_active"]  # Discord の照合までログインさせない（R1）
    staff = (await db_session.execute(text(
        "SELECT id, status, user_id, surname_en FROM staff WHERE user_id = :u"), {"u": user["id"]}
    )).mappings().first()
    assert staff["status"] == "pending"
    roles = (await db_session.execute(text(
        "SELECT role_id, assigned_by FROM user_roles WHERE user_id = :u"), {"u": user["id"]})).all()
    assert [(r[0], r[1]) for r in roles] == [(ROLE_STAFF, ACTOR_ID)]  # 付与者は招待を作った人

    row = await _invite_row(db_session, body["id"])
    assert row["status"] == "submitted"
    assert row["user_id"] == user["id"] and row["staff_id"] == staff["id"]
    assert row["submitted_at"] is not None
    normalized = out["registration_code"].replace("-", "")
    assert bytes(row["reg_code_hash"]) == hashlib.sha256(normalized.encode("ascii")).digest()
    assert normalized not in str(dict(row))  # 登録番号の生の値は保存しない
    reg_expires = datetime.fromisoformat(str(row["reg_code_expires_at"]))
    if reg_expires.tzinfo is None:
        reg_expires = reg_expires.replace(tzinfo=timezone.utc)
    assert timedelta(days=6, hours=23) < reg_expires - datetime.now(timezone.utc) <= timedelta(days=7)

    # 監査ログの new_data に via が入る
    audit = await _scalar(
        db_session,
        "SELECT new_data FROM audit_logs WHERE table_name = 'staff' AND action = 'create' ORDER BY id DESC LIMIT 1",
    )
    assert "self_registration" in audit
    # 招待メールの鍵は作られず、メールも出ない
    assert await _scalar(db_session, "SELECT COUNT(*) FROM password_reset_tokens") == 0
    for name, mock in mail_guard.items():
        assert not mock.called, name

    # 一度申し込んだ鍵は使えない
    assert (await client.get(f"{PUBLIC_BASE}/{key}")).status_code == 404
    assert (await client.post(f"{PUBLIC_BASE}/{key}", json=BODY)).status_code == 404


async def test_password_reset_request_after_submit_makes_no_token_and_no_mail(client, db_session, mail_guard):
    body = await _create(client)
    res = await client.post(f"{PUBLIC_BASE}/{_key_of(body['url'])}", json=BODY)
    assert res.status_code == 200, res.text

    with patch("app.routers.auth.check_auth_rate_limit", new=AsyncMock(return_value=False)), \
         patch("app.routers.auth.count_password_reset_request", new=AsyncMock(return_value=1)):
        reset = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "staffjoin-new1@example.com"}, headers={"origin": ORIGIN},
        )

    assert reset.status_code == 200, reset.text  # 応答は常に同じ
    assert await _scalar(db_session, "SELECT COUNT(*) FROM password_reset_tokens") == 0
    assert not mail_guard["reset"].called
    assert not mail_guard["smtp"].called and not mail_guard["smtp_ssl"].called


async def test_existing_email_is_409_even_in_same_tenant(client, db_session):
    await db_session.execute(text(
        "INSERT INTO users (tenant_id, username, email, is_active) "
        "VALUES (999, 'old', 'StaffJoin-New1@Example.com', 1)"  # 大文字小文字違いでも同じメール
    ))
    await db_session.commit()
    users_before = await _scalar(db_session, "SELECT COUNT(*) FROM users")
    body = await _create(client)

    res = await client.post(f"{PUBLIC_BASE}/{_key_of(body['url'])}", json=BODY)

    assert res.status_code == 409
    assert res.json()["detail"] == EMAIL_UNAVAILABLE_DETAIL
    assert await _scalar(db_session, "SELECT COUNT(*) FROM users") == users_before
    assert await _scalar(db_session, "SELECT COUNT(*) FROM staff") == 0
    assert (await _invite_row(db_session, body["id"]))["status"] == "open"  # 直して送り直せる


async def test_submit_requires_english_name(client, db_session):
    body = await _create(client)
    bad = {**BODY, "surname_en": "  "}
    res = await client.post(f"{PUBLIC_BASE}/{_key_of(body['url'])}", json=bad)
    assert res.status_code == 422
    assert (await _invite_row(db_session, body["id"]))["status"] == "open"


# ── 作った人の検査し直し（R3） ──

async def test_submit_is_403_when_creator_is_inactive(client, db_session):
    body = await _create(client)
    await db_session.execute(text("UPDATE users SET is_active = 0 WHERE id = :u"), {"u": ACTOR_ID})
    await db_session.commit()

    res = await client.post(f"{PUBLIC_BASE}/{_key_of(body['url'])}", json=BODY)

    assert res.status_code == 403
    assert await _scalar(db_session, "SELECT COUNT(*) FROM staff") == 0
    assert await _scalar(db_session, "SELECT COUNT(*) FROM users WHERE email = 'staffjoin-new1@example.com'") == 0
    assert (await _invite_row(db_session, body["id"]))["status"] == "open"


async def test_submit_is_403_when_creator_lost_staff_create(client, db_session):
    body = await _create(client)

    async def only_view(db, tenant_id, user_id):
        return {"staff.view"}

    with patch("app.auth.dependencies.load_user_permissions", only_view):
        res = await client.post(f"{PUBLIC_BASE}/{_key_of(body['url'])}", json=BODY)

    assert res.status_code == 403
    assert await _scalar(db_session, "SELECT COUNT(*) FROM staff") == 0
    assert (await _invite_row(db_session, body["id"]))["status"] == "open"


async def test_submit_is_403_when_creator_priority_dropped_below_role(client, db_session):
    body = await _create(client)
    await db_session.execute(text("UPDATE roles SET priority = 0 WHERE id = :r"), {"r": ROLE_ACTOR})
    await db_session.commit()

    res = await client.post(f"{PUBLIC_BASE}/{_key_of(body['url'])}", json=BODY)

    assert res.status_code == 403
    assert await _scalar(db_session, "SELECT COUNT(*) FROM staff") == 0


# ── 鍵の形・会社 ──

@pytest.mark.parametrize("key", [
    "abc",                                      # 形が違う
    "0." + "a" * 43,                            # 会社番号が 0 から始まる
    "01." + "a" * 43,                           # 先頭 0
    "999." + "a" * 42,                          # 短い
    "999." + "a" * 44,                          # 長い
    "999." + "a" * 42 + "!",                    # 使えない文字
    "99999999999." + "a" * 43,                  # 11 桁
    "-1." + "a" * 43,
])
async def test_malformed_key_is_404_without_touching_db(client, key):
    with patch("app.routers.staff_join.select") as sel:
        get = await client.get(f"{PUBLIC_BASE}/{key}")
        post = await client.post(f"{PUBLIC_BASE}/{key}", json=BODY)
    assert get.status_code == 404 and post.status_code == 404
    assert get.json()["detail"] == post.json()["detail"] == "staff_join_invalid"
    assert not sel.called  # 形が合わなければ DB を引かない


async def test_unknown_tenant_and_unknown_key_are_the_same_404(client):
    valid_shape = "a" * 43
    unknown_tenant = await client.get(f"{PUBLIC_BASE}/424242.{valid_shape}")
    unknown_key = await client.get(f"{PUBLIC_BASE}/{TENANT}.{valid_shape}")
    assert unknown_tenant.status_code == unknown_key.status_code == 404
    assert unknown_tenant.json() == unknown_key.json()


async def test_stopped_tenant_is_404(client, db_session):
    body = await _create(client)
    await db_session.execute(text("UPDATE tenants SET is_active = 0 WHERE id = :t"), {"t": TENANT})
    await db_session.commit()
    assert (await client.get(f"{PUBLIC_BASE}/{_key_of(body['url'])}")).status_code == 404


async def test_rewriting_tenant_number_does_not_open_the_invite(client):
    body = await _create(client)
    raw = _key_of(body["url"]).split(".", 1)[1]
    assert (await client.get(f"{PUBLIC_BASE}/1.{raw}")).status_code == 404  # 会社番号を書き換えても sha256 が合わない


async def test_rate_limit_returns_429(client):
    with patch("app.routers.staff_join.check_auth_rate_limit", new=AsyncMock(return_value=True)):
        assert (await client.get(f"{PUBLIC_BASE}/{TENANT}.{'a' * 43}")).status_code == 429
        assert (await client.post(f"{PUBLIC_BASE}/{TENANT}.{'a' * 43}", json=BODY)).status_code == 429
