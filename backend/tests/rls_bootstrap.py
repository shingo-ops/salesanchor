from __future__ import annotations

from contextlib import asynccontextmanager, suppress

from sqlalchemy import text

from app.services.tenant import create_tenant_schema

_TENANT_SCHEMA_LOCK_NAMESPACE = 20260623


@asynccontextmanager
async def tenant_schema_lock(admin_engine, tenant_id: int):
    """同じ tenant schema を使う PG/RLS テストを xdist 下で直列化する。"""
    async with admin_engine.connect() as conn:
        await conn.execute(
            text("SELECT pg_advisory_lock(:namespace, :tenant_id)"),
            {"namespace": _TENANT_SCHEMA_LOCK_NAMESPACE, "tenant_id": int(tenant_id)},
        )
        try:
            yield
        finally:
            with suppress(Exception):
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:namespace, :tenant_id)"),
                    {"namespace": _TENANT_SCHEMA_LOCK_NAMESPACE, "tenant_id": int(tenant_id)},
                )


async def bootstrap_tenant_schema(admin_engine, tenant_id: int) -> str:
    """本番 migration 順で tenant schema を冪等に作成する。"""
    async with admin_engine.begin() as conn:
        schema_name = f"tenant_{int(tenant_id):03d}"
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        schema_name = await create_tenant_schema(conn, tenant_id, admin_db=conn)
    return schema_name


@asynccontextmanager
async def tenant_rls_session(session_factory, tenant_id: int):
    """RLS 用に app.tenant_id を設定した session を返す。"""
    async with session_factory() as session:
        async with session.begin():
            schema_name = f"tenant_{int(tenant_id):03d}"
            await session.execute(text(f"SET search_path = {schema_name}, public"))
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(int(tenant_id))},
            )
            await session.execute(text("SELECT set_config('app.is_operator', '', true)"))
            yield session
