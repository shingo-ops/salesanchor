"""「システム管理者」ロール（system_key='admin'）を super admin 以外に見せない・付けさせない試験。

設計: docs/handoff/hide-system-admin-role/design.md（K1, K3, K3b, K4, K5）。
見分けは roles.system_key で行い、名前では見分けない（隠すロールの名前をわざと別名にして確かめる）。
"""
import pytest
from sqlalchemy import text

from app.auth.system_roles import ROLE_KEY_ADMIN, ROLE_KEY_OWNER, TENANT_HIDDEN_SYSTEM_KEYS

TARGET_USER_ID = 998


@pytest.fixture
async def seeded(db_session):
    """隠すロール（名前は別名）・オーナー・通常ロール・対象ユーザーを用意する。"""
    rows = {}
    for key, name, prio, sys_key in (
        ("hidden", "運営専用ロールX", 900, ROLE_KEY_ADMIN),
        ("owner", "オーナーX", 500, ROLE_KEY_OWNER),
        ("normal", "通常ロールX", 10, None),
    ):
        res = await db_session.execute(
            text(
                "INSERT INTO roles (tenant_id, name, priority, is_system, system_key) "
                "VALUES (999, :n, :p, :s, :k) RETURNING id"
            ),
            {"n": name, "p": prio, "s": sys_key is not None, "k": sys_key},
        )
        rows[key] = res.scalar_one()
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO users (id, tenant_id, username, email, role, is_active) "
            "VALUES (:u, 999, 'target', 'target@example.com', 'user', TRUE)"
        ),
        {"u": TARGET_USER_ID},
    )
    await db_session.commit()
    return rows


def _as_super_admin():
    from app.main import app
    from app.auth.dependencies import get_current_user
    from tests.conftest import _mock_user

    user = _mock_user()
    user.is_super_admin = True
    app.dependency_overrides[get_current_user] = lambda: user


async def _assign_directly(db_session, user_id, role_id):
    await db_session.execute(
        text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
        {"u": user_id, "r": role_id},
    )
    await db_session.commit()


async def _role_ids_of(db_session, user_id):
    res = await db_session.execute(text("SELECT role_id FROM user_roles WHERE user_id = :u"), {"u": user_id})
    return {r[0] for r in res.fetchall()}


def test_hidden_keys_constant_is_admin_only():
    assert TENANT_HIDDEN_SYSTEM_KEYS == frozenset({ROLE_KEY_ADMIN})


# ---------- K1 / K5: 一覧 ----------

async def test_list_roles_hides_admin_for_non_super_admin(client, seeded):
    res = await client.get("/api/v1/roles")
    assert res.status_code == 200
    ids = {r["id"] for r in res.json()}
    assert seeded["hidden"] not in ids
    assert seeded["owner"] in ids and seeded["normal"] in ids  # K5


async def test_role_response_shape_has_no_system_key(client, seeded):
    res = await client.get("/api/v1/roles")
    assert all("system_key" not in r for r in res.json())


# ---------- K3: _get_role の5本は 404 ----------

async def test_role_detail_routes_return_404_for_hidden_role(client, seeded):
    rid = seeded["hidden"]
    assert (await client.patch(f"/api/v1/roles/{rid}", json={"description": "x"})).status_code == 404
    assert (await client.delete(f"/api/v1/roles/{rid}")).status_code == 404
    assert (await client.get(f"/api/v1/roles/{rid}/permissions")).status_code == 404
    assert (await client.put(f"/api/v1/roles/{rid}/permissions", json={"permission_keys": []})).status_code == 404


async def test_hidden_role_404_matches_missing_role_404(client, seeded):
    hidden = await client.get(f"/api/v1/roles/{seeded['hidden']}/permissions")
    missing = await client.get("/api/v1/roles/987654/permissions")
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json() == missing.json()


async def test_normal_role_detail_routes_still_work(client, seeded):
    rid = seeded["normal"]
    assert (await client.get(f"/api/v1/roles/{rid}/permissions")).status_code == 200
    assert (await client.patch(f"/api/v1/roles/{rid}", json={"description": "ok"})).status_code == 200


# ---------- K3: ユーザーへの付与 ----------

async def test_put_user_roles_rejects_hidden_role_with_400(client, seeded, db_session):
    res = await client.put(
        f"/api/v1/users/{TARGET_USER_ID}/roles", json={"role_ids": [seeded["hidden"]]}
    )
    assert res.status_code == 400
    assert await _role_ids_of(db_session, TARGET_USER_ID) == set()


async def test_put_user_roles_normal_role_still_works(client, seeded, db_session):
    res = await client.put(
        f"/api/v1/users/{TARGET_USER_ID}/roles", json={"role_ids": [seeded["normal"], seeded["owner"]]}
    )
    assert res.status_code == 200, res.text
    assert await _role_ids_of(db_session, TARGET_USER_ID) == {seeded["normal"], seeded["owner"]}


async def test_get_user_roles_hides_hidden_role(client, seeded, db_session):
    await _assign_directly(db_session, TARGET_USER_ID, seeded["hidden"])
    await _assign_directly(db_session, TARGET_USER_ID, seeded["normal"])
    res = await client.get(f"/api/v1/users/{TARGET_USER_ID}/roles")
    assert res.status_code == 200
    assert {r["role_id"] for r in res.json()} == {seeded["normal"]}


# ---------- K3b: 既に持つ隠すロールは普通の人の操作で外れない ----------

async def test_put_user_roles_keeps_existing_hidden_assignment(client, seeded, db_session):
    await _assign_directly(db_session, TARGET_USER_ID, seeded["hidden"])
    res = await client.put(
        f"/api/v1/users/{TARGET_USER_ID}/roles", json={"role_ids": [seeded["normal"]]}
    )
    assert res.status_code == 200, res.text
    assert await _role_ids_of(db_session, TARGET_USER_ID) == {seeded["hidden"], seeded["normal"]}


# ---------- K3: スタッフ追加・編集 ----------

def _staff_body(email, role_id):
    return {
        "surname_jp": "山田", "given_name_jp": "太郎",
        "surname_en": "Yamada", "given_name_en": "Taro",
        "primary_email": email, "role_id": role_id,
    }


async def test_create_staff_with_hidden_role_is_400(client, seeded):
    res = await client.post("/api/v1/staff", json=_staff_body("h1@example.com", seeded["hidden"]))
    assert res.status_code == 400


async def test_create_staff_with_normal_role_still_works(client, seeded):
    res = await client.post("/api/v1/staff", json=_staff_body("n1@example.com", seeded["normal"]))
    assert res.status_code == 201, res.text


async def test_update_staff_to_hidden_role_is_400_and_unchanged(client, seeded):
    created = await client.post("/api/v1/staff", json=_staff_body("n2@example.com", seeded["normal"]))
    sid = created.json()["id"]
    res = await client.patch(f"/api/v1/staff/{sid}", json={"role_id": seeded["hidden"]})
    assert res.status_code == 400
    after = await client.get(f"/api/v1/staff/{sid}")
    assert after.json()["role_id"] == seeded["normal"]


async def test_update_staff_to_missing_role_is_400(client, seeded):
    created = await client.post("/api/v1/staff", json=_staff_body("n3@example.com", seeded["normal"]))
    res = await client.patch(f"/api/v1/staff/{created.json()['id']}", json={"role_id": 987654})
    assert res.status_code == 400


async def test_update_staff_to_normal_role_and_other_fields_still_work(client, seeded):
    created = await client.post("/api/v1/staff", json=_staff_body("n4@example.com", seeded["normal"]))
    sid = created.json()["id"]
    res = await client.patch(f"/api/v1/staff/{sid}", json={"role_id": seeded["owner"]})
    assert res.status_code == 200, res.text
    res = await client.patch(f"/api/v1/staff/{sid}", json={"surname_jp": "鈴木"})
    assert res.status_code == 200, res.text


# ---------- K4: super admin ----------

async def test_super_admin_sees_hidden_role_in_list(client, seeded):
    _as_super_admin()
    res = await client.get("/api/v1/roles")
    assert seeded["hidden"] in {r["id"] for r in res.json()}


async def test_super_admin_can_open_hidden_role(client, seeded):
    _as_super_admin()
    assert (await client.get(f"/api/v1/roles/{seeded['hidden']}/permissions")).status_code == 200


async def test_super_admin_can_assign_hidden_role(client, seeded, db_session):
    _as_super_admin()
    res = await client.put(
        f"/api/v1/users/{TARGET_USER_ID}/roles", json={"role_ids": [seeded["hidden"]]}
    )
    assert res.status_code == 200, res.text
    assert await _role_ids_of(db_session, TARGET_USER_ID) == {seeded["hidden"]}
    listed = await client.get(f"/api/v1/users/{TARGET_USER_ID}/roles")
    assert {r["role_id"] for r in listed.json()} == {seeded["hidden"]}


async def test_super_admin_put_replaces_hidden_assignment(client, seeded, db_session):
    _as_super_admin()
    await _assign_directly(db_session, TARGET_USER_ID, seeded["hidden"])
    res = await client.put(
        f"/api/v1/users/{TARGET_USER_ID}/roles", json={"role_ids": [seeded["normal"]]}
    )
    assert res.status_code == 200
    assert await _role_ids_of(db_session, TARGET_USER_ID) == {seeded["normal"]}


async def test_super_admin_can_create_and_update_staff_with_hidden_role(client, seeded):
    _as_super_admin()
    res = await client.post("/api/v1/staff", json=_staff_body("s1@example.com", seeded["hidden"]))
    assert res.status_code == 201, res.text
    created = await client.post("/api/v1/staff", json=_staff_body("s2@example.com", seeded["normal"]))
    res = await client.patch(f"/api/v1/staff/{created.json()['id']}", json={"role_id": seeded["hidden"]})
    assert res.status_code == 200, res.text
