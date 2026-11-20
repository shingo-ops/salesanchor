"""ADR-1063 便6（K9）: 会社の分け方の毎日点検の試験。A は DB なし、B は実 PostgreSQL（無ければ skip）。"""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlsplit, urlunsplit

import pytest
from celery.schedules import crontab
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.tasks.tenant_isolation_daily_check import _run_check, build_message, collect, judge
from tests.conftest import RLS_PROBE_TABLE_DDL

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

ROLES = {"r_ok": "理由"}
TABLES = {"t_ok": "理由"}


def _facts(**kw) -> dict:
    base = {
        "current_role": "app_role",
        "current_super": False,
        "current_bypass": False,
        "bypass_roles": ["r_ok"],
        "tables": ["t_ok"],
    }
    base.update(kw)
    return base


def test_a1_green():
    assert judge(_facts(), ROLES, TABLES) == ("green", [], [])


def test_a2_yellow_when_roles_unpinned():
    color, broken, _ = judge(_facts(), {}, TABLES)
    assert color == "yellow"
    assert broken == []


@pytest.mark.parametrize("key", ["current_super", "current_bypass"])
def test_a3_current_role_bypass_is_red(key):
    color, broken, _ = judge(_facts(**{key: True}), ROLES, TABLES)
    assert color == "red"
    assert any(b.startswith("項目1:") for b in broken)


def test_a4_roles():
    color, broken, _ = judge(_facts(bypass_roles=["r_ok", "r_new"]), ROLES, TABLES)
    assert color == "red"
    assert any(b.startswith("項目2:") and "r_new" in b for b in broken)
    color, broken, notes = judge(_facts(bypass_roles=[]), ROLES, TABLES)
    assert color != "red"
    assert any("（参考）許可一覧にあるが見つからない役" in n for n in notes)


def test_a5_tables():
    color, broken, _ = judge(_facts(tables=["t_ok", "t_new"]), ROLES, TABLES)
    assert color == "red"
    assert any(b.startswith("項目3:") and "t_new" in b for b in broken)
    color, broken, notes = judge(_facts(tables=[]), ROLES, TABLES)
    assert color != "red"
    assert broken == []
    assert any("（参考）許可一覧にあるが見つからない表" in n for n in notes)


def test_a6_red_beats_yellow():
    assert judge(_facts(current_super=True), {}, TABLES)[0] == "red"
    assert judge(_facts(tables=["t_ok", "t_new"]), {}, TABLES)[0] == "red"


def test_a7_build_message():
    facts = _facts(bypass_roles=["r1", "r2"], tables=["a", "b", "c"])
    for color, mark in (("green", "✅"), ("yellow", "🟡"), ("red", "🔴")):
        lines = build_message(color, [], [], facts).split("\n")
        assert lines[0].startswith(mark)
        assert "app_role" in lines[1]
        assert "2 件" in lines[2] and "r1" in lines[2] and "r2" in lines[2]
        assert "3 件" in lines[3]


def _fake_engine() -> MagicMock:
    fake_conn_cm = MagicMock()
    fake_conn_cm.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_conn_cm.__aexit__ = AsyncMock(return_value=False)
    fake_engine = MagicMock()
    fake_engine.connect.return_value = fake_conn_cm
    return fake_engine


@pytest.mark.asyncio
async def test_a8_run_check_posts_once():
    facts = _facts()
    with (
        patch("app.database.engine", _fake_engine()),
        patch("app.tasks.tenant_isolation_daily_check.collect", new_callable=AsyncMock, return_value=facts),
        patch("app.tasks.tenant_isolation_daily_check._post_discord", new_callable=AsyncMock) as post,
    ):
        result = await _run_check()
    post.assert_awaited_once()
    from app.tasks.tenant_isolation_daily_check import BYPASSRLS_ROLES, PUBLIC_TABLES_WITHOUT_RLS

    color = judge(facts, BYPASSRLS_ROLES, PUBLIC_TABLES_WITHOUT_RLS)[0]
    assert result["color"] == color
    mark = {"green": "✅", "yellow": "🟡", "red": "🔴"}[color]
    assert post.await_args.args[0].split("\n")[0].startswith(mark)


@pytest.mark.asyncio
async def test_a9_run_check_reports_failure():
    with (
        patch("app.database.engine", _fake_engine()),
        patch(
            "app.tasks.tenant_isolation_daily_check.collect",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ),
        patch("app.tasks.tenant_isolation_daily_check._post_discord", new_callable=AsyncMock) as post,
    ):
        with pytest.raises(RuntimeError):
            await _run_check()
    post.assert_awaited_once()
    assert "点検が動けなかった" in post.await_args.args[0]


def test_a10_beat_schedule():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["tenant-isolation-daily-check"]
    assert entry["task"] == "app.tasks.tenant_isolation_daily_check.run_tenant_isolation_daily_check"
    assert entry["schedule"] == crontab(hour=9, minute=5)
    assert "app.tasks.tenant_isolation_daily_check" in celery_app.conf.include


# ---- B: 実 PostgreSQL ----

needs_pg = pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)


def _asyncpg_url(dbname: str | None = None) -> str:
    url = ADMIN_PG_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    if dbname:
        url = urlunsplit(urlsplit(url)._replace(path="/" + dbname))
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest.fixture()
async def scratch_db():
    name = f"rls_daily_{uuid.uuid4().hex[:12]}"
    control = create_async_engine(_asyncpg_url(), isolation_level="AUTOCOMMIT")
    async with control.connect() as c:
        await c.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield name
    finally:
        async with control.connect() as c:
            await c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await control.dispose()


async def _autocommit_conn(engine):
    conn = await engine.connect()
    return await conn.execution_options(isolation_level="AUTOCOMMIT")


@needs_pg
@pytest.mark.asyncio
async def test_b1_probe_table(scratch_db):
    engine = create_async_engine(_asyncpg_url(scratch_db))
    try:
        conn = await _autocommit_conn(engine)
        try:
            await conn.execute(text(RLS_PROBE_TABLE_DDL))
            facts = await collect(conn)
            assert "ci_rls_probe" in facts["tables"]
            color, broken, _ = judge(facts, ROLES, {})
            assert color == "red"
            assert any(b.startswith("項目3:") for b in broken)
            await conn.execute(text("ALTER TABLE public.ci_rls_probe ENABLE ROW LEVEL SECURITY"))
            assert "ci_rls_probe" not in (await collect(conn))["tables"]
        finally:
            await conn.close()
    finally:
        await engine.dispose()


@needs_pg
@pytest.mark.asyncio
async def test_b2_bypass_role(scratch_db):
    role = "ci_bypass_" + uuid.uuid4().hex[:12]
    engine = create_async_engine(_asyncpg_url(scratch_db))
    try:
        conn = await _autocommit_conn(engine)
        try:
            await conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN BYPASSRLS'))
            facts = await collect(conn)
            assert role in facts["bypass_roles"]
            others = {r: "試験" for r in facts["bypass_roles"] if r != role} or {"ci_placeholder": "試験"}
            color, broken, _ = judge(facts, others, {t: "x" for t in facts["tables"]})
            assert color == "red"
            assert any(b.startswith("項目2:") and role in b for b in broken)
        finally:
            await conn.close()
    finally:
        cleanup = await _autocommit_conn(create_async_engine(_asyncpg_url(scratch_db)))
        try:
            await cleanup.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        finally:
            await cleanup.close()
            await cleanup.engine.dispose()
        await engine.dispose()


@needs_pg
@pytest.mark.asyncio
async def test_b3_plain_role(scratch_db):
    role = "ci_plain_" + uuid.uuid4().hex[:12]
    engine = create_async_engine(_asyncpg_url(scratch_db))
    try:
        conn = await _autocommit_conn(engine)
        try:
            await conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
            await conn.execute(text(f'GRANT "{role}" TO CURRENT_USER'))
            await conn.execute(text(f'SET ROLE "{role}"'))
            facts = await collect(conn)
            assert facts["current_role"] == role
            assert facts["current_super"] is False
            assert facts["current_bypass"] is False
            assert not any(b.startswith("項目1:") for b in judge(facts, ROLES, TABLES)[1])
            await conn.execute(text("RESET ROLE"))
            facts = await collect(conn)
            row = (
                await conn.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"))
            ).one()
            assert (facts["current_super"], facts["current_bypass"]) == (bool(row[0]), bool(row[1]))
        finally:
            try:
                await conn.execute(text("RESET ROLE"))
            finally:
                await conn.close()
    finally:
        cleanup = await _autocommit_conn(create_async_engine(_asyncpg_url(scratch_db)))
        try:
            await cleanup.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        finally:
            await cleanup.close()
            await cleanup.engine.dispose()
        await engine.dispose()
