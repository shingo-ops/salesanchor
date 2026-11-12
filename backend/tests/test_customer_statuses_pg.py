"""会社と連絡先の status が public.customer_statuses に外部キーで結ばれていることの守り（PostgreSQL・RLS）。

使い捨て DB を試験ごとに作り、tenant.py の表の形（bootstrap_tenant_schema）で確かめる。
RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL が無ければ skip。会社番号は 979。
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not ADMIN_PG_URL or not APP_PG_URL,
        reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。",
    ),
    pytest.mark.asyncio,
]

_TENANT = 979
_SCHEMA = "tenant_979"
_GRANT_DDL = f"""
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
GRANT USAGE ON SCHEMA {_SCHEMA} TO salesanchor_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {_SCHEMA} TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {_SCHEMA} TO salesanchor_app;
"""


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り、会社の領域を用意して (admin_engine, app_engine, lead_id) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.rls_bootstrap import bootstrap_tenant_schema

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "cust_st_" + uuid.uuid4().hex[:12]
    async with control.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine = create_async_engine(_with_db(ADMIN_PG_URL, name), echo=False)
    app_engine = create_async_engine(_with_db(APP_PG_URL, name), echo=False, pool_size=1, max_overflow=0)
    try:
        await bootstrap_tenant_schema(admin_engine, _TENANT)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
            lead_id = (
                await conn.execute(
                    text(f"INSERT INTO {_SCHEMA}.leads (customer_name) VALUES ('lead') RETURNING id")
                )
            ).scalar_one()
        yield admin_engine, app_engine, lead_id
    finally:
        await app_engine.dispose()
        await admin_engine.dispose()
        async with control.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await control.dispose()


async def _ctx_conn(app_engine):
    from sqlalchemy import text

    conn = await app_engine.connect()
    trans = await conn.begin()
    await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(_TENANT)})
    return conn, trans


async def _insert_company(conn, lead_id: int, code: str, status: str) -> int:
    from sqlalchemy import text

    return (
        await conn.execute(
            text(
                f"INSERT INTO {_SCHEMA}.companies (company_code, lead_id, name, status) "
                "VALUES (:c, :l, :n, :s) RETURNING id"
            ),
            {"c": code, "l": lead_id, "n": code, "s": status},
        )
    ).scalar_one()


async def _insert_contact(conn, company_id: int, code: str, status: str) -> None:
    from sqlalchemy import text

    await conn.execute(
        text(
            f"INSERT INTO {_SCHEMA}.contacts (company_id, contact_code, status) VALUES (:co, :c, :s)"
        ),
        {"co": company_id, "c": code, "s": status},
    )


async def test_k10_app_role_can_insert_company_and_contact_with_listed_status():
    async with _fresh() as (_admin, app_engine, lead_id):
        conn, trans = await _ctx_conn(app_engine)
        try:
            company_id = await _insert_company(conn, lead_id, "C-OK", "active")
            await _insert_contact(conn, company_id, "P-OK", "pending_dedup_review")
        finally:
            await trans.rollback()
            await conn.close()


async def test_k3_unknown_status_is_refused_by_foreign_key():
    async with _fresh() as (_admin, app_engine, lead_id):
        conn, trans = await _ctx_conn(app_engine)
        try:
            with pytest.raises((IntegrityError, DBAPIError)) as exc:
                await _insert_company(conn, lead_id, "C-NG", "no_such_status")
            assert "23503" in str(exc.value) or "ForeignKeyViolation" in str(exc.value)
        finally:
            await trans.rollback()
            await conn.close()

        conn, trans = await _ctx_conn(app_engine)
        try:
            company_id = await _insert_company(conn, lead_id, "C-OK2", "active")
            with pytest.raises((IntegrityError, DBAPIError)) as exc:
                await _insert_contact(conn, company_id, "P-NG", "no_such_status")
            assert "23503" in str(exc.value) or "ForeignKeyViolation" in str(exc.value)
        finally:
            await trans.rollback()
            await conn.close()


async def test_status_foreign_keys_exist_and_old_checks_are_gone():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, _app, _lead):
        async with admin_engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT c.relname, con.conname, con.contype::text, con.convalidated "
                        "FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = :s AND c.relname IN ('companies', 'contacts') "
                        "AND con.conname IN ('companies_status_fkey', 'contacts_status_fkey', "
                        "'companies_status_check', 'contacts_status_check')"
                    ),
                    {"s": _SCHEMA},
                )
            ).all()
        found = {(r[0], r[1]): (r[2], r[3]) for r in rows}
        assert found.get(("companies", "companies_status_fkey")) == ("f", True)
        assert found.get(("contacts", "contacts_status_fkey")) == ("f", True)
        assert ("companies", "companies_status_check") not in found
        assert ("contacts", "contacts_status_check") not in found


def _repo_sql_codes() -> set[str]:
    """docs/handoff/status-ssot-contact-company/insert-customer-statuses.sql の4行の code。"""
    import re
    from pathlib import Path

    sql = (
        Path(__file__).resolve().parents[2]
        / "docs" / "handoff" / "status-ssot-contact-company" / "insert-customer-statuses.sql"
    ).read_text("utf-8")
    return set(re.findall(r"^\s*\('([a-z_]+)'\s*,", sql, re.MULTILINE))


async def test_k14_enums_match_table_codes_and_insert_sql():
    from sqlalchemy import text

    from app.schemas.company import CompanyStatus
    from app.schemas.contact import ContactStatus

    async with _fresh() as (admin_engine, _app, _lead):
        async with admin_engine.connect() as conn:
            table_codes = {
                r[0] for r in (await conn.execute(text("SELECT code FROM public.customer_statuses"))).all()
            }
    assert {s.value for s in CompanyStatus} == table_codes
    assert {s.value for s in ContactStatus} == table_codes
    assert _repo_sql_codes() == table_codes


async def test_k14_list_customer_statuses_has_selectable_on_create_like_table():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.customer_statuses import (
        STATUS_PENDING_DEDUP_REVIEW,
        list_customer_statuses,
    )

    async with _fresh() as (admin_engine, _app, _lead):
        async with AsyncSession(admin_engine) as db:
            rows = await list_customer_statuses(db)
            table = (
                await db.execute(
                    text(
                        "SELECT code, selectable_on_create FROM public.customer_statuses ORDER BY sort_order"
                    )
                )
            ).all()
    assert [r["code"] for r in rows] == [r[0] for r in table]
    assert all("selectable_on_create" in r and "name_ja" in r and "name_en" in r for r in rows)
    assert {r["code"]: r["selectable_on_create"] for r in rows} == {r[0]: r[1] for r in table}
    assert {r["code"] for r in rows if not r["selectable_on_create"]} == {STATUS_PENDING_DEDUP_REVIEW}


async def test_k14_api_customer_statuses_returns_table_rows():
    from types import SimpleNamespace

    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth import dependencies as auth_deps
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.routers import customer_statuses as router_mod
    from app.services.customer_statuses import list_customer_statuses

    async with _fresh() as (_admin, app_engine, _lead):
        async with AsyncSession(app_engine) as db:
            app = FastAPI()
            app.include_router(router_mod.router, prefix="/api/v1")
            app.dependency_overrides[router_mod.get_db] = lambda: db
            app.dependency_overrides[auth_deps.get_db] = lambda: db
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7, is_super_admin=False)
            app.dependency_overrides[get_current_tenant] = lambda: _TENANT
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/v1/customer-statuses")
            expected = await list_customer_statuses(db)
    assert res.status_code == 200
    assert res.json() == expected
    assert all("selectable_on_create" in row for row in res.json())
