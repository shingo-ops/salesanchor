"""
テナント論理削除 / 物理削除 API テスト。

SQLite テスト（CI 相当）は conftest.py の rewrite listener により
public.tenants / public.tenant_deletion_audit を SQLite テーブルに変換して実行。

物理削除の DROP SCHEMA CASCADE は SQLite では再現不可のため
admin_db.execute が呼ばれることを mock で確認する。
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from unittest.mock import patch, AsyncMock


def _make_super_admin_user():
    """is_super_admin=True のテスト用ユーザー"""
    from app.models import User

    user = User()
    user.id = 888
    user.tenant_id = None  # super_admin は tenant に紐付かない
    user.username = "superadmin"
    user.email = "superadmin@example.com"
    user.role = "super_admin"
    user.is_active = True
    user.is_super_admin = True
    return user


def _make_normal_user():
    """is_super_admin=False（デフォルト）のテスト用ユーザー"""
    from app.models import User

    user = User()
    user.id = 999
    user.tenant_id = 999
    user.username = "normaluser"
    user.email = "normal@example.com"
    user.role = "admin"
    user.is_active = True
    # is_super_admin は設定しない → getattr で False
    return user


@pytest_asyncio.fixture
async def super_admin_client(db_session):
    """
    is_super_admin=True のユーザーで認証された HTTP クライアント。
    require_super_admin を通過させるために get_current_user を override する。
    """
    from app.main import app
    from app.auth.dependencies import get_current_user, get_current_tenant
    from app.database import get_db

    super_admin = _make_super_admin_user()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return super_admin

    async def override_get_current_tenant():
        return None  # super_admin EP は get_current_tenant を使わない

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def normal_client(db_session):
    """
    is_super_admin が設定されていないユーザーで認証された HTTP クライアント。
    require_super_admin に 403 を返させるために使用。
    """
    from app.main import app
    from app.auth.dependencies import get_current_user, get_current_tenant
    from app.database import get_db

    normal_user = _make_normal_user()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return normal_user

    async def override_get_current_tenant():
        return 999

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── 権限ガード: normal_client は 403 ─────────────────────────────────────

@pytest.mark.asyncio
async def test_logical_delete_requires_super_admin(normal_client: AsyncClient):
    """非 super_admin は 403"""
    resp = await normal_client.request(
        "DELETE",
        "/api/v1/super-admin/tenants/1",
        json={"confirm": "DELETE:test-corp"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_physical_delete_requires_super_admin(normal_client: AsyncClient):
    """非 super_admin は 403"""
    resp = await normal_client.request(
        "DELETE",
        "/api/v1/super-admin/tenants/1/physical",
        json={"confirm": "DELETE:test-corp"},
    )
    assert resp.status_code == 403


# ── confirm バリデーション ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logical_delete_wrong_confirm(super_admin_client: AsyncClient, db_session):
    """confirm 文字列不一致で 400"""
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO tenants"
            " (id, tenant_name, tenant_code, is_active)"
            " VALUES (97, 'Test', 'test-97', 1)"
        )
    )
    await db_session.commit()

    resp = await super_admin_client.request(
        "DELETE",
        "/api/v1/super-admin/tenants/97",
        json={"confirm": "WRONG"},
    )
    assert resp.status_code == 400


# ── 論理削除成功 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logical_delete_success(super_admin_client: AsyncClient, db_session):
    """is_active=False になること・監査ログが記録されること"""
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO tenants"
            " (id, tenant_name, tenant_code, is_active)"
            " VALUES (99, 'Test', 'test-99', 1)"
        )
    )
    await db_session.commit()

    resp = await super_admin_client.request(
        "DELETE",
        "/api/v1/super-admin/tenants/99",
        json={"confirm": "DELETE:test-99"},
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "logical"

    row = (
        await db_session.execute(text("SELECT is_active FROM tenants WHERE id = 99"))
    ).one()
    assert not row.is_active

    audit = (
        await db_session.execute(
            text(
                "SELECT mode, status FROM tenant_deletion_audit"
                " WHERE tenant_id = 99"
            )
        )
    ).one()
    assert audit.mode == "logical"
    assert audit.status == "succeeded"


@pytest.mark.asyncio
async def test_logical_delete_already_deleted(super_admin_client: AsyncClient, db_session):
    """すでに論理削除済みテナントは 400"""
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO tenants"
            " (id, tenant_name, tenant_code, is_active)"
            " VALUES (98, 'Test', 'test-98', 0)"
        )
    )
    await db_session.commit()

    resp = await super_admin_client.request(
        "DELETE",
        "/api/v1/super-admin/tenants/98",
        json={"confirm": "DELETE:test-98"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_logical_delete_not_found(super_admin_client: AsyncClient):
    """存在しないテナントは 404"""
    resp = await super_admin_client.request(
        "DELETE",
        "/api/v1/super-admin/tenants/99999",
        json={"confirm": "DELETE:nonexistent"},
    )
    assert resp.status_code == 404


# ── 物理削除: 論理削除が先に必要 ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_physical_delete_requires_logical_first(
    super_admin_client: AsyncClient, db_session
):
    """is_active=True のテナントへの物理削除は 400"""
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO tenants"
            " (id, tenant_name, tenant_code, is_active)"
            " VALUES (96, 'Test', 'test-96', 1)"
        )
    )
    await db_session.commit()

    resp = await super_admin_client.request(
        "DELETE",
        "/api/v1/super-admin/tenants/96/physical",
        json={"confirm": "DELETE:test-96"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_physical_delete_wrong_confirm(
    super_admin_client: AsyncClient, db_session
):
    """confirm 文字列不一致で物理削除も 400"""
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO tenants"
            " (id, tenant_name, tenant_code, is_active)"
            " VALUES (95, 'Test', 'test-95', 0)"
        )
    )
    await db_session.commit()

    resp = await super_admin_client.request(
        "DELETE",
        "/api/v1/super-admin/tenants/95/physical",
        json={"confirm": "WRONG"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_physical_delete_success(
    super_admin_client: AsyncClient, db_session
):
    """
    物理削除成功パス（SQLite 環境）。
    DROP SCHEMA CASCADE は admin_db.execute を mock し、
    audit=started → succeeded、public.tenants 行削除を確認する。
    """
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO tenants"
            " (id, tenant_name, tenant_code, is_active)"
            " VALUES (94, 'Phys', 'test-94', 0)"
        )
    )
    await db_session.commit()

    mock_admin_session = AsyncMock()
    mock_admin_session.execute = AsyncMock(return_value=None)
    mock_admin_session.commit = AsyncMock(return_value=None)

    async def override_get_admin_db():
        yield mock_admin_session

    from app.main import app
    from app.database import get_admin_db

    app.dependency_overrides[get_admin_db] = override_get_admin_db

    try:
        resp = await super_admin_client.request(
            "DELETE",
            "/api/v1/super-admin/tenants/94/physical",
            json={"confirm": "DELETE:test-94"},
        )
    finally:
        # super_admin_client fixture が clear() するが念のため get_admin_db だけ削除
        app.dependency_overrides.pop(get_admin_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "physical"
    assert data["schema_dropped"] == "tenant_094"

    # admin_db.execute が DROP SCHEMA で呼ばれたこと
    mock_admin_session.execute.assert_called_once()
    actual_sql = str(mock_admin_session.execute.call_args.args[0])
    assert "DROP SCHEMA" in actual_sql and "tenant_094" in actual_sql

    # public.tenants 行が削除されていること
    row = (
        await db_session.execute(text("SELECT id FROM tenants WHERE id = 94"))
    ).one_or_none()
    assert row is None

    # 監査ログが succeeded になっていること
    audit = (
        await db_session.execute(
            text(
                "SELECT status FROM tenant_deletion_audit"
                " WHERE tenant_id = 94 ORDER BY id DESC LIMIT 1"
            )
        )
    ).one()
    assert audit.status == "succeeded"
