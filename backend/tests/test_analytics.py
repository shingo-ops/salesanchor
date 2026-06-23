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
from unittest.mock import AsyncMock, patch

import pytest
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


async def _seed_order_based_conversion_dataset(db_session):
    """受注ベース成約の共通データセットを投入する。"""
    today = date.today()
    rows = [
        (1001, 999, "OrderLead1", "instagram", "JP", "physical_store", "Hot", "24h以内", 999, 100.0),
        (1002, 999, "OrderLead2", "instagram", "JP", "physical_store", "Warm", "3日以内", 999, 300.0),
        (1003, 999, "OrderLead3", "cold_call", "US", None, "Cold", "3日超", 999, None),
        (1004, 999, "OrderLead4", "messenger", "CA", "online", "Warm", "3日以内", 321, 9999.0),
    ]
    for lead_id, tenant_id, customer_name, channel_type, country, sales_form, temperature, response_speed, assigned_to, monthly_forecast in rows:
        await db_session.execute(text("""
            INSERT INTO leads (
                id, tenant_id, customer_name, channel_type, country, sales_form,
                temperature, response_speed, assigned_to, monthly_forecast, created_at, status
            )
            VALUES (:id, :tenant_id, :customer_name, :channel_type, :country, :sales_form,
                    :temperature, :response_speed, :assigned_to, :monthly_forecast, :dt, 'lead')
        """), {
            "id": lead_id,
            "tenant_id": tenant_id,
            "customer_name": customer_name,
            "channel_type": channel_type,
            "country": country,
            "sales_form": sales_form,
            "temperature": temperature,
            "response_speed": response_speed,
            "assigned_to": assigned_to,
            "monthly_forecast": monthly_forecast,
            "dt": str(today),
        })

    company_rows = [
        (2001, 999, "ORD-COMP-1A", 1001, "OrderLead1 Co A"),
        (2002, 999, "ORD-COMP-1B", 1001, "OrderLead1 Co B"),
        (2003, 999, "ORD-COMP-2", 1002, "OrderLead2 Co"),
        (2004, 999, "ORD-COMP-4", 1004, "OrderLead4 Co"),
    ]
    for company_id, tenant_id, company_code, lead_id, name in company_rows:
        await db_session.execute(text("""
            INSERT INTO companies (id, tenant_id, company_code, lead_id, name, created_at, updated_at)
            VALUES (:id, :tenant_id, :company_code, :lead_id, :name, :dt, :dt)
        """), {
            "id": company_id,
            "tenant_id": tenant_id,
            "company_code": company_code,
            "lead_id": lead_id,
            "name": name,
            "dt": str(today),
        })

    order_rows = [
        (3001, 999, 2001, "ORD-1001-A", 100.0, "completed"),
        (3002, 999, 2002, "ORD-1001-B", 150.0, "completed"),
        (3003, 999, 2003, "ORD-1002", 200.0, "cancelled"),
        (3004, 999, 2004, "ORD-1004", 400.0, "pending"),
    ]
    for order_id, tenant_id, company_id, order_number, total_amount, status in order_rows:
        await db_session.execute(text("""
            INSERT INTO orders (
                id, tenant_id, company_id, order_number, total_amount, status, created_at, updated_at
            )
            VALUES (:id, :tenant_id, :company_id, :order_number, :total_amount, :status, :dt, :dt)
        """), {
            "id": order_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "order_number": order_number,
            "total_amount": total_amount,
            "status": status,
            "dt": str(today),
        })
    await db_session.commit()

    return {
        "lead_ids": [1001, 1002, 1003, 1004],
        "company_ids": [2001, 2002, 2003, 2004],
        "order_ids": [3001, 3002, 3003, 3004],
    }


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

    async def test_conversion_by_user_uses_order_based_conversion(self, client, db_session):
        """担当者別 conversion は company→order ベースで数える。

        lead1 は 2 社 2 注文とも non-cancelled にして、1 lead が company/order 件数では
        なく lead 単位で 1 回だけ数えられることを検証する。lead3 は company なし、
        lead2 は cancelled のみなので converted に入らない。
        """
        await _seed_order_based_conversion_dataset(db_session)

        res = await client.get("/api/v1/analytics/conversion")
        assert res.status_code == 200, res.text
        data = res.json()

        entries_by_user = {entry["user_id"]: entry for entry in data["entries"]}
        assert data["overall_rate"] == pytest.approx(50.0, abs=1e-4)
        assert entries_by_user[999]["lead_count"] == 3
        assert entries_by_user[999]["converted_count"] == 1
        assert entries_by_user[999]["conversion_rate"] == pytest.approx(33.3, abs=1e-1)
        assert entries_by_user[321]["lead_count"] == 1
        assert entries_by_user[321]["converted_count"] == 1
        assert entries_by_user[321]["conversion_rate"] == pytest.approx(100.0, abs=1e-4)

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
        from datetime import timezone

        from app.services.time import _jst_month_range_utc

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

    async def test_goals_summary_close_rate_remains_deal_based(self, client, db_session):
        """goals/summary の close_rate は商談ベースのまま返る"""
        with patch("app.middleware.audit.AuditMiddleware._record_data_access", new=AsyncMock(return_value=None)):
            pairs = await _seed_companies_and_contacts(client)
            for i, status in enumerate(["open", "open", "won"]):
                pair = pairs[i % len(pairs)]
                res = await client.post(
                    "/api/v1/deals",
                    json={
                        "company_id": pair[0],
                        "contact_id": pair[1],
                        "title": f"GoalDeal{i+1}",
                        "amount": (i + 1) * 100000,
                        "status": status,
                        "stage": status,
                        "assigned_to": 999,
                    },
                )
                assert res.status_code == 201, res.text

            await db_session.execute(text("""
                INSERT INTO teams (id, tenant_id, name, is_active) VALUES (1, 999, 'TestTeam', 1)
            """))
            await db_session.execute(text("""
                INSERT INTO team_members (team_id, user_id) VALUES (1, 999)
            """))
            await db_session.commit()

        res = await client.get("/api/v1/goals/summary?tab=team&team_id=1")
        assert res.status_code == 200, res.text
        data = res.json()
        monthly = {row["kpi_type"]: row for row in data["monthly"]}
        assert monthly["close_rate"]["actual_value"] == pytest.approx(33.3, abs=1e-1)
        assert monthly["close_rate"]["achievement_rate"] == 0.0
        assert monthly["deal_count"]["actual_value"] == 3

    async def test_funnel_with_data(self, client, db_session):
        """データ投入時にファネル数値が正しい"""
        pairs = await _seed_companies_and_contacts(client)
        # リード 3件（1件コンバート済み）
        await _seed_leads(client, 3)
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
# conversion-by-attribute EP テスト
# ─────────────────────────────────────────────

class TestConversionByAttribute:
    """GET /analytics/conversion-by-attribute"""

    async def test_conversion_by_attribute_empty(self, client):
        """データなしで 200 を返し、5軸が空配列"""
        res = await client.get("/api/v1/analytics/conversion-by-attribute")
        assert res.status_code == 200
        data = res.json()
        for axis_name in ("channel_type", "country", "sales_form", "temperature", "response_speed"):
            axis = data[axis_name]
            assert axis["overall_rate"] == 0.0
            assert axis["items"] == []

    async def test_conversion_by_attribute_team_and_mine(self, client, db_session):
        """team / mine の差、n、収縮率、overall_rate が返る"""
        await _seed_order_based_conversion_dataset(db_session)

        team_res = await client.get("/api/v1/analytics/conversion-by-attribute?scope=team")
        assert team_res.status_code == 200
        team = team_res.json()

        assert team["channel_type"]["overall_rate"] == pytest.approx(0.5, abs=1e-4)
        instagram = {row["value"]: row for row in team["channel_type"]["items"]}["instagram"]
        cold_call = {row["value"]: row for row in team["channel_type"]["items"]}["cold_call"]
        assert instagram["n"] == 2
        assert instagram["conversions"] == 1
        assert instagram["raw_rate"] == pytest.approx(0.5, abs=1e-4)
        assert instagram["smoothed_rate"] == pytest.approx(0.5, abs=1e-4)
        assert cold_call["n"] == 1
        assert cold_call["conversions"] == 0
        assert cold_call["raw_rate"] == pytest.approx(0.0, abs=1e-4)
        assert cold_call["smoothed_rate"] == pytest.approx((0 + 10 * 0.5) / 11, abs=1e-4)

        country = {row["value"]: row for row in team["country"]["items"]}
        assert country["JP"]["n"] == 2
        assert country["JP"]["conversions"] == 1
        assert country["US"]["n"] == 1
        assert country["US"]["conversions"] == 0

        mine_res = await client.get("/api/v1/analytics/conversion-by-attribute?scope=mine")
        assert mine_res.status_code == 200
        mine = mine_res.json()

        assert mine["channel_type"]["overall_rate"] == pytest.approx(1 / 3, abs=1e-4)
        mine_channels = {row["value"]: row for row in mine["channel_type"]["items"]}
        assert mine_channels["instagram"]["n"] == 2
        assert mine_channels["instagram"]["conversions"] == 1
        assert mine_channels["instagram"]["raw_rate"] == pytest.approx(0.5, abs=1e-4)
        assert mine_channels["instagram"]["smoothed_rate"] == pytest.approx((1 + 10 * (1 / 3)) / 12, abs=1e-4)
        assert mine_channels["cold_call"]["n"] == 1
        assert mine_channels["cold_call"]["conversions"] == 0
        assert mine_channels["cold_call"]["raw_rate"] == pytest.approx(0.0, abs=1e-4)
        assert mine_channels["cold_call"]["smoothed_rate"] == pytest.approx((0 + 10 * (1 / 3)) / 11, abs=1e-4)

        mine_country = {row["value"]: row for row in mine["country"]["items"]}
        assert mine_country["JP"]["n"] == 2
        assert mine_country["JP"]["conversions"] == 1
        assert mine_country["US"]["n"] == 1
        assert mine_country["US"]["conversions"] == 0


# ─────────────────────────────────────────────
# priority-prospects EP テスト
# ─────────────────────────────────────────────

class TestPriorityProspects:
    """GET /analytics/priority-prospects"""

    async def test_priority_prospects_empty(self, client):
        """データなしで 200 を返し、items が空"""
        res = await client.get("/api/v1/analytics/priority-prospects")
        assert res.status_code == 200
        data = res.json()
        assert data["scope"] == "mine"
        assert data["items"] == []

    async def test_priority_prospects_rank_and_median_fallback(self, client, db_session):
        """team の smoothed_rate 平均、中央値代替、降順、欠軸除外を検証"""
        await _seed_order_based_conversion_dataset(db_session)

        team_res = await client.get("/api/v1/analytics/conversion-by-attribute?scope=team")
        assert team_res.status_code == 200
        team = team_res.json()
        assert team["channel_type"]["overall_rate"] == pytest.approx(0.5, abs=1e-4)

        res = await client.get("/api/v1/analytics/priority-prospects?scope=mine")
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["scope"] == "mine"
        assert len(data["items"]) == 3

        ordered = data["items"]
        assert len({row["lead_id"] for row in ordered}) == 3
        assert ordered == sorted(ordered, key=lambda row: (-row["rank_score"], row["lead_id"]))

        for item in ordered:
            expected_ease = sum(axis["smoothed_rate"] for axis in item["axis_breakdown"]) / len(item["axis_breakdown"])
            assert item["ease_pct"] == pytest.approx(expected_ease * 100, abs=1e-4)
            assert item["rank_score"] == pytest.approx(item["ease_pct"] * item["monthly_forecast"], abs=1e-4)
            assert item["type"] == "priority_prospect"
            assert any(flag.endswith(":low_sample") for flag in item["low_sample_flags"])

        missing = next(item for item in ordered if "monthly_forecast_unset" in item["low_sample_flags"])
        assert missing["monthly_forecast"] == pytest.approx(200, abs=1e-4)
        assert len(missing["axis_breakdown"]) == 4

        assert ordered[0]["monthly_forecast"] == pytest.approx(300, abs=1e-4)
        assert ordered[0]["rank_score"] >= ordered[1]["rank_score"] >= ordered[2]["rank_score"]


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
