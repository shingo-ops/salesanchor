"""
Cross-tenant product reference check test (SA-18 Phase2).

Verifies that ``_check_product_references`` correctly detects when a product
is referenced by another tenant's downstream tables (quote_items etc.) using
the admin_db connection for cross-schema scanning.

Requires:
  RLS_TEST_DATABASE_URL  - non-superuser connection (salesanchor_app / jarvis_app)
  RLS_ADMIN_DATABASE_URL - superuser/owner connection (jarvis) [optional]

When RLS_TEST_DATABASE_URL is not set, this test is skipped (SQLite-only CI).
"""
from __future__ import annotations

import os
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

_APP_URL: Optional[str] = os.getenv("RLS_TEST_DATABASE_URL")
_ADMIN_URL: str = os.getenv(
    "RLS_ADMIN_DATABASE_URL",
    "postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db",
)

pytestmark = pytest.mark.skipif(
    not _APP_URL,
    reason="RLS_TEST_DATABASE_URL not set (PostgreSQL-only test)",
)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def admin_engine():
    eng = create_async_engine(_ADMIN_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def app_engine():
    assert _APP_URL
    eng = create_async_engine(_APP_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def setup_cross_tenant_tables(admin_engine):
    """
    Create a minimal schema (tenant_998) with a quote_items table
    that references a product, to test cross-tenant FK detection.
    """
    async with admin_engine.begin() as conn:
        # Create test schema
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS tenant_998"))
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS tenant_998.quote_items (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL
            )
        """)
        )
        # Grant access to app roles.
        # SAVEPOINT per role: if the role doesn't exist the savepoint rolls back,
        # but the outer transaction remains alive (plain try/except doesn't prevent
        # asyncpg from aborting the transaction on error).
        for role in ("salesanchor_app", "jarvis_app"):
            try:
                async with conn.begin_nested():
                    await conn.execute(
                        text(f"GRANT USAGE ON SCHEMA tenant_998 TO {role}")
                    )
                    await conn.execute(
                        text(
                            f"GRANT SELECT ON ALL TABLES IN SCHEMA tenant_998 TO {role}"
                        )
                    )
            except Exception:
                pass  # role may not exist in this environment

        # Seed a reference row
        await conn.execute(
            text(
                "INSERT INTO tenant_998.quote_items (product_id) VALUES (99999)"
            )
        )
    yield
    async with admin_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS tenant_998 CASCADE"))


@pytest.mark.asyncio(loop_scope="module")
async def test_cross_tenant_product_reference_detected(
    admin_engine, app_engine, setup_cross_tenant_tables
):
    """
    When a product_id is referenced in another tenant's quote_items,
    the cross-schema scan via admin_db should detect it.
    """
    # Import the function under test
    from app.routers.products import _check_product_references

    # Use admin connection for the cross-schema scan
    async with admin_engine.connect() as admin_conn:
        async with admin_conn.begin():
            # Verify is_postgresql returns True for this connection
            # We need an AsyncSession-like object, but _check_product_references
            # uses db for dialect check and admin_db for scanning.
            # Use admin_conn for both in this test context.
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy.orm import sessionmaker

            AdminSession = sessionmaker(
                admin_engine, class_=AsyncSession, expire_on_commit=False
            )
            async with AdminSession() as admin_session:
                async with admin_session.begin():
                    blocking = await _check_product_references(
                        db=admin_session,
                        product_id=99999,
                        tenant_id=1,
                        admin_db=admin_session,
                    )
                    assert "quote_items" in blocking, (
                        f"Expected 'quote_items' in blocking references, got: {blocking}"
                    )


@pytest.mark.asyncio(loop_scope="module")
async def test_unreferenced_product_not_blocked(
    admin_engine, app_engine, setup_cross_tenant_tables
):
    """
    A product_id that is NOT referenced in any tenant's downstream tables
    should return an empty blocking list.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    AdminSession = sessionmaker(
        admin_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AdminSession() as admin_session:
        async with admin_session.begin():
            from app.routers.products import _check_product_references

            blocking = await _check_product_references(
                db=admin_session,
                product_id=77777,  # not referenced anywhere
                tenant_id=1,
                admin_db=admin_session,
            )
            assert blocking == [], f"Expected no blocking references, got: {blocking}"
