"""
POST /api/v1/admin/tenants と POST /api/v1/auth/register は super admin 専用。

- role='admin' でも is_super_admin=False なら 403
- is_super_admin=True なら権限判定を通過する（403 にならない）
- 未認証は 401 または 403
"""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from httpx import ASGITransport, AsyncClient

TENANT_PATH = "/api/v1/admin/tenants"
REGISTER_PATH = "/api/v1/auth/register"
TENANT_BODY = {"tenant_name": "Test Corp", "tenant_code": "test-corp"}
REGISTER_BODY = {
    "email": "new@example.com",
    "username": "newuser",
    "tenant_code": "other-tenant",
}
_ORIGIN = "https://app.salesanchor.jp"
ENDPOINTS = [
    pytest.param(TENANT_PATH, TENANT_BODY, id="admin-tenants"),
    pytest.param(REGISTER_PATH, REGISTER_BODY, id="auth-register"),
]


def _make_user(*, is_super_admin: bool):
    from app.models import User

    user = User()
    user.id = 999
    user.tenant_id = 999
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "admin"  # 旧欄: admin でも super admin でなければ拒否される
    user.is_active = True
    user.is_super_admin = is_super_admin
    return user


@pytest.fixture
def override_user():
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.main import app

    def _apply(user):
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_current_tenant] = lambda: 999

    yield _apply
    app.dependency_overrides.clear()


async def _post(path, body):
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=body, headers={"origin": _ORIGIN})


@pytest.mark.parametrize("path,body", ENDPOINTS)
async def test_tenant_admin_without_super_admin_gets_403(override_user, path, body):
    override_user(_make_user(is_super_admin=False))

    resp = await _post(path, body)

    assert resp.status_code == 403


@pytest.mark.parametrize("path,body", ENDPOINTS)
async def test_super_admin_passes_permission_check(override_user, path, body):
    override_user(_make_user(is_super_admin=True))

    resp = await _post(path, body)

    # 権限判定は通過する。後続の処理（DB 等）の結果は問わない。
    assert resp.status_code != 403
    assert resp.status_code != 401


@pytest.mark.parametrize("path,body", ENDPOINTS)
async def test_unauthenticated_is_rejected(path, body):
    resp = await _post(path, body)

    assert resp.status_code in (401, 403)


async def test_register_function_body_rejects_non_super_admin():
    """二重防御: 依存を外して関数を直接呼んでも、関数内で 403 になる。"""
    from fastapi import BackgroundTasks, HTTPException
    from starlette.requests import Request

    from app.routers.auth import register_user
    from app.schemas.auth import UserRegister

    request = Request({"type": "http", "headers": [(b"origin", _ORIGIN.encode())]})
    with pytest.raises(HTTPException) as exc:
        await register_user(
            data=UserRegister(**REGISTER_BODY),
            request=request,
            background_tasks=BackgroundTasks(),
            db=None,
            current_user=_make_user(is_super_admin=False),
        )

    assert exc.value.status_code == 403


async def test_register_tenant_function_body_rejects_non_super_admin():
    from fastapi import HTTPException

    from app.routers.admin import register_tenant
    from app.schemas.tenant import TenantCreate

    with pytest.raises(HTTPException) as exc:
        await register_tenant(
            data=TenantCreate(**TENANT_BODY),
            db=None,
            admin_db=None,
            current_user=_make_user(is_super_admin=False),
        )

    assert exc.value.status_code == 403
