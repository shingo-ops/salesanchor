"""owner / admin の権限を check 時に計算する部品と、新テナント作成の状態の単体試験（DB 不要）。

- compute_permission_keys: 保存済みの付与 ∪ システムロールの計算結果（和集合）。
- DEFAULT_ROLES / seed_system_roles / create_tenant_schema: system_key・is_system・goals 付与・phase 'B'。
実関数 load_user_permissions を PostgreSQL で流す試験は test_permission_resolution_pg.py。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.system_roles import (
    ROLE_KEY_ADMIN,
    ROLE_KEY_OWNER,
    SYSTEM_MANAGE_KEY,
    compute_permission_keys,
)
from app.services import tenant as tenant_service

ALL_KEYS = {"customers.view", "roles.update", SYSTEM_MANAGE_KEY, "zz.new_key"}


class TestComputePermissionKeys:
    def test_owner_gets_all_keys(self):
        assert compute_permission_keys(set(), {ROLE_KEY_OWNER}, ALL_KEYS) == ALL_KEYS

    def test_admin_gets_all_but_system_manage(self):
        result = compute_permission_keys(set(), {ROLE_KEY_ADMIN}, ALL_KEYS)
        assert result == ALL_KEYS - {SYSTEM_MANAGE_KEY}

    def test_admin_with_other_role_granting_system_manage_keeps_it(self):
        """5b: 保存済みの付与との和集合（今と同じ。他ロールの system.manage は残る）。"""
        result = compute_permission_keys({SYSTEM_MANAGE_KEY}, {ROLE_KEY_ADMIN}, ALL_KEYS)
        assert SYSTEM_MANAGE_KEY in result
        assert result == ALL_KEYS

    def test_admin_union_with_other_role_grants(self):
        result = compute_permission_keys({"customers.view"}, {ROLE_KEY_ADMIN}, ALL_KEYS)
        assert result == ALL_KEYS - {SYSTEM_MANAGE_KEY}

    def test_owner_wins_over_admin(self):
        result = compute_permission_keys(set(), {ROLE_KEY_OWNER, ROLE_KEY_ADMIN}, ALL_KEYS)
        assert result == ALL_KEYS

    def test_normal_role_returns_exactly_its_stored_grants(self):
        stored = {"customers.view"}
        assert compute_permission_keys(stored, set(), ALL_KEYS) == stored

    def test_new_key_reaches_owner_and_admin_without_stored_rows(self):
        assert "zz.new_key" in compute_permission_keys(set(), {ROLE_KEY_OWNER}, ALL_KEYS)
        assert "zz.new_key" in compute_permission_keys(set(), {ROLE_KEY_ADMIN}, ALL_KEYS)
        assert "zz.new_key" not in compute_permission_keys({"customers.view"}, set(), ALL_KEYS)

    def test_inputs_are_not_mutated(self):
        stored, system_keys = {"customers.view"}, {ROLE_KEY_ADMIN}
        compute_permission_keys(stored, system_keys, ALL_KEYS)
        assert stored == {"customers.view"} and system_keys == {ROLE_KEY_ADMIN}


def _role(name: str) -> dict:
    return next(role for role in tenant_service.DEFAULT_ROLES if role["name"] == name)


class TestDefaultRoles:
    def test_system_keys(self):
        assert _role("オーナー")["system_key"] == ROLE_KEY_OWNER
        assert _role("システム管理者")["system_key"] == ROLE_KEY_ADMIN
        others = [r for r in tenant_service.DEFAULT_ROLES if r["name"] not in ("オーナー", "システム管理者")]
        assert all(r.get("system_key") is None for r in others)

    def test_admin_is_system_role(self):
        """023 と同じ状態: オーナーもシステム管理者も is_system=True。"""
        assert _role("オーナー")["is_system"] is True
        assert _role("システム管理者")["is_system"] is True

    def test_goals_grants_match_migration_075(self):
        for name in ("マネージャー", "営業", "CS", "仕入れ", "発送"):
            assert "goals.view" in _role(name)["permissions"], name
        assert "goals.edit" in _role("マネージャー")["permissions"]
        for name in ("営業", "CS", "仕入れ", "発送"):
            assert "goals.edit" not in _role(name)["permissions"], name


def _captured_sql(mock: AsyncMock) -> list[tuple[str, dict]]:
    calls = []
    for call in mock.await_args_list:
        statement = str(call.args[0]) if call.args else ""
        params = call.args[1] if len(call.args) > 1 else {}
        calls.append((statement, params))
    return calls


@pytest.mark.asyncio
async def test_seed_system_roles_writes_system_key_without_overwriting():
    db = AsyncMock()
    result = AsyncMock()
    result.first = lambda: None
    result.scalar_one = lambda: 1
    db.execute = AsyncMock(return_value=result)

    await tenant_service.seed_system_roles(db, 7, "tenant_007")

    inserts = [(s, p) for s, p in _captured_sql(db.execute) if "INSERT INTO tenant_007.roles" in s]
    assert len(inserts) == len(tenant_service.DEFAULT_ROLES)
    for statement, _ in inserts:
        assert "system_key" in statement
        assert "COALESCE(tenant_007.roles.system_key, EXCLUDED.system_key)" in statement
    keys = {params["name"]: params["system_key"] for _, params in inserts}
    assert keys["オーナー"] == "owner" and keys["システム管理者"] == "admin"
    assert keys["営業"] is None


@pytest.mark.asyncio
async def test_create_tenant_schema_seeds_phase_b(monkeypatch):
    db = AsyncMock()
    ddl_db = AsyncMock()

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(tenant_service, "_execute_statements_preserving_do_blocks", noop)
    monkeypatch.setattr(tenant_service, "seed_system_roles", AsyncMock())
    monkeypatch.setattr(tenant_service, "seed_default_channel_masters", AsyncMock())
    monkeypatch.setattr(tenant_service, "_META_PAGE_ROUTING_TRIGGER_SQL", "SELECT 1")
    db.execute = AsyncMock()
    ddl_db.execute = AsyncMock()
    savepoint = MagicMock()
    savepoint.__aenter__ = AsyncMock(return_value=None)
    savepoint.__aexit__ = AsyncMock(return_value=False)
    db.begin_nested = MagicMock(return_value=savepoint)

    await tenant_service.create_tenant_schema(db, 7, admin_db=ddl_db)

    settings_sql = [s for s, _ in _captured_sql(db.execute) if "INSERT INTO public.tenant_settings" in s]
    assert len(settings_sql) == 1
    assert "VALUES (:tid, 'B'" in settings_sql[0]
    assert "VALUES (:tid, 'A'" not in settings_sql[0]
