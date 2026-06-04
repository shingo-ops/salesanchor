"""ADR-108: GET /leads/{id}/summary 実績サマリー（読み取り専用派生値）テスト。

検証する受け入れ条件:
  - 取引額累計 = invoices の `paid_at IS NOT NULL AND voided_at IS NULL` の合計。
    void 済み / 未入金は集計しない（status では判定しない）。
  - リード ↔ invoice の対応は `deals.lead_id` 経由（company_id + contact_id 突合）。
  - 取引が 1 件も無い場合 deal_count=0 / total_deal_amount=0（フロントは「取引実績なし」）。
  - 会話数 / 最終会話は meta_messages から集計。
"""

from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.routers import leads as leads_router

_LEAD_DDL = """
    CREATE TABLE leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL DEFAULT 999,
        lead_code VARCHAR(20),
        customer_name VARCHAR(200),
        status VARCHAR(50),
        converted_deal_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_DEALS_DDL = """
    CREATE TABLE deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL DEFAULT 999,
        lead_id INTEGER,
        company_id INTEGER,
        contact_id INTEGER
    )
"""

_INVOICES_DDL = """
    CREATE TABLE invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL DEFAULT 999,
        company_id INTEGER,
        contact_id INTEGER,
        total_amount NUMERIC(15, 2) DEFAULT 0,
        paid_at TIMESTAMP,
        voided_at TIMESTAMP
    )
"""

_META_MESSAGES_DDL = """
    CREATE TABLE meta_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL DEFAULT 999,
        lead_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _setup(dbapi_conn, _):
        dbapi_conn.create_function(
            "NOW", 0,
            lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00"),
        )

    async with eng.begin() as conn:
        await conn.execute(text(_LEAD_DDL))
        await conn.execute(text(_DEALS_DDL))
        await conn.execute(text(_INVOICES_DDL))
        await conn.execute(text(_META_MESSAGES_DDL))

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


def _mock_user():
    u = MagicMock()
    u.id = 1
    u.tenant_id = 999
    u.email = "tester@example.com"
    return u


@pytest_asyncio.fixture
async def app_client(db_session):
    app = FastAPI()

    async def override_db():
        yield db_session

    app.include_router(leads_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    app.dependency_overrides[get_current_tenant] = lambda: 999

    transport = ASGITransport(app=app)
    with ExitStack() as stack:
        stack.enter_context(patch(
            "app.auth.dependencies.load_user_permissions",
            new=AsyncMock(return_value={"leads.view"}),
        ))
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


async def _insert_lead(db, *, lead_id: int, status: str = "新規", tenant_id: int = 999):
    await db.execute(text("""
        INSERT INTO leads (id, tenant_id, lead_code, customer_name, status)
        VALUES (:id, :tid, :code, 'Cust', :status)
    """), {"id": lead_id, "tid": tenant_id, "code": f"LD-{lead_id:05d}", "status": status})


async def _insert_deal(db, *, lead_id: int, company_id: int, contact_id: int, tenant_id: int = 999):
    await db.execute(text("""
        INSERT INTO deals (tenant_id, lead_id, company_id, contact_id)
        VALUES (:tid, :lid, :cid, :ctid)
    """), {"tid": tenant_id, "lid": lead_id, "cid": company_id, "ctid": contact_id})


async def _insert_invoice(db, *, company_id, contact_id, total, paid_at, voided_at=None, tenant_id=999):
    await db.execute(text("""
        INSERT INTO invoices (tenant_id, company_id, contact_id, total_amount, paid_at, voided_at)
        VALUES (:tid, :cid, :ctid, :total, :paid, :void)
    """), {"tid": tenant_id, "cid": company_id, "ctid": contact_id,
           "total": total, "paid": paid_at, "void": voided_at})


async def _insert_message(db, *, lead_id, tenant_id=999, created_at=None):
    await db.execute(text("""
        INSERT INTO meta_messages (tenant_id, lead_id, created_at)
        VALUES (:tid, :lid, COALESCE(:ca, CURRENT_TIMESTAMP))
    """), {"tid": tenant_id, "lid": lead_id, "ca": created_at})


@pytest.mark.asyncio
async def test_summary_sums_only_paid_non_voided_invoices(app_client, db_session):
    """取引額累計は paid_at 非NULL かつ voided_at NULL の合計に一致する。"""
    await _insert_lead(db_session, lead_id=1)
    await _insert_deal(db_session, lead_id=1, company_id=10, contact_id=20)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
    # 集計対象: paid かつ未void → 1000 + 480
    await _insert_invoice(db_session, company_id=10, contact_id=20, total=1000, paid_at=now)
    await _insert_invoice(db_session, company_id=10, contact_id=20, total=480, paid_at=now)
    # 除外: void 済み
    await _insert_invoice(db_session, company_id=10, contact_id=20, total=9999, paid_at=now, voided_at=now)
    # 除外: 未入金
    await _insert_invoice(db_session, company_id=10, contact_id=20, total=7777, paid_at=None)
    # 除外: 別 company/contact（このリードの deal と不一致）
    await _insert_invoice(db_session, company_id=99, contact_id=99, total=5555, paid_at=now)
    await _insert_message(db_session, lead_id=1)
    await _insert_message(db_session, lead_id=1)
    await db_session.commit()

    resp = await app_client.get("/api/v1/leads/1/summary")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_deal_amount"] == 1480.0
    assert data["deal_count"] == 2
    assert data["last_deal_at"] is not None
    assert data["conversation_count"] == 2
    assert data["last_conversation_at"] is not None


@pytest.mark.asyncio
async def test_summary_no_transactions_returns_zero(app_client, db_session):
    """取引が 1 件も無いとき deal_count=0 / total=0（フロントは「取引実績なし」）。"""
    await _insert_lead(db_session, lead_id=2, status="新規")
    await db_session.commit()

    resp = await app_client.get("/api/v1/leads/2/summary")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_deal_amount"] == 0
    assert data["deal_count"] == 0
    assert data["last_deal_at"] is None
    assert data["conversation_count"] == 0


@pytest.mark.asyncio
async def test_summary_404_for_missing_lead(app_client, db_session):
    resp = await app_client.get("/api/v1/leads/999/summary")
    assert resp.status_code == 404
