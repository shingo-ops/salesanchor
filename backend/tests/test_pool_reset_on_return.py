"""ADR-1070 Bx: 接続を返すたびに会社の文脈を消す（design-pool-reset.md §5 便2 T1〜T4）。"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import exc, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.database import install_pool_reset

_RLS_DB_URL = os.getenv("RLS_TEST_DATABASE_URL")
_BACKEND_DIR = Path(__file__).resolve().parents[1]

_PROBE = (
    "import json\n"
    "from sqlalchemy import event\n"
    "from sqlalchemy.pool.base import reset_none\n"
    "import app.database as d\n"
    "pool = d.engine.sync_engine.pool\n"
    "print(json.dumps({\n"
    "    'listened': event.contains(pool, 'reset', d._reset_session_state),\n"
    "    'reset_none': pool._reset_on_return is reset_none,\n"
    "}))\n"
)


def _probe(database_url: str) -> dict:
    """別の Python で app.database を読み、本体の engine に Bx が付いたかを返す（T1）。"""
    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    env["ADMIN_DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_t1_installed_on_postgresql_engine():
    got = _probe("postgresql+asyncpg://u:p@127.0.0.1:1/x")
    assert got == {"listened": True, "reset_none": True}


def test_t1_not_installed_on_sqlite_engine():
    got = _probe("sqlite+aiosqlite:///:memory:")
    assert got["listened"] is False


def _pg_url() -> str:
    """T2〜T4 の DB。CI では無ければ失敗にする（黙って skip させない。design §5）。"""
    if _RLS_DB_URL:
        return _RLS_DB_URL
    if os.getenv("CI") == "true":
        pytest.fail("RLS_TEST_DATABASE_URL が無い（CI では skip にしない。ADR-1070）")
    pytest.skip("RLS_TEST_DATABASE_URL 未設定のため skip（PostgreSQL 専用）")


def _engine(with_bx: bool):
    url = _pg_url()
    if with_bx:
        eng = create_async_engine(url, pool_size=1, max_overflow=0, pool_reset_on_return=None)
        install_pool_reset(eng)
        return eng
    return create_async_engine(url, pool_size=1, max_overflow=0)


async def _leave_context_then_read(eng) -> dict:
    """session A が文脈を張って commit・close、同じ接続を借りた session B が読む。"""
    async with AsyncSession(eng) as a:
        pid_a = (await a.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        fresh_path = (await a.execute(text("SHOW search_path"))).scalar_one()
        await a.execute(text("SELECT set_config('app.tenant_id', '991', false)"))
        await a.execute(text("SELECT set_config('app.is_operator', 'true', false)"))
        await a.execute(text("SET search_path TO tenant_991, public"))
        await a.commit()
    async with AsyncSession(eng) as b:
        pid_b = (await b.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        tenant = (await b.execute(text("SELECT current_setting('app.tenant_id', true)"))).scalar_one()
        operator = (await b.execute(text("SELECT current_setting('app.is_operator', true)"))).scalar_one()
        path = (await b.execute(text("SHOW search_path"))).scalar_one()
    return {
        "pid_a": pid_a,
        "pid_b": pid_b,
        "fresh_path": fresh_path,
        "tenant": tenant,
        "operator": operator,
        "path": path,
    }


async def test_t2_context_empty_after_return():
    eng = _engine(with_bx=True)
    try:
        got = await _leave_context_then_read(eng)
    finally:
        await eng.dispose()
    assert got["pid_a"] == got["pid_b"]
    assert got["tenant"] in ("", None)
    assert got["operator"] in ("", None)
    assert got["path"] == got["fresh_path"]
    assert "tenant_991" not in got["path"]


async def test_t3_without_bx_context_leaks():
    """対照: Bx を外すと T2 の判定が赤になる（＝T2 が漏れを見分けられる証拠）。"""
    eng = _engine(with_bx=False)
    try:
        got = await _leave_context_then_read(eng)
    finally:
        await eng.dispose()
    assert got["pid_a"] == got["pid_b"]
    assert got["tenant"] == "991"
    assert got["operator"] == "true"


async def test_t4_next_checkout_ok_after_failed_transaction():
    """回帰の確認: 失敗した取引の後に rollback せず close しても、次が借りられる。"""
    eng = _engine(with_bx=True)
    try:
        async with AsyncSession(eng) as a:
            with pytest.raises(exc.DBAPIError):
                await a.execute(text("SELECT 1/0"))
        async with AsyncSession(eng) as b:
            one = (await b.execute(text("SELECT 1"))).scalar_one()
    finally:
        await eng.dispose()
    assert one == 1
