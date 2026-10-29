"""
POST /api/v1/staff が users と user_roles も同じトランザクションで作る（ADR-1008 P3）。
"""

import pytest
from sqlalchemy import text


async def _seed_role(db_session):
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (1, 999, 'staff', '#888888', 0, FALSE)
    """))
    # 操作する側（テストユーザー 999）に priority=1000 のロールを user_roles 経由で付与する
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (2, 999, 'actor', '#000000', 1000, FALSE)
    """))
    await db_session.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (999, 2)"))
    await db_session.commit()


def _body(email: str, **extra):
    return {
        "surname_jp": "山田", "given_name_jp": "太郎",
        "surname_en": "Yamada", "given_name_en": "Taro",
        "primary_email": email, "role_id": 1, **extra,
    }


async def _count(db_session, table: str) -> int:
    return (await db_session.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()


@pytest.mark.asyncio
async def test_new_email_creates_user_staff_and_user_role(client, db_session):
    await _seed_role(db_session)
    users_before = await _count(db_session, "users")

    res = await client.post("/api/v1/staff", json=_body("brandnew@example.com"))

    assert res.status_code == 201, res.text
    user = (await db_session.execute(text(
        "SELECT id, tenant_id, username, full_name, role, is_active FROM users "
        "WHERE email = 'brandnew@example.com'"
    ))).mappings().first()
    assert user is not None
    assert await _count(db_session, "users") == users_before + 1
    assert user["tenant_id"] == 999
    assert user["username"] == "山田 太郎"
    assert user["full_name"] == "山田 太郎"
    assert user["role"] == "user"
    assert bool(user["is_active"]) is True
    assert res.json()["user_id"] == user["id"]
    staff_user_id = (await db_session.execute(text(
        "SELECT user_id FROM staff WHERE id = :id"), {"id": res.json()["id"]})).scalar()
    assert staff_user_id == user["id"]
    roles = (await db_session.execute(text(
        "SELECT role_id FROM user_roles WHERE user_id = :uid"), {"uid": user["id"]})).all()
    assert [r[0] for r in roles] == [1]


@pytest.mark.asyncio
async def test_existing_user_without_roster_is_linked_not_duplicated(client, db_session):
    await _seed_role(db_session)
    await db_session.execute(text(
        "INSERT INTO users (tenant_id, username, email, role, is_active) "
        "VALUES (999, 'old', 'Existing@Example.com', 'user', TRUE)"
    ))
    await db_session.commit()
    existing_id = (await db_session.execute(text(
        "SELECT id FROM users WHERE email = 'Existing@Example.com'"))).scalar()
    users_before = await _count(db_session, "users")

    res = await client.post("/api/v1/staff", json=_body("existing@example.com"))

    assert res.status_code == 201, res.text
    assert await _count(db_session, "users") == users_before
    assert res.json()["user_id"] == existing_id
    roles = (await db_session.execute(text(
        "SELECT role_id FROM user_roles WHERE user_id = :uid"), {"uid": existing_id})).all()
    assert [r[0] for r in roles] == [1]


@pytest.mark.asyncio
async def test_existing_user_with_roster_returns_409(client, db_session):
    await _seed_role(db_session)
    first = await client.post("/api/v1/staff", json=_body("dup@example.com"))
    assert first.status_code == 201, first.text
    users_before = await _count(db_session, "users")
    staff_before = await _count(db_session, "staff")

    res = await client.post("/api/v1/staff", json=_body("dup@example.com"))

    assert res.status_code == 409, res.text
    assert await _count(db_session, "users") == users_before
    assert await _count(db_session, "staff") == staff_before


@pytest.mark.asyncio
async def test_user_in_other_tenant_returns_409_and_creates_nothing(client, db_session):
    await _seed_role(db_session)
    await db_session.execute(text(
        "INSERT INTO users (tenant_id, username, email, role, is_active) "
        "VALUES (4, 'other', 'othertenant@example.com', 'user', TRUE)"
    ))
    await db_session.commit()
    users_before = await _count(db_session, "users")
    staff_before = await _count(db_session, "staff")
    roles_before = await _count(db_session, "user_roles")

    res = await client.post("/api/v1/staff", json=_body("othertenant@example.com"))

    assert res.status_code == 409, res.text
    assert "他の会社" in res.json()["detail"]
    assert await _count(db_session, "users") == users_before
    assert await _count(db_session, "staff") == staff_before
    assert await _count(db_session, "user_roles") == roles_before


@pytest.mark.asyncio
async def test_user_id_in_request_returns_400(client, db_session):
    await _seed_role(db_session)
    staff_before = await _count(db_session, "staff")

    res = await client.post("/api/v1/staff", json=_body("withuid@example.com", user_id=999))

    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "user_id は指定できません"
    assert await _count(db_session, "staff") == staff_before


@pytest.mark.asyncio
async def test_patch_with_user_id_returns_400_and_keeps_roster_user_id(client, db_session):
    await _seed_role(db_session)
    created = await client.post("/api/v1/staff", json=_body("patchuid@example.com"))
    assert created.status_code == 201, created.text
    staff_id = created.json()["id"]
    before = (await db_session.execute(text(
        "SELECT user_id FROM staff WHERE id = :id"), {"id": staff_id})).scalar()

    res = await client.patch(f"/api/v1/staff/{staff_id}", json={"user_id": 999999})

    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "user_id は変更できません"
    after = (await db_session.execute(text(
        "SELECT user_id FROM staff WHERE id = :id"), {"id": staff_id})).scalar()
    assert after == before


@pytest.mark.asyncio
async def test_create_does_not_write_staff_primary_email_and_ignores_firebase_uid(client, db_session):
    await _seed_role(db_session)

    res = await client.post(
        "/api/v1/staff", json=_body("loginmail@example.com", firebase_uid="fb-should-not-be-saved"))

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["primary_email"] == "loginmail@example.com"  # users.email から出る
    assert "firebase_uid" not in body
    row = (await db_session.execute(text(
        "SELECT primary_email, firebase_uid FROM staff WHERE id = :id"), {"id": body["id"]})).mappings().first()
    assert row["primary_email"] is None
    assert row["firebase_uid"] is None
    user_email = (await db_session.execute(text(
        "SELECT email FROM users WHERE id = :id"), {"id": body["user_id"]})).scalar()
    assert user_email == "loginmail@example.com"


@pytest.mark.asyncio
async def test_create_users_row_gets_default_role_without_writing_it(client, db_session):
    await _seed_role(db_session)

    res = await client.post("/api/v1/staff", json=_body("defaultrole@example.com"))

    assert res.status_code == 201, res.text
    role = (await db_session.execute(text(
        "SELECT role FROM users WHERE email = 'defaultrole@example.com'"))).scalar()
    assert role == "user"  # 列の既定値（INSERT には書かない）


@pytest.mark.asyncio
async def test_roster_email_comes_from_users_not_staff_column(client, db_session):
    await _seed_role(db_session)
    created = await client.post("/api/v1/staff", json=_body("fromusers@example.com"))
    assert created.status_code == 201, created.text
    staff_id = created.json()["id"]
    await db_session.execute(text(
        "UPDATE staff SET primary_email = 'stale-column@example.com' WHERE id = :id"), {"id": staff_id})
    await db_session.commit()

    one = await client.get(f"/api/v1/staff/{staff_id}")
    listed = await client.get("/api/v1/staff", params={"search": "fromusers"})
    stale = await client.get("/api/v1/staff", params={"search": "stale-column"})

    assert one.status_code == 200, one.text
    assert one.json()["primary_email"] == "fromusers@example.com"
    assert [r["primary_email"] for r in listed.json()] == ["fromusers@example.com"]
    assert stale.json() == []


@pytest.mark.asyncio
async def test_patch_with_primary_email_returns_400_and_keeps_users_email(client, db_session):
    await _seed_role(db_session)
    created = await client.post("/api/v1/staff", json=_body("keepmail@example.com"))
    assert created.status_code == 201, created.text
    staff_id, user_id = created.json()["id"], created.json()["user_id"]

    res = await client.patch(f"/api/v1/staff/{staff_id}", json={"primary_email": "changed@example.com"})

    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "メールアドレスはここでは変更できません"
    email = (await db_session.execute(text(
        "SELECT email FROM users WHERE id = :id"), {"id": user_id})).scalar()
    assert email == "keepmail@example.com"


@pytest.mark.asyncio
async def test_patch_with_firebase_uid_is_ignored(client, db_session):
    await _seed_role(db_session)
    created = await client.post("/api/v1/staff", json=_body("fbpatch@example.com"))
    assert created.status_code == 201, created.text
    staff_id = created.json()["id"]

    res = await client.patch(
        f"/api/v1/staff/{staff_id}", json={"surname_jp": "鈴木", "firebase_uid": "fb-ignored"})

    assert res.status_code == 200, res.text
    assert "firebase_uid" not in res.json()
    stored = (await db_session.execute(text(
        "SELECT firebase_uid FROM staff WHERE id = :id"), {"id": staff_id})).scalar()
    assert stored is None


# ── 初回設定メール（ADR-1013 便4a。新しく利用者ができたときだけ・AUTH_PROVIDER=self のときだけ） ──

_SELF_SECRET = "test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


async def _invite_count(db_session, email: str) -> int:
    return (await db_session.execute(text(
        "SELECT COUNT(*) FROM password_reset_tokens t JOIN users u ON u.id = t.user_id "
        "WHERE lower(u.email) = :e AND t.purpose = 'invite'"), {"e": email.lower()})).scalar()


@pytest.fixture
async def invite_sender(db_session):
    from unittest.mock import MagicMock, patch

    import sqlalchemy as sa

    with patch("app.routers.staff.send_invite_email", new=MagicMock()) as m:
        yield m
    # 他の試験（test_password_reset.py）が表全体の件数を数えるので、作った鍵を残さない
    await db_session.rollback()
    await db_session.execute(sa.delete(sa.table("password_reset_tokens")))
    await db_session.commit()


@pytest.mark.asyncio
async def test_new_user_gets_invite_key_and_one_mail_when_self(client, db_session, invite_sender, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    monkeypatch.setenv("AUTH_JWT_SECRET", _SELF_SECRET)
    await _seed_role(db_session)

    res = await client.post("/api/v1/staff", json=_body("invite-new@example.com"))

    assert res.status_code == 201, res.text
    assert await _invite_count(db_session, "invite-new@example.com") == 1
    assert invite_sender.call_count == 1
    to_addr, url = invite_sender.call_args.args
    assert to_addr == "invite-new@example.com"
    assert "/reset-password?token=" in url


@pytest.mark.asyncio
async def test_new_user_gets_no_invite_when_firebase(client, db_session, invite_sender, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "firebase")
    await _seed_role(db_session)

    res = await client.post("/api/v1/staff", json=_body("invite-fb@example.com"))

    assert res.status_code == 201, res.text
    assert await _invite_count(db_session, "invite-fb@example.com") == 0
    assert invite_sender.call_count == 0


@pytest.mark.asyncio
async def test_existing_user_gets_no_invite_even_when_self(client, db_session, invite_sender, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "self")
    monkeypatch.setenv("AUTH_JWT_SECRET", _SELF_SECRET)
    await _seed_role(db_session)
    await db_session.execute(text(
        "INSERT INTO users (tenant_id, username, email, role, is_active) "
        "VALUES (999, 'old', 'invite-existing@example.com', 'user', TRUE)"
    ))
    await db_session.commit()

    res = await client.post("/api/v1/staff", json=_body("invite-existing@example.com"))

    assert res.status_code == 201, res.text
    assert await _invite_count(db_session, "invite-existing@example.com") == 0
    assert invite_sender.call_count == 0
