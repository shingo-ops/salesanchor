"""PostgreSQL regression coverage for the DIST-01 preview precision gate."""
import os
from datetime import datetime, timedelta, timezone
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

from app.routers import tcg_distribution as routes
from app.services import tcg_distribution_svc as svc
from tests.conftest import _PUBLIC_SUPPLIERS_DDL
from tests.test_tcg_work_matching_integration import _PUBLIC_PRODUCTS_DDL

URL = os.getenv("RLS_ADMIN_DATABASE_URL")
if not URL and os.getenv("CI"):
    raise RuntimeError("RLS_ADMIN_DATABASE_URL is required for PostgreSQL regression tests in CI")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="Disposable PostgreSQL required locally")]


async def _exec_multi_stmt(conn, sql: str) -> None:
    """Execute multi-statement SQL via asyncpg Simple Query protocol.

    asyncpg's exec_driver_sql() uses the Prepared Statement protocol which
    rejects multi-statement SQL (including DO $$ ... $$ blocks).  Dropping
    to the raw driver connection and calling .execute() uses the Simple Query
    protocol instead, which handles multiple statements in one call.
    """
    raw = await conn.get_raw_connection()
    await raw.driver_connection.execute(sql)


async def create_schema(conn, schema, corrections=True):
    await conn.execute(text(f"CREATE SCHEMA {schema}"))
    await conn.exec_driver_sql("SELECT pg_advisory_lock(2147483647)")
    try:
        await conn.exec_driver_sql("SAVEPOINT public_products_ddl")
        for stmt in _PUBLIC_PRODUCTS_DDL.split(';'):
            stmt = stmt.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)
        for stmt in _PUBLIC_SUPPLIERS_DDL.split(';'):
            stmt = stmt.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)
    except Exception:
        await conn.exec_driver_sql("ROLLBACK TO SAVEPOINT public_products_ddl")
    await conn.exec_driver_sql("SELECT pg_advisory_unlock(2147483647)")
    # Guarantee work_id column exists even if SAVEPOINT rolled back (pre-existing table).
    # IF EXISTS prevents failure when public.products was never created (SAVEPOINT rolled back due to
    # something other than a duplicate-table conflict, e.g. early-stage provisioning on a fresh DB).
    await conn.exec_driver_sql("ALTER TABLE IF EXISTS public.products ADD COLUMN IF NOT EXISTS work_id INTEGER")
    migrations = Path(__file__).resolve().parents[2] / "migrations"
    # Phase 2 SSOT: public.type_master required by fetch_output_rows JOIN
    for sql_file in (
        "085_create_tcg_type_master.sql",
        "086_seed_additional_tcg_types.sql",
        "20260921_060000_create_product_kinds.sql",
        "20260921_070000_rename_tcg_type_master_to_type_master.sql",
    ):
        sql_path = migrations / sql_file
        if sql_path.exists():
            await _exec_multi_stmt(conn, sql_path.read_text())
    # Phase 3 SSOT: public.conditions / public.units required by review_joins() in condition_review_svc.
    # Only the DDL is needed; seeding data is not required because all JOINs are LEFT JOINs.
    await _exec_multi_stmt(conn, (migrations / "20260919_020000_master_ssot_public_tables.sql").read_text())
    names = [
        "20260831_110000_create_tcg_analysis_tables_t004.sql",
        "20260903_210000_tcg_distribution_settings_t004.sql",
    ]
    if corrections:
        names.insert(1, "20260903_170000_item_corrections_t004.sql")
    for name in names:
        await conn.exec_driver_sql((migrations / name).read_text().replace("tenant_004", schema))


@pytest_asyncio.fixture
async def distribution_db(monkeypatch):
    url = make_url(URL)
    assert url.database == "jarvis_test_db" and url.host in ("localhost", "127.0.0.1")
    schema = "dist01_test_" + uuid4().hex
    monkeypatch.setattr(svc, "TCG_SCHEMA", schema)
    engine = create_async_engine(url.set(drivername="postgresql+asyncpg"))
    try:
        async with engine.connect() as conn:
            transaction = await conn.begin()
            try:
                await create_schema(conn, schema)
                async with AsyncSession(bind=conn) as db:
                    yield db, schema
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


async def add_flag(db, schema, computed_at, updated_at=None, correction_at=None, flag="FLAG_SINGLE"):
    """Insert the real FK chain required by one analysis result."""
    now = datetime.now(timezone.utc)
    message_id = uuid4()
    job_id = uuid4()
    item_id = uuid4()
    await db.execute(text(
        f"INSERT INTO {schema}.source_messages (id, raw_text, raw_sha256, is_active) "
        "VALUES (:id, 'fixture', :sha, true)"
    ), {"id": message_id, "sha": uuid4().hex + uuid4().hex})
    await db.execute(text(
        f"INSERT INTO {schema}.extraction_jobs (id, source_message_id, status) "
        "VALUES (:id, :message, 'completed')"
    ), {"id": job_id, "message": message_id})
    await db.execute(text(
        f"INSERT INTO {schema}.extraction_items (id, extraction_job_id) VALUES (:id, :job)"
    ), {"id": item_id, "job": job_id})
    await db.execute(text(
        f"INSERT INTO {schema}.analysis_results "
        "(extraction_item_id,pid_resolved,unit_resolved,condition_canonical,price_normalized,"
        "needs_review,engine_version,computed_at,updated_at) "
        "VALUES (:item,true,true,:flag,100,true,'test',:computed,:updated)"
    ), {"item": item_id, "flag": flag, "computed": computed_at, "updated": updated_at or now})
    if correction_at is not None:
        await db.execute(text(
            f"INSERT INTO {schema}.item_corrections "
            "(extraction_item_id,source_message_id,field_name,human_value,corrected_by,corrected_at) "
            "VALUES (:item,:message,'price','100','tester',:corrected)"
        ), {"item": item_id, "message": message_id, "corrected": correction_at})


async def gate(db):
    return await svc._fetch_flag_gate_status(db, await svc.load_distribution_settings(db))


async def transaction_now(db):
    return (await db.execute(text("SELECT NOW()"))).scalar_one()


async def test_empty_and_threshold_boundaries(distribution_db):
    db, schema = distribution_db
    empty = await gate(db)
    assert empty["recent_samples"] == 0
    assert empty["correction_rate_pct"] is None
    assert empty["gate_status"] == "insufficient_samples"
    now = await transaction_now(db)
    for _ in range(49):
        await add_flag(db, schema, now)
    result = await gate(db)
    assert result["recent_samples"] == 49 and result["correction_rate_pct"] == 0.0
    assert result["gate_status"] == "insufficient_samples"
    await add_flag(db, schema, now)
    result = await gate(db)
    assert result["recent_samples"] == 50 and result["correction_rate_pct"] == 0.0
    assert result["gate_status"] == "threshold_met"


@pytest.mark.parametrize(("corrections", "status"), [(5, "threshold_met"), (6, "threshold_not_met")])
async def test_correction_rate_threshold(distribution_db, corrections, status):
    db, schema = distribution_db
    now = await transaction_now(db)
    for index in range(100):
        await add_flag(db, schema, now, correction_at=now if index < corrections else None)
    result = await gate(db)
    assert result["recent_samples"] == 100
    assert result["correction_rate_pct"] == corrections
    assert result["gate_status"] == status


async def test_computed_at_30_day_boundary(distribution_db):
    db, schema = distribution_db
    now = await transaction_now(db)
    await add_flag(db, schema, now - timedelta(days=30, seconds=1))
    await add_flag(db, schema, now - timedelta(days=30))
    await add_flag(db, schema, now - timedelta(days=30) + timedelta(seconds=1))
    result = await gate(db)
    assert result["recent_samples"] == 2


async def test_correction_30_day_boundary(distribution_db):
    db, schema = distribution_db
    now = await transaction_now(db)
    # Corrections have an independent inclusive boundary on three otherwise recent rows.
    for index, delta in enumerate((timedelta(seconds=-1), timedelta(), timedelta(seconds=1))):
        await add_flag(db, schema, now, correction_at=now - timedelta(days=30) + delta)
    result = await gate(db)
    assert result["recent_samples"] == 3
    assert result["correction_rate_pct"] == 66.7


async def test_computed_at_is_not_updated_at(distribution_db):
    db, schema = distribution_db
    now = await transaction_now(db)
    await add_flag(db, schema, now - timedelta(days=1), now - timedelta(days=31), now)
    await add_flag(db, schema, now - timedelta(days=31), now - timedelta(days=1))
    result = await gate(db)
    assert result["recent_samples"] == 1
    assert result["correction_rate_pct"] == 100.0


async def test_non_flag_rows_are_excluded(distribution_db):
    db, schema = distribution_db
    await add_flag(db, schema, await transaction_now(db), flag="NORMAL")
    assert (await gate(db))["recent_samples"] == 0


async def test_missing_correction_table_is_reported(monkeypatch):
    url = make_url(URL)
    assert url.database == "jarvis_test_db" and url.host in ("localhost", "127.0.0.1")
    schema = "dist01_no_correction_" + uuid4().hex
    monkeypatch.setattr(svc, "TCG_SCHEMA", schema)
    engine = create_async_engine(url.set(drivername="postgresql+asyncpg"))
    try:
        async with engine.connect() as conn:
            transaction = await conn.begin()
            try:
                await create_schema(conn, schema, corrections=False)
                async with AsyncSession(bind=conn) as db:
                    assert (await gate(db))["gate_status"] == "no_correction_table"
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


async def test_preview_api_uses_real_service_and_keeps_flag_disabled(distribution_db, monkeypatch):
    db, schema = distribution_db
    await add_flag(db, schema, await transaction_now(db))
    monkeypatch.setattr(routes.svc, "TCG_SCHEMA", schema)
    monkeypatch.setattr(svc, "_build_gspread_client", lambda: (_ for _ in ()).throw(AssertionError("preview called Sheets")))
    settings_before = await svc.load_distribution_settings(db)
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[routes.get_db] = lambda: db
    app.dependency_overrides[routes.require_super_admin] = lambda: SimpleNamespace(is_super_admin=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/tcg/distribution/preview")
    assert response.status_code == 200
    body = response.json()
    assert body["output_count"] == 0
    assert body["flag_gate"]["recent_samples"] == 1
    assert body["flag_gate"]["include_flag_single"] is False
    assert body["settings"] == settings_before == await svc.load_distribution_settings(db)


async def test_production_migration_has_no_created_at(distribution_db):
    db, schema = distribution_db
    columns = (await db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = :schema AND table_name = 'analysis_results'"
    ), {"schema": schema})).scalars().all()
    assert "created_at" not in columns
    assert {"computed_at", "updated_at"}.issubset(columns)
