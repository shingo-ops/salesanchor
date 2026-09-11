"""Real query semantics for the product management list, in a rolled-back schema."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.routers import tcg_product_import as routes

URL = os.getenv("RLS_ADMIN_DATABASE_URL")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="Disposable PostgreSQL required")]


async def test_all_products_search_and_pagination(monkeypatch):
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
                ):
                    sql = (migrations / name).read_text().replace("tenant_004", schema)
                    await conn.exec_driver_sql(sql)
                await conn.execute(text(
                    f"INSERT INTO {schema}.tcg_products "
                    "(code,japanese_title,category_class,is_active) VALUES "
                    "('PM01','Alpha','Box',true),"
                    "('PM02','Alpha hidden','Box',false),"
                    "('PM03','Beta','Box',true)"
                ))
                await conn.execute(text(
                    f"INSERT INTO {schema}.product_search_keywords "
                    "(product_id,keyword,position) "
                    f"SELECT id,'hidden',0 FROM {schema}.tcg_products WHERE code='PM02'"
                ))
                async with AsyncSession(bind=conn) as db:
                    first = await routes.list_products(query="", limit=1, offset=0, db=db, _user={})
                    second = await routes.list_products(query="", limit=1, offset=1, db=db, _user={})
                    assert first.total == second.total == 3
                    assert first.items[0].code == "PM03"
                    assert second.items[0].code == "PM02" and second.items[0].keyword_count == 1
                    found = await routes.list_products(query="alpha", limit=50, offset=0, db=db, _user={})
                    assert found.total == 2 and {row.code for row in found.items} == {"PM01", "PM02"}
                    empty = await routes.list_products(query="absent", limit=50, offset=0, db=db, _user={})
                    assert empty.total == 0 and empty.items == []
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
