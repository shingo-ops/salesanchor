"""super-admin 単位にしない言い回し（line_unit_ignore_phrases）API のテスト。

- 権限なし 403: DB 不要（require_super_admin が先に拒否する）。ローカルでも実行される。
- 追加・重複(409)・無効化・一覧順: 実 PostgreSQL 必須。
  CI（test.yml）は RLS_ADMIN_DATABASE_URL（jarvis: DDL 用）と RLS_TEST_DATABASE_URL
  （salesanchor_app: DML のみ）を渡す。TEST_PG_URL は CI では未設定のため、
  手本 test_countries_master.py と同じ環境変数を読む。どれも無ければ skip。
"""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.rls_bootstrap import _apply_migration

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL") or os.getenv("TEST_PG_URL")
MIGRATION_FILE = "20261008_100000_create_line_unit_ignore_phrases.sql"
BASE = "/api/v1/super-admin/unit-ignore-phrases"

requires_pg = pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason=(
        "実 PostgreSQL 環境が必要 "
        "(RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL / TEST_PG_URL 未設定)。"
    ),
)


def _make_client(*, is_super_admin: bool, get_db_override=None):
    from httpx import ASGITransport, AsyncClient

    from app.auth.dependencies import get_current_user
    from app.database import get_db
    from app.main import app
    from app.models import User

    async def fake_user() -> User:
        u = User()
        u.id = 9301
        u.is_super_admin = is_super_admin
        u.role = "admin" if is_super_admin else "ops"
        u.tenant_id = 6
        return u

    app.dependency_overrides[get_current_user] = fake_user
    if get_db_override is not None:
        app.dependency_overrides[get_db] = get_db_override
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test"), app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", BASE, None),
        ("post", BASE, {"phrase": "x"}),
        ("patch", f"{BASE}/1", {"is_active": False}),
        ("delete", f"{BASE}/1", None),
    ],
)
async def test_non_super_admin_gets_403(method, path, body):
    client, app = _make_client(is_super_admin=False)
    try:
        async with client as c:
            r = await c.request(method.upper(), path, json=body)
        assert r.status_code == 403, r.text
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def pg_client():
    """管理者接続で migration を適用し、API はアプリ接続（salesanchor_app）で呼ぶ。"""
    if not ADMIN_PG_URL or not APP_PG_URL:
        pytest.skip("実 PostgreSQL 環境が必要")
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    session_local = async_sessionmaker(app_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_local() as session:
            yield session

    created: list[int] = []
    client, app = _make_client(is_super_admin=True, get_db_override=override_get_db)
    try:
        await _apply_migration(admin_engine, MIGRATION_FILE)
        async with client as c:
            yield c, created
    finally:
        app.dependency_overrides.clear()
        async with admin_engine.begin() as conn:
            for pid in created:
                await conn.execute(
                    text("DELETE FROM public.line_unit_ignore_phrases WHERE id = :id"),
                    {"id": pid},
                )
        await app_engine.dispose()
        await admin_engine.dispose()


@requires_pg
@pytest.mark.asyncio
async def test_create_and_duplicate_returns_409(pg_client):
    c, created = pg_client
    phrase = f"TEST_PHRASE_{uuid.uuid4().hex[:8]}"
    r = await c.post(BASE, json={"phrase": phrase, "note": "テスト"})
    assert r.status_code == 201, r.text
    created.append(r.json()["id"])
    assert r.json()["phrase"] == phrase
    assert r.json()["is_active"] is True

    dup = await c.post(BASE, json={"phrase": phrase})
    assert dup.status_code == 409, dup.text


@requires_pg
@pytest.mark.asyncio
async def test_deactivate_and_list_orders_active_first(pg_client):
    c, created = pg_client
    tag = uuid.uuid4().hex[:8]
    first = await c.post(BASE, json={"phrase": f"TEST_A_{tag}"})
    second = await c.post(BASE, json={"phrase": f"TEST_B_{tag}"})
    created.extend([first.json()["id"], second.json()["id"]])

    r = await c.patch(f"{BASE}/{first.json()['id']}", json={"is_active": False})
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False

    listed = (await c.get(BASE)).json()
    ids = [row["id"] for row in listed]
    assert ids.index(second.json()["id"]) < ids.index(first.json()["id"])
    actives = [row["is_active"] for row in listed]
    assert actives == sorted(actives, reverse=True)


@requires_pg
@pytest.mark.asyncio
async def test_update_missing_returns_404_and_delete_removes(pg_client):
    c, created = pg_client
    missing = await c.patch(f"{BASE}/2147483000", json={"note": "x"})
    assert missing.status_code == 404

    r = await c.post(BASE, json={"phrase": f"TEST_DEL_{uuid.uuid4().hex[:8]}"})
    pid = r.json()["id"]
    created.append(pid)
    assert (await c.delete(f"{BASE}/{pid}")).status_code == 204
    assert (await c.delete(f"{BASE}/{pid}")).status_code == 404
