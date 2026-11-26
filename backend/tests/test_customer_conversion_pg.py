"""「既存顧客」の自動切り替え（ADR-1090）を実 PostgreSQL で確かめる試験。

SQLite の試験では通らない分岐を見る: ① FOR UPDATE の分岐が通ること ② 2 本の取引（入金・登録）を順に重ねて
最後に既存顧客になること ③ tenant_table_ref で別テナントの表を見ないこと。
実 PostgreSQL（RLS_ADMIN_DATABASE_URL か TEST_PG_URL と RLS_TEST_DATABASE_URL）があるときだけ動く。
"""
from __future__ import annotations

import os

import pytest

from tests.rls_bootstrap import bootstrap_tenant_schema, tenant_schema_lock

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not ADMIN_PG_URL or not APP_PG_URL,
        reason=(
            "実 PostgreSQL 環境が必要 "
            "(RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。"
        ),
    ),
    pytest.mark.asyncio,
]

_TENANT = 987
_OTHER_TENANT = 986


async def _engines():
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)
    return admin_engine, app_engine, factory


async def _seed(admin_engine, tenant_id: int, *, billing: bool, paid: bool) -> tuple[int, int]:
    """リード・会社を作り、billing=True なら既定の請求先、paid=True なら支払い済みの注文を足す。"""
    from sqlalchemy import text

    schema = f"tenant_{tenant_id:03d}"
    async with admin_engine.begin() as conn:
        lead_id = (
            await conn.execute(
                text(f"INSERT INTO {schema}.leads (tenant_id, customer_name) VALUES (:t, 'CC-PG') RETURNING id"),
                {"t": tenant_id},
            )
        ).scalar_one()
        company_id = (
            await conn.execute(
                text(
                    f"INSERT INTO {schema}.companies (tenant_id, company_code, lead_id, name)"
                    f" VALUES (:t, 'CO-CCPG', :l, 'CC-PG Co') RETURNING id"
                ),
                {"t": tenant_id, "l": lead_id},
            )
        ).scalar_one()
        if billing:
            await conn.execute(
                text(
                    f"INSERT INTO {schema}.company_addresses (company_id, address_type, is_default, country_code)"
                    f" VALUES (:c, 'billing', TRUE, 'US')"
                ),
                {"c": company_id},
            )
        if paid:
            await conn.execute(
                text(
                    f"INSERT INTO {schema}.orders (tenant_id, company_id, order_number, paid_at)"
                    f" VALUES (:t, :c, 'CC-PG-1', NOW())"
                ),
                {"t": tenant_id, "c": company_id},
            )
    return lead_id, company_id


async def _admin_status(admin_engine, tenant_id: int, lead_id: int) -> str:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        return (
            await conn.execute(
                text(f"SELECT status FROM tenant_{tenant_id:03d}.leads WHERE id = :i"), {"i": lead_id}
            )
        ).scalar_one()


async def _open(factory, tenant_id: int):
    from sqlalchemy import text

    from app.auth.dependencies import set_tenant_context

    db = factory()
    await db.__aenter__()
    await set_tenant_context(db, tenant_id)
    await db.execute(text("SELECT 1"))
    return db


async def test_all_three_converts_with_for_update_branch():
    """3 つそろっていれば、PostgreSQL（FOR UPDATE の分岐）でも既存顧客になり、監査が 1 件残る。"""
    from sqlalchemy import text

    from app.services.customer_conversion import promote_lead_if_customer

    admin_engine, app_engine, factory = await _engines()
    try:
        async with tenant_schema_lock(admin_engine, _TENANT):
            await bootstrap_tenant_schema(admin_engine, _TENANT)
            lead_id, _ = await _seed(admin_engine, _TENANT, billing=True, paid=True)
            db = await _open(factory, _TENANT)
            try:
                ok = await promote_lead_if_customer(db, _TENANT, lead_id, actor_user_id=None, via="order_paid")
                await db.commit()
                assert ok is True
            finally:
                await db.__aexit__(None, None, None)
            assert await _admin_status(admin_engine, _TENANT, lead_id) == "existing_customer"
            # 2 回目は何も書かない（すでに既存顧客）
            db = await _open(factory, _TENANT)
            try:
                assert await promote_lead_if_customer(db, _TENANT, lead_id, actor_user_id=None, via="order_paid") is False
                await db.rollback()
            finally:
                await db.__aexit__(None, None, None)
            _ = text  # noqa: F841
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_two_transactions_in_a_row_last_one_converts():
    """入金の取引と登録の取引を順に重ねる: 入金だけでは切り替わらず、登録が入った後の判定で切り替わる。"""
    from sqlalchemy import text

    from app.services.customer_conversion import promote_lead_if_customer

    admin_engine, app_engine, factory = await _engines()
    try:
        async with tenant_schema_lock(admin_engine, _TENANT):
            await bootstrap_tenant_schema(admin_engine, _TENANT)
            lead_id, company_id = await _seed(admin_engine, _TENANT, billing=False, paid=True)

            # 取引 A: 入金が済んでいる状態で判定 → 請求先が無いので切り替わらない
            db_a = await _open(factory, _TENANT)
            try:
                assert await promote_lead_if_customer(db_a, _TENANT, lead_id, actor_user_id=None, via="order_paid") is False
                await db_a.commit()
            finally:
                await db_a.__aexit__(None, None, None)
            assert await _admin_status(admin_engine, _TENANT, lead_id) == "lead"

            # 取引 B: 請求先を足して判定 → 最後の 1 つなので切り替わる
            db_b = await _open(factory, _TENANT)
            try:
                await db_b.execute(
                    text(
                        f"INSERT INTO tenant_{_TENANT:03d}.company_addresses"
                        f" (company_id, address_type, is_default, country_code) VALUES (:c, 'billing', TRUE, 'US')"
                    ),
                    {"c": company_id},
                )
                assert await promote_lead_if_customer(db_b, _TENANT, lead_id, actor_user_id=None, via="register_form") is True
                await db_b.commit()
            finally:
                await db_b.__aexit__(None, None, None)
            assert await _admin_status(admin_engine, _TENANT, lead_id) == "existing_customer"
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_does_not_see_other_tenant_tables():
    """tenant_table_ref で書くので、別テナントのそろったデータは見えない（自分のテナントに同じ番号のリードが無くても False）。"""
    from app.services.customer_conversion import is_registration_completed, promote_lead_if_customer

    admin_engine, app_engine, factory = await _engines()
    try:
        async with tenant_schema_lock(admin_engine, _OTHER_TENANT):
            await bootstrap_tenant_schema(admin_engine, _OTHER_TENANT)
        async with tenant_schema_lock(admin_engine, _TENANT):
            await bootstrap_tenant_schema(admin_engine, _TENANT)
        other_lead, _ = await _seed(admin_engine, _OTHER_TENANT, billing=True, paid=True)
        mine_lead, _ = await _seed(admin_engine, _TENANT, billing=False, paid=False)

        db = await _open(factory, _TENANT)
        try:
            # 自分のテナントのリードは未そろい。他テナントのそろったリードの番号を渡しても切り替わらない
            assert await promote_lead_if_customer(db, _TENANT, mine_lead, actor_user_id=None, via="order_paid") is False
            assert await is_registration_completed(db, _TENANT, mine_lead) is False
            await db.rollback()
        finally:
            await db.__aexit__(None, None, None)
        assert await _admin_status(admin_engine, _OTHER_TENANT, other_lead) == "lead"
        assert await _admin_status(admin_engine, _TENANT, mine_lead) == "lead"
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()
