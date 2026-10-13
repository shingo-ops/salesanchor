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
