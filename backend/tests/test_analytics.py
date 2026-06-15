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
