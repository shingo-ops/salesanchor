"""他社の人の番号を保存させない 6 入口の試験（ADR-1008。CI の使い捨て PostgreSQL 専用）。

対象の入口（backend/app/services/tenant_users.py の ensure_user_in_tenant を呼ぶ所）:
  leads 作成・更新（assigned_to）／shifts 作成（user_id）／goals 作成（user_id）／teams 作成・更新（leader_id）

各入口で確かめること:
  - 他社の人の番号 → 422、行が増えない／変わらない
  - 自社の人の番号 → 今までどおり成功
  - 担当なし（None）→ 成功（leads・goals の team 目標・teams）

照合は差し替えない（mock しない）。public.users に本物の行を入れて、実 PostgreSQL に問い合わせる。
テナントの表は rls_bootstrap の bootstrap_tenant_schema で本物の定義から作る。shifts 表だけは
テナント作成では作られないので、test_shifts_pg.py と同じく本物の migration の区間を読み込んで作る（表の定義を書き写さない）。
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.models import User
from app.routers import goals as goals_router
from app.routers import leads as leads_router
from app.routers import shifts as shifts_router
from app.routers import teams as teams_router
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
pytestmark = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") != "true" or not ADMIN_PG_URL,
    reason="Disposable CI PostgreSQL service required",
)

_TENANT_ID = 992
_OTHER_TENANT_ID = 9920
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_OWN_USER_ID = 99201  # 自社の人（ログイン中の人）
_OWN_USER_2_ID = 99202  # 自社のもう1人
_OTHER_USER_ID = 99901  # 他社の人
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PHASE5_PATH = _REPO_ROOT / "migrations" / "011_add_phase5_tenant_tables.sql"
_SHIFTS_BANNER = "-- === シフト管理 ===\n"
_SHIFTS_END_BANNER = "-- === ERP連携ログ ===\n"
_PERMS = {"leads.create", "leads.update", "shifts.manage", "goals.edit", "teams.create", "teams.update"}
_NOT_FOUND = "指定された担当者が見つかりません"

# テナント作成では作られない leads の列を作る本物の migration（この順で流す）。
_LEAD_COLUMN_MIGRATIONS = (
    "090_add_lead_contact_links.sql",
    "091_add_leads_discord_messaging_columns.sql",
    "095_add_lead_social_links.sql",
    "099_add_discord_guild_config.sql",
    "20260602_120000_add_discord_ticket_config.sql",
)

_bootstrapped = False


async def _apply_lead_column_migrations(engine) -> None:
    """leads の列を作る本物の migration を、試験のテナントのスキーマだけに流す。"""
    async with public_bootstrap_lock(engine):
        async with engine.begin() as conn:
            for filename in _LEAD_COLUMN_MIGRATIONS:
                await _apply_migration_on_conn(conn, filename, schema_name=_SCHEMA)


def _shifts_table_sql() -> str:
    sql_all = _PHASE5_PATH.read_text(encoding="utf-8")
    start = sql_all.index(_SHIFTS_BANNER)
    end = sql_all.index(_SHIFTS_END_BANNER, start)
    return sql_all[start:end].replace("{schema}", _SCHEMA).replace("{tenant_id}", str(_TENANT_ID))


def _build_user() -> User:
    u = User()
    u.id = _OWN_USER_ID
    u.tenant_id = _TENANT_ID
    u.username = "user-ref-guard-tester"
    u.email = "user-ref-guard-tester@example.com"
    u.role = "admin"
    u.is_active = True
    return u


class _Env:
    def __init__(self, engine, client):
        self.engine = engine
        self.client = client

    async def run(self, sql: str, params: dict | None = None):
        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(_TENANT_ID)})
            res = await conn.execute(text(sql), params or {})
            return res.mappings().all() if res.returns_rows else []

    async def count(self, table: str) -> int:
        return int((await self.run(f"SELECT count(*) AS n FROM {_SCHEMA}.{table}"))[0]["n"])

    async def value(self, table: str, row_id: int, column: str):
        rows = await self.run(f"SELECT {column} AS v FROM {_SCHEMA}.{table} WHERE id = :id", {"id": row_id})
        return rows[0]["v"]


@pytest_asyncio.fixture
async def env():
    global _bootstrapped
    engine = create_async_engine(ADMIN_PG_URL, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            await session.execute(text(f"SET search_path = {_SCHEMA}, public"))
            await session.execute(text("SELECT set_config('app.tenant_id', :t, false)"), {"t": str(_TENANT_ID)})
            await session.execute(text("SELECT set_config('app.is_operator', '', false)"))
            yield session

    app = FastAPI()
    for module in (leads_router, shifts_router, goals_router, teams_router):
        app.include_router(module.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _build_user()
    app.dependency_overrides[get_current_tenant] = lambda: _TENANT_ID

    try:
        async with tenant_schema_lock(engine, _TENANT_ID):
            if not _bootstrapped:
                await bootstrap_tenant_schema(engine, _TENANT_ID)
                await _apply_lead_column_migrations(engine)
                async with engine.begin() as conn:
                    exists = (await conn.execute(text(f"SELECT to_regclass('{_SCHEMA}.shifts')"))).scalar()
                    if exists is None:
                        raw = await conn.get_raw_connection()
                        await raw.driver_connection.execute(_shifts_table_sql())
                _bootstrapped = True
            async with engine.begin() as conn:
                # 自社 2 人と他社 1 人の本物の users 行（照合はこれを読む。差し替えない）
                for user_id, tenant_id in (
                    (_OWN_USER_ID, _TENANT_ID),
                    (_OWN_USER_2_ID, _TENANT_ID),
                    (_OTHER_USER_ID, _OTHER_TENANT_ID),
                ):
                    await conn.execute(
                        text(
                            "INSERT INTO public.users (id, tenant_id) VALUES (:id, :t) "
                            "ON CONFLICT (id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id"
                        ),
                        {"id": user_id, "t": tenant_id},
                    )
                await conn.execute(
                    text(
                        f"TRUNCATE {_SCHEMA}.leads, {_SCHEMA}.shifts, {_SCHEMA}.goals, "
                        f"{_SCHEMA}.team_members, {_SCHEMA}.teams, {_SCHEMA}.audit_logs RESTART IDENTITY CASCADE"
                    )
                )
            with patch("app.auth.dependencies.load_user_permissions", new=AsyncMock(return_value=_PERMS)), \
                 patch("app.services.lead_assign_notifier.notify_lead_assigned", new=AsyncMock()):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    yield _Env(engine, client)
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ---------------------------------------------------------------------------
# leads
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_lead_rejects_other_tenant_user(env):
    resp = await env.client.post("/api/v1/leads", json={"customer_name": "Guard Co", "assigned_to": _OTHER_USER_ID})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == _NOT_FOUND
    assert await env.count("leads") == 0


@pytest.mark.asyncio
async def test_create_lead_accepts_own_tenant_user_and_none(env):
    own = await env.client.post("/api/v1/leads", json={"customer_name": "Guard Own", "assigned_to": _OWN_USER_2_ID})
    assert own.status_code == 201, own.text
    assert own.json()["assigned_to"] == _OWN_USER_2_ID
    unassigned = await env.client.post("/api/v1/leads", json={"customer_name": "Guard None"})
    assert unassigned.status_code == 201, unassigned.text
    assert unassigned.json()["assigned_to"] is None
    assert await env.count("leads") == 2


@pytest.mark.asyncio
async def test_update_lead_rejects_other_tenant_user_and_keeps_row(env):
    created = await env.client.post("/api/v1/leads", json={"customer_name": "Guard Upd", "assigned_to": _OWN_USER_ID})
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]

    resp = await env.client.patch(f"/api/v1/leads/{lead_id}", json={"assigned_to": _OTHER_USER_ID})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == _NOT_FOUND
    assert await env.value("leads", lead_id, "assigned_to") == _OWN_USER_ID

    ok = await env.client.patch(f"/api/v1/leads/{lead_id}", json={"assigned_to": _OWN_USER_2_ID})
    assert ok.status_code == 200, ok.text
    assert await env.value("leads", lead_id, "assigned_to") == _OWN_USER_2_ID


# ---------------------------------------------------------------------------
# shifts
# ---------------------------------------------------------------------------

def _shift_body(user_id: int) -> dict:
    return {"user_id": user_id, "shift_date": "2026-11-10", "start_time": "09:00", "end_time": "18:00"}


@pytest.mark.asyncio
async def test_create_shift_rejects_other_tenant_user(env):
    resp = await env.client.post("/api/v1/shifts", json=_shift_body(_OTHER_USER_ID))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == _NOT_FOUND
    assert await env.count("shifts") == 0


@pytest.mark.asyncio
async def test_create_shift_accepts_own_tenant_user(env):
    resp = await env.client.post("/api/v1/shifts", json=_shift_body(_OWN_USER_2_ID))
    assert resp.status_code == 201, resp.text
    assert resp.json()["user_id"] == _OWN_USER_2_ID
    assert await env.count("shifts") == 1


# ---------------------------------------------------------------------------
# goals
# ---------------------------------------------------------------------------

def _goal_body(**owner) -> dict:
    return {
        "period_type": "monthly", "period_year": date.today().year, "period_num": 1,
        "kpi_type": "revenue", "target_value": 1000, **owner,
    }


@pytest.mark.asyncio
async def test_create_goal_rejects_other_tenant_user(env):
    resp = await env.client.post("/api/v1/goals", json=_goal_body(user_id=_OTHER_USER_ID))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == _NOT_FOUND
    assert await env.count("goals") == 0


@pytest.mark.asyncio
async def test_create_goal_accepts_own_user_and_team_goal(env):
    own = await env.client.post("/api/v1/goals", json=_goal_body(user_id=_OWN_USER_2_ID))
    assert own.status_code == 201, own.text
    team = await env.client.post("/api/v1/teams", json={"name": "Guard Team For Goal"})
    assert team.status_code == 201, team.text
    team_goal = await env.client.post("/api/v1/goals", json=_goal_body(team_id=team.json()["id"]))
    assert team_goal.status_code == 201, team_goal.text
    assert await env.count("goals") == 2


# ---------------------------------------------------------------------------
# teams
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_team_rejects_other_tenant_leader(env):
    resp = await env.client.post("/api/v1/teams", json={"name": "Guard Team", "leader_id": _OTHER_USER_ID})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == _NOT_FOUND
    assert await env.count("teams") == 0


@pytest.mark.asyncio
async def test_create_team_accepts_own_leader_and_none(env):
    own = await env.client.post("/api/v1/teams", json={"name": "Guard Team Own", "leader_id": _OWN_USER_2_ID})
    assert own.status_code == 201, own.text
    none_leader = await env.client.post("/api/v1/teams", json={"name": "Guard Team None"})
    assert none_leader.status_code == 201, none_leader.text
    assert await env.count("teams") == 2


@pytest.mark.asyncio
async def test_update_team_rejects_other_tenant_leader_and_keeps_row(env):
    created = await env.client.post("/api/v1/teams", json={"name": "Guard Team Upd", "leader_id": _OWN_USER_ID})
    assert created.status_code == 201, created.text
    team_id = created.json()["id"]

    resp = await env.client.patch(f"/api/v1/teams/{team_id}", json={"leader_id": _OTHER_USER_ID})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == _NOT_FOUND
    assert await env.value("teams", team_id, "leader_id") == _OWN_USER_ID

    ok = await env.client.patch(f"/api/v1/teams/{team_id}", json={"leader_id": _OWN_USER_2_ID})
    assert ok.status_code == 200, ok.text
    assert await env.value("teams", team_id, "leader_id") == _OWN_USER_2_ID
