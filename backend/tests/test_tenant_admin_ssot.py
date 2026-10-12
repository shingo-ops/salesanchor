"""権限判定の正本は user_roles（system_key）だけ。users.role は判定に使わない（PR-C）。

- is_tenant_admin: owner / admin のシステムロールだけ True
- require_tenant_admin: owner・admin は通過、それ以外は 403（users.role='admin' でも 403）
- load_user_permissions: ロール 0 件なら users.role が admin でも空集合（救済の撤去）
- カレンダー予定の編集・削除: 本人、または tenant admin のみ
- /me/permissions: user_id と is_tenant_admin を返す
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.auth.dependencies import (
    get_user_system_keys,
    require_tenant_admin,
)
from app.auth.dependencies import load_user_permissions as real_load_user_permissions
from app.auth.system_roles import ROLE_KEY_ADMIN, ROLE_KEY_OWNER, is_tenant_admin
from app.models import User

# 実関数は import 時に束縛する（conftest.py の自動モックは module 属性を差し替えるため）。
# 自動モックは上書きしない: routers を最初に import する側が差し替え済みの束縛を持つ前提を崩さない


def _user(user_id: int = 1, legacy_role: str = "user") -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = legacy_role  # 判定に使われないことを試験で確かめる
    return user


def _db_returning(rows: list[tuple]) -> AsyncMock:
    """execute() の結果が fetchall() で rows を返す偽 DB。"""
    result = MagicMock()
    result.fetchall.return_value = rows
    result.first.return_value = rows[0] if rows else None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db


class TestIsTenantAdmin:
    def test_owner_is_admin(self):
        assert is_tenant_admin({ROLE_KEY_OWNER}) is True

    def test_admin_is_admin(self):
        assert is_tenant_admin({ROLE_KEY_ADMIN}) is True

    def test_other_or_empty_is_not_admin(self):
        assert is_tenant_admin(set()) is False
        assert is_tenant_admin({"sales"}) is False


class TestGetUserSystemKeys:
    @pytest.mark.asyncio
    async def test_returns_set_of_system_keys(self):
        db = _db_returning([("owner",), ("admin",)])
        assert await get_user_system_keys(db, 7) == {"owner", "admin"}
        assert db.execute.await_count == 1


class TestRequireTenantAdmin:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("keys", [{ROLE_KEY_OWNER}, {ROLE_KEY_ADMIN}])
    async def test_owner_and_admin_pass(self, keys):
        user = _user(legacy_role="user")
        with patch("app.auth.dependencies.get_user_system_keys", AsyncMock(return_value=keys)):
            assert await require_tenant_admin(tenant_id=1, user=user, db=AsyncMock()) is user

    @pytest.mark.asyncio
    @pytest.mark.parametrize("keys", [set(), {"sales"}])
    async def test_others_get_403_even_if_users_role_is_admin(self, keys):
        user = _user(legacy_role="admin")
        with patch("app.auth.dependencies.get_user_system_keys", AsyncMock(return_value=keys)):
            with pytest.raises(HTTPException) as exc:
                await require_tenant_admin(tenant_id=1, user=user, db=AsyncMock())
        assert exc.value.status_code == 403
        assert exc.value.detail == "この操作は管理者のみ実行できます"


class TestLoadUserPermissionsNoLegacyFallback:
    @pytest.mark.asyncio
    async def test_no_roles_and_legacy_admin_gets_empty_set(self):
        db = _db_returning([])
        with patch("app.auth.dependencies.get_cached_user_permissions", AsyncMock(return_value=None)), patch(
            "app.auth.dependencies.cache_user_permissions", AsyncMock()
        ):
            keys = await real_load_user_permissions(db, 1, 5)
        assert keys == set()
        executed = " ".join(str(c.args[0]) for c in db.execute.await_args_list)
        assert "public.users" not in executed


class TestCalendarEventOwnership:
    @staticmethod
    def _db_with_event(created_by: int) -> AsyncMock:
        result = MagicMock()
        result.first.return_value = (created_by, "shared")
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.mark.asyncio
    async def test_delete_by_other_non_admin_is_403(self):
        from app.routers.calendar import delete_event

        user = _user(user_id=1, legacy_role="admin")
        with patch("app.routers.calendar.get_user_system_keys", AsyncMock(return_value={"sales"})):
            with pytest.raises(HTTPException) as exc:
                await delete_event(event_id=1, tenant_id=1, user=user, db=self._db_with_event(2))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_by_owner_of_event_passes_without_admin(self):
        from app.routers.calendar import delete_event

        user = _user(user_id=2)
        with patch("app.routers.calendar.get_user_system_keys", AsyncMock(return_value=set())), patch(
            "app.routers.calendar.cal_svc.delete_event", AsyncMock()
        ) as deleted:
            await delete_event(event_id=1, tenant_id=1, user=user, db=self._db_with_event(2))
        deleted.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_by_tenant_admin_passes(self):
        from app.routers.calendar import delete_event

        user = _user(user_id=1, legacy_role="user")
        with patch("app.routers.calendar.get_user_system_keys", AsyncMock(return_value={ROLE_KEY_OWNER})), patch(
            "app.routers.calendar.cal_svc.delete_event", AsyncMock()
        ) as deleted:
            await delete_event(event_id=1, tenant_id=1, user=user, db=self._db_with_event(2))
        deleted.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_by_other_non_admin_is_403(self):
        from app.routers.calendar import UpdateEventBody, update_event

        user = _user(user_id=1, legacy_role="admin")
        body = UpdateEventBody(title="x")
        with patch("app.routers.calendar.get_user_system_keys", AsyncMock(return_value=set())):
            with pytest.raises(HTTPException) as exc:
                await update_event(event_id=1, body=body, tenant_id=1, user=user, db=self._db_with_event(2))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_by_tenant_admin_passes(self):
        from app.routers.calendar import UpdateEventBody, update_event

        user = _user(user_id=1, legacy_role="user")
        body = UpdateEventBody(title="x")
        with patch("app.routers.calendar.get_user_system_keys", AsyncMock(return_value={ROLE_KEY_ADMIN})), patch(
            "app.routers.calendar.cal_svc.update_event", AsyncMock(return_value={"id": 1})
        ):
            result = await update_event(event_id=1, body=body, tenant_id=1, user=user, db=self._db_with_event(2))
        assert result == {"id": 1}


class TestMyPermissions:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "system_keys,expected",
        [({ROLE_KEY_OWNER}, True), ({ROLE_KEY_ADMIN}, True), ({"sales"}, False), (set(), False)],
    )
    async def test_returns_user_id_and_is_tenant_admin(self, system_keys, expected):
        from app.routers.roles import get_my_permissions

        user = _user(user_id=42, legacy_role="admin")
        user.is_super_admin = False
        db = _db_returning([])
        with patch("app.routers.roles.load_user_permissions", AsyncMock(return_value={"goals.view"})), patch(
            "app.routers.roles.get_user_system_keys", AsyncMock(return_value=system_keys)
        ):
            body = await get_my_permissions(db=db, tenant_id=3, current_user=user)
        assert body["user_id"] == 42
        assert body["is_tenant_admin"] is expected
        assert body["permissions"] == ["goals.view"]


# tenant admin 専用のエンドポイント（method, path）。require_tenant_admin が依存に入っていること
_ADMIN_ONLY_ROUTES = [
    ("PATCH", "/api/v1/calendar/sync-mode"),
    ("GET", "/api/v1/google-calendar/connect/start"),
    ("DELETE", "/api/v1/google-calendar/connect"),
    ("GET", "/api/v1/integrations/google-drive/connect/start"),
    ("DELETE", "/api/v1/integrations/google-drive/connect"),
    ("PUT", "/api/v1/integrations/carriers/{carrier}/credentials"),
    ("DELETE", "/api/v1/integrations/carriers/{carrier}/credentials"),
    ("PUT", "/api/v1/integrations/paypal/credentials"),
    ("DELETE", "/api/v1/integrations/paypal/credentials"),
    ("POST", "/api/v1/integrations/paypal/test-invoice"),
]


def _dependency_calls(dependant) -> set:
    found = set()
    for sub in dependant.dependencies:
        found.add(sub.call)
        found |= _dependency_calls(sub)
    return found


class TestAdminOnlyRoutesWiring:
    @pytest.mark.parametrize("method,path", _ADMIN_ONLY_ROUTES)
    def test_route_requires_tenant_admin(self, method, path):
        from fastapi.routing import APIRoute

        from app.main import app

        matched = [
            r for r in app.routes if isinstance(r, APIRoute) and r.path == path and method in r.methods
        ]
        assert len(matched) == 1, f"{method} {path} が見つからない"
        assert require_tenant_admin in _dependency_calls(matched[0].dependant)
