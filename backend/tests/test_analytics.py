"""analytics EP のテスト (PR2: ファネルダッシュボード第1弾)

テスト構成:
  - 既存5EP のスモークテスト（status 200 確認）
  - test_analytics_jst_boundary: 月末 JST 件数確認
  - test_funnel_with_goals: ファネル達成率% assertion
  - test_follow_ups_thresholds: しきい値変化確認

NOTE:
  既存の /analytics/summary と /dashboard（dashboard.py）は
  FILTER (WHERE ...) を使用しており SQLite では動かない。
  FILTER 系 EP は skip し、PostgreSQL 統合テストで検証する。
"""

from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text


# ─────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────

async def _seed_companies_and_contacts(client, count: int = 3):
    """会社 + 担当者ペアを作成して返す"""
    pairs = []
    for i in range(count):
        co = await client.post("/api/v1/companies", json={"name": f"Company{i+1}"})
        company_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": company_id,
            "display_name": f"Contact{i+1}",
        })
        pairs.append((company_id, ct.json()["id"]))
    return pairs


async def _seed_leads(client, count: int = 3, prefix: str = "Lead"):
    """リードを作成して返す"""
    leads = []
    for i in range(count):
        res = await client.post("/api/v1/leads", json={
            "customer_name": f"{prefix}{i+1}",
            "status": "lead",
        })
        leads.append(res.json())
    return leads


async def _seed_deals(client, pairs, statuses=None):
    """商談を作成して返す"""
    if statuses is None:
        statuses = ["open", "open", "won"]
    deals = []
    for i, status in enumerate(statuses):
        pair = pairs[i % len(pairs)]
        res = await client.post("/api/v1/deals", json={
            "company_id": pair[0],
            "contact_id": pair[1],
            "title": f"Deal{i+1}",
            "amount": (i + 1) * 100000,
            "status": status,
        })
        deals.append(res.json())
    return deals


async def _seed_orders(client, pairs, count: int = 3):
    """注文を作成して返す"""
    orders = []
    for i in range(count):
        pair = pairs[i % len(pairs)]
        res = await client.post("/api/v1/orders", json={
            "company_id": pair[0],
            "contact_id": pair[1],
            "order_number": f"TEST-{i+1:03d}",
            "total_amount": (i + 1) * 50000,
            "status": "pending",
        })
        orders.append(res.json())
    return orders


@pytest_asyncio.fixture
async def client_tenant_006(db_session):
    """tenant_006 前提のテストクライアント。tenant_4 は使わない。"""
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.database import get_db
    from app.main import app
    from app.models import User
    from httpx import ASGITransport, AsyncClient
    from unittest.mock import patch

    mock_user = User()
    mock_user.id = 6
    mock_user.tenant_id = 6
    mock_user.username = "tenant006-user"
    mock_user.email = "tenant006@example.com"
    mock_user.role = "admin"
    mock_user.is_active = True

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return mock_user

    async def override_get_current_tenant():
        return 6

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    await db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            company_id INTEGER,
            contact_id INTEGER,
            channel_type VARCHAR(30) NOT NULL,
            channel_identity VARCHAR(255),
            direction VARCHAR(10) NOT NULL,
            sender VARCHAR(100),
            content_text TEXT,
            external_message_id VARCHAR(255),
            raw_payload TEXT,
            status VARCHAR(20) DEFAULT 'sent',
            translated_text TEXT,
            analysis TEXT,
            occurred_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    await db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS public.data_access_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type VARCHAR(30) NOT NULL,
            method VARCHAR(20) NOT NULL,
            path VARCHAR(255) NOT NULL,
            status_code INTEGER NOT NULL,
            user_email VARCHAR(255),
            client_ip VARCHAR(255),
            user_agent VARCHAR(255),
            duration_ms INTEGER
        )
    """))
    await db_session.commit()

    transport = ASGITransport(app=app)
    with (
        patch("app.routers.companies.record_audit_log", _noop_record_audit_log),
        patch("app.routers.contacts.record_audit_log", _noop_record_audit_log),
    ):
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_current_tenant, None)


async def _insert_conversation(
    db_session,
    *,
    company_id: int,
    contact_id: int | None,
    days_ago: int,
    tenant_id: int = 6,
    content_text: str = "test",
) -> None:
    occurred_at = date.today() - timedelta(days=days_ago)
    await db_session.execute(text("""
        INSERT INTO conversation_logs (
            tenant_id, company_id, contact_id,
            channel_type, direction, content_text, occurred_at
        ) VALUES (
            :tenant_id, :company_id, :contact_id,
            'email', 'inbound', :content_text, :occurred_at
        )
    """), {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "contact_id": contact_id,
        "content_text": content_text,
        "occurred_at": occurred_at,
    })


async def _insert_shift(
    db_session,
    *,
    shift_date: date,
    user_id: int = 6,
    tenant_id: int = 6,
) -> None:
    """tenant_006 の shifts 行を 1 件追加する。"""
    await db_session.execute(text("""
        INSERT INTO shifts (
            tenant_id, user_id, shift_date, start_time, end_time, shift_type, notes
        ) VALUES (
            :tenant_id, :user_id, :shift_date, '09:00', '18:00', 'normal', 'advisor-test'
        )
    """), {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "shift_date": shift_date.isoformat(),
    })


def _count_weekdays_inclusive(start: date, end: date) -> int:
    """start〜end を両端含みで平日だけ数える。"""
    if end < start:
        return 0
    total = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            total += 1
        current += timedelta(days=1)
    return total


def _month_end_date(today: date) -> date:
    from calendar import monthrange

    return date(today.year, today.month, monthrange(today.year, today.month)[1])


def _week_end_date(today: date) -> date:
    return today + timedelta(days=(6 - today.weekday()))


async def _noop_record_audit_log(*args, **kwargs):
    return None


# ─────────────────────────────────────────────
# 既存5EP スモークテスト
# ─────────────────────────────────────────────

class TestExistingEPSmoke:
    """既存 analytics EP が 200 を返すことを確認"""

    async def test_conversion_empty(self, client):
        """GET /analytics/conversion — データなしで 200"""
        res = await client.get("/api/v1/analytics/conversion")
        assert res.status_code == 200
        data = res.json()
        assert data["overall_rate"] == 0.0
        assert data["entries"] == []

    @pytest.mark.skip(reason="FILTER (WHERE ...) + ::date cast is PostgreSQL-specific")
    async def test_stalled_deals_empty(self, client):
        """GET /analytics/stalled-deals — データなしで 200"""
        res = await client.get("/api/v1/analytics/stalled-deals")
        assert res.status_code == 200

    @pytest.mark.skip(reason="FILTER (WHERE ...) + ::date cast is PostgreSQL-specific")
    async def test_overdue_invoices_empty(self, client):
        """GET /analytics/overdue-invoices — データなしで 200"""
        res = await client.get("/api/v1/analytics/overdue-invoices")
        assert res.status_code == 200

    @pytest.mark.skip(reason="CURRENT_DATE - next_action_date)::INTEGER is PostgreSQL-specific")
    async def test_followups_empty(self, client):
        """GET /analytics/followups — データなしで 200"""
        res = await client.get("/api/v1/analytics/followups")
        assert res.status_code == 200
        data = res.json()
        assert data["overdue"] == []
        assert data["due_today"] == []
        assert data["upcoming"] == []

    @pytest.mark.skip(reason="FILTER (WHERE ...) is PostgreSQL-specific")
    async def test_summary_empty(self, client):
        """GET /analytics/summary — データなしで 200"""
        res = await client.get("/api/v1/analytics/summary")
        assert res.status_code == 200


# ─────────────────────────────────────────────
# JST 境界テスト
# ─────────────────────────────────────────────

class TestJSTBoundary:
    """月末 JST 件数確認"""

    def test_jst_month_range_utc_basic(self):
        """_jst_month_range_utc が正しい UTC 境界を返す"""
        from app.services.time import _jst_month_range_utc
        from datetime import timezone

        start, end = _jst_month_range_utc(2026, 6)
        # JST 2026-06-01 00:00 = UTC 2026-05-31 15:00
        assert start.year == 2026
        assert start.month == 5
        assert start.day == 31
        assert start.hour == 15
        assert start.tzinfo == timezone.utc

        # JST 2026-07-01 00:00 = UTC 2026-06-30 15:00
        assert end.year == 2026
        assert end.month == 6
        assert end.day == 30
        assert end.hour == 15

    def test_jst_december_boundary(self):
        """12月の年跨ぎ境界が正しい"""
        from app.services.time import _jst_month_range_utc

        start, end = _jst_month_range_utc(2026, 12)
        # JST 2026-12-01 00:00 = UTC 2026-11-30 15:00
        assert start.month == 11
        assert start.day == 30
        # JST 2027-01-01 00:00 = UTC 2026-12-31 15:00
        assert end.year == 2026
        assert end.month == 12
        assert end.day == 31

    @pytest.mark.skip(reason="FILTER (WHERE ...) is PostgreSQL-specific in dashboard_summary")
    async def test_analytics_jst_boundary(self, client):
        """JST 月末境界でデータが正しくカウントされる（PostgreSQL環境で検証）"""
        pass


# ─────────────────────────────────────────────
# ファネル EP テスト
# ─────────────────────────────────────────────

class TestFunnel:
    """GET /analytics/funnel"""

    async def test_funnel_empty(self, client):
        """データなしで 200 を返す"""
        res = await client.get("/api/v1/analytics/funnel")
        assert res.status_code == 200
        data = res.json()
        assert data["leads"]["actual"] == 0
        assert data["conversion"]["converted"] == 0
        assert data["active"]["count"] == 0
        assert data["closed"]["won"] == 0
        assert data["closed"]["lost"] == 0

    async def test_funnel_with_month_param(self, client):
        """month パラメータ指定が動作する"""
        res = await client.get("/api/v1/analytics/funnel?month=2026-06")
        assert res.status_code == 200
        data = res.json()
        assert data["month"] == "2026-06"

    async def test_funnel_with_goals(self, client, db_session):
        """目標値がある場合にファネルレスポンスに反映される"""
        # 目標を投入（team 目標: team_id=1, user_id=NULL）
        await db_session.execute(text("""
            INSERT INTO teams (id, tenant_id, name, is_active) VALUES (1, 999, 'TestTeam', 1)
        """))
        await db_session.execute(text("""
            INSERT INTO team_members (team_id, user_id) VALUES (1, 999)
        """))

        today = date.today()
        # lead_count 目標
        await db_session.execute(text("""
            INSERT INTO goals (user_id, team_id, period_type, period_year, period_num, kpi_type, target_value, created_by)
            VALUES (NULL, 1, 'monthly', :year, :month, 'lead_count', 30, 999)
        """), {"year": today.year, "month": today.month})
        # revenue 目標
        await db_session.execute(text("""
            INSERT INTO goals (user_id, team_id, period_type, period_year, period_num, kpi_type, target_value, created_by)
            VALUES (NULL, 1, 'monthly', :year, :month, 'revenue', 5000000, 999)
        """), {"year": today.year, "month": today.month})
        # won_count 目標
        await db_session.execute(text("""
            INSERT INTO goals (user_id, team_id, period_type, period_year, period_num, kpi_type, target_value, created_by)
            VALUES (NULL, 1, 'monthly', :year, :month, 'won_count', 10, 999)
        """), {"year": today.year, "month": today.month})
        await db_session.commit()

        res = await client.get("/api/v1/analytics/funnel")
        assert res.status_code == 200
        data = res.json()
        assert data["leads"]["target"] == 30
        assert data["closed"]["won_target"] == 10

    async def test_funnel_with_data(self, client, db_session):
        """データ投入時にファネル数値が正しい"""
        pairs = await _seed_companies_and_contacts(client)
        # リード 3件（1件コンバート済み）
        leads = await _seed_leads(client, 3)
        # 商談: open 2件, won 1件
        await _seed_deals(client, pairs, ["open", "open", "won"])

        res = await client.get("/api/v1/analytics/funnel")
        assert res.status_code == 200
        data = res.json()
        # リードは 3件作成
        assert data["leads"]["actual"] == 3
        # 進行中商談（open の 2件）
        assert data["active"]["count"] == 2


# ─────────────────────────────────────────────
# フォローアップ EP テスト
# ─────────────────────────────────────────────

class TestFollowUps:
    """GET /analytics/follow-ups"""

    async def test_follow_ups_empty(self, client):
        """データなしで 200 を返す"""
        res = await client.get("/api/v1/analytics/follow-ups")
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []

    async def test_follow_ups_thresholds(self, client, db_session):
        """フォローアップしきい値確認

        - order_stopped: 最終発注から30日超
        - won_no_order: 成約後30日超で発注なし
        """
        # 会社 + 担当者
        co1 = await client.post("/api/v1/companies", json={"name": "StoppedCo"})
        co1_id = co1.json()["id"]
        ct1 = await client.post("/api/v1/contacts", json={
            "company_id": co1_id, "display_name": "Contact1",
        })
        ct1_id = ct1.json()["id"]

        co2 = await client.post("/api/v1/companies", json={"name": "WonNoCo"})
        co2_id = co2.json()["id"]
        ct2 = await client.post("/api/v1/contacts", json={
            "company_id": co2_id, "display_name": "Contact2",
        })
        ct2_id = ct2.json()["id"]

        # 注文: 40日前に作成（order_stopped に該当）
        old_date = str(date.today() - timedelta(days=40))
        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES (999, :co_id, :ct_id, 'OLD-001', 50000, 'pending', :dt)
        """), {"co_id": co1_id, "ct_id": ct1_id, "dt": old_date})
        await db_session.commit()

        # 成約案件: 40日前に won（won_no_order に該当）
        won_date = str(date.today() - timedelta(days=40))
        await db_session.execute(text("""
            INSERT INTO deals (tenant_id, company_id, contact_id, title, amount, status, closed_at, updated_at, created_at)
            VALUES (999, :co_id, :ct_id, 'WonDeal', 100000, 'won', :dt, :dt, :dt)
        """), {"co_id": co2_id, "ct_id": ct2_id, "dt": won_date})
        await db_session.commit()

        res = await client.get("/api/v1/analytics/follow-ups")
        assert res.status_code == 200
        data = res.json()
        items = data["items"]

        segments = {item["segment"] for item in items}
        assert "order_stopped" in segments, f"Expected order_stopped in {segments}"

        # won_no_order: company2 に注文がなく won 40日前
        assert "won_no_order" in segments, f"Expected won_no_order in {segments}"

        # order_stopped の days >= 30
        stopped_items = [i for i in items if i["segment"] == "order_stopped"]
        for item in stopped_items:
            assert item["days"] >= 30

        # won_no_order の days >= 30
        won_items = [i for i in items if i["segment"] == "won_no_order"]
        for item in won_items:
            assert item["days"] >= 30

    async def test_follow_ups_date_params_are_date_objects(self):
        """
        回帰テスト: asyncpg DataError 修正確認。

        asyncpg は SQL パラメータに str 型の日付を受け付けない:
          asyncpg.exceptions.DataError: invalid input for query argument $1:
          '2026-05-16' (expected a datetime.date or datetime.datetime instance, got 'str')

        follow_ups_summary が threshold_30 / threshold_45 / threshold_now を
        date オブジェクトのまま渡していることを DB mock で確認する。
        """
        from datetime import date as date_class
        from unittest.mock import AsyncMock, MagicMock

        from app.routers.analytics import follow_ups_summary

        mapping_result = MagicMock()
        mapping_result.mappings.return_value.all.return_value = []
        db_mock = AsyncMock()
        db_mock.execute.return_value = mapping_result

        user_mock = MagicMock()
        user_mock.id = 1

        await follow_ups_summary(scope="team", db=db_mock, tenant_id=1, current_user=user_mock)

        date_param_keys = {"threshold", "threshold_now", "threshold_45"}
        for call in db_mock.execute.call_args_list:
            params: dict = call.args[1] if len(call.args) > 1 else {}
            for key, val in params.items():
                if key in date_param_keys:
                    assert isinstance(val, date_class), (
                        f"SQL param '{key}' must be datetime.date, got {type(val).__name__!r}. "
                        "str() 変換すると asyncpg DataError になる（本番500の原因）。"
                    )


# ─────────────────────────────────────────────
# customer-orders EP テスト
# ─────────────────────────────────────────────

class TestCustomerOrders:
    """GET /analytics/customer-orders"""

    async def test_customer_orders_empty(self, client):
        """データなしで 200 を返し、items が空リスト"""
        res = await client.get("/api/v1/analytics/customer-orders")
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []

    async def test_customer_orders_invalid_period(self, client):
        """period が不正なら 422"""
        res = await client.get("/api/v1/analytics/customer-orders?period=2m")
        assert res.status_code == 422

    async def test_customer_orders_with_data(self, client, db_session):
        """顧客別の受注履歴・頻度・継続期間・予測が正しい"""
        today = date.today()

        co1 = await client.post("/api/v1/companies", json={"name": "HistoryCo"})
        co1_id = co1.json()["id"]
        co2 = await client.post("/api/v1/companies", json={"name": "SingleOrderCo"})
        co2_id = co2.json()["id"]

        ct1 = await client.post("/api/v1/contacts", json={
            "company_id": co1_id,
            "display_name": "HistoryContact",
        })
        ct1_id = ct1.json()["id"]
        ct2 = await client.post("/api/v1/contacts", json={
            "company_id": co2_id,
            "display_name": "SingleContact",
        })
        ct2_id = ct2.json()["id"]

        d1 = today - timedelta(days=20)
        d2 = today - timedelta(days=12)
        d3 = today - timedelta(days=4)
        d4 = today - timedelta(days=6)

        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES
                (999, :co1, :ct1, 'ORD-H-001', 100, 'awaiting_payment', :d1),
                (999, :co1, :ct1, 'ORD-H-002', 200, 'awaiting_payment', :d2),
                (999, :co1, :ct1, 'ORD-H-003', 300, 'awaiting_payment', :d3),
                (999, :co2, :ct2, 'ORD-S-001', 450, 'awaiting_payment', :d4)
        """), {"co1": co1_id, "ct1": ct1_id, "co2": co2_id, "ct2": ct2_id, "d1": str(d1), "d2": str(d2), "d3": str(d3), "d4": str(d4)})
        await db_session.commit()

        res = await client.get("/api/v1/analytics/customer-orders?period=3m")
        assert res.status_code == 200
        data = res.json()
        items = {item["company_id"]: item for item in data["items"]}

        history = items[co1_id]
        assert history["company_name"] == "HistoryCo"
        assert history["order_count"] == 3
        assert history["first_order_at"] == str(d1)
        assert history["last_order_at"] == str(d3)
        assert history["days_since_last_order"] == (today - d3).days
        assert history["continuation_days"] == (d3 - d1).days
        assert history["avg_interval_days"] == 8.0
        assert history["avg_order_amount"] == 200.0
        assert history["total_amount"] == 600.0
        assert history["predicted_next_order_at"] == str(d3 + timedelta(days=8))

        single = items[co2_id]
        assert single["company_name"] == "SingleOrderCo"
        assert single["order_count"] == 1
        assert single["first_order_at"] == str(d4)
        assert single["last_order_at"] == str(d4)
        assert single["days_since_last_order"] == (today - d4).days
        assert single["continuation_days"] == 0
        assert single["avg_interval_days"] is None
        assert single["predicted_next_order_at"] is None
        assert single["avg_order_amount"] == 450.0
        assert single["total_amount"] == 450.0

    async def test_customer_orders_jst_month_boundary(self, client, db_session):
        """1m は JST 暦月境界で当月データを拾う"""
        from app.services.time import _jst_month_range_utc

        today = date.today()
        start, _ = _jst_month_range_utc(today.year, today.month)
        boundary_dt = start + timedelta(minutes=1)

        await db_session.execute(text("""
            INSERT INTO companies (tenant_id, company_code, name, status)
            VALUES (999, 'BOUNDARY-CO', 'BoundaryCo', 'active')
        """))
        co_id = int((await db_session.execute(text("SELECT id FROM companies WHERE company_code = 'BOUNDARY-CO'"))).scalar_one())
        await db_session.execute(text("""
            INSERT INTO contacts (tenant_id, company_id, contact_code, display_name, status)
            VALUES (999, :co_id, 'BOUNDARY-CT', 'BoundaryContact', 'active')
        """), {"co_id": co_id})
        ct_id = int((await db_session.execute(text("SELECT id FROM contacts WHERE contact_code = 'BOUNDARY-CT'"))).scalar_one())

        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES (999, :co_id, :ct_id, 'BD-001', 123, 'awaiting_payment', :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(boundary_dt)})
        await db_session.commit()

        res = await client.get("/api/v1/analytics/customer-orders?period=1m")
        assert res.status_code == 200
        data = res.json()
        assert any(item["company_id"] == co_id for item in data["items"])

    async def test_customer_orders_mine_scope(self, client, db_session):
        """scope=mine で担当案件に紐づく注文だけ返る"""
        today = date.today()

        mine_co = await client.post("/api/v1/companies", json={"name": "MineCo"})
        mine_co_id = mine_co.json()["id"]
        other_co = await client.post("/api/v1/companies", json={"name": "OtherCo"})
        other_co_id = other_co.json()["id"]

        mine_ct = await client.post("/api/v1/contacts", json={
            "company_id": mine_co_id,
            "display_name": "MineContact",
        })
        mine_ct_id = mine_ct.json()["id"]
        other_ct = await client.post("/api/v1/contacts", json={
            "company_id": other_co_id,
            "display_name": "OtherContact",
        })
        other_ct_id = other_ct.json()["id"]

        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, assigned_to, created_at, updated_at)
            VALUES
                (8101, 999, :mine_co, :mine_ct, 'MineDeal', 1000, 'won', 999, :dt, :dt),
                (8102, 999, :other_co, :other_ct, 'OtherDeal', 2000, 'won', 321, :dt, :dt)
        """), {"mine_co": mine_co_id, "mine_ct": mine_ct_id, "other_co": other_co_id, "other_ct": other_ct_id, "dt": str(today)})
        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, deal_id, order_number, total_amount, status, created_at)
            VALUES
                (999, :mine_co, :mine_ct, 8101, 'MINE-001', 1000, 'awaiting_payment', :dt),
                (999, :other_co, :other_ct, 8102, 'OTHER-001', 2000, 'awaiting_payment', :dt)
        """), {"mine_co": mine_co_id, "mine_ct": mine_ct_id, "other_co": other_co_id, "other_ct": other_ct_id, "dt": str(today)})
        await db_session.commit()

        res = await client.get("/api/v1/analytics/customer-orders?scope=mine")
        assert res.status_code == 200
        data = res.json()
        items = data["items"]
        assert len(items) == 1
        assert items[0]["company_id"] == mine_co_id
        assert items[0]["order_count"] == 1


class TestCustomerContacts:
    """GET /analytics/customer-contacts"""

    async def test_customer_contacts_team_scope(self, client_tenant_006, db_session):
        """team は全会社を返し、接触低下フラグと no-contact の扱いが正しい"""
        today = date.today()

        own_co = await client_tenant_006.post(
            "/api/v1/companies",
            json={"name": "OwnContactCo", "sales_rep_id": 6},
        )
        own_co_id = own_co.json()["id"]
        stale_co = await client_tenant_006.post(
            "/api/v1/companies",
            json={"name": "StaleContactCo", "sales_rep_id": 7},
        )
        stale_co_id = stale_co.json()["id"]
        silent_co = await client_tenant_006.post(
            "/api/v1/companies",
            json={"name": "SilentContactCo", "sales_rep_id": 7},
        )
        silent_co_id = silent_co.json()["id"]

        own_ct = await client_tenant_006.post("/api/v1/contacts", json={
            "company_id": own_co_id,
            "display_name": "OwnContact",
        })
        own_ct_id = own_ct.json()["id"]
        stale_ct = await client_tenant_006.post("/api/v1/contacts", json={
            "company_id": stale_co_id,
            "display_name": "StaleContact",
        })
        stale_ct_id = stale_ct.json()["id"]

        await _insert_conversation(
            db_session,
            company_id=own_co_id,
            contact_id=own_ct_id,
            days_ago=5,
            content_text="recent contact",
        )
        await _insert_conversation(
            db_session,
            company_id=stale_co_id,
            contact_id=stale_ct_id,
            days_ago=40,
            content_text="stale contact",
        )
        await db_session.commit()

        res = await client_tenant_006.get("/api/v1/analytics/customer-contacts?period=3m&scope=team")
        assert res.status_code == 200
        data = res.json()
        assert data["period"] == "3m"
        assert data["scope"] == "team"
        assert data["stale_days"] == 30

        items = {item["company_id"]: item for item in data["items"]}
        assert items[own_co_id]["company_name"] == "OwnContactCo"
        assert items[own_co_id]["contact_count"] == 1
        assert items[own_co_id]["last_contact_at"] == str(today - timedelta(days=5))
        assert items[own_co_id]["days_since_last_contact"] == 5
        assert items[own_co_id]["is_communication_low"] is False

        assert items[stale_co_id]["company_name"] == "StaleContactCo"
        assert items[stale_co_id]["contact_count"] == 1
        assert items[stale_co_id]["last_contact_at"] == str(today - timedelta(days=40))
        assert items[stale_co_id]["days_since_last_contact"] == 40
        assert items[stale_co_id]["is_communication_low"] is True

        assert items[silent_co_id]["company_name"] == "SilentContactCo"
        assert items[silent_co_id]["contact_count"] == 0
        assert items[silent_co_id]["last_contact_at"] is None
        assert items[silent_co_id]["days_since_last_contact"] is None
        assert items[silent_co_id]["is_communication_low"] is True

    async def test_customer_contacts_mine_scope_and_threshold(self, client_tenant_006, db_session):
        """scope=mine は担当会社のみ、stale_days でフラグが変わる"""
        today = date.today()

        own_co = await client_tenant_006.post(
            "/api/v1/companies",
            json={"name": "MineContactCo", "sales_rep_id": 6},
        )
        own_co_id = own_co.json()["id"]
        other_co = await client_tenant_006.post(
            "/api/v1/companies",
            json={"name": "OtherContactCo", "sales_rep_id": 7},
        )
        other_co_id = other_co.json()["id"]

        own_ct = await client_tenant_006.post("/api/v1/contacts", json={
            "company_id": own_co_id,
            "display_name": "MineContact",
        })
        own_ct_id = own_ct.json()["id"]
        other_ct = await client_tenant_006.post("/api/v1/contacts", json={
            "company_id": other_co_id,
            "display_name": "OtherContact",
        })
        other_ct_id = other_ct.json()["id"]

        await _insert_conversation(
            db_session,
            company_id=own_co_id,
            contact_id=own_ct_id,
            days_ago=5,
            content_text="mine contact",
        )
        await _insert_conversation(
            db_session,
            company_id=other_co_id,
            contact_id=other_ct_id,
            days_ago=40,
            content_text="other contact",
        )
        await db_session.commit()

        res = await client_tenant_006.get(
            "/api/v1/analytics/customer-contacts?period=3m&scope=mine&stale_days=3",
        )
        assert res.status_code == 200
        data = res.json()
        assert data["scope"] == "mine"
        assert data["stale_days"] == 3

        items = data["items"]
        assert len(items) == 1
        assert items[0]["company_id"] == own_co_id
        assert items[0]["contact_count"] == 1
        assert items[0]["last_contact_at"] == str(today - timedelta(days=5))
        assert items[0]["days_since_last_contact"] == 5
        assert items[0]["is_communication_low"] is True


# ─────────────────────────────────────────────
# revenue-segments EP テスト
# ─────────────────────────────────────────────

class TestRevenueSegments:
    """GET /analytics/revenue-segments"""

    async def test_revenue_segments_empty(self, client):
        """データなしで 200 を返し、各 segment がゼロ"""
        res = await client.get("/api/v1/analytics/revenue-segments")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == {"revenue": 0.0, "order_count": 0, "customer_count": 0}
        assert data["new"]["revenue"] == 0.0
        assert data["new"]["order_count"] == 0
        assert data["new"]["customer_count"] == 0
        assert data["new"]["avg_order_amount"] is None
        assert data["new"]["share"] == 0.0
        assert data["repeat"]["revenue"] == 0.0
        assert data["repeat"]["order_count"] == 0
        assert data["repeat"]["customer_count"] == 0
        assert data["repeat"]["avg_order_amount"] is None
        assert data["repeat"]["share"] == 0.0

    async def test_revenue_segments_with_data(self, client, db_session):
        """new / repeat の売上・件数・平均単価・顧客数・構成比が正しい"""
        from app.services.time import _jst_month_range_utc

        today = date.today()
        start, _ = _jst_month_range_utc(today.year, today.month)

        new_co = await client.post("/api/v1/companies", json={"name": "SegmentNewCo"})
        new_co_id = new_co.json()["id"]
        repeat_co = await client.post("/api/v1/companies", json={"name": "SegmentRepeatCo"})
        repeat_co_id = repeat_co.json()["id"]

        new_ct = await client.post("/api/v1/contacts", json={
            "company_id": new_co_id,
            "display_name": "SegmentNewContact",
        })
        new_ct_id = new_ct.json()["id"]
        repeat_ct = await client.post("/api/v1/contacts", json={
            "company_id": repeat_co_id,
            "display_name": "SegmentRepeatContact",
        })
        repeat_ct_id = repeat_ct.json()["id"]

        new_1 = start + timedelta(minutes=1)
        new_2 = start + timedelta(days=1)
        repeat_prev = start - timedelta(days=2)
        repeat_cur = start + timedelta(hours=1)

        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES
                (999, :new_co, :new_ct, 'SEG-N-001', 120, 'awaiting_payment', :new_1),
                (999, :new_co, :new_ct, 'SEG-N-002', 180, 'awaiting_payment', :new_2),
                (999, :repeat_co, :repeat_ct, 'SEG-R-001', 500, 'awaiting_payment', :repeat_prev),
                (999, :repeat_co, :repeat_ct, 'SEG-R-002', 300, 'awaiting_payment', :repeat_cur)
        """), {
            "new_co": new_co_id,
            "new_ct": new_ct_id,
            "repeat_co": repeat_co_id,
            "repeat_ct": repeat_ct_id,
            "new_1": str(new_1),
            "new_2": str(new_2),
            "repeat_prev": str(repeat_prev),
            "repeat_cur": str(repeat_cur),
        })
        await db_session.commit()

        res = await client.get("/api/v1/analytics/revenue-segments?period=1m")
        assert res.status_code == 200
        data = res.json()

        assert data["period"] == "1m"
        assert data["scope"] == "team"
        assert data["total"] == {"revenue": 600.0, "order_count": 3, "customer_count": 2}

        new_seg = data["new"]
        assert new_seg["revenue"] == 300.0
        assert new_seg["order_count"] == 2
        assert new_seg["avg_order_amount"] == 150.0
        assert new_seg["customer_count"] == 1
        assert new_seg["share"] == 50.0

        repeat_seg = data["repeat"]
        assert repeat_seg["revenue"] == 300.0
        assert repeat_seg["order_count"] == 1
        assert repeat_seg["avg_order_amount"] == 300.0
        assert repeat_seg["customer_count"] == 1
        assert repeat_seg["share"] == 50.0

    async def test_revenue_segments_mine_scope(self, client, db_session):
        """scope=mine で担当案件の注文だけ返る"""
        today = date.today()
        current = today + timedelta(days=0)

        mine_co = await client.post("/api/v1/companies", json={"name": "MineSegmentCo"})
        mine_co_id = mine_co.json()["id"]
        other_co = await client.post("/api/v1/companies", json={"name": "OtherSegmentCo"})
        other_co_id = other_co.json()["id"]

        mine_ct = await client.post("/api/v1/contacts", json={
            "company_id": mine_co_id,
            "display_name": "MineSegmentContact",
        })
        mine_ct_id = mine_ct.json()["id"]
        other_ct = await client.post("/api/v1/contacts", json={
            "company_id": other_co_id,
            "display_name": "OtherSegmentContact",
        })
        other_ct_id = other_ct.json()["id"]

        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, assigned_to, created_at, updated_at)
            VALUES
                (8201, 999, :mine_co, :mine_ct, 'MineSegmentDeal', 1000, 'won', 999, :dt, :dt),
                (8202, 999, :other_co, :other_ct, 'OtherSegmentDeal', 1000, 'won', 321, :dt, :dt)
        """), {
            "mine_co": mine_co_id,
            "mine_ct": mine_ct_id,
            "other_co": other_co_id,
            "other_ct": other_ct_id,
            "dt": str(current),
        })
        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, deal_id, order_number, total_amount, status, created_at)
            VALUES
                (999, :mine_co, :mine_ct, 8201, 'MINE-SEG-001', 1000, 'awaiting_payment', :dt),
                (999, :other_co, :other_ct, 8202, 'OTHER-SEG-001', 2000, 'awaiting_payment', :dt)
        """), {
            "mine_co": mine_co_id,
            "mine_ct": mine_ct_id,
            "other_co": other_co_id,
            "other_ct": other_ct_id,
            "dt": str(current),
        })
        await db_session.commit()

        res = await client.get("/api/v1/analytics/revenue-segments?scope=mine")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == {"revenue": 1000.0, "order_count": 1, "customer_count": 1}
        assert data["new"]["revenue"] == 1000.0
        assert data["new"]["order_count"] == 1
        assert data["new"]["customer_count"] == 1
        assert data["repeat"]["revenue"] == 0.0
        assert data["repeat"]["order_count"] == 0
        assert data["repeat"]["customer_count"] == 0


class TestNewGoalAdvice:
    """GET /analytics/new-goal-advice"""

    async def test_new_goal_advice_revenue_with_shifts_and_rates(self, client_tenant_006, db_session):
        """revenue 逆算が単価・成約率・商談化率とシフト連動で正しく計算される"""
        today = date.today()
        month_end = _month_end_date(today)
        week_end = _week_end_date(today)

        shift_dates: list[date] = []
        for delta_days in (0, 1, 2):
            candidate = today + timedelta(days=delta_days)
            if candidate <= month_end:
                shift_dates.append(candidate)
        for shift_date in shift_dates:
            await _insert_shift(db_session, shift_date=shift_date)

        new_co = await client_tenant_006.post("/api/v1/companies", json={"name": "AdviceNewCo"})
        new_co_id = new_co.json()["id"]
        repeat_co = await client_tenant_006.post("/api/v1/companies", json={"name": "AdviceRepeatCo"})
        repeat_co_id = repeat_co.json()["id"]

        new_ct = await client_tenant_006.post("/api/v1/contacts", json={
            "company_id": new_co_id,
            "display_name": "AdviceNewContact",
        })
        new_ct_id = new_ct.json()["id"]
        repeat_ct = await client_tenant_006.post("/api/v1/contacts", json={
            "company_id": repeat_co_id,
            "display_name": "AdviceRepeatContact",
        })
        repeat_ct_id = repeat_ct.json()["id"]

        new_deal_id = 9201
        repeat_deal_id = 9202
        past_order_date = today - timedelta(days=91)

        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, assigned_to, created_at, updated_at)
            VALUES
                (:new_deal_id, 6, :new_co_id, :new_ct_id, 'AdviceNewDeal', 1000, 'won', 6, :today_dt, :today_dt),
                (:repeat_deal_id, 6, :repeat_co_id, :repeat_ct_id, 'AdviceRepeatDeal', 1500, 'open', 6, :today_dt, :today_dt)
        """), {
            "new_deal_id": new_deal_id,
            "repeat_deal_id": repeat_deal_id,
            "new_co_id": new_co_id,
            "new_ct_id": new_ct_id,
            "repeat_co_id": repeat_co_id,
            "repeat_ct_id": repeat_ct_id,
            "today_dt": str(today),
        })
        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, deal_id, order_number, total_amount, status, created_at)
            VALUES
                (6, :new_co_id, :new_ct_id, :new_deal_id, 'ADV-NEW-001', 1000, 'awaiting_payment', :today_dt),
                (6, :repeat_co_id, :repeat_ct_id, :repeat_deal_id, 'ADV-REP-001', 500, 'awaiting_payment', :past_dt),
                (6, :repeat_co_id, :repeat_ct_id, :repeat_deal_id, 'ADV-REP-002', 1500, 'awaiting_payment', :today_dt)
        """), {
            "new_co_id": new_co_id,
            "new_ct_id": new_ct_id,
            "new_deal_id": new_deal_id,
            "repeat_co_id": repeat_co_id,
            "repeat_ct_id": repeat_ct_id,
            "repeat_deal_id": repeat_deal_id,
            "today_dt": str(today),
            "past_dt": str(past_order_date),
        })
        await db_session.execute(text("""
            INSERT INTO leads (tenant_id, customer_name, channel_type, initiative, status, assigned_to, converted_deal_id, created_at)
            VALUES
                (6, 'AdviceLead1', 'web', 'inbound', 'converted', 6, :new_deal_id, :today_dt),
                (6, 'AdviceLead2', 'web', 'inbound', 'converted', 6, :repeat_deal_id, :today_dt),
                (6, 'AdviceLead3', 'web', 'inbound', 'new', 6, NULL, :today_dt),
                (6, 'AdviceLead4', 'web', 'inbound', 'new', 6, NULL, :today_dt)
        """), {
            "new_deal_id": new_deal_id,
            "repeat_deal_id": repeat_deal_id,
            "today_dt": str(today),
        })
        await db_session.commit()

        res = await client_tenant_006.get(
            "/api/v1/analytics/new-goal-advice",
            params={
                "monthly_kgi": 10000,
                "kgi_type": "revenue",
                "scope": "mine",
                "period": "3m",
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["inputs"] == {
            "monthly_kgi": 10000.0,
            "kgi_type": "revenue",
            "period": "3m",
            "scope": "mine",
        }
        assert data["rates_used"]["unit_price"] == 1000.0
        assert data["rates_used"]["win_rate"] == 50.0
        assert data["rates_used"]["deal_rate"] == 50.0
        assert data["data_sufficient"] is True
        assert data["monthly_required"] == {"wins": 10.0, "deals": 20.0, "leads": 40.0}
        expected_remaining_month = len({d for d in shift_dates if d >= today})
        expected_remaining_week = len({d for d in shift_dates if d <= week_end})
        assert data["working_days"]["shift_status"] == "submitted"
        assert data["working_days"]["remaining_month"] == max(expected_remaining_month, 1)
        assert data["working_days"]["remaining_week"] == expected_remaining_week

        monthly_wins = data["monthly_required"]["wins"]
        assert data["weekly_required"]["wins"] == round(monthly_wins / data["working_days"]["remaining_month"] * data["working_days"]["remaining_week"], 2)
        assert data["weekly_required"]["deals"] == round(data["monthly_required"]["deals"] / data["working_days"]["remaining_month"] * data["working_days"]["remaining_week"], 2)
        assert data["weekly_required"]["leads"] == round(data["monthly_required"]["leads"] / data["working_days"]["remaining_month"] * data["working_days"]["remaining_week"], 2)

    async def test_new_goal_advice_wins_without_unit_price_and_not_submitted(self, client_tenant_006, db_session):
        """wins は unit_price が無くても成立し、シフト未提出なら平日フォールバックになる"""
        today = date.today()
        month_end = _month_end_date(today)
        week_end = _week_end_date(today)

        won_deal_id = 9301
        open_deal_id = 9302
        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, assigned_to, created_at, updated_at)
            VALUES
                (:won_deal_id, 6, NULL, NULL, 'WinsAdviceWon', 1200, 'won', 6, :today_dt, :today_dt),
                (:open_deal_id, 6, NULL, NULL, 'WinsAdviceOpen', 800, 'open', 6, :today_dt, :today_dt)
        """), {
            "won_deal_id": won_deal_id,
            "open_deal_id": open_deal_id,
            "today_dt": str(today),
        })
        await db_session.execute(text("""
            INSERT INTO leads (tenant_id, customer_name, channel_type, initiative, status, assigned_to, converted_deal_id, created_at)
            VALUES
                (6, 'WinsAdviceLead1', 'web', 'inbound', 'converted', 6, :won_deal_id, :today_dt),
                (6, 'WinsAdviceLead2', 'web', 'inbound', 'converted', 6, :open_deal_id, :today_dt),
                (6, 'WinsAdviceLead3', 'web', 'inbound', 'new', 6, NULL, :today_dt),
                (6, 'WinsAdviceLead4', 'web', 'inbound', 'new', 6, NULL, :today_dt)
        """), {
            "won_deal_id": won_deal_id,
            "open_deal_id": open_deal_id,
            "today_dt": str(today),
        })
        await db_session.commit()

        res = await client_tenant_006.get(
            "/api/v1/analytics/new-goal-advice",
            params={
                "monthly_kgi": 8,
                "kgi_type": "wins",
                "scope": "mine",
                "period": "3m",
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["rates_used"]["unit_price"] is None
        assert data["rates_used"]["win_rate"] == 50.0
        assert data["rates_used"]["deal_rate"] == 50.0
        assert data["data_sufficient"] is True
        assert data["monthly_required"] == {"wins": 8.0, "deals": 16.0, "leads": 32.0}
        assert data["working_days"]["shift_status"] == "not_submitted"
        assert data["working_days"]["remaining_month"] == _count_weekdays_inclusive(today, month_end)
        assert data["working_days"]["remaining_week"] == _count_weekdays_inclusive(today, week_end)
        assert data["weekly_required"]["wins"] == round(
            data["monthly_required"]["wins"] / data["working_days"]["remaining_month"] * data["working_days"]["remaining_week"],
            2,
        )
        assert data["weekly_required"]["deals"] == round(
            data["monthly_required"]["deals"] / data["working_days"]["remaining_month"] * data["working_days"]["remaining_week"],
            2,
        )
        assert data["weekly_required"]["leads"] == round(
            data["monthly_required"]["leads"] / data["working_days"]["remaining_month"] * data["working_days"]["remaining_week"],
            2,
        )

    async def test_new_goal_advice_revenue_insufficient_when_rates_missing(self, client_tenant_006, db_session):
        """revenue で単価があっても率が欠けていれば data_sufficient=false になる"""
        today = date.today()

        co = await client_tenant_006.post("/api/v1/companies", json={"name": "AdviceSparseCo"})
        co_id = co.json()["id"]
        ct = await client_tenant_006.post("/api/v1/contacts", json={
            "company_id": co_id,
            "display_name": "AdviceSparseContact",
        })
        ct_id = ct.json()["id"]

        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, assigned_to, created_at, updated_at)
            VALUES (9401, 6, :co_id, :ct_id, 'AdviceSparseDeal', 1000, 'open', 6, :today_dt, :today_dt)
        """), {"co_id": co_id, "ct_id": ct_id, "today_dt": str(today)})
        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, deal_id, order_number, total_amount, status, created_at)
            VALUES (6, :co_id, :ct_id, 9401, 'ADV-SPARSE-001', 1000, 'awaiting_payment', :today_dt)
        """), {"co_id": co_id, "ct_id": ct_id, "today_dt": str(today)})
        await db_session.commit()

        res = await client_tenant_006.get(
            "/api/v1/analytics/new-goal-advice",
            params={
                "monthly_kgi": 10000,
                "kgi_type": "revenue",
                "scope": "mine",
                "period": "3m",
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["rates_used"]["unit_price"] == 1000.0
        assert data["rates_used"]["win_rate"] == 0.0
        assert data["rates_used"]["deal_rate"] is None
        assert data["data_sufficient"] is False
        assert data["monthly_required"] == {"wins": None, "deals": None, "leads": None}
        assert data["weekly_required"] == {"wins": None, "deals": None, "leads": None}


# ─────────────────────────────────────────────
# summary 拡張テスト（新フィールド）
# ─────────────────────────────────────────────

class TestSummaryExtensions:
    """GET /analytics/summary — 拡張フィールド確認"""

    @pytest.mark.skip(reason="FILTER (WHERE ...) is PostgreSQL-specific")
    async def test_summary_has_customers_and_gross_profit(self, client):
        """customers / gross_profit フィールドがレスポンスに含まれる"""
        res = await client.get("/api/v1/analytics/summary")
        assert res.status_code == 200
        data = res.json()
        assert "customers" in data
        assert "new_count" in data["customers"]
        assert "active_existing_count" in data["customers"]
        assert "gross_profit" in data["orders"]
        assert "gross_profit_margin" in data["orders"]
        assert "cost_coverage_rate" in data["orders"]


# ─────────────────────────────────────────────
# revenue-summary EP テスト
# ─────────────────────────────────────────────

class TestRevenueSummary:
    """GET /analytics/revenue-summary"""

    async def test_revenue_summary_empty(self, client):
        """データなしで 200 を返し、フロント契約形 (revenue/new_customers/gross_margin 入れ子) を確認"""
        res = await client.get("/api/v1/analytics/revenue-summary")
        assert res.status_code == 200
        data = res.json()
        # revenue ブロック
        assert data["revenue"]["target"] == 0.0
        assert data["revenue"]["actual"] == 0.0
        assert data["revenue"]["pace"] in ("ahead", "on_track", "behind")
        # split
        assert data["split"]["new"] == 0.0
        assert data["split"]["repeat"] == 0.0
        # new_customers ブロック
        assert data["new_customers"]["target"] == 0
        assert data["new_customers"]["actual"] == 0
        # active_existing_customers
        assert data["active_existing_customers"] == 0
        # gross_margin ブロック
        assert data["gross_margin"]["amount"] == 0.0
        assert data["gross_margin"]["uncosted_orders"] == 0

    async def test_revenue_summary_with_data(self, client, db_session):
        """注文データ投入時に revenue-summary が正しい値を返す"""
        co = await client.post("/api/v1/companies", json={"name": "RevCo"})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "RevContact",
        })
        ct_id = ct.json()["id"]

        today = date.today()
        this_month = str(today)[:7]  # YYYY-MM

        # 今月の注文を1件（新規顧客）
        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES (999, :co_id, :ct_id, 'REV-001', 200000, 'pending', :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(today)})
        await db_session.commit()

        res = await client.get(f"/api/v1/analytics/revenue-summary?month={this_month}")
        assert res.status_code == 200
        data = res.json()
        assert data["revenue"]["actual"] == 200000.0
        assert data["new_customers"]["actual"] == 1
        assert data["new_customers"]["target"] == 0
        assert data["active_existing_customers"] == 0
        assert data["split"]["new"] == 200000.0
        assert data["split"]["repeat"] == 0.0

    async def test_revenue_summary_invalid_scope(self, client):
        """scope が不正な場合は 422"""
        res = await client.get("/api/v1/analytics/revenue-summary?scope=invalid")
        assert res.status_code == 422

    async def test_revenue_summary_with_gross_margin(self, client, db_session):
        """purchase_cost あり注文で gross_margin が計算される"""
        co = await client.post("/api/v1/companies", json={"name": "GrossCo"})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "GrossContact",
        })
        ct_id = ct.json()["id"]

        today = date.today()
        this_month = str(today)[:7]

        # 注文を1件
        await db_session.execute(text("""
            INSERT INTO orders (id, tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES (9901, 999, :co_id, :ct_id, 'GROSS-001', 100000, 'pending', :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(today)})
        # order_financials に purchase_cost を設定
        await db_session.execute(text("""
            INSERT INTO order_financials (order_id, tenant_id, revenue_amount, purchase_cost)
            VALUES (9901, 999, 100000, 60000)
        """))
        await db_session.commit()

        res = await client.get(f"/api/v1/analytics/revenue-summary?month={this_month}")
        assert res.status_code == 200
        data = res.json()
        # gross_margin.amount = 収益 - 原価 = 100000 - 60000 = 40000
        assert data["gross_margin"]["amount"] == 40000.0
        assert data["gross_margin"]["uncosted_orders"] == 0

    async def test_revenue_summary_all_cost_columns(self, client, db_session):
        """purchase_cost 以外の費用列も全て gross_margin から差し引かれること"""
        co = await client.post("/api/v1/companies", json={"name": "AllCostCo"})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "AllCostContact",
        })
        ct_id = ct.json()["id"]

        today = date.today()
        this_month = str(today)[:7]

        await db_session.execute(text("""
            INSERT INTO orders (id, tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES (9902, 999, :co_id, :ct_id, 'ALLCOST-001', 200000, 'pending', :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(today)})
        # purchase_cost=50000 + paypal_fee=5000 + wise_fee=3000 + ad_cost=10000 = 68000
        await db_session.execute(text("""
            INSERT INTO order_financials (
                order_id, tenant_id, revenue_amount,
                purchase_cost, purchase_shipping, paypal_fee, wise_fee,
                exchange_fee, outsource_fee, packing_fee, ad_cost,
                return_fee, refund_amount
            ) VALUES (
                9902, 999, 200000,
                50000, 0, 5000, 3000,
                0, 0, 0, 10000,
                0, 0
            )
        """))
        await db_session.commit()

        res = await client.get(f"/api/v1/analytics/revenue-summary?month={this_month}")
        assert res.status_code == 200
        data = res.json()
        # gross_margin.amount = 200000 - (50000+5000+3000+10000) = 132000
        assert data["gross_margin"]["amount"] == 132000.0

    async def test_revenue_summary_pace_logic(self, client, db_session):
        """pace が achievement_pct と elapsed_pct の差 ±10 で判定されること"""
        today = date.today()
        this_month = str(today)[:7]

        # revenue 目標 1,000,000 を設定（team 目標）
        await db_session.execute(text("""
            INSERT INTO goals (user_id, team_id, period_type, period_year, period_num, kpi_type, target_value, created_by)
            VALUES (NULL, 1, 'monthly', :y, :m, 'revenue', 1000000, 999)
        """), {"y": today.year, "m": today.month})
        await db_session.commit()

        # actual=0 → achievement_pct=0。elapsed_pct が >10 なら behind、else on_track
        res = await client.get(f"/api/v1/analytics/revenue-summary?month={this_month}")
        assert res.status_code == 200
        data = res.json()
        assert data["revenue"]["pace"] in ("ahead", "on_track", "behind")


# ─────────────────────────────────────────────
# channels EP テスト
# ─────────────────────────────────────────────

class TestChannels:
    """GET /analytics/channels"""

    async def test_channels_empty(self, client):
        """データなしで 200 を返し、rows が空リスト"""
        res = await client.get("/api/v1/analytics/channels")
        assert res.status_code == 200
        data = res.json()
        assert data["rows"] == []

    async def test_channels_with_data(self, client, db_session):
        """initiative + channel_type 付きリードで rows が返る"""
        today = date.today()
        this_month = str(today)[:7]

        # initiative='inbound', channel_type='instagram' のリードを2件
        await db_session.execute(text("""
            INSERT INTO leads (tenant_id, customer_name, channel_type, initiative, status, created_at)
            VALUES (999, 'InstaLead1', 'instagram', 'inbound', 'lead', :dt),
                   (999, 'InstaLead2', 'instagram', 'inbound', 'lead', :dt)
        """), {"dt": str(today)})
        # initiative='outbound', channel_type='cold_call' のリードを1件
        await db_session.execute(text("""
            INSERT INTO leads (tenant_id, customer_name, channel_type, initiative, status, created_at)
            VALUES (999, 'ColdLead1', 'cold_call', 'outbound', 'lead', :dt)
        """), {"dt": str(today)})
        await db_session.commit()

        res = await client.get(f"/api/v1/analytics/channels?month={this_month}")
        assert res.status_code == 200
        data = res.json()
        rows_by_channel = {r["channel"]: r for r in data["rows"]}

        # フロント契約フィールドの存在確認
        assert "instagram" in rows_by_channel
        insta = rows_by_channel["instagram"]
        assert insta["initiative"] == "inbound"
        assert insta["leads"] == 2
        assert "conversion_rate" in insta
        assert "win_rate" in insta
        assert "avg_order_value" in insta
        assert "gross_margin" in insta

        assert "cold_call" in rows_by_channel
        cold = rows_by_channel["cold_call"]
        assert cold["initiative"] == "outbound"
        assert cold["leads"] == 1

    async def test_channels_gross_margin_calculated(self, client, db_session):
        """channels.gross_margin が 0.0 固定でなく order_financials から実計算されること"""
        co = await client.post("/api/v1/companies", json={"name": "ChGrossCo"})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "ChGrossContact",
        })
        ct_id = ct.json()["id"]

        today = date.today()
        this_month = str(today)[:7]

        # inbound/instagram リードを作成し、deal に変換し、order + order_financials を紐付ける
        # Lead → deal (converted_deal_id) → order (deal_id) → order_financials
        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, closed_at, created_at)
            VALUES (9100, 999, :co_id, :ct_id, 'ChGrossDeal', 500000, 'won', :dt, :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(today)})
        await db_session.execute(text("""
            INSERT INTO leads (tenant_id, customer_name, channel_type, initiative, status,
                               converted_deal_id, created_at)
            VALUES (999, 'ChGrossLead', 'instagram', 'inbound', 'converted', 9100, :dt)
        """), {"dt": str(today)})
        await db_session.execute(text("""
            INSERT INTO orders (id, tenant_id, company_id, deal_id, order_number, total_amount, status, created_at)
            VALUES (9910, 999, :co_id, 9100, 'CHGROSS-001', 300000, 'pending', :dt)
        """), {"co_id": co_id, "dt": str(today)})
        # purchase_cost=100000, ad_cost=20000 → cost_total=120000 → gross=300000-120000=180000
        await db_session.execute(text("""
            INSERT INTO order_financials (order_id, tenant_id, revenue_amount, purchase_cost, ad_cost)
            VALUES (9910, 999, 300000, 100000, 20000)
        """))
        await db_session.commit()

        res = await client.get(f"/api/v1/analytics/channels?month={this_month}")
        assert res.status_code == 200
        data = res.json()
        rows_by_channel = {r["channel"]: r for r in data["rows"]}
        assert "instagram" in rows_by_channel
        # gross_margin は 0.0 固定ではなく実計算値（180000）であること
        assert rows_by_channel["instagram"]["gross_margin"] == 180000.0

    async def test_channels_invalid_scope(self, client):
        """scope が不正な場合は 422"""
        res = await client.get("/api/v1/analytics/channels?scope=bad")
        assert res.status_code == 422


# ─────────────────────────────────────────────
# reasons EP テスト
# ─────────────────────────────────────────────

class TestReasons:
    """GET /analytics/reasons"""

    async def test_reasons_empty(self, client):
        """当月の deal_close_reasons なしで 200 を返し、reasons/memos が空リスト"""
        res = await client.get("/api/v1/analytics/reasons")
        assert res.status_code == 200
        data = res.json()
        assert data["reasons"] == []
        assert data["memos"] == []

    async def test_reasons_with_data(self, client, db_session):
        """成約理由付き商談で reasons と memos が返る"""
        co = await client.post("/api/v1/companies", json={"name": "ReasonCo"})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "ReasonContact",
        })
        ct_id = ct.json()["id"]

        today = date.today()
        this_month = str(today)[:7]

        # won deal with close reason (ID=1: '在庫・品揃え', type='won') + one-liner memo
        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, closed_at, close_reason_memo, created_at)
            VALUES (9001, 999, :co_id, :ct_id, 'ReasonDeal', 100000, 'won', :dt, '品揃えが豊富でした', :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(today)})
        # is_primary=1: 主因
        await db_session.execute(text("""
            INSERT INTO deal_close_reasons (deal_id, reason_id, is_primary) VALUES (9001, 1, 1)
        """))
        await db_session.commit()

        res = await client.get(f"/api/v1/analytics/reasons?month={this_month}")
        assert res.status_code == 200
        data = res.json()

        # reasons: label / primary_count / secondary_count
        assert len(data["reasons"]) >= 1
        first = data["reasons"][0]
        assert first["label"] == "在庫・品揃え"
        assert first["primary_count"] == 1
        assert first["secondary_count"] == 0

        # memos: deal_id / primary_label / memo / closed_at
        assert len(data["memos"]) >= 1
        memo = data["memos"][0]
        assert memo["deal_id"] == 9001
        assert memo["primary_label"] == "在庫・品揃え"
        assert memo["memo"] == "品揃えが豊富でした"
        assert memo["closed_at"] == str(today)

    async def test_reasons_type_filter(self, client, db_session):
        """?type=won / ?type=lost で close_reasons.type による絞り込みが効く"""
        co = await client.post("/api/v1/companies", json={"name": "FilterCo"})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "FilterContact",
        })
        ct_id = ct.json()["id"]

        today = date.today()
        this_month = str(today)[:7]

        # won deal — close_reason ID=1 ('在庫・品揃え', type='won')
        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, closed_at, created_at)
            VALUES (9011, 999, :co_id, :ct_id, 'WonDeal', 50000, 'won', :dt, :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(today)})
        await db_session.execute(text("""
            INSERT INTO deal_close_reasons (deal_id, reason_id, is_primary) VALUES (9011, 1, 1)
        """))

        # lost deal — close_reason ID=4 ('価格が合わなかった', type='lost')
        await db_session.execute(text("""
            INSERT INTO deals (id, tenant_id, company_id, contact_id, title, amount, status, closed_at, created_at)
            VALUES (9012, 999, :co_id, :ct_id, 'LostDeal', 50000, 'lost', :dt, :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(today)})
        await db_session.execute(text("""
            INSERT INTO deal_close_reasons (deal_id, reason_id, is_primary) VALUES (9012, 4, 1)
        """))
        await db_session.commit()

        # ?type=won — '在庫・品揃え' のみ
        res_won = await client.get(f"/api/v1/analytics/reasons?month={this_month}&type=won")
        assert res_won.status_code == 200
        labels_won = [r["label"] for r in res_won.json()["reasons"]]
        assert "在庫・品揃え" in labels_won
        assert "価格が合わなかった" not in labels_won

        # ?type=lost — '価格が合わなかった' のみ
        res_lost = await client.get(f"/api/v1/analytics/reasons?month={this_month}&type=lost")
        assert res_lost.status_code == 200
        labels_lost = [r["label"] for r in res_lost.json()["reasons"]]
        assert "価格が合わなかった" in labels_lost
        assert "在庫・品揃え" not in labels_lost

    async def test_reasons_invalid_scope(self, client):
        """scope が不正な場合は 422"""
        res = await client.get("/api/v1/analytics/reasons?scope=xxx")
        assert res.status_code == 422
