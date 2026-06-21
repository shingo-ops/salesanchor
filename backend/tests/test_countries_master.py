from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

TEST_PG_URL = (
    os.getenv("RLS_ADMIN_DATABASE_URL")
    or os.getenv("TEST_PG_URL")
)
MIGRATION_FILE = "20260621_010000_create_countries_master.sql"


def _split_sql_preserving_do_blocks(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    in_dollar = False
    dollar_tag = ""
    while i < len(sql):
        if sql[i] == "$":
            j = i + 1
            while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < len(sql) and sql[j] == "$":
                tag = sql[i : j + 1]
                if not in_dollar:
                    in_dollar = True
                    dollar_tag = tag
                    buf.append(tag)
                    i = j + 1
                    continue
                if tag == dollar_tag:
                    in_dollar = False
                    dollar_tag = ""
                    buf.append(tag)
                    i = j + 1
                    continue
        if sql[i] == ";" and not in_dollar:
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(sql[i])
        i += 1
    if buf:
        statements.append("".join(buf))
    return statements


def _load_country_seed_rows() -> list[tuple[str, str, str]]:
    src = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "countries.ts").read_text("utf-8")
    pattern = re.compile(r'\{ name: "([^"]+)", code: "([A-Z]{2})", dial: "([^"]+)" \}')
    return [(m.group(2), m.group(1), m.group(3)) for m in pattern.finditer(src)]


async def _apply_migration(eng, filename: str) -> None:
    from sqlalchemy import text

    sql = (Path(__file__).resolve().parents[2] / "migrations" / filename).read_text("utf-8")
    async with eng.begin() as conn:
        for stmt in _split_sql_preserving_do_blocks(sql):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(text(stmt))


def _mock_user():
    from app.models import User

    user = User()
    user.id = 999
    user.tenant_id = 999
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_get_countries_returns_seeded_shared_master(client):
    resp = await client.get("/api/v1/countries")
    assert resp.status_code == 200

    rows = resp.json()
    expected = _load_country_seed_rows()
    assert len(rows) == len(expected) == 190
    assert rows[0] == {"code": "AF", "name": "Afghanistan", "dial_code": "+93", "is_active": True}
    assert rows[-1] == {"code": "ZW", "name": "Zimbabwe", "dial_code": "+263", "is_active": True}

    lookup = {row["code"]: row for row in rows}
    assert lookup["JP"] == {"code": "JP", "name": "Japan", "dial_code": "+81", "is_active": True}
    assert lookup["US"] == {"code": "US", "name": "United States", "dial_code": "+1", "is_active": True}


@pytest.mark.asyncio
async def test_get_countries_shared_across_tenants(db_session):
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.database import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return _mock_user()

    async def override_get_current_tenant():
        return 123

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/countries")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()[0]["code"] == "AF"
    assert resp.json()[1]["code"] == "AL"


@pytest.mark.skipif(not TEST_PG_URL, reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。")
@pytest.mark.asyncio
async def test_countries_migration_creates_shared_master():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(TEST_PG_URL, echo=False)
    try:
        await _apply_migration(engine, MIGRATION_FILE)
        async with engine.connect() as conn:
            exists = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name='countries'"
                )
            )
            assert exists.scalar_one_or_none() == 1

            rows = (await conn.execute(
                text(
                    "SELECT code, name, dial_code, is_active "
                    "FROM public.countries "
                    "ORDER BY name, code"
                )
            )).mappings().all()

        expected = _load_country_seed_rows()
        assert len(rows) == len(expected) == 190
        assert rows[0]["code"] == "AF"
        assert rows[-1]["code"] == "ZW"
        assert {row["code"] for row in rows} == {code for code, _, _ in expected}
    finally:
        await engine.dispose()
