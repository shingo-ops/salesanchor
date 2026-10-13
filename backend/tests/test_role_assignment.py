"""名簿（スタッフ画面）のロールは user_roles が正本（ADR-1008 P4a）。

- POST /staff は user_roles に1件作り、staff.role_id には書かない
- PATCH /staff/{id} の role_id は user_roles を置き換え、権限キャッシュを破棄する
- 自分以上の priority のロール・同格以上の人のロール変更は 403、roles.assign が無くても 403
"""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from app.auth.system_roles import ROLE_KEY_ADMIN

ACTOR_ID = 999


async def _insert_role(db, name, priority, system_key=None):
    res = await db.execute(
        text(
            "INSERT INTO roles (tenant_id, name, priority, is_system, system_key) "
            "VALUES (999, :n, :p, :s, :k) RETURNING id"
        ),
        {"n": name, "p": priority, "s": system_key is not None, "k": system_key},
    )
    return res.scalar_one()


@pytest.fixture
async def seeded(db_session):
    """操作する側(999)は priority 800 のロール。低い2つ・同格1つ・隠すロール1つを用意する。"""
    ids = {
        "actor": await _insert_role(db_session, "操作者ロール", 800),
        "low": await _insert_role(db_session, "営業X", 300),
        "mid": await _insert_role(db_session, "CSX", 200),
        "same": await _insert_role(db_session, "同格ロール", 800),
        "hidden": await _insert_role(db_session, "運営専用X", 900, ROLE_KEY_ADMIN),
    }
    await db_session.execute(
        text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
        {"u": ACTOR_ID, "r": ids["actor"]},
    )
    await db_session.commit()
    return ids


def _body(email, role_id):
    return {
        "surname_jp": "山田", "given_name_jp": "太郎",
        "surname_en": "Yamada", "given_name_en": "Taro",
        "primary_email": email, "role_id": role_id,
    }


async def _user_role_ids(db, user_id):
    res = await db.execute(text("SELECT role_id FROM user_roles WHERE user_id = :u"), {"u": user_id})
    return {r[0] for r in res.fetchall()}


async def _staff_row(db, staff_id):
    res = await db.execute(
        text("SELECT user_id, role_id FROM staff WHERE id = :i"), {"i": staff_id}
    )
    return res.mappings().first()


async def _create(client, email, role_id):
    res = await client.post("/api/v1/staff", json=_body(email, role_id))
    assert res.status_code == 201, res.text
    return res.json()


async def _insert_peer(db, role_id, peer_user_id):
    """同格以上の人（users + staff + user_roles）を直接作る。"""
    await db.execute(text(
        "INSERT INTO users (id, tenant_id, username, email, role, is_active) "
        "VALUES (:u, 999, :n, :e, 'user', TRUE)"),
        {"u": peer_user_id, "n": f"peer{peer_user_id}", "e": f"peer{peer_user_id}@example.com"})
    res = await db.execute(text(
        "INSERT INTO staff (tenant_id, user_id, staff_code, surname_jp, given_name_jp, "
        "primary_email, status) VALUES (999, :u, :c, '同', '格', :e, 'active') "
        "RETURNING id"),
        {"u": peer_user_id, "c": f"EMP-P{peer_user_id}", "e": f"peer{peer_user_id}@example.com"})
    staff_id = res.scalar_one()
    await db.execute(
        text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
        {"u": peer_user_id, "r": role_id},
    )
    await db.commit()
    return staff_id


# ---------- 作成 ----------

async def test_create_writes_user_roles_and_leaves_staff_role_id_null(client, seeded, db_session):
    body = await _create(client, "new1@example.com", seeded["low"])

    row = await _staff_row(db_session, body["id"])
    assert row["role_id"] is None
    assert await _user_role_ids(db_session, row["user_id"]) == {seeded["low"]}
    assert body["role_id"] == seeded["low"]
    assert body["role_name"] == "営業X"


# ---------- 変更 ----------

async def test_patch_replaces_user_roles_and_purges_cache(client, seeded, db_session):
    body = await _create(client, "chg1@example.com", seeded["low"])
    user_id = (await _staff_row(db_session, body["id"]))["user_id"]

    with patch("app.routers.staff.invalidate_user_permissions", new=AsyncMock()) as purge:
        res = await client.patch(f"/api/v1/staff/{body['id']}", json={"role_id": seeded["mid"]})

    assert res.status_code == 200, res.text
    assert res.json()["role_id"] == seeded["mid"]
    assert res.json()["role_name"] == "CSX"
    assert await _user_role_ids(db_session, user_id) == {seeded["mid"]}
    assert (await _staff_row(db_session, body["id"]))["role_id"] is None
    purge.assert_awaited_once_with(999, user_id)


async def test_patch_same_role_id_is_noop_and_other_fields_still_update(client, seeded, db_session):
    body = await _create(client, "same1@example.com", seeded["low"])
    user_id = (await _staff_row(db_session, body["id"]))["user_id"]

    with patch("app.routers.staff.invalidate_user_permissions", new=AsyncMock()) as purge:
        res = await client.patch(
            f"/api/v1/staff/{body['id']}", json={"role_id": seeded["low"], "surname_jp": "鈴木"}
        )

    assert res.status_code == 200, res.text
    assert res.json()["surname_jp"] == "鈴木"
    assert await _user_role_ids(db_session, user_id) == {seeded["low"]}
    purge.assert_not_awaited()


async def test_patch_target_holding_hidden_role_above_own_priority_is_403(client, seeded, db_session):
    body = await _create(client, "hid1@example.com", seeded["low"])
    user_id = (await _staff_row(db_session, body["id"]))["user_id"]
    await db_session.execute(
        text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
        {"u": user_id, "r": seeded["hidden"]},
    )
    await db_session.commit()

    res = await client.patch(f"/api/v1/staff/{body['id']}", json={"role_id": seeded["mid"]})

    assert res.status_code == 403, res.text  # 対象は隠すロール(900)を持つので自分(800)以上


# ---------- 403 ----------

async def test_create_with_role_at_or_above_own_priority_is_403(client, seeded, db_session):
    res = await client.post("/api/v1/staff", json=_body("up1@example.com", seeded["same"]))
    assert res.status_code == 403, res.text
    assert (await db_session.execute(text("SELECT COUNT(*) FROM staff"))).scalar() == 0


async def test_patch_to_role_at_or_above_own_priority_is_403(client, seeded, db_session):
    body = await _create(client, "up2@example.com", seeded["low"])
    user_id = (await _staff_row(db_session, body["id"]))["user_id"]

    res = await client.patch(f"/api/v1/staff/{body['id']}", json={"role_id": seeded["same"]})

    assert res.status_code == 403, res.text
    assert await _user_role_ids(db_session, user_id) == {seeded["low"]}


async def test_patch_role_of_peer_at_or_above_own_priority_is_403(client, seeded, db_session):
    peer_staff_id = await _insert_peer(db_session, seeded["same"], 7001)

    res = await client.patch(f"/api/v1/staff/{peer_staff_id}", json={"role_id": seeded["low"]})

    assert res.status_code == 403, res.text
    assert await _user_role_ids(db_session, 7001) == {seeded["same"]}


async def test_patch_peer_other_fields_with_unchanged_role_is_allowed(client, seeded, db_session):
    peer_staff_id = await _insert_peer(db_session, seeded["same"], 7002)

    res = await client.patch(
        f"/api/v1/staff/{peer_staff_id}", json={"role_id": seeded["same"], "surname_jp": "新"}
    )

    assert res.status_code == 200, res.text


async def test_patch_role_without_roles_assign_is_403(client, seeded, db_session):
    body = await _create(client, "noperm1@example.com", seeded["low"])
    user_id = (await _staff_row(db_session, body["id"]))["user_id"]

    async def only_staff_update(db, tenant_id, user_id_):
        return {"staff.view", "staff.update"}

    with patch("app.auth.dependencies.load_user_permissions", only_staff_update):
        res = await client.patch(f"/api/v1/staff/{body['id']}", json={"role_id": seeded["mid"]})
        other = await client.patch(f"/api/v1/staff/{body['id']}", json={"surname_jp": "鈴木"})

    assert res.status_code == 403, res.text
    assert other.status_code == 200, other.text  # role_id を変えない更新は roles.assign 不要
    assert await _user_role_ids(db_session, user_id) == {seeded["low"]}


# ---------- 隠すロール ----------

async def test_hidden_role_cannot_be_assigned_by_non_super_admin(client, seeded):
    res = await client.post("/api/v1/staff", json=_body("hid2@example.com", seeded["hidden"]))
    assert res.status_code == 400, res.text


# ---------- PUT /users/{id}/roles（複数ロール API） ----------

async def test_put_user_roles_of_peer_at_or_above_own_priority_is_403(client, seeded, db_session):
    await _insert_peer(db_session, seeded["same"], 7101)

    res = await client.put("/api/v1/users/7101/roles", json={"role_ids": [seeded["low"]]})

    assert res.status_code == 403, res.text
    assert await _user_role_ids(db_session, 7101) == {seeded["same"]}


async def test_put_user_roles_of_lower_user_still_succeeds(client, seeded, db_session):
    await _insert_peer(db_session, seeded["low"], 7102)

    res = await client.put("/api/v1/users/7102/roles", json={"role_ids": [seeded["mid"]]})

    assert res.status_code == 200, res.text
    assert await _user_role_ids(db_session, 7102) == {seeded["mid"]}
