"""Stored-decision contracts: API mocks are separate from real PostgreSQL acceptance."""
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import psycopg2
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from psycopg2 import sql
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.routers import tcg_analysis_review as routes
from app.services import tcg_sold_out_results_svc as service
from tests.conftest import _PUBLIC_SUPPLIERS_DDL, _supplier_ssot_premigration
from tests.test_tcg_work_matching_integration import _rewire_keyword_fks

STAMP = datetime(2026, 9, 14, tzinfo=timezone.utc)
PRODUCT_UUID = UUID("b3505000-0000-4000-8000-000000000001")


def empty():
    return dict(items=[], total=0, offset=0, limit=50, as_of=STAMP)


def client_app(role=True):
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")

    async def user():
        if role is None:
            raise HTTPException(401)
        return SimpleNamespace(is_super_admin=role)

    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    return app


@pytest.mark.asyncio
@pytest.mark.parametrize("role,expected", [(None, 401), (False, 403), (True, 200)])
async def test_real_authorization_dependency(monkeypatch, role, expected):
    reader = AsyncMock(return_value=empty())
    monkeypatch.setattr(routes, "fetch_sold_out_results", reader)
    async with AsyncClient(transport=ASGITransport(app=client_app(role)), base_url="http://test") as client:
        response = await client.get("/api/v1/tcg/sold-out-results")
    assert response.status_code == expected
    assert reader.await_count == (1 if expected == 200 else 0)
    if expected == 200:
        assert set(response.json()) == {"items", "total", "offset", "limit", "as_of"}
        assert response.headers["cache-control"] == "no-store"
        assert reader.call_args.kwargs == dict(q=None, source_scope="all", offset=0, limit=50)


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["source_scope=unknown", "offset=-1", "limit=0", "limit=101", "offset=word", "q=" + "x" * 101])
async def test_invalid_input_rejected_before_read(monkeypatch, query):
    reader = AsyncMock()
    monkeypatch.setattr(routes, "fetch_sold_out_results", reader)
    async with AsyncClient(transport=ASGITransport(app=client_app()), base_url="http://test") as client:
        response = await client.get("/api/v1/tcg/sold-out-results?" + query)
    assert response.status_code == 422
    reader.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [SQLAlchemyError("PRIVATE SOURCE"), service.SoldOutResultsUnavailable()])
async def test_unavailable_is_safe_503(monkeypatch, failure):
    monkeypatch.setattr(routes, "fetch_sold_out_results", AsyncMock(side_effect=failure))
    async with AsyncClient(transport=ASGITransport(app=client_app()), base_url="http://test") as client:
        response = await client.get("/api/v1/tcg/sold-out-results")
    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "SOLD_OUT_RESULTS_UNAVAILABLE"}}
    assert "PRIVATE" not in response.text


@pytest.mark.asyncio
async def test_one_statement_bound_search_and_missing_source():
    row = dict(missing_sources=0, total=7, items=[], as_of=STAMP)
    result = Mock()
    result.mappings.return_value.one.return_value = row
    db = AsyncMock()
    db.execute.return_value = result
    value = "  %_\\' OR 1=1 --  "
    response = await service.fetch_sold_out_results(db, q=value, offset=99)
    assert response["total"] == 7 and response["items"] == []
    statement, bindings = db.execute.call_args.args
    assert "OR 1=1 --" not in str(statement)
    assert bindings["search"] == value.strip()
    assert bindings["pattern"] == "%\\%\\_\\\\' OR 1=1 --%"
    assert db.execute.await_count == 1
    row["missing_sources"] = 1
    with pytest.raises(service.SoldOutResultsUnavailable):
        await service.fetch_sold_out_results(db)


@pytest_asyncio.fixture
async def pg(monkeypatch):
    """A new CI-only database, real migrations, then SELECT in a read-only transaction."""
    assert os.getenv("GITHUB_ACTIONS") == "true", "Disposable CI PostgreSQL required; do not fake this flag"
    configured = os.getenv("RLS_ADMIN_DATABASE_URL")
    assert configured, "Real PostgreSQL acceptance requires CI database credentials"
    url = make_url(configured)
    assert url.host in ("localhost", "127.0.0.1") and url.database == "jarvis_test_db"
    name = "sold_out_test_" + uuid4().hex
    kwargs = dict(host=url.host, port=url.port, user=url.username, password=url.password)
    admin = psycopg2.connect(dbname=url.database, **kwargs)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    finally:
        admin.close()
    connection = psycopg2.connect(dbname=name, **kwargs)
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA tenant_951")
            migrations = Path(__file__).resolve().parents[2] / "migrations"
            for filename in ("20260831_110000_create_tcg_analysis_tables_t004.sql", "20260910_010000_tcg_import_message_links.sql"):
                cursor.execute((migrations / filename).read_text().replace("tenant_004", "tenant_951"))
            cursor.execute((Path(__file__).parent / "fixtures" / "public_products_test.sql").read_text())
            cursor.execute(_rewire_keyword_fks("tenant_951"))
            cursor.execute(_PUBLIC_SUPPLIERS_DDL)
            cursor.execute("INSERT INTO tenant_951.tcg_suppliers(code,name,is_active) VALUES ('S','Supplier percent%',true)")
            # Sprint 1 migration: copy tcg_suppliers → public.suppliers, rewire supplier_channels FK UUID→INTEGER
            sprint1 = Path(__file__).resolve().parents[2] / "migrations/20260917_020000_supplier_ssot_migration.sql"
            _supplier_ssot_premigration(cursor, "tenant_951")
            cursor.execute(sprint1.read_text())
            cursor.execute("SELECT id FROM public.suppliers WHERE supplier_code='SP-00000'")
            supplier = cursor.fetchone()[0]
            cursor.execute("INSERT INTO tenant_951.supplier_channels(supplier_id,channel,is_active) VALUES (%s,'LINE',true) RETURNING id", (supplier,))
            channel = cursor.fetchone()[0]
            cursor.execute("INSERT INTO tenant_951.tcg_products(id,code,japanese_title,category_class,is_active) VALUES (%s,'P','Legacy title','Box',true)", (str(PRODUCT_UUID),))
            cursor.execute("INSERT INTO public.products(product_code,name,category_class,is_active) VALUES ('P','Master','Box',true) RETURNING id")
            product = cursor.fetchone()[0]
            for index in range(6):
                cursor.execute("INSERT INTO tenant_951.source_messages(supplier_channel_id,raw_text,raw_sha256,is_active,line_posted_at) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                               (channel if index < 3 else None, "Heading\nSlot 1 sold\nSlot 2 available", str(index), index < 2, STAMP if index < 3 else None))
                source = cursor.fetchone()[0]
                cursor.execute("INSERT INTO tenant_951.extraction_jobs(source_message_id,status) VALUES (%s,'completed') RETURNING id", (source,))
                job = cursor.fetchone()[0]
                cursor.execute("INSERT INTO tenant_951.extraction_items(extraction_job_id,raw_product_name,raw_quantity,raw_price,raw_unit,line_start,line_end) VALUES (%s,%s,%s,%s,%s,2,2) RETURNING id",
                               (job, "Literal%_\\" if index == 2 else "Shared", None if index == 3 else "84", "1200", "BOX" if index % 2 else "case"))
                item = cursor.fetchone()[0]
                cursor.execute("INSERT INTO tenant_951.analysis_results(id,extraction_item_id,product_id,pid_resolved,unit_resolved,needs_review,engine_version,status) VALUES (%s,%s,%s,false,false,false,'fixture',%s)",
                               (str(UUID(int=index + 1)), item, product if index < 2 else None, "In Stock" if index == 4 else "Pre-order" if index == 5 else "Sold out"))
        connection.commit()
    finally:
        connection.close()
    monkeypatch.setattr(service, "TCG_SCHEMA", "tenant_951")
    engine = create_async_engine(url.set(database=name, drivername="postgresql+asyncpg"), echo=False)
    try:
        async with AsyncSession(engine) as db:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            yield db
            await db.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pg_scopes_paging_and_authoritative_values(pg):
    all_rows = await service.fetch_sold_out_results(pg)
    assert all_rows["total"] == 4
    assert [r["analysis_result_id"] for r in all_rows["items"]] == [str(UUID(int=i)) for i in (3, 2, 1, 4)]
    assert len({r["analysis_result_id"] for r in all_rows["items"]}) == 4
    assert {r["status"] for r in all_rows["items"]} == {"Sold out"}
    assert all_rows["items"][-1]["raw_quantity"] == ""
    assert all_rows["items"][-1]["provider"] == ""
    assert all_rows["items"][-1]["supplier_id"] is None
    assert all_rows["items"][-1]["product_id"] is None
    assert all_rows["items"][-1]["product_title"] == ""
    assert all_rows["items"][-1]["line_posted_at"] is None
    for scope, count in (("active", 2), ("history", 2)):
        assert (await service.fetch_sold_out_results(pg, source_scope=scope))["total"] == count
    beyond = await service.fetch_sold_out_results(pg, offset=99)
    assert beyond["items"] == [] and beyond["total"] == 4
    first = await service.fetch_sold_out_results(pg, limit=1)
    second = await service.fetch_sold_out_results(pg, limit=1, offset=1)
    assert first["total"] == second["total"] == 4
    assert first["items"][0]["analysis_result_id"] != second["items"][0]["analysis_result_id"]
    known = [row for row in all_rows["items"] if row["product_id"] is not None]
    assert len(known) == 2
    known_pids = {row["product_id"] for row in known}
    assert len(known_pids) == 1
    assert isinstance(next(iter(known_pids)), int)
    assert {row["product_title"] for row in known} == {"Master"}
    routes.SoldOutResultsResponse.model_validate(all_rows)


@pytest.mark.asyncio
async def test_pg_literal_search_and_read_only(pg):
    assert (await pg.execute(text("SHOW transaction_read_only"))).scalar_one() == "on"
    for q, expected in (("%_\\", 1), ("percent%", 3), ("Master", 2), ("Legacy title", 0), (" Shared ", 3), ("' OR 1=1 --", 0), ("missing", 0)):
        result = await service.fetch_sold_out_results(pg, q=q)
        assert result["total"] == expected
    result = await service.fetch_sold_out_results(pg)
    assert result["as_of"].tzinfo is not None
    assert (await pg.execute(text("SHOW transaction_read_only"))).scalar_one() == "on"
