"""Real query semantics for the product management list, in a rolled-back schema."""
import os
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.dependencies import get_current_user
from app.routers import tcg_product_import as routes

URL = os.getenv("RLS_ADMIN_DATABASE_URL")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="Disposable PostgreSQL required")]


@pytest_asyncio.fixture
async def product_db(monkeypatch):
    url = make_url(URL)
    assert url.database == "jarvis_test_db" and url.host in ("localhost", "127.0.0.1")
    schema = "product_csv_test_" + uuid4().hex
    monkeypatch.setattr(routes, "TCG_SCHEMA", schema)
    engine = create_async_engine(url.set(drivername="postgresql+asyncpg"))
    try:
        async with engine.connect() as conn:
            transaction = await conn.begin()
            try:
                await conn.execute(text(f"CREATE SCHEMA {schema}"))
                migrations = Path(__file__).resolve().parents[2] / "migrations"
                for name in (
                    "20260831_110000_create_tcg_analysis_tables_t004.sql",
                    "20260903_180000_tcg_products_mark_en_t004.sql",
                    "20260902_110000_tcg_classification_masters.sql",
                ):
                    sql = (migrations / name).read_text().replace("tenant_004", schema)
                    await conn.exec_driver_sql(sql)
                async with AsyncSession(bind=conn) as db:
                    yield db, schema
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


async def test_all_products_search_and_pagination(product_db):
    db, schema = product_db
    await db.execute(text(
        f"INSERT INTO {schema}.tcg_products "
        "(code,japanese_title,category_class,is_active) VALUES "
        "('PM01','Alpha','Box',true),('PM02','Alpha hidden','Box',false),('PM03','Beta','Box',true)"
    ))
    await db.execute(text(
        f"INSERT INTO {schema}.product_search_keywords (product_id,keyword,position) "
        f"SELECT id,'hidden',0 FROM {schema}.tcg_products WHERE code='PM02'"
    ))
    first = await routes.list_products(query="", limit=1, offset=0, work_id=None, db=db, _user={})
    second = await routes.list_products(query="", limit=1, offset=1, work_id=None, db=db, _user={})
    assert first.total == second.total == 3
    assert first.items[0].code == "PM03"
    assert second.items[0].code == "PM02" and second.items[0].keyword_count == 1
    found = await routes.list_products(query="alpha", limit=50, offset=0, work_id=None, db=db, _user={})
    assert found.total == 2 and {row.code for row in found.items} == {"PM01", "PM02"}
    empty = await routes.list_products(query="absent", limit=50, offset=0, work_id=None, db=db, _user={})
    assert empty.total == 0 and empty.items == []


async def test_date_order_work_search_candidates_and_schema_boundary(product_db):
    """AC1/3/4/5: real DATE/UUID semantics and independent work candidates."""
    db, schema = product_db
    ids = dict((await db.execute(text(f"SELECT code,id FROM {schema}.tcg_series"))).all())
    await db.execute(text(f"UPDATE {schema}.tcg_series SET is_active = code IN ('IP001','IP002','IP003')"))
    fixtures = [
        ("A", date(2099, 1, 1), ids["IP001"], True),
        ("C", date(2026, 1, 1), ids["IP001"], True),
        ("B", date(2026, 1, 1), ids["IP001"], False),
        ("Z", date(2025, 1, 1), ids["IP002"], True),
        ("N2", None, ids["IP004"], False),
        ("N1", None, None, True),
        ("N0", None, uuid4(), True),
    ]
    for code, release, work, active in fixtures:
        await db.execute(text(
            f"INSERT INTO {schema}.tcg_products "
            "(code,japanese_title,category_class,is_active,release_date,work_id) "
            "VALUES (:code,'Shared','Box',:active,:release,:work)"
        ), {"code": code, "active": active, "release": release, "work": work})
    # A same-named table in another disposable schema must not supply rows.
    other = schema + "_other"
    await db.execute(text(f"CREATE SCHEMA {other}"))
    await db.execute(text(f"CREATE TABLE {other}.tcg_products (LIKE {schema}.tcg_products INCLUDING DEFAULTS)"))
    await db.execute(text(
        f"INSERT INTO {other}.tcg_products (code,japanese_title,category_class,is_active) "
        "VALUES ('WRONG','Shared','Box',true)"
    ))
    await db.execute(text(f"SET LOCAL search_path TO {other}, public"))
    expected_works = [
        (str(ids["IP001"]), "IP001", "Pokemon", "ポケモン"),
        (str(ids["IP002"]), "IP002", "One Piece", "ワンピース"),
        (str(ids["IP003"]), "IP003", "Dragon Ball", "ドラゴンボール"),
        (str(ids["IP004"]), "IP004", "Yu-Gi-Oh", "遊戯王"),
    ]
    for query, work_id, offset, expected, total in [
        ("", None, 0, ["A", "C", "B", "Z", "N2", "N1", "N0"], 7),
        ("sHaReD", None, 0, ["A", "C", "B", "Z", "N2", "N1", "N0"], 7),
        ("Shared", ids["IP001"], 0, ["A", "C", "B"], 3),
        ("Shared", ids["IP002"], 0, ["Z"], 1),
        ("Shared", ids["IP001"], 100, [], 3),
        ("absent", ids["IP001"], 0, [], 0),
        ("", uuid4(), 0, [], 0),
    ]:
        result = await routes.list_products(query=query, work_id=work_id, offset=offset, limit=50, db=db, _user={})
        assert result.total == total
        assert [item.code for item in result.items] == expected
        assert [(w.id, w.code, w.display_name, w.alt_name) for w in result.works] == expected_works
    result = await routes.list_products(query="", work_id=None, offset=0, limit=50, db=db, _user={})
    assert result.items[0].release_date == "2099-01-01"
    assert result.items[-1].release_date == ""


async def test_date_order_across_fifty_row_pages(product_db):
    """AC2: compare both pages against independently generated chronological order."""
    db, schema = product_db
    work_id = (await db.execute(text(f"SELECT id FROM {schema}.tcg_series WHERE code='IP001'"))).scalar_one()
    for index in range(53):
        await db.execute(text(
            f"INSERT INTO {schema}.tcg_products (code,japanese_title,category_class,is_active,release_date,work_id) "
            "VALUES (:code,'Paged','Box',true,:release,:work)"
        ), {"code": f"P{index:03}", "release": date(2026, 1, 1) + timedelta(days=52-index), "work": work_id})
    first = await routes.list_products(query="Paged", work_id=work_id, offset=0, limit=50, db=db, _user={})
    second = await routes.list_products(query="Paged", work_id=work_id, offset=50, limit=50, db=db, _user={})
    assert first.total == second.total == 53
    assert len(first.items) == 50 and len(second.items) == 3
    assert [item.code for item in first.items + second.items] == [f"P{i:03}" for i in range(53)]
    assert first.works == second.works


@pytest.mark.parametrize("work_id", ["", "not-a-uuid"])
async def test_invalid_work_uuid_is_rejected_before_sql(product_db, work_id):
    """AC5: mount the actual router; do not replace require_super_admin."""
    db, _ = product_db
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[routes.get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_super_admin=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/tcg/products/list", params={"work_id": work_id})
    assert response.status_code == 422
    assert any(error["loc"] == ["query", "work_id"] for error in response.json()["detail"])


@pytest.mark.parametrize("authenticated", [False, True])
async def test_list_denies_unauthenticated_and_non_admin(product_db, authenticated):
    db, _ = product_db
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[routes.get_db] = lambda: db
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_super_admin=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/tcg/products/list")
    assert response.status_code == 403 if authenticated else response.status_code in (401, 403)
