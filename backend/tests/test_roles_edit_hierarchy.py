"""ロール画面の編集の決まり（ADR-147 追補 2026-11-09）の HTTP 試験。

設計: docs/handoff/role-edit-hierarchy/design.md（K2, K3, K5, K7）。
試験ユーザー (id=999) に、役割ごとの system_key を持つロールを付けて操作する。
見分けは roles.system_key で行い、名前では見分けない。
権限キーの計算（K4: 営業等は roles.* を持たない）は test_system_roles.py の単体試験で固定する。
非空の権限 ID を使う PUT は PostgreSQL 専用のため、ここでは空リストの経路を試験する。
"""
import pytest
from sqlalchemy import text

TARGET_USER_ID = 998


async def _insert_role(db_session, name, priority, system_key=None, tenant_id=999):
    res = await db_session.execute(
        text(
            "INSERT INTO roles (tenant_id, name, priority, is_system, system_key) "
            "VALUES (:t, :n, :p, :s, :k) RETURNING id"
        ),
        {"t": tenant_id, "n": name, "p": priority, "s": system_key in ("owner", "admin"), "k": system_key},
    )
    return res.scalar_one()


@pytest.fixture
async def roles(db_session):
    """役割ごとのロールと、対象ユーザーを用意する（名前は別名にして system_key で見分けることを確かめる）。"""
    ids = {
        "owner": await _insert_role(db_session, "甲", 1000, "owner"),
        "admin": await _insert_role(db_session, "乙", 900, "admin"),
        "manager": await _insert_role(db_session, "丙", 500, "manager"),
        "inspector": await _insert_role(db_session, "丁", 300, "inspector"),
        "smoke": await _insert_role(db_session, "戊", 100, "smoke"),
        "sales": await _insert_role(db_session, "己", 300, None),
        "low": await _insert_role(db_session, "庚", 10, None),
    }
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO users (id, tenant_id, username, email, role, is_active) "
            "VALUES (:u, 999, 'target', 'target@example.com', 'user', TRUE)"
        ),
        {"u": TARGET_USER_ID},
    )
    await db_session.commit()
    return ids


async def _act_as(db_session, roles, who):
    """試験ユーザー (id=999) を、指定した役割だけを持つ状態にする。"""
    await db_session.execute(text("DELETE FROM user_roles WHERE user_id = 999"))
    await db_session.execute(
        text("INSERT INTO user_roles (user_id, role_id) VALUES (999, :r)"), {"r": roles[who]}
    )
    await db_session.commit()


async def _role_ids_of(db_session, user_id):
    res = await db_session.execute(text("SELECT role_id FROM user_roles WHERE user_id = :u"), {"u": user_id})
    return {r[0] for r in res.fetchall()}


def _perm_url(role_id):
    return f"/api/v1/roles/{role_id}/permissions"


# ---------- K2 / K5: 一覧 scope ----------

@pytest.mark.parametrize("who", ["owner", "admin", "manager"])
async def test_role_page_list_hides_four_keys_for_every_editor(client, db_session, roles, who):
    await _act_as(db_session, roles, who)
    res = await client.get("/api/v1/roles?scope=role_page")
    assert res.status_code == 200
    ids = {r["id"] for r in res.json()}
    for hidden in ("owner", "admin", "inspector", "smoke"):
        assert roles[hidden] not in ids, hidden
    assert {roles["manager"], roles["sales"], roles["low"]} <= ids


async def test_role_page_list_hides_even_for_super_admin(client, db_session, roles):
    from app.auth.dependencies import get_current_user
    from app.main import app
    from tests.conftest import _mock_user

    await _act_as(db_session, roles, "owner")
    user = _mock_user()
    user.is_super_admin = True
    app.dependency_overrides[get_current_user] = lambda: user
    res = await client.get("/api/v1/roles?scope=role_page")
    ids = {r["id"] for r in res.json()}
    assert roles["admin"] not in ids and roles["owner"] not in ids


async def test_unscoped_list_is_unchanged(client, db_session, roles):
    """K5: scope 無しはスタッフ画面用。オーナーも点検用も今までどおり出る（admin だけ super admin 以外に隠す）。"""
    await _act_as(db_session, roles, "manager")
    res = await client.get("/api/v1/roles")
    ids = {r["id"] for r in res.json()}
    assert roles["owner"] in ids and roles["inspector"] in ids and roles["smoke"] in ids
    assert roles["admin"] not in ids


async def test_unknown_scope_is_422(client, db_session, roles):
    res = await client.get("/api/v1/roles?scope=other")
    assert res.status_code == 422


# ---------- K3: 権限の保存 ----------

@pytest.mark.parametrize("who", ["owner", "admin", "manager"])
async def test_editors_can_save_normal_role_permissions(client, db_session, roles, who):
    await _act_as(db_session, roles, who)
    res = await client.put(_perm_url(roles["sales"]), json={"permission_ids": []})
    assert res.status_code == 200, res.text


async def test_manager_can_save_manager_role_itself(client, db_session, roles):
    await _act_as(db_session, roles, "manager")
    res = await client.put(_perm_url(roles["manager"]), json={"permission_ids": []})
    assert res.status_code == 200, res.text


@pytest.mark.parametrize("who", ["owner", "admin", "manager"])
@pytest.mark.parametrize("target", ["owner", "admin", "inspector", "smoke"])
async def test_hidden_roles_permissions_cannot_be_saved(client, db_session, roles, who, target):
    await _act_as(db_session, roles, who)
    res = await client.put(_perm_url(roles[target]), json={"permission_ids": []})
    # admin は super admin 以外には「無い」ものとして 404（既存の隠し方）。それ以外は 403
    assert res.status_code == (404 if target == "admin" else 403)


async def test_non_editor_cannot_save_permissions(client, db_session, roles):
    await _act_as(db_session, roles, "sales")
    res = await client.put(_perm_url(roles["low"]), json={"permission_ids": []})
    assert res.status_code == 403


@pytest.mark.parametrize("target", ["owner", "admin", "inspector", "smoke"])
async def test_hidden_roles_permissions_cannot_be_read(client, db_session, roles, target):
    await _act_as(db_session, roles, "manager")
    assert (await client.get(_perm_url(roles[target]))).status_code == 404


async def test_normal_role_permissions_can_be_read(client, db_session, roles):
    await _act_as(db_session, roles, "manager")
    assert (await client.get(_perm_url(roles["manager"]))).status_code == 200
    assert (await client.get(_perm_url(roles["sales"]))).status_code == 200


# ---------- K7: 作成・削除・名前の変更・割当 ----------

async def test_manager_can_create_role_below_manager_only(client, db_session, roles):
    await _act_as(db_session, roles, "manager")
    ok = await client.post("/api/v1/roles", json={"name": "新規下位", "priority": 499})
    assert ok.status_code == 201, ok.text
    for prio in (500, 900):
        res = await client.post("/api/v1/roles", json={"name": f"新規上位{prio}", "priority": prio})
        assert res.status_code == 403


async def test_manager_can_delete_normal_role(client, db_session, roles):
    await _act_as(db_session, roles, "manager")
    assert (await client.delete(f"/api/v1/roles/{roles['low']}")).status_code == 204


@pytest.mark.parametrize("who", ["owner", "admin", "manager"])
@pytest.mark.parametrize("target", ["owner", "admin", "manager", "inspector", "smoke"])
async def test_roles_with_system_key_cannot_be_deleted(client, db_session, roles, who, target):
    await _act_as(db_session, roles, who)
    res = await client.delete(f"/api/v1/roles/{roles[target]}")
    assert res.status_code in (403, 404)  # admin は super admin 以外には「無い」ものとして 404
    still = await db_session.execute(text("SELECT COUNT(*) FROM roles WHERE id = :i"), {"i": roles[target]})
    assert still.scalar_one() == 1


@pytest.mark.parametrize("target", ["owner", "admin", "inspector", "smoke"])
async def test_manager_cannot_rename_hidden_roles(client, db_session, roles, target):
    await _act_as(db_session, roles, "manager")
    res = await client.patch(f"/api/v1/roles/{roles[target]}", json={"description": "x"})
    assert res.status_code in (403, 404)


async def test_manager_can_rename_normal_role(client, db_session, roles):
    await _act_as(db_session, roles, "manager")
    res = await client.patch(f"/api/v1/roles/{roles['sales']}", json={"description": "ok"})
    assert res.status_code == 200, res.text


@pytest.mark.parametrize("target", ["owner", "manager", "inspector", "smoke"])
async def test_manager_cannot_assign_owner_admin_only_roles(client, db_session, roles, target):
    await _act_as(db_session, roles, "manager")
    res = await client.put(f"/api/v1/users/{TARGET_USER_ID}/roles", json={"role_ids": [roles[target]]})
    assert res.status_code == 403
    assert await _role_ids_of(db_session, TARGET_USER_ID) == set()


async def test_manager_can_assign_normal_roles(client, db_session, roles):
    await _act_as(db_session, roles, "manager")
    res = await client.put(f"/api/v1/users/{TARGET_USER_ID}/roles", json={"role_ids": [roles["sales"], roles["low"]]})
    assert res.status_code == 200, res.text
    assert await _role_ids_of(db_session, TARGET_USER_ID) == {roles["sales"], roles["low"]}


@pytest.mark.parametrize("target", ["manager", "inspector", "smoke"])
async def test_owner_can_still_assign_manager_inspector_smoke(client, db_session, roles, target):
    await _act_as(db_session, roles, "owner")
    res = await client.put(f"/api/v1/users/{TARGET_USER_ID}/roles", json={"role_ids": [roles[target]]})
    assert res.status_code == 200, res.text
    assert await _role_ids_of(db_session, TARGET_USER_ID) == {roles[target]}


# ---------- K7: スタッフ画面の道（check_assignable_role）でも同じ止め ----------

async def _granter(db_session):
    from app.models import User

    user = await db_session.get(User, 999)
    assert user is not None, "BLOCKED: 試験ユーザー 999 が取れない"
    return user


@pytest.mark.parametrize("target", ["owner", "manager", "inspector", "smoke"])
async def test_manager_check_assignable_role_blocks_owner_admin_only(db_session, roles, target):
    from fastapi import HTTPException

    from app.services.role_assignment import check_assignable_role

    await _act_as(db_session, roles, "manager")
    granter = await _granter(db_session)
    with pytest.raises(HTTPException) as exc:
        await check_assignable_role(db_session, 999, granter, roles[target])
    assert exc.value.status_code == 403
    assert exc.value.detail == "role_not_assignable"


@pytest.mark.parametrize("target", ["sales", "low"])
async def test_manager_check_assignable_role_allows_normal(db_session, roles, target):
    from app.services.role_assignment import check_assignable_role

    await _act_as(db_session, roles, "manager")
    granter = await _granter(db_session)
    await check_assignable_role(db_session, 999, granter, roles[target])


@pytest.mark.parametrize("target", ["inspector", "smoke", "manager"])
async def test_owner_check_assignable_role_allows_special(db_session, roles, target):
    from app.services.role_assignment import check_assignable_role

    await _act_as(db_session, roles, "owner")
    granter = await _granter(db_session)
    await check_assignable_role(db_session, 999, granter, roles[target])
