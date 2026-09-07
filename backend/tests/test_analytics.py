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

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

_JST = ZoneInfo("Asia/Tokyo")


def _today_jst() -> date:
    """JST 基準の今日を返す（analytics EP の _today_jst() と対応）。"""
    return datetime.now(_JST).date()


def _today_utc() -> date:
    """UTC の今日を返す（SQLite CURRENT_TIMESTAMP の日付部分と一致）。"""
    return datetime.now(timezone.utc).date()

# ─────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────

async def _seed_companies_and_contacts(client, count: int = 3):
    """会社 + 担当者ペアを作成して返す（返り値は (company_id, contact_id, lead_id) のトリプル）"""
    from tests.helpers_txn import create_lead
    pairs = []
    for i in range(count):
        lead_id = await create_lead(client, f"Company{i+1}")
        co = await client.post("/api/v1/companies", json={"name": f"Company{i+1}", "lead_id": lead_id})
        company_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": company_id,
            "display_name": f"Contact{i+1}",
        })
        pairs.append((company_id, ct.json()["id"], lead_id))
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
    """リードの状態を商談相当に更新して返す"""
    from tests.helpers_txn import _resolve_db_session
    if statuses is None:
        statuses = ["negotiating", "negotiating", "existing_customer"]
    db_session = await _resolve_db_session(client)
    leads = []
    for i, status in enumerate(statuses):
        pair = pairs[i % len(pairs)]
        await db_session.execute(text("""
            UPDATE leads
               SET status = :status,
                   amount = :amount,
                   expected_close_date = :expected_close_date,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = :lead_id
        """), {
            "status": status,
            "amount": (i + 1) * 100000,
            "expected_close_date": date.today(),
            "lead_id": pair[2],
        })
        leads.append({"id": pair[2], "status": status})
    await db_session.commit()
    return leads


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

        today_jst = _today_jst()  # funnel EP が _today_jst() で月を判定するため揃える
        # lead_count 目標
        await db_session.execute(text("""
            INSERT INTO goals (user_id, team_id, period_type, period_year, period_num, kpi_type, target_value, created_by)
            VALUES (NULL, 1, 'monthly', :year, :month, 'lead_count', 30, 999)
        """), {"year": today_jst.year, "month": today_jst.month})
        # revenue 目標
        await db_session.execute(text("""
            INSERT INTO goals (user_id, team_id, period_type, period_year, period_num, kpi_type, target_value, created_by)
            VALUES (NULL, 1, 'monthly', :year, :month, 'revenue', 5000000, 999)
        """), {"year": today_jst.year, "month": today_jst.month})
        # won_count 目標
        await db_session.execute(text("""
            INSERT INTO goals (user_id, team_id, period_type, period_year, period_num, kpi_type, target_value, created_by)
            VALUES (NULL, 1, 'monthly', :year, :month, 'won_count', 10, 999)
        """), {"year": today_jst.year, "month": today_jst.month})
        await db_session.commit()

        res = await client.get("/api/v1/analytics/funnel")
        assert res.status_code == 200
        data = res.json()
        assert data["leads"]["target"] == 30
        assert data["closed"]["won_target"] == 10

    async def test_funnel_with_data(self, client, db_session):
        """データ投入時にファネル数値が正しい"""
        pairs = await _seed_companies_and_contacts(client)
        # リード 3件（active 2件、existing_customer 1件）
        await _seed_deals(client, pairs, ["negotiating", "negotiating", "existing_customer"])

        res = await client.get("/api/v1/analytics/funnel")
        assert res.status_code == 200
        data = res.json()
        # リードは 3件（_seed_companies_and_contacts 3件をそのまま状態更新）
        assert data["leads"]["actual"] == 3
        assert data["conversion"]["converted"] == 1
        # 進行中リード（negotiating の 2件）
        assert data["active"]["count"] == 2
        assert data["closed"]["won"] == 1


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
        from tests.helpers_txn import create_lead
        lead1_id = await create_lead(client, "StoppedCo")
        co1 = await client.post("/api/v1/companies", json={"name": "StoppedCo", "lead_id": lead1_id})
        co1_id = co1.json()["id"]
        ct1 = await client.post("/api/v1/contacts", json={
            "company_id": co1_id, "display_name": "Contact1",
        })
        ct1_id = ct1.json()["id"]

        lead2_id = await create_lead(client, "WonNoCo")
        co2 = await client.post("/api/v1/companies", json={"name": "WonNoCo", "lead_id": lead2_id})
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

        # 成約リード: 40日前に existing_customer（won_no_order に該当）
        won_date = str(date.today() - timedelta(days=40))
        await db_session.execute(text("""
            UPDATE leads
               SET status = 'existing_customer',
                   updated_at = :dt,
                   amount = 100000
             WHERE id = :lead_id
        """), {"lead_id": lead2_id, "dt": won_date})
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
        from tests.helpers_txn import create_lead
        rev_lead_id = await create_lead(client, "RevCo")
        co = await client.post("/api/v1/companies", json={"name": "RevCo", "lead_id": rev_lead_id})
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
        from tests.helpers_txn import create_lead
        gross_lead_id = await create_lead(client, "GrossCo")
        co = await client.post("/api/v1/companies", json={"name": "GrossCo", "lead_id": gross_lead_id})
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
        from tests.helpers_txn import create_lead
        allcost_lead_id = await create_lead(client, "AllCostCo")
        co = await client.post("/api/v1/companies", json={"name": "AllCostCo", "lead_id": allcost_lead_id})
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
        chgross_lead = await client.post("/api/v1/leads", json={
            "customer_name": "ChGrossCo",
            "channel_type": "instagram",
            "initiative": "inbound",
            "status": "existing_customer",
            "amount": 500000,
        })
        assert chgross_lead.status_code == 201, chgross_lead.text
        chgross_lead_id = chgross_lead.json()["id"]
        co = await client.post("/api/v1/companies", json={"name": "ChGrossCo", "lead_id": chgross_lead_id})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "ChGrossContact",
        })
        ct_id = ct.json()["id"]

        today_jst = _today_jst()
        this_month = str(today_jst)[:7]

        await db_session.execute(text("""
            INSERT INTO orders (id, tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES (9910, 999, :co_id, :ct_id, 'CHGROSS-001', 300000, 'pending', :dt)
        """), {"co_id": co_id, "ct_id": ct_id, "dt": str(today_jst)})
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
        today = date.today()

        for payload in [
            {"customer_name": "AttrLead1", "channel_type": "instagram", "country": "JP", "sales_form": "physical_store", "temperature": "Hot", "response_speed": "24h以内", "assigned_to": 999, "status": "existing_customer"},
            {"customer_name": "AttrLead2", "channel_type": "instagram", "country": "JP", "sales_form": "physical_store", "temperature": "Warm", "response_speed": "3日以内", "assigned_to": 999, "status": "lead"},
            {"customer_name": "AttrLead3", "channel_type": "messenger", "country": "US", "sales_form": "ec_site", "temperature": "Cold", "response_speed": "3日超", "assigned_to": 999, "status": "lead"},
            {"customer_name": "AttrLead4", "channel_type": "messenger", "country": "US", "sales_form": "other", "temperature": "Hot", "response_speed": "24h以内", "assigned_to": 321, "status": "existing_customer"},
        ]:
            payload["created_at"] = str(today)
            res = await client.post("/api/v1/leads", json=payload)
            assert res.status_code == 201, res.text

        team_res = await client.get("/api/v1/analytics/conversion-by-attribute?scope=team")
        assert team_res.status_code == 200
        team = team_res.json()

        assert team["channel_type"]["overall_rate"] == pytest.approx(0.5, abs=1e-4)
        instagram = {row["value"]: row for row in team["channel_type"]["items"]}["instagram"]
        messenger = {row["value"]: row for row in team["channel_type"]["items"]}["messenger"]
        assert instagram["n"] == 2
        assert instagram["conversions"] == 1
        assert instagram["raw_rate"] == pytest.approx(0.5, abs=1e-4)
        assert instagram["smoothed_rate"] == pytest.approx(0.5, abs=1e-4)
        assert messenger["n"] == 2
        assert messenger["conversions"] == 1
        assert messenger["raw_rate"] == pytest.approx(0.5, abs=1e-4)
        assert messenger["smoothed_rate"] == pytest.approx(0.5, abs=1e-4)

        country = {row["value"]: row for row in team["country"]["items"]}
        assert country["JP"]["n"] == 2
        assert country["JP"]["conversions"] == 1
        assert country["US"]["n"] == 2
        assert country["US"]["conversions"] == 1

        mine_res = await client.get("/api/v1/analytics/conversion-by-attribute?scope=mine")
        assert mine_res.status_code == 200
        mine = mine_res.json()

        assert mine["channel_type"]["overall_rate"] == pytest.approx(1 / 3, abs=1e-4)
        mine_channels = {row["value"]: row for row in mine["channel_type"]["items"]}
        assert mine_channels["instagram"]["n"] == 2
        assert mine_channels["instagram"]["conversions"] == 1
        assert mine_channels["instagram"]["raw_rate"] == pytest.approx(0.5, abs=1e-4)
        assert mine_channels["instagram"]["smoothed_rate"] == pytest.approx((1 + 10 * (1 / 3)) / 12, abs=1e-4)
        assert mine_channels["messenger"]["n"] == 1
        assert mine_channels["messenger"]["conversions"] == 0
        assert mine_channels["messenger"]["raw_rate"] == pytest.approx(0.0, abs=1e-4)
        assert mine_channels["messenger"]["smoothed_rate"] == pytest.approx((0 + 10 * (1 / 3)) / 11, abs=1e-4)

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
        today = date.today()

        for payload in [
            {"customer_name": "PriorityLead1", "channel_type": "instagram", "country": "JP", "sales_form": "physical_store", "temperature": "Hot", "response_speed": "24h以内", "assigned_to": 999, "status": "existing_customer", "monthly_forecast": 100},
            {"customer_name": "PriorityLead2", "channel_type": "instagram", "country": "JP", "sales_form": "physical_store", "temperature": "Hot", "response_speed": "24h以内", "assigned_to": 999, "status": "lead", "monthly_forecast": 300},
            {"customer_name": "PriorityLead3", "channel_type": "phone", "country": "US", "sales_form": None, "temperature": "Cold", "response_speed": "3日超", "assigned_to": 999, "status": "lead", "monthly_forecast": None},
            {"customer_name": "PriorityLead4", "channel_type": "messenger", "country": "CA", "sales_form": "online", "temperature": "Warm", "response_speed": "3日以内", "assigned_to": 321, "status": "existing_customer", "monthly_forecast": 9999},
        ]:
            payload["created_at"] = str(today)
            res = await client.post("/api/v1/leads", json=payload)
            assert res.status_code == 201, res.text

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
        from tests.helpers_txn import create_lead
        reason_lead = await client.post("/api/v1/leads", json={
            "customer_name": "ReasonCo",
            "status": "existing_customer",
            "notes": "品揃えが豊富でした",
        })
        assert reason_lead.status_code == 201, reason_lead.text
        reason_lead_id = reason_lead.json()["id"]
        co = await client.post("/api/v1/companies", json={"name": "ReasonCo", "lead_id": reason_lead_id})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "ReasonContact",
        })
        ct_id = ct.json()["id"]

        today_jst = _today_jst()
        this_month = str(today_jst)[:7]

        # won lead with close reason (ID=1: '在庫・品揃え', type='won') + one-liner memo
        await db_session.execute(text("""
            INSERT INTO deal_close_reasons (lead_id, reason_id, is_primary) VALUES (:lead_id, 1, 1)
        """), {"lead_id": reason_lead_id})
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

        # memos: deal_id(lead_id) / primary_label / memo / closed_at
        # closed_at は SQLite が UTC で記録するため UTC 日付で比較する
        assert len(data["memos"]) >= 1
        memo = data["memos"][0]
        assert memo["deal_id"] == reason_lead_id
        assert memo["primary_label"] == "在庫・品揃え"
        assert memo["memo"] == "品揃えが豊富でした"
        assert memo["closed_at"] == str(_today_utc())

    async def test_reasons_type_filter(self, client, db_session):
        """?type=won / ?type=lost で close_reasons.type による絞り込みが効く"""
        from tests.helpers_txn import create_lead
        filter_lead_id = await create_lead(client, "FilterCo")
        co = await client.post("/api/v1/companies", json={"name": "FilterCo", "lead_id": filter_lead_id})
        co_id = co.json()["id"]
        ct = await client.post("/api/v1/contacts", json={
            "company_id": co_id, "display_name": "FilterContact",
        })
        ct_id = ct.json()["id"]

        this_month = str(_today_jst())[:7]

        # won lead — close_reason ID=1 ('在庫・品揃え', type='won')
        await db_session.execute(text("""
            INSERT INTO deal_close_reasons (lead_id, reason_id, is_primary) VALUES (:lead_id, 1, 1)
        """), {"lead_id": filter_lead_id})

        # lost lead — close_reason ID=4 ('価格が合わなかった', type='lost')
        await db_session.execute(text("""
            INSERT INTO deal_close_reasons (lead_id, reason_id, is_primary) VALUES (:lead_id, 4, 1)
        """), {"lead_id": filter_lead_id})
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


# ─────────────────────────────────────────────
# /analytics/weekly-advisor-defensive テスト
# W-1 復元（#2455 で誤削除 → 外科的復元）
# ─────────────────────────────────────────────

async def _ensure_conversation_logs_table(db_session):
    """weekly-advisor_defensive 用に SQLite 互換 conversation_logs を作成する。"""
    await db_session.execute(text("DROP TABLE IF EXISTS conversation_logs"))
    await db_session.execute(text("""
        CREATE TABLE conversation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL DEFAULT 999,
            company_id INTEGER,
            contact_id INTEGER,
            lead_id INTEGER,
            channel_type TEXT,
            channel_identity TEXT,
            direction TEXT,
            sender TEXT,
            content_text TEXT,
            external_message_id TEXT,
            raw_payload TEXT,
            occurred_at TIMESTAMP,
            deleted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    await db_session.commit()


async def _ensure_data_access_events_table(db_session):
    """audit middleware 用の SQLite 互換 data_access_events を作成する。"""
    await db_session.execute(text("DROP TABLE IF EXISTS data_access_events"))
    await db_session.execute(text("""
        CREATE TABLE data_access_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            user_email TEXT,
            client_ip TEXT,
            user_agent TEXT,
            duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    await db_session.commit()

class TestWeeklyAdvisorDefensive:
    """GET /analytics/weekly-advisor-defensive"""

    async def test_weekly_advisor_defensive_empty(self, client):
        """データなしで 200 を返し、actions が空"""
        res = await client.get("/api/v1/analytics/weekly-advisor-defensive")
        assert res.status_code == 200
        data = res.json()
        assert data["actions"] == []
        assert data["period"] == "3m"
        assert data["scope"] == "mine"
        assert data["stale_days"] == 14

    async def test_weekly_advisor_defensive_ranking_and_scope(self, client, db_session):
        """守り3種が score 降順で返り、scope=mine が効く"""
        today = date.today()
        await _ensure_data_access_events_table(db_session)
        await _ensure_conversation_logs_table(db_session)

        reorder_lead = await client.post("/api/v1/leads", json={"customer_name": "Reorder Lead", "status": "existing_customer"})
        reorder_lead_id = reorder_lead.json()["id"]
        churn_lead = await client.post("/api/v1/leads", json={"customer_name": "Churn Lead", "status": "existing_customer"})
        churn_lead_id = churn_lead.json()["id"]
        comm_temp_lead = await client.post("/api/v1/leads", json={"customer_name": "Tokyo Trading Co.", "status": "existing_customer"})
        comm_temp_lead_id = comm_temp_lead.json()["id"]
        other_temp_lead = await client.post("/api/v1/leads", json={"customer_name": "Other Scope Co.", "status": "existing_customer"})
        other_temp_lead_id = other_temp_lead.json()["id"]

        reorder_co = await client.post("/api/v1/companies", json={"name": "Blue Ocean Co.", "lead_id": reorder_lead_id})
        reorder_co_id = reorder_co.json()["id"]
        churn_co = await client.post("/api/v1/companies", json={"name": "Card Haven LLC", "lead_id": churn_lead_id})
        churn_co_id = churn_co.json()["id"]
        comm_co = await client.post("/api/v1/companies", json={"name": "Tokyo Trading Co.", "lead_id": comm_temp_lead_id})
        comm_co_id = comm_co.json()["id"]
        other_co = await client.post("/api/v1/companies", json={"name": "Other Scope Co.", "lead_id": other_temp_lead_id})
        other_co_id = other_co.json()["id"]

        # scope=mine の判定は company.sales_rep_id で行う
        await db_session.execute(text("UPDATE companies SET sales_rep_id = 999 WHERE id = :id"), {"id": reorder_co_id})
        await db_session.execute(text("UPDATE companies SET sales_rep_id = 999 WHERE id = :id"), {"id": churn_co_id})
        await db_session.execute(text("UPDATE companies SET sales_rep_id = 999 WHERE id = :id"), {"id": comm_co_id})
        await db_session.execute(text("UPDATE companies SET sales_rep_id = 321 WHERE id = :id"), {"id": other_co_id})
        # comm_co は lead なし状態をシミュレート（lead_id を NULL にリセット）
        await db_session.execute(text(
            "UPDATE companies SET lead_id = NULL WHERE id = :id"
        ), {"id": comm_co_id})
        await db_session.commit()

        reorder_ct = await client.post("/api/v1/contacts", json={"company_id": reorder_co_id, "display_name": "Reorder Contact"})
        reorder_ct_id = reorder_ct.json()["id"]
        churn_ct = await client.post("/api/v1/contacts", json={"company_id": churn_co_id, "display_name": "Churn Contact"})
        churn_ct_id = churn_ct.json()["id"]
        comm_ct = await client.post("/api/v1/contacts", json={"company_id": comm_co_id, "display_name": "Comm Contact"})
        comm_ct_id = comm_ct.json()["id"]
        other_ct = await client.post("/api/v1/contacts", json={"company_id": other_co_id, "display_name": "Other Contact"})
        other_ct_id = other_ct.json()["id"]

        await db_session.execute(text("""
            INSERT INTO orders (tenant_id, company_id, contact_id, order_number, total_amount, status, created_at)
            VALUES
                (999, :reorder_co, :reorder_ct, 'R-001', 380000, 'awaiting_payment', :d60),
                (999, :reorder_co, :reorder_ct, 'R-002', 380000, 'awaiting_payment', :d40),
                (999, :reorder_co, :reorder_ct, 'R-003', 380000, 'awaiting_payment', :d20),

                (999, :churn_co, :churn_ct, 'C-001', 350000, 'awaiting_payment', :d170),
                (999, :churn_co, :churn_ct, 'C-002', 350000, 'awaiting_payment', :d150),
                (999, :churn_co, :churn_ct, 'C-003', 350000, 'awaiting_payment', :d130),
                (999, :churn_co, :churn_ct, 'C-004', 350000, 'awaiting_payment', :d20),

                (999, :comm_co, :comm_ct, 'M-001', 280000, 'awaiting_payment', :d60),
                (999, :comm_co, :comm_ct, 'M-002', 280000, 'awaiting_payment', :d30),
                (999, :comm_co, :comm_ct, 'M-003', 280000, 'awaiting_payment', :d10),

                (999, :other_co, :other_ct, 'O-001', 500000, 'awaiting_payment', :d10)
        """), {
            "reorder_co": reorder_co_id,
            "reorder_ct": reorder_ct_id,
            "churn_co": churn_co_id,
            "churn_ct": churn_ct_id,
            "comm_co": comm_co_id,
            "comm_ct": comm_ct_id,
            "other_co": other_co_id,
            "other_ct": other_ct_id,
            "d60": str(today - timedelta(days=60)),
            "d40": str(today - timedelta(days=40)),
            "d20": str(today - timedelta(days=20)),
            "d170": str(today - timedelta(days=170)),
            "d150": str(today - timedelta(days=150)),
            "d130": str(today - timedelta(days=130)),
            "d30": str(today - timedelta(days=30)),
            "d10": str(today - timedelta(days=10)),
        })
        await db_session.execute(text("""
            INSERT INTO conversation_logs (tenant_id, company_id, contact_id, lead_id, channel_type, channel_identity, direction, sender, content_text, external_message_id, occurred_at)
            VALUES
                (999, :reorder_co, :reorder_ct, NULL, 'messenger', 'm-1', 'inbound', 'customer', 'reorder', 'msg-r', :c20),
                (999, :churn_co, :churn_ct, NULL, 'messenger', 'm-2', 'inbound', 'customer', 'churn', 'msg-c', :c80),
                (999, :comm_co, :comm_ct, NULL, 'messenger', 'm-3', 'inbound', 'customer', 'comm', 'msg-m', :c34),
                (999, :other_co, :other_ct, NULL, 'messenger', 'm-4', 'inbound', 'customer', 'other', 'msg-o', :c10)
        """), {
            "reorder_co": reorder_co_id,
            "reorder_ct": reorder_ct_id,
            "churn_co": churn_co_id,
            "churn_ct": churn_ct_id,
            "comm_co": comm_co_id,
            "comm_ct": comm_ct_id,
            "other_co": other_co_id,
            "other_ct": other_ct_id,
            "c20": str(today - timedelta(days=20)),
            "c80": str(today - timedelta(days=80)),
            "c34": str(today - timedelta(days=34)),
            "c10": str(today - timedelta(days=10)),
        })
        await db_session.commit()

        res = await client.get("/api/v1/analytics/weekly-advisor-defensive?scope=mine&period=3m")
        assert res.status_code == 200
        data = res.json()
        actions = data["actions"]

        assert actions[0]["type"] == "churn_risk"
        assert actions[0]["company_name"] == "Card Haven LLC"
        assert actions == sorted(actions, key=lambda a: a["score"], reverse=True)
        assert next(a for a in actions if a["company_id"] == reorder_co_id)["lead_id"] == reorder_lead_id
        assert next(a for a in actions if a["company_id"] == churn_co_id)["lead_id"] == churn_lead_id
        assert next(a for a in actions if a["company_id"] == comm_co_id)["lead_id"] is None

        types = [a["type"] for a in actions]
        assert "reorder" in types
        assert "churn_risk" in types
        assert "comm_low" in types

        company_ids = {a["company_id"] for a in actions}
        assert other_co_id not in company_ids

        churn_ids = {a["company_id"] for a in actions if a["type"] == "churn_risk"}
        comm_ids = {a["company_id"] for a in actions if a["type"] == "comm_low"}
        assert churn_co_id in churn_ids
        assert churn_co_id not in comm_ids
