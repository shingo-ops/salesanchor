from __future__ import annotations

"""
レポート・分析API（Phase 3）。

担当者別コンバージョン分析、案件停滞検出、着地予測、ダッシュボードサマリー。

変更履歴:
  2026-04-17: 初版作成（Phase 3）
  2026-04-27: Phase 1-B-2 Step 5d — customer_id 参照を company_id に置換
  2026-05-25: ダッシュボード強化 — 着地予測・期間別サマリー追加
  2026-05-31: Sprint 2 — 月別受注実績＋着地予想API追加（予実比較グラフ用）
  2026-05-31: Sprint 3 — 先月比（前期比較）フィールドをサマリーAPIに追加
  2026-06-13: PR2 — JST月次統一 + ファネル/フォローアップEP追加
"""

from datetime import date, datetime, timedelta
from statistics import median
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant, get_current_user, require_permission
from app.database import get_db
from app.models import User
from app.services.time import _jst_month_range_utc

router = APIRouter()


class ConversionEntry(BaseModel):
    user_id: int
    username: str | None
    lead_count: int
    converted_count: int
    conversion_rate: float


class ConversionReport(BaseModel):
    entries: list[ConversionEntry]
    overall_rate: float


class StalledDeal(BaseModel):
    id: int
    title: str
    company_id: int | None
    amount: float | None
    stage: str | None
    status: str
    days_stalled: int
    updated_at: str


class StalledDealsReport(BaseModel):
    threshold_days: int
    total_open: int
    stalled_count: int
    stalled_deals: list[StalledDeal]


class OverdueInvoice(BaseModel):
    id: int
    invoice_number: str | None
    company_id: int
    total_amount: float | None
    currency: str
    due_date: str | None
    days_overdue: int


class OverdueReport(BaseModel):
    count: int
    total_amount: float
    invoices: list[OverdueInvoice]


@router.get(
    "/analytics/conversion",
    response_model=ConversionReport,
    dependencies=[Depends(require_permission("reports.view"))],
)
async def conversion_analysis(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """担当者別のリード→案件コンバージョン分析"""
    result = await db.execute(text("""
        SELECT
            l.assigned_to AS user_id,
            u.username,
            COUNT(*) AS lead_count,
            COUNT(l.converted_deal_id) AS converted_count
        FROM leads l
        LEFT JOIN public.users u ON u.id = l.assigned_to
        WHERE l.assigned_to IS NOT NULL
        GROUP BY l.assigned_to, u.username
        ORDER BY converted_count DESC
    """))
    rows = result.mappings().all()

    entries = []
    total_leads = 0
    total_converted = 0
    for row in rows:
        lc = row["lead_count"] or 0
        cc = row["converted_count"] or 0
        rate = round((cc / lc * 100), 1) if lc > 0 else 0.0
        entries.append(ConversionEntry(
            user_id=row["user_id"], username=row["username"],
            lead_count=lc, converted_count=cc, conversion_rate=rate,
        ))
        total_leads += lc
        total_converted += cc

    overall = round((total_converted / total_leads * 100), 1) if total_leads > 0 else 0.0
    return ConversionReport(entries=entries, overall_rate=overall)


@router.get(
    "/analytics/stalled-deals",
    response_model=StalledDealsReport,
    dependencies=[Depends(require_permission("reports.view"))],
)
async def stalled_deals_report(
    threshold_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """指定日数以上更新のない停滞案件を検出"""
    # 全オープン案件数
    total_result = await db.execute(
        text("SELECT COUNT(*) FROM deals WHERE status NOT IN ('won', 'lost')")
    )
    total_open = total_result.scalar() or 0

    # 停滞案件
    # NOTE: PostgreSQL の (CURRENT_DATE - timestamp::date) は INTEGER 日数を返す。
    # SQLite 互換の julianday() は使わない（本番は PG のみ、SQLite テストは別件で baseline 故障中）。
    result = await db.execute(
        text("""
            SELECT id, title, company_id, amount, stage, status, updated_at,
                   (CURRENT_DATE - updated_at::date)::INTEGER AS days_stalled
            FROM deals
            WHERE status NOT IN ('won', 'lost')
              AND (CURRENT_DATE - updated_at::date) >= :threshold
            ORDER BY updated_at ASC
        """),
        {"threshold": threshold_days},
    )
    rows = result.mappings().all()

    stalled = [
        StalledDeal(
            id=row["id"], title=row["title"], company_id=row["company_id"],
            amount=float(row["amount"]) if row["amount"] else None,
            stage=row["stage"], status=row["status"],
            days_stalled=row["days_stalled"] or 0,
            updated_at=str(row["updated_at"]),
        )
        for row in rows
    ]

    return StalledDealsReport(
        threshold_days=threshold_days, total_open=total_open,
        stalled_count=len(stalled), stalled_deals=stalled,
    )


@router.get(
    "/analytics/overdue-invoices",
    response_model=OverdueReport,
    dependencies=[Depends(require_permission("reports.view"))],
)
async def overdue_invoices_report(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """支払期限超過の未入金請求書一覧"""
    result = await db.execute(text("""
        SELECT id, invoice_number, company_id, total_amount, currency, due_date,
               (CURRENT_DATE - due_date::date)::INTEGER AS days_overdue
        FROM invoices
        WHERE status IN ('issued', 'overdue')
          AND due_date IS NOT NULL
          AND due_date < CURRENT_DATE
        ORDER BY due_date ASC
    """))
    rows = result.mappings().all()

    invoices = [
        OverdueInvoice(
            id=row["id"], invoice_number=row["invoice_number"],
            company_id=row["company_id"],
            total_amount=float(row["total_amount"]) if row["total_amount"] else None,
            currency=row["currency"], due_date=str(row["due_date"]),
            days_overdue=row["days_overdue"] or 0,
        )
        for row in rows
    ]
    total = sum(i.total_amount or 0 for i in invoices)

    return OverdueReport(count=len(invoices), total_amount=total, invoices=invoices)


# ─────────────────────────────────────────────
# フォローアップリマインド
# ─────────────────────────────────────────────

class FollowUpItem(BaseModel):
    id: int
    customer_name: str
    next_action: str | None
    next_action_date: str | None
    days_overdue: int


class FollowUpReport(BaseModel):
    overdue: list[FollowUpItem]
    due_today: list[FollowUpItem]
    upcoming: list[FollowUpItem]


@router.get(
    "/analytics/followups",
    response_model=FollowUpReport,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def followup_reminders(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    フォローアップリマインド。

    - overdue: next_action_date が今日より前
    - due_today: 今日が期限
    - upcoming: 今後7日以内
    """
    today = date.today()
    upcoming_end = today + timedelta(days=7)

    result = await db.execute(
        text("""
            SELECT
                id, customer_name, next_action, next_action_date,
                (CURRENT_DATE - next_action_date)::INTEGER AS days_overdue
            FROM leads
            WHERE next_action_date IS NOT NULL
              AND next_action_date <= :upcoming_end
              AND status NOT IN ('lost', 'out_of_scope', 'existing_customer')
            ORDER BY next_action_date ASC
        """),
        {"upcoming_end": upcoming_end},
    )
    rows = result.mappings().all()

    overdue, due_today, upcoming = [], [], []
    for row in rows:
        item = FollowUpItem(
            id=row["id"],
            customer_name=row["customer_name"] or "",
            next_action=row["next_action"],
            next_action_date=str(row["next_action_date"]) if row["next_action_date"] else None,
            days_overdue=max(row["days_overdue"] or 0, 0),
        )
        nd = row["next_action_date"]
        if nd < today:
            overdue.append(item)
        elif nd == today:
            due_today.append(item)
        else:
            upcoming.append(item)

    return FollowUpReport(overdue=overdue, due_today=due_today, upcoming=upcoming)


# ─────────────────────────────────────────────
# 着地予測
# ─────────────────────────────────────────────

class ForecastResponse(BaseModel):
    forecast_amount: float
    open_deal_count: int
    won_amount: float
    period_start: str
    period_end: str


@router.get(
    "/analytics/forecast",
    response_model=ForecastResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def landing_forecast(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    今月の着地予測。

    計算式: Σ(deal.amount × deal.probability / 100)
    対象: status NOT IN ('won', 'lost') AND expected_close_date の月 = 今月
    """
    today = date.today()
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1)

    result = await db.execute(
        text("""
            SELECT
                COALESCE(SUM(amount * probability / 100.0), 0) AS forecast_amount,
                COUNT(*) AS open_deal_count
            FROM deals
            WHERE status NOT IN ('won', 'lost')
              AND expected_close_date >= :start
              AND expected_close_date < :end
        """),
        {"start": month_start, "end": month_end},
    )
    row = result.mappings().first() or {}

    # 今月成約済み売上
    won_result = await db.execute(
        text("""
            SELECT COALESCE(SUM(amount), 0) AS won_amount
            FROM deals
            WHERE status = 'won'
              AND updated_at >= :start AND updated_at < :end
        """),
        {"start": month_start, "end": month_end},
    )
    won_row = won_result.mappings().first() or {}

    return ForecastResponse(
        forecast_amount=float(row.get("forecast_amount", 0) or 0),
        open_deal_count=int(row.get("open_deal_count", 0) or 0),
        won_amount=float(won_row.get("won_amount", 0) or 0),
        period_start=str(month_start),
        period_end=str(month_end),
    )


# ─────────────────────────────────────────────
# 期間別ダッシュボードサマリー
# ─────────────────────────────────────────────

PERIOD_DAYS: dict[str, int] = {
    "1w": 7,
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "12m": 365,
}


class LeadSummary(BaseModel):
    total: int
    converted: int
    excluded: int
    conversion_rate: float


class DealSummary(BaseModel):
    total: int
    active: int
    won: int
    win_rate: float


class OrderSummary(BaseModel):
    total_revenue: float
    order_count: int
    active_count: int
    gross_profit: float = 0.0
    gross_profit_margin: float | None = None
    cost_coverage_rate: float = 0.0


class CustomerSummary(BaseModel):
    """新規 / 既存アクティブ顧客の内訳"""
    new_count: int = 0
    active_existing_count: int = 0


class KpiChange(BaseModel):
    """前期比の変化率。prev が 0 の場合は pct=None"""
    pct: float | None
    direction: str  # "up" | "down" | "flat"


class PeriodComparison(BaseModel):
    """現在期間 vs 前期間の主要KPI変化率"""
    leads_total: KpiChange
    leads_cv_rate: KpiChange
    deals_active: KpiChange
    deals_won: KpiChange
    deals_win_rate: KpiChange
    orders_revenue: KpiChange
    orders_count: KpiChange


class DashboardSummaryResponse(BaseModel):
    period: str
    start_date: str
    end_date: str
    leads: LeadSummary
    deals: DealSummary
    orders: OrderSummary
    customers: CustomerSummary = CustomerSummary()
    comparison: PeriodComparison


@router.get(
    "/analytics/summary",
    response_model=DashboardSummaryResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def dashboard_summary(
    period: str = Query(default="1m", description="1w / 1m / 3m / 6m / 12m"),
    tab: str = Query(default="team", description="team または individual"),
    user_id: int | None = Query(default=None, description="individual タブ時のユーザーID"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    期間・タブ別のリード/商談/受注サマリー。

    period: 1w=7日 / 1m=JST暦月 / 3m=90日 / 6m=180日 / 12m=365日
    tab: team=テナント全体 / individual=自分（または指定ユーザー）

    ⚠️ 挙動変更（PR2）: period="1m" は JST 暦月境界に統一。
    以前は date.today() - timedelta(30) だったため UTC/JST 差（最大9時間）で
    月初・月末のデータが漏れていた。_jst_month_range_utc() を適用。
    """
    today = date.today()
    if period == "1m":
        # ⚠️ 挙動変更: JST 暦月境界（UTC aware datetime）に統一。
        # 以前は date.today() - timedelta(30) だったため UTC/JST 差（最大9時間）で
        # 月初・月末のデータが漏れていた。
        start_date, end_date = _jst_month_range_utc(today.year, today.month)
        # 半開区間 [start, end) — created_at >= :start AND created_at < :end
        date_filter = "created_at >= :start AND created_at < :end"
        # 前期: 前月 JST 暦月
        prev_month = today.month - 1
        prev_year = today.year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1
        prev_start, prev_end = _jst_month_range_utc(prev_year, prev_month)
    else:
        days = PERIOD_DAYS.get(period, 30)
        end_date = today
        start_date = end_date - timedelta(days=days)
        # 閉区間 [start, end] — 既存動作互換
        date_filter = "created_at::date >= :start AND created_at::date <= :end"
        prev_end = start_date
        prev_start = prev_end - timedelta(days=days)

    if tab == "individual":
        target_user_id = user_id or current_user.id
        assign_filter_leads = "AND assigned_to = :uid"
        assign_filter_deals = "AND assigned_to = :uid"
        params: dict = {"start": start_date, "end": end_date, "uid": target_user_id}
    else:
        assign_filter_leads = ""
        assign_filter_deals = ""
        params = {"start": start_date, "end": end_date}

    # リード集計
    lead_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE converted_deal_id IS NOT NULL) AS converted,
                COUNT(*) FILTER (WHERE status = 'out_of_scope') AS excluded
            FROM leads
            WHERE {date_filter}
            {assign_filter_leads}
        """),
        params,
    )
    lr = lead_result.mappings().first() or {}
    lead_total = int(lr.get("total", 0) or 0)
    lead_converted = int(lr.get("converted", 0) or 0)
    lead_excluded = int(lr.get("excluded", 0) or 0)
    cv_rate = round(lead_converted / lead_total * 100, 1) if lead_total > 0 else 0.0

    # 商談集計
    deal_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status NOT IN ('won', 'lost')) AS active,
                COUNT(*) FILTER (WHERE status = 'won') AS won
            FROM deals
            WHERE {date_filter}
            {assign_filter_deals}
        """),
        params,
    )
    dr = deal_result.mappings().first() or {}
    deal_total = int(dr.get("total", 0) or 0)
    deal_active = int(dr.get("active", 0) or 0)
    deal_won = int(dr.get("won", 0) or 0)
    win_rate = round(deal_won / deal_total * 100, 1) if deal_total > 0 else 0.0

    # 受注集計（受注はテナント全体のみ）
    order_result = await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(total_amount), 0) AS revenue,
                COUNT(*) AS cnt,
                COUNT(*) FILTER (WHERE status IN ('pending', 'processing', 'shipped')) AS active
            FROM orders
            WHERE {date_filter}
        """),
        {"start": start_date, "end": end_date},
    )
    orr = order_result.mappings().first() or {}

    # ── 前期（同じ期間幅の一つ前）を集計して比較データを生成 ──
    if tab == "individual":
        prev_params: dict = {"start": prev_start, "end": prev_end, "uid": target_user_id}
    else:
        prev_params = {"start": prev_start, "end": prev_end}

    # 前期も同じ date_filter パターンを使用（1m: JST 暦月、他: days ベース）
    prev_lead_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE converted_deal_id IS NOT NULL) AS converted
            FROM leads
            WHERE {date_filter}
            {assign_filter_leads}
        """),
        prev_params,
    )
    plr = prev_lead_result.mappings().first() or {}
    prev_lead_total = int(plr.get("total", 0) or 0)
    prev_lead_converted = int(plr.get("converted", 0) or 0)
    prev_cv_rate = round(prev_lead_converted / prev_lead_total * 100, 1) if prev_lead_total > 0 else 0.0

    prev_deal_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) FILTER (WHERE status NOT IN ('won', 'lost')) AS active,
                COUNT(*) FILTER (WHERE status = 'won') AS won,
                COUNT(*) AS total
            FROM deals
            WHERE {date_filter}
            {assign_filter_deals}
        """),
        prev_params,
    )
    pdr = prev_deal_result.mappings().first() or {}
    prev_deal_total = int(pdr.get("total", 0) or 0)
    prev_deal_active = int(pdr.get("active", 0) or 0)
    prev_deal_won = int(pdr.get("won", 0) or 0)
    prev_win_rate = round(prev_deal_won / prev_deal_total * 100, 1) if prev_deal_total > 0 else 0.0

    prev_order_result = await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(total_amount), 0) AS revenue,
                COUNT(*) AS cnt
            FROM orders
            WHERE {date_filter}
        """),
        {"start": prev_start, "end": prev_end},
    )
    porr = prev_order_result.mappings().first() or {}
    prev_revenue = float(porr.get("revenue", 0) or 0)
    prev_order_count = int(porr.get("cnt", 0) or 0)

    def _kpi_change(current: float, prev: float) -> KpiChange:
        if prev == 0:
            return KpiChange(pct=None, direction="flat")
        pct = round((current - prev) / prev * 100, 1)
        return KpiChange(pct=pct, direction="up" if pct > 0 else "down" if pct < 0 else "flat")

    current_order_count = int(orr.get("cnt", 0) or 0)
    current_revenue = float(orr.get("revenue", 0) or 0)

    # ── 粗利集計（order_financials JOIN）──
    gp_result = await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(f.revenue_amount), 0) AS rev,
                COALESCE(SUM(
                    f.purchase_cost + f.purchase_shipping +
                    f.paypal_fee + f.wise_fee + f.exchange_fee +
                    f.outsource_fee + f.packing_fee + f.ad_cost +
                    f.return_fee + f.refund_amount
                ), 0) AS cost,
                COUNT(f.id) AS costed_cnt
            FROM orders o
            LEFT JOIN order_financials f ON f.order_id = o.id
            WHERE {date_filter.replace('created_at', 'o.created_at')}
        """),
        {"start": start_date, "end": end_date},
    )
    gp_row = gp_result.mappings().first() or {}
    gp_rev = float(gp_row.get("rev", 0) or 0)
    gp_cost = float(gp_row.get("cost", 0) or 0)
    gross_profit = gp_rev - gp_cost
    gross_profit_margin = round(gross_profit / gp_rev * 100, 1) if gp_rev > 0 else None
    costed_cnt = int(gp_row.get("costed_cnt", 0) or 0)
    cost_coverage_rate = round(costed_cnt / current_order_count * 100, 1) if current_order_count > 0 else 0.0

    # ── 顧客集計 ──
    # 新規顧客: 当期間に初めて発注した会社
    new_cust_result = await db.execute(
        text(f"""
            SELECT COUNT(DISTINCT o.company_id) AS cnt
            FROM orders o
            WHERE {date_filter.replace('created_at', 'o.created_at')}
              AND o.company_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM orders o2
                  WHERE o2.company_id = o.company_id
                    AND o2.created_at < :start
              )
        """),
        {"start": start_date, "end": end_date},
    )
    new_count = int((new_cust_result.scalar() or 0))

    # アクティブ既存顧客: 過去12ヶ月以内に発注があった会社（当期間の新規を除く）
    twelve_months_ago = today - timedelta(days=365)
    active_existing_result = await db.execute(
        text("""
            SELECT COUNT(DISTINCT company_id) AS cnt
            FROM orders
            WHERE company_id IS NOT NULL
              AND created_at >= :twelve_months_ago
              AND company_id IN (
                  SELECT company_id FROM orders
                  WHERE created_at < :start AND company_id IS NOT NULL
              )
        """),
        {"twelve_months_ago": twelve_months_ago, "start": start_date},
    )
    active_existing_count = int((active_existing_result.scalar() or 0))

    return DashboardSummaryResponse(
        period=period,
        start_date=str(start_date),
        end_date=str(end_date),
        leads=LeadSummary(
            total=lead_total,
            converted=lead_converted,
            excluded=lead_excluded,
            conversion_rate=cv_rate,
        ),
        deals=DealSummary(
            total=deal_total,
            active=deal_active,
            won=deal_won,
            win_rate=win_rate,
        ),
        orders=OrderSummary(
            total_revenue=current_revenue,
            order_count=current_order_count,
            active_count=int(orr.get("active", 0) or 0),
            gross_profit=gross_profit,
            gross_profit_margin=gross_profit_margin,
            cost_coverage_rate=cost_coverage_rate,
        ),
        customers=CustomerSummary(
            new_count=new_count,
            active_existing_count=active_existing_count,
        ),
        comparison=PeriodComparison(
            leads_total=_kpi_change(lead_total, prev_lead_total),
            leads_cv_rate=_kpi_change(cv_rate, prev_cv_rate),
            deals_active=_kpi_change(deal_active, prev_deal_active),
            deals_won=_kpi_change(deal_won, prev_deal_won),
            deals_win_rate=_kpi_change(win_rate, prev_win_rate),
            orders_revenue=_kpi_change(current_revenue, prev_revenue),
            orders_count=_kpi_change(current_order_count, prev_order_count),
        ),
    )


# ─────────────────────────────────────────────
# 受注実績グラフ（期間・粒度切り替え対応）
# ─────────────────────────────────────────────

# period → (granularity, 取得日数 or 月数)
_PERIOD_CHART_MAP: dict[str, tuple[str, int]] = {
    "1w":  ("daily",   7),
    "1m":  ("daily",  30),
    "3m":  ("monthly", 3),
    "6m":  ("monthly", 6),
    "12m": ("monthly", 12),
}


class RevenueChartEntry(BaseModel):
    label: str            # 月次: "2026-01" / 日次: "2026-05-31"
    actual: float
    forecast: float | None  # 月次・当月のみ
    remaining: float        # 月次・当月のみ
    is_current: bool        # 月次: 当月 / 日次: 今日


class RevenueChartResponse(BaseModel):
    granularity: str       # "daily" | "monthly"
    entries: list[RevenueChartEntry]


# 後方互換のため旧モデルを残す
class MonthlyRevenueEntry(BaseModel):
    month: str
    actual: float
    forecast: float | None
    remaining: float
    is_current: bool


class MonthlyRevenueResponse(BaseModel):
    entries: list[MonthlyRevenueEntry]


@router.get(
    "/analytics/monthly-revenue",
    response_model=RevenueChartResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def monthly_revenue(
    period: str = Query(default="6m", description="1w/1m/3m/6m/12m"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RevenueChartResponse:
    """
    受注実績グラフ用データ。period により粒度が変わる。

    - 1w / 1m  → 日次（daily）: 日別 actual のみ（forecast なし）
    - 3m / 6m / 12m → 月次（monthly）: 月別 actual + 当月 forecast/remaining
    """
    today = date.today()
    granularity, count = _PERIOD_CHART_MAP.get(period, ("monthly", 6))

    if granularity == "daily":
        range_start = today - timedelta(days=count - 1)
        range_end = today + timedelta(days=1)  # 翌日 0時（exclusive）

        actual_result = await db.execute(
            text("""
                SELECT
                    TO_CHAR(DATE_TRUNC('day', created_at), 'YYYY-MM-DD') AS label,
                    COALESCE(SUM(total_amount), 0) AS actual
                FROM orders
                WHERE created_at >= :start AND created_at < :end
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY DATE_TRUNC('day', created_at)
            """),
            {"start": range_start, "end": range_end},
        )
        actual_rows = {row["label"]: float(row["actual"]) for row in actual_result.mappings().all()}

        entries: list[RevenueChartEntry] = []
        cur = range_start
        while cur < range_end.replace(hour=0, minute=0, second=0, microsecond=0) if hasattr(range_end, 'hour') else range_end:
            label = cur.strftime("%Y-%m-%d")
            entries.append(RevenueChartEntry(
                label=label,
                actual=actual_rows.get(label, 0.0),
                forecast=None,
                remaining=0.0,
                is_current=(cur == today),
            ))
            cur = cur + timedelta(days=1)
            if cur > today:
                break

        return RevenueChartResponse(granularity="daily", entries=entries)

    # ── 月次 ──
    months = count
    start_year = today.year
    start_month = today.month - (months - 1)
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    range_start_m = date(start_year, start_month, 1)

    if today.month == 12:
        range_end_m = date(today.year + 1, 1, 1)
    else:
        range_end_m = date(today.year, today.month + 1, 1)

    actual_result = await db.execute(
        text("""
            SELECT
                TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') AS label,
                COALESCE(SUM(total_amount), 0) AS actual
            FROM orders
            WHERE created_at >= :start AND created_at < :end
            GROUP BY DATE_TRUNC('month', created_at)
            ORDER BY DATE_TRUNC('month', created_at)
        """),
        {"start": range_start_m, "end": range_end_m},
    )
    actual_rows_m = {row["label"]: float(row["actual"]) for row in actual_result.mappings().all()}

    current_month_str = today.strftime("%Y-%m")
    month_start = today.replace(day=1)

    won_result = await db.execute(
        text("""
            SELECT COALESCE(SUM(amount), 0) AS won
            FROM deals
            WHERE status = 'won'
              AND updated_at >= :start AND updated_at < :end
        """),
        {"start": month_start, "end": range_end_m},
    )
    won_amount = float((won_result.mappings().first() or {}).get("won", 0) or 0)

    open_result = await db.execute(
        text("""
            SELECT COALESCE(SUM(amount * probability / 100.0), 0) AS weighted
            FROM deals
            WHERE status NOT IN ('won', 'lost')
              AND expected_close_date >= :start
              AND expected_close_date < :end
        """),
        {"start": month_start, "end": range_end_m},
    )
    weighted_amount = float((open_result.mappings().first() or {}).get("weighted", 0) or 0)
    forecast_total = won_amount + weighted_amount

    entries_m: list[RevenueChartEntry] = []
    cur_year, cur_month = start_year, start_month
    for _ in range(months):
        month_key = f"{cur_year:04d}-{cur_month:02d}"
        is_current = month_key == current_month_str
        actual = actual_rows_m.get(month_key, 0.0)
        entries_m.append(RevenueChartEntry(
            label=month_key,
            actual=actual,
            forecast=forecast_total if is_current else None,
            remaining=max(0.0, forecast_total - actual) if is_current else 0.0,
            is_current=is_current,
        ))
        cur_month += 1
        if cur_month > 12:
            cur_month = 1
            cur_year += 1

    return RevenueChartResponse(granularity="monthly", entries=entries_m)


# ─────────────────────────────────────────────
# ファネルダッシュボード: ファネル4ステージ
# ─────────────────────────────────────────────

class FunnelLeads(BaseModel):
    target: int
    actual: int


class FunnelConversion(BaseModel):
    target_rate: int
    actual_rate: int
    converted: int


class FunnelActive(BaseModel):
    count: int
    amount: float
    coverage_pct_of_remaining_target: int


class FunnelClosed(BaseModel):
    won_target: int
    won: int
    won_rate: int
    lost: int


class FunnelResponse(BaseModel):
    month: str
    month_elapsed_pct: int
    leads: FunnelLeads
    conversion: FunnelConversion
    active: FunnelActive
    closed: FunnelClosed


def _month_elapsed_pct(today: date) -> int:
    """当月の経過率（0-100 整数）"""
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    return min(100, int(today.day / days_in_month * 100))


def _parse_month(month: str | None, today: date) -> tuple[int, int]:
    """month クエリパラメータを (year, month_num) に変換する。
    省略時は今月。形式が不正なら HTTPException 422 を上げる。
    """
    if month is None:
        return today.year, today.month
    parts = month.split("-")
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="month は YYYY-MM 形式で指定してください")
    try:
        y, m = int(parts[0]), int(parts[1])
    except ValueError:
        raise HTTPException(status_code=422, detail="month は YYYY-MM 形式で指定してください")
    if not (1 <= m <= 12):
        raise HTTPException(status_code=422, detail="month の月は 1〜12 の範囲で指定してください")
    return y, m


def _validate_scope(scope: str) -> None:
    """scope が team / mine 以外なら HTTPException 422 を上げる。"""
    if scope not in ("team", "mine"):
        raise HTTPException(status_code=422, detail="scope は team または mine で指定してください")


class AttributeConversionBucket(BaseModel):
    value: str
    n: int
    conversions: int
    raw_rate: float
    smoothed_rate: float


class AttributeConversionAxis(BaseModel):
    overall_rate: float
    items: list[AttributeConversionBucket]


class AttributeConversionResponse(BaseModel):
    channel_type: AttributeConversionAxis
    country: AttributeConversionAxis
    sales_form: AttributeConversionAxis
    temperature: AttributeConversionAxis
    response_speed: AttributeConversionAxis


ATTRIBUTE_CONVERSION_SHRINK_K = 10
ATTRIBUTE_CONVERSION_AXES: dict[str, str] = {
    "channel_type": "COALESCE(NULLIF(TRIM(l.channel_type), ''), 'unknown')",
    "country": "COALESCE(NULLIF(UPPER(TRIM(l.country)), ''), 'unknown')",
    "sales_form": "COALESCE(NULLIF(TRIM(l.sales_form), ''), 'unknown')",
    "temperature": "COALESCE(NULLIF(TRIM(l.temperature), ''), 'unknown')",
    "response_speed": "COALESCE(NULLIF(TRIM(l.response_speed), ''), 'unknown')",
}


def _attribute_rate(conversions: int, n: int) -> float:
    """率を 0〜1 の小数で返す。"""
    if n <= 0:
        return 0.0
    return conversions / n


def _smoothed_attribute_rate(
    conversions: int,
    n: int,
    overall_rate: float,
    k: int = ATTRIBUTE_CONVERSION_SHRINK_K,
) -> float:
    """overall_rate へ k で縮退させた率を返す。"""
    if n < 0:
        return 0.0
    return (conversions + k * overall_rate) / (n + k)

def _normalize_attribute_value(axis_name: str, raw_value: object | None) -> str | None:
    """集計に使う属性値を lead 側で照合しやすい形に正規化する。"""
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    if not value:
        return None
    if axis_name == "country":
        return value.upper()
    return value

async def _fetch_attribute_conversion_axis(
    db: AsyncSession,
    value_expr: str,
    lead_assign: str,
    scope_params: dict[str, object],
    overall_rate: float,
) -> AttributeConversionAxis:
    """属性1軸分の集計を返す。"""
    result = await db.execute(
        text(f"""
            SELECT
                {value_expr} AS value,
                COUNT(*) AS n,
                COUNT(l.converted_deal_id) AS conversions
            FROM leads l
            WHERE 1 = 1
            {lead_assign}
            GROUP BY {value_expr}
            ORDER BY {value_expr}
        """),
        scope_params,
    )
    items: list[AttributeConversionBucket] = []
    for row in result.mappings().all():
        n = int(row["n"] or 0)
        conversions = int(row["conversions"] or 0)
        raw_rate = _attribute_rate(conversions, n)
        smoothed_rate = _smoothed_attribute_rate(conversions, n, overall_rate)
        items.append(AttributeConversionBucket(
            value=str(row["value"] or "unknown"),
            n=n,
            conversions=conversions,
            raw_rate=round(raw_rate, 4),
            smoothed_rate=round(smoothed_rate, 4),
        ))
    return AttributeConversionAxis(
        overall_rate=round(overall_rate, 4),
        items=items,
    )

async def _fetch_attribute_conversion_summary(
    db: AsyncSession,
    lead_assign: str,
    scope_params: dict[str, object],
) -> tuple[float, AttributeConversionResponse]:
    """属性別成約率の全体値と5軸集計をまとめて返す。"""
    overall_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) AS n,
                COUNT(l.converted_deal_id) AS conversions
            FROM leads l
            WHERE 1 = 1
            {lead_assign}
        """),
        scope_params,
    )
    overall_row = overall_result.mappings().first() or {}
    overall_n = int(overall_row.get("n", 0) or 0)
    overall_conversions = int(overall_row.get("conversions", 0) or 0)
    overall_rate = _attribute_rate(overall_conversions, overall_n)

    axes: dict[str, AttributeConversionAxis] = {}
    for axis_name, value_expr in ATTRIBUTE_CONVERSION_AXES.items():
        axes[axis_name] = await _fetch_attribute_conversion_axis(
            db=db,
            value_expr=value_expr,
            lead_assign=lead_assign,
            scope_params=scope_params,
            overall_rate=overall_rate,
        )

    return overall_rate, AttributeConversionResponse(**axes)


@router.get(
    "/analytics/conversion-by-attribute",
    response_model=AttributeConversionResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def conversion_by_attribute_summary(
    scope: str = Query(default="team", description="team / mine"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    リード属性別の成約率を all-time で返す read-only 集計。

    - 成約定義: leads.converted_deal_id IS NOT NULL
    - 5軸: channel_type / country / sales_form / temperature / response_speed
    - 率は 0〜1 の小数で返す
    """
    _validate_scope(scope)
    lead_assign = "AND l.assigned_to = :uid" if scope == "mine" else ""
    scope_params: dict[str, object] = {"uid": current_user.id} if scope == "mine" else {}
    _, response = await _fetch_attribute_conversion_summary(db, lead_assign, scope_params)
    return response


@router.get(
    "/analytics/funnel",
    response_model=FunnelResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def funnel_stages(
    month: str | None = Query(default=None, description="YYYY-MM 形式。省略時は今月"),
    scope: str = Query(default="team", description="team / mine"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    ファネル4ステージ: リード獲得 → 商談化 → 進行中 → 成約/失注

    api-contract.md section 2 に準拠。
    目標値は goals テーブルから取得（未設定時は 0）。
    """
    _validate_scope(scope)
    today = date.today()
    target_year, target_month = _parse_month(month, today)
    month_str = f"{target_year:04d}-{target_month:02d}"
    start_utc, end_utc = _jst_month_range_utc(target_year, target_month)
    elapsed_pct = _month_elapsed_pct(today) if (target_year == today.year and target_month == today.month) else 100

    # scope filter
    if scope == "mine":
        assign_filter_leads = "AND assigned_to = :uid"
        assign_filter_deals = "AND assigned_to = :uid"
        extra_params: dict = {"uid": current_user.id}
    else:
        assign_filter_leads = ""
        assign_filter_deals = ""
        extra_params = {}

    base_params = {"start": start_utc, "end": end_utc, **extra_params}

    # リード獲得数
    # SUM(CASE ...) は SQLite / PostgreSQL 両互換
    lead_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN converted_deal_id IS NOT NULL THEN 1 ELSE 0 END) AS converted
            FROM leads
            WHERE created_at >= :start AND created_at < :end
            {assign_filter_leads}
        """),
        base_params,
    )
    lr = lead_result.mappings().first() or {}
    lead_actual = int(lr.get("total", 0) or 0)
    converted = int(lr.get("converted", 0) or 0)
    conversion_rate = int(round(converted / lead_actual * 100)) if lead_actual > 0 else 0

    # 進行中商談
    active_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) AS cnt,
                COALESCE(SUM(amount), 0) AS amount
            FROM deals
            WHERE status NOT IN ('won', 'lost')
              AND created_at >= :start AND created_at < :end
            {assign_filter_deals}
        """),
        base_params,
    )
    ar = active_result.mappings().first() or {}
    active_count = int(ar.get("cnt", 0) or 0)
    active_amount = float(ar.get("amount", 0) or 0)

    # 成約/失注（closed_at 基準・closed_at IS NULL = 集計対象外）
    closed_result = await db.execute(
        text(f"""
            SELECT
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) AS won,
                SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END) AS lost
            FROM deals
            WHERE closed_at >= :start AND closed_at < :end
              AND closed_at IS NOT NULL
              AND status IN ('won', 'lost')
            {assign_filter_deals}
        """),
        base_params,
    )
    cr = closed_result.mappings().first() or {}
    won_count = int(cr.get("won", 0) or 0)
    lost_count = int(cr.get("lost", 0) or 0)
    total_closed = won_count + lost_count
    won_rate = int(round(won_count / total_closed * 100)) if total_closed > 0 else 0

    # 目標値取得（goals テーブル）
    # owner_id: scope=mine なら current_user.id、team なら NULL (team_id 使用)
    # 現時点では team 目標は team_id=NULL (テナント全体) で取得
    goal_filter = "user_id = :goal_owner AND team_id IS NULL" if scope == "mine" else "team_id IS NOT NULL AND user_id IS NULL"
    goal_owner_params: dict = {"goal_owner": current_user.id} if scope == "mine" else {}
    goal_result = await db.execute(
        text(f"""
            SELECT kpi_type, COALESCE(target_value, 0) AS target_value
            FROM goals
            WHERE {goal_filter}
              AND period_type = 'monthly'
              AND period_year = :year
              AND period_num = :month
        """),
        {"year": target_year, "month": target_month, **goal_owner_params},
    )
    goals: dict[str, float] = {
        row["kpi_type"]: float(row["target_value"]) for row in goal_result.mappings().all()
    }
    lead_target = int(goals.get("lead_count", 0))
    conversion_target_rate = int(goals.get("conversion_rate", 0))
    won_target = int(goals.get("won_count", goals.get("deal_count", 0)))

    # 残り目標に対する進行中商談カバー率
    revenue_target = goals.get("revenue", 0)
    # 既に成約分の売上（当月 won の amount 合計・closed_at 基準）
    won_amount_result = await db.execute(
        text(f"""
            SELECT COALESCE(SUM(amount), 0) AS won_amount
            FROM deals
            WHERE status = 'won'
              AND closed_at >= :start AND closed_at < :end
              AND closed_at IS NOT NULL
            {assign_filter_deals}
        """),
        base_params,
    )
    won_amount = float((won_amount_result.mappings().first() or {}).get("won_amount", 0) or 0)
    remaining_target = max(0, revenue_target - won_amount)
    coverage_pct = int(round(active_amount / remaining_target * 100)) if remaining_target > 0 else (100 if active_amount > 0 else 0)

    return FunnelResponse(
        month=month_str,
        month_elapsed_pct=elapsed_pct,
        leads=FunnelLeads(target=lead_target, actual=lead_actual),
        conversion=FunnelConversion(
            target_rate=conversion_target_rate,
            actual_rate=conversion_rate,
            converted=converted,
        ),
        active=FunnelActive(
            count=active_count,
            amount=active_amount,
            coverage_pct_of_remaining_target=coverage_pct,
        ),
        closed=FunnelClosed(
            won_target=won_target,
            won=won_count,
            won_rate=won_rate,
            lost=lost_count,
        ),
    )


# ─────────────────────────────────────────────
# ファネルダッシュボード: 要フォロー顧客
# ─────────────────────────────────────────────

class FollowUpCustomer(BaseModel):
    customer_id: int
    name: str
    segment: str
    days: int
    last_order_at: str | None
    last_contact_at: str | None
    assignee: str | None


class FollowUpsResponse(BaseModel):
    items: list[FollowUpCustomer]


@router.get(
    "/analytics/follow-ups",
    response_model=FollowUpsResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def follow_ups_summary(
    scope: str = Query(default="team", description="team / mine"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    要フォロー顧客3区分カウント。

    api-contract.md section 5 に準拠:
    - order_stopped: 発注停止（最終発注から30日超）
    - no_repeat_after_first: 初回後未フォロー（初回発注から45日以内に2回目なし）
    - won_no_order: 成約後未発注（成約後30日超で発注なし）
    """
    _validate_scope(scope)
    today = date.today()
    items: list[FollowUpCustomer] = []
    # 境界日を Python 側で計算（date オブジェクトのまま渡す・str 変換禁止）
    threshold_30 = today - timedelta(days=30)
    threshold_45 = today - timedelta(days=45)

    # scope filter for deals
    deal_assign_filter = "AND d.assigned_to = :uid" if scope == "mine" else ""
    scope_params: dict = {"uid": current_user.id} if scope == "mine" else {}

    # ── 1. order_stopped: 最終発注から30日超 ──
    stopped_result = await db.execute(
        text("""
            SELECT
                c.id AS company_id,
                c.name,
                MAX(o.created_at) AS last_order_at,
                u.username AS assignee
            FROM companies c
            JOIN orders o ON o.company_id = c.id
            LEFT JOIN deals d ON d.company_id = c.id AND d.status NOT IN ('lost')
            LEFT JOIN users u ON u.id = d.assigned_to
            WHERE o.company_id IS NOT NULL
            GROUP BY c.id, c.name, u.username
            HAVING MAX(o.created_at) < :threshold
            ORDER BY MAX(o.created_at) ASC
        """),
        {"threshold": threshold_30},
    )
    for row in stopped_result.mappings().all():
        last_order = str(row["last_order_at"])[:10] if row["last_order_at"] else None
        days_since = (today - date.fromisoformat(last_order)).days if last_order else 0
        items.append(FollowUpCustomer(
            customer_id=row["company_id"],
            name=row["name"],
            segment="order_stopped",
            days=days_since,
            last_order_at=last_order,
            last_contact_at=None,
            assignee=row["assignee"],
        ))

    # ── 2. no_repeat_after_first: 初回発注から45日以内に2回目なし ──
    no_repeat_result = await db.execute(
        text("""
            SELECT
                c.id AS company_id,
                c.name,
                MIN(o.created_at) AS first_order_at,
                COUNT(o.id) AS order_cnt,
                u.username AS assignee
            FROM companies c
            JOIN orders o ON o.company_id = c.id
            LEFT JOIN deals d ON d.company_id = c.id AND d.status NOT IN ('lost')
            LEFT JOIN users u ON u.id = d.assigned_to
            WHERE o.company_id IS NOT NULL
            GROUP BY c.id, c.name, u.username
            HAVING COUNT(o.id) = 1
              AND MIN(o.created_at) < :threshold_now
              AND MIN(o.created_at) >= :threshold_45
            ORDER BY MIN(o.created_at) ASC
        """),
        {"threshold_now": today, "threshold_45": threshold_45},
    )
    for row in no_repeat_result.mappings().all():
        first_order = str(row["first_order_at"])[:10] if row["first_order_at"] else None
        days_since = (today - date.fromisoformat(first_order)).days if first_order else 0
        items.append(FollowUpCustomer(
            customer_id=row["company_id"],
            name=row["name"],
            segment="no_repeat_after_first",
            days=days_since,
            last_order_at=first_order,
            last_contact_at=None,
            assignee=row["assignee"],
        ))

    # ── 3. won_no_order: 成約後30日超で発注なし（closed_at 基準）──
    won_no_order_result = await db.execute(
        text(f"""
            SELECT
                d.company_id,
                c.name,
                d.closed_at,
                u.username AS assignee
            FROM deals d
            JOIN companies c ON c.id = d.company_id
            LEFT JOIN users u ON u.id = d.assigned_to
            WHERE d.status = 'won'
              AND d.company_id IS NOT NULL
              AND d.closed_at IS NOT NULL
              AND d.closed_at < :threshold
              AND NOT EXISTS (
                  SELECT 1 FROM orders o
                  WHERE o.company_id = d.company_id
                    AND o.created_at >= d.closed_at
              )
            {deal_assign_filter}
            ORDER BY d.closed_at ASC
        """),
        {"threshold": threshold_30, **scope_params},
    )
    for row in won_no_order_result.mappings().all():
        closed_at = str(row["closed_at"])[:10] if row["closed_at"] else None
        days_since = (today - date.fromisoformat(closed_at)).days if closed_at else 0
        items.append(FollowUpCustomer(
            customer_id=row["company_id"],
            name=row["name"],
            segment="won_no_order",
            days=days_since,
            last_order_at=None,
            last_contact_at=None,
            assignee=row["assignee"],
        ))

    return FollowUpsResponse(items=items)


# ─────────────────────────────────────────────
# /analytics/revenue-summary
# ─────────────────────────────────────────────

class RevenueBlock(BaseModel):
    target: float
    actual: float
    pace: str  # "ahead" | "on_track" | "behind"


class RevenueSplit(BaseModel):
    new: float
    repeat: float


class NewCustomersBlock(BaseModel):
    target: int
    actual: int


class GrossMarginBlock(BaseModel):
    amount: float
    uncosted_orders: int


class RevenueSummaryResponse(BaseModel):
    revenue: RevenueBlock
    split: RevenueSplit
    new_customers: NewCustomersBlock
    active_existing_customers: int
    gross_margin: GrossMarginBlock


def _pace_label(actual: float, target: float, elapsed_pct: int) -> str:
    """目標達成ペース判定。

    achievement_pct = actual / target * 100
    ahead    : achievement_pct > elapsed_pct + 10
    on_track : abs(achievement_pct - elapsed_pct) <= 10
    behind   : achievement_pct < elapsed_pct - 10
    target <= 0: actual > 0 → ahead, actual == 0 → on_track
    """
    if target <= 0:
        return "ahead" if actual > 0 else "on_track"
    achievement_pct = actual / target * 100
    if achievement_pct > elapsed_pct + 10:
        return "ahead"
    if achievement_pct < elapsed_pct - 10:
        return "behind"
    return "on_track"


@router.get(
    "/analytics/revenue-summary",
    response_model=RevenueSummaryResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def revenue_summary(
    month: str | None = Query(default=None, description="YYYY-MM 形式。省略時は今月"),
    scope: str = Query(default="team", description="team / mine"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    月次売上サマリー。api-contract.md section 3 に準拠。
    - target: goals.revenue 目標
    - actual: 当月 closed_at の won deals amount 合計
    - pace: elapsed_pct 基準の目標按分に対する達成率（%）
    - split.new: 新規顧客（当月初回発注）の売上合計
    - split.repeat: リピート顧客の売上合計
    - new_customers: 当月新規顧客数
    - active_existing_customers: 当月リピート購買のユニーク既存顧客数
    - gross_margin: (revenue - purchase_cost) / revenue * 100（costed orders のみ）
    - uncosted_orders: purchase_cost が NULL の注文数
    """
    _validate_scope(scope)
    today = date.today()
    target_year, target_month = _parse_month(month, today)
    start_utc, end_utc = _jst_month_range_utc(target_year, target_month)
    elapsed_pct = _month_elapsed_pct(today) if (target_year == today.year and target_month == today.month) else 100

    # scope で orders を絞る: mine は deal 経由で assigned_to
    if scope == "mine":
        order_scope_join = "JOIN deals od ON od.id = o.deal_id AND od.assigned_to = :uid"
        order_scope_params: dict = {"uid": current_user.id}
    else:
        order_scope_join = ""
        order_scope_params = {}

    # ── 目標値 ──
    if scope == "mine":
        goal_filter = "user_id = :goal_owner AND team_id IS NULL"
        goal_extra: dict = {"goal_owner": current_user.id}
    else:
        goal_filter = "team_id IS NOT NULL AND user_id IS NULL"
        goal_extra = {}
    goal_result = await db.execute(
        text(f"""
            SELECT kpi_type, COALESCE(target_value, 0) AS target_value
            FROM goals
            WHERE {goal_filter}
              AND period_type = 'monthly'
              AND period_year = :year
              AND period_num = :month_num
        """),
        {"year": target_year, "month_num": target_month, **goal_extra},
    )
    goals: dict[str, float] = {
        row["kpi_type"]: float(row["target_value"]) for row in goal_result.mappings().all()
    }
    revenue_target = goals.get("revenue", 0.0)

    # ── 実績: 当月 closed_at won の orders.amount 合計（scope 適用）──
    actual_result = await db.execute(
        text(f"""
            SELECT COALESCE(SUM(o.total_amount), 0) AS actual
            FROM orders o
            {order_scope_join}
            WHERE o.created_at >= :start AND o.created_at < :end
        """),
        {"start": start_utc, "end": end_utc, **order_scope_params},
    )
    actual = float((actual_result.mappings().first() or {}).get("actual", 0) or 0)

    # ── 新規 / リピート 分類 ──
    # 新規顧客: 当月に初めて発注した company（当月以前に orders なし）
    # order_scope_join は mine の場合のみ適用
    split_result = await db.execute(
        text(f"""
            SELECT
                o.company_id,
                SUM(o.total_amount) AS total_amount,
                MIN(o.created_at) AS first_ever
            FROM orders o
            {order_scope_join}
            WHERE o.company_id IS NOT NULL
              AND o.created_at >= :start AND o.created_at < :end
            GROUP BY o.company_id
        """),
        {"start": start_utc, "end": end_utc, **order_scope_params},
    )
    split_rows = split_result.mappings().all()

    new_revenue = 0.0
    repeat_revenue = 0.0
    new_customer_ids: set[int] = set()
    repeat_customer_ids: set[int] = set()

    for row in split_rows:
        company_id = row["company_id"]
        amt = float(row["total_amount"] or 0)
        # 当月以前に発注があるか確認
        prior_result = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM orders WHERE company_id = :cid AND created_at < :start"),
            {"cid": company_id, "start": start_utc},
        )
        prior_cnt = int((prior_result.mappings().first() or {}).get("cnt", 0) or 0)
        if prior_cnt == 0:
            new_revenue += amt
            new_customer_ids.add(company_id)
        else:
            repeat_revenue += amt
            repeat_customer_ids.add(company_id)

    # ── 粗利計算（purchase_cost IS NOT NULL の orders のみ・全コスト列を合算）──
    # cost_total = purchase_cost + purchase_shipping + paypal_fee + wise_fee
    #            + exchange_fee + outsource_fee + packing_fee + ad_cost
    #            + return_fee + refund_amount
    margin_result = await db.execute(
        text(f"""
            SELECT
                COUNT(o.id) AS total_orders,
                SUM(CASE WHEN f.purchase_cost IS NOT NULL THEN 1 ELSE 0 END) AS costed_cnt,
                COALESCE(SUM(CASE WHEN f.purchase_cost IS NOT NULL THEN o.total_amount ELSE 0 END), 0) AS costed_revenue,
                COALESCE(SUM(CASE WHEN f.purchase_cost IS NOT NULL THEN (
                    COALESCE(f.purchase_cost, 0)
                    + COALESCE(f.purchase_shipping, 0)
                    + COALESCE(f.paypal_fee, 0)
                    + COALESCE(f.wise_fee, 0)
                    + COALESCE(f.exchange_fee, 0)
                    + COALESCE(f.outsource_fee, 0)
                    + COALESCE(f.packing_fee, 0)
                    + COALESCE(f.ad_cost, 0)
                    + COALESCE(f.return_fee, 0)
                    + COALESCE(f.refund_amount, 0)
                ) ELSE 0 END), 0) AS total_cost
            FROM orders o
            {order_scope_join}
            LEFT JOIN order_financials f ON f.order_id = o.id
            WHERE o.created_at >= :start AND o.created_at < :end
        """),
        {"start": start_utc, "end": end_utc, **order_scope_params},
    )
    mr = margin_result.mappings().first() or {}
    total_orders = int(mr.get("total_orders", 0) or 0)
    costed_cnt = int(mr.get("costed_cnt", 0) or 0)
    costed_revenue = float(mr.get("costed_revenue", 0) or 0)
    total_cost = float(mr.get("total_cost", 0) or 0)
    uncosted_orders = total_orders - costed_cnt
    gross_amount = round(costed_revenue - total_cost, 2)

    return RevenueSummaryResponse(
        revenue=RevenueBlock(
            target=revenue_target,
            actual=actual,
            pace=_pace_label(actual, revenue_target, elapsed_pct),
        ),
        split=RevenueSplit(new=new_revenue, repeat=repeat_revenue),
        new_customers=NewCustomersBlock(target=0, actual=len(new_customer_ids)),
        active_existing_customers=len(repeat_customer_ids),
        gross_margin=GrossMarginBlock(amount=gross_amount, uncosted_orders=uncosted_orders),
    )


# ─────────────────────────────────────────────
# /analytics/channels
# ─────────────────────────────────────────────

class ChannelRow(BaseModel):
    initiative: str   # "inbound" | "outbound"
    channel: str
    leads: int
    conversion_rate: float
    win_rate: float
    avg_order_value: float
    gross_margin: float


class ChannelsResponse(BaseModel):
    rows: list[ChannelRow]


class PriorityProspectAxisBreakdown(BaseModel):
    axis: str
    value: str
    n: int
    conversions: int
    raw_rate: float
    smoothed_rate: float
    low_sample: bool


class PriorityProspectItem(BaseModel):
    lead_id: int
    type: Literal["priority_prospect"] = "priority_prospect"
    ease_pct: float
    monthly_forecast: float
    rank_score: float
    score: float
    expected_value: float
    suggested_action: str
    axis_breakdown: list[PriorityProspectAxisBreakdown]
    low_sample_flags: list[str]


class PriorityProspectsResponse(BaseModel):
    scope: str
    items: list[PriorityProspectItem]


@router.get(
    "/analytics/channels",
    response_model=ChannelsResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def channels_summary(
    month: str | None = Query(default=None, description="YYYY-MM 形式。省略時は今月"),
    scope: str = Query(default="team", description="team / mine"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    チャネル別集計。api-contract.md section 4 に準拠。
    initiative IN ('inbound','outbound') のみ返す（frontend が initiative_short キーを使用）。
    """
    _validate_scope(scope)
    today = date.today()
    target_year, target_month = _parse_month(month, today)
    start_utc, end_utc = _jst_month_range_utc(target_year, target_month)

    lead_assign = "AND l.assigned_to = :uid" if scope == "mine" else ""
    scope_params: dict = {"uid": current_user.id} if scope == "mine" else {}

    # initiative × channel_type でリード集計（inbound/outbound のみ）
    result = await db.execute(
        text(f"""
            SELECT
                l.initiative,
                COALESCE(l.channel_type, 'unknown') AS channel,
                COUNT(*) AS leads,
                COUNT(l.converted_deal_id) AS converted,
                COUNT(DISTINCT d.id) AS total_deals,
                SUM(CASE WHEN d.status = 'won' THEN 1 ELSE 0 END) AS won,
                COALESCE(
                    AVG(CASE WHEN d.status = 'won' THEN d.amount ELSE NULL END),
                    0
                ) AS avg_order_value
            FROM leads l
            LEFT JOIN deals d ON d.id = l.converted_deal_id
            WHERE l.created_at >= :start AND l.created_at < :end
              AND l.initiative IN ('inbound', 'outbound')
            {lead_assign}
            GROUP BY l.initiative, COALESCE(l.channel_type, 'unknown')
            ORDER BY l.initiative, COALESCE(l.channel_type, 'unknown')
        """),
        {"start": start_utc, "end": end_utc, **scope_params},
    )
    rows_raw = result.mappings().all()

    # ── 粗利: lead → deal → order → order_financials（二重カウント回避のため別クエリ）──
    margin_result = await db.execute(
        text(f"""
            SELECT
                COALESCE(l.initiative, '') AS initiative,
                COALESCE(l.channel_type, 'unknown') AS channel,
                COALESCE(SUM(CASE WHEN f.purchase_cost IS NOT NULL THEN (
                    o.total_amount
                    - COALESCE(f.purchase_cost, 0)
                    - COALESCE(f.purchase_shipping, 0)
                    - COALESCE(f.paypal_fee, 0)
                    - COALESCE(f.wise_fee, 0)
                    - COALESCE(f.exchange_fee, 0)
                    - COALESCE(f.outsource_fee, 0)
                    - COALESCE(f.packing_fee, 0)
                    - COALESCE(f.ad_cost, 0)
                    - COALESCE(f.return_fee, 0)
                    - COALESCE(f.refund_amount, 0)
                ) ELSE 0 END), 0.0) AS gross_margin_amount
            FROM leads l
            JOIN deals d ON d.id = l.converted_deal_id
            JOIN orders o ON o.deal_id = d.id
            LEFT JOIN order_financials f ON f.order_id = o.id
            WHERE l.created_at >= :start AND l.created_at < :end
              AND l.initiative IN ('inbound', 'outbound')
            {lead_assign}
            GROUP BY COALESCE(l.initiative, ''), COALESCE(l.channel_type, 'unknown')
        """),
        {"start": start_utc, "end": end_utc, **scope_params},
    )
    margin_map: dict[tuple[str, str], float] = {
        (row["initiative"], row["channel"]): float(row["gross_margin_amount"] or 0)
        for row in margin_result.mappings().all()
    }

    rows: list[ChannelRow] = []
    for row in rows_raw:
        leads = int(row["leads"] or 0)
        converted = int(row["converted"] or 0)
        total_deals = int(row["total_deals"] or 0)
        won = int(row["won"] or 0)
        conversion_rate = round(converted / leads * 100, 1) if leads > 0 else 0.0
        win_rate = round(won / total_deals * 100, 1) if total_deals > 0 else 0.0
        ini = row["initiative"]
        ch = row["channel"]
        rows.append(ChannelRow(
            initiative=ini,
            channel=ch,
            leads=leads,
            conversion_rate=conversion_rate,
            win_rate=win_rate,
            avg_order_value=round(float(row["avg_order_value"] or 0), 2),
            gross_margin=round(margin_map.get((ini, ch), 0.0), 2),
        ))

    return ChannelsResponse(rows=rows)


@router.get(
    "/analytics/priority-prospects",
    response_model=PriorityProspectsResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def priority_prospects(
    scope: str = Query(default="mine", description="mine only"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    しやすさ% × 見込み金額の read-only 優先リストを返す。

    - しやすさ% は team の属性別 smoothed_rate を平均したもの
    - 欠軸は平均から除外
    - 全欠けは overall_rate にフォールバック
    - monthly_forecast が null の場合は、scope 内の中央値で補完
    """
    if scope != "mine":
        raise HTTPException(status_code=422, detail="scope は mine で指定してください")

    scope_params: dict[str, object] = {"uid": current_user.id}
    overall_rate, team_axes = await _fetch_attribute_conversion_summary(
        db,
        lead_assign="",
        scope_params={},
    )

    lead_result = await db.execute(
        text("""
            SELECT
                id,
                monthly_forecast,
                channel_type,
                country,
                sales_form,
                temperature,
                response_speed
            FROM leads l
            WHERE 1 = 1
              AND l.assigned_to = :uid
            ORDER BY id
        """),
        scope_params,
    )
    lead_rows = lead_result.mappings().all()
    forecast_values = [
        float(row["monthly_forecast"])
        for row in lead_rows
        if row["monthly_forecast"] is not None
    ]
    representative_forecast = median(forecast_values) if forecast_values else 0.0

    items: list[PriorityProspectItem] = []
    for row in lead_rows:
        axis_breakdown: list[PriorityProspectAxisBreakdown] = []
        sampled_rates: list[float] = []
        low_sample_flags: list[str] = []
        for axis_name in ATTRIBUTE_CONVERSION_AXES:
            normalized_value = _normalize_attribute_value(axis_name, row[axis_name])
            if normalized_value is None:
                continue
            axis_data = getattr(team_axes, axis_name)
            bucket_map = {item.value: item for item in axis_data.items}
            bucket = bucket_map.get(normalized_value)
            if bucket is None:
                bucket = bucket_map.get("unknown")
            if bucket is None:
                continue
            low_sample = bucket.n < ATTRIBUTE_CONVERSION_SHRINK_K
            if low_sample:
                low_sample_flags.append(f"{axis_name}:low_sample")
            axis_breakdown.append(PriorityProspectAxisBreakdown(
                axis=axis_name,
                value=normalized_value,
                n=bucket.n,
                conversions=bucket.conversions,
                raw_rate=bucket.raw_rate,
                smoothed_rate=bucket.smoothed_rate,
                low_sample=low_sample,
            ))
            sampled_rates.append(bucket.smoothed_rate)

        ease_rate = sum(sampled_rates) / len(sampled_rates) if sampled_rates else overall_rate
        ease_pct = round(ease_rate * 100, 4)

        monthly_forecast_raw = row["monthly_forecast"]
        monthly_forecast = (
            float(monthly_forecast_raw)
            if monthly_forecast_raw is not None
            else float(representative_forecast)
        )
        if monthly_forecast_raw is None:
            low_sample_flags.append("monthly_forecast_unset")

        rank_score = round(ease_pct * monthly_forecast, 2)
        items.append(PriorityProspectItem(
            lead_id=int(row["id"]),
            ease_pct=ease_pct,
            monthly_forecast=round(monthly_forecast, 2),
            rank_score=rank_score,
            score=rank_score,
            expected_value=round(monthly_forecast, 2),
            suggested_action="今やること",
            axis_breakdown=axis_breakdown,
            low_sample_flags=low_sample_flags,
        ))

    items.sort(key=lambda item: (-item.rank_score, item.lead_id))
    for item in items:
        item.rank_score = round(item.rank_score, 2)
        item.score = item.rank_score

    return PriorityProspectsResponse(scope=scope, items=items)


# ─────────────────────────────────────────────
# /analytics/reasons
# ─────────────────────────────────────────────

class ReasonItem(BaseModel):
    label: str
    primary_count: int
    secondary_count: int


class ReasonMemo(BaseModel):
    deal_id: int
    primary_label: str
    memo: str
    closed_at: str  # YYYY-MM-DD


class ReasonsResponse(BaseModel):
    reasons: list[ReasonItem]
    memos: list[ReasonMemo]


@router.get(
    "/analytics/reasons",
    response_model=ReasonsResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def reasons_summary(
    type: str | None = Query(default=None, description="won / lost でフィルタ。省略時は両方"),
    month: str | None = Query(default=None, description="YYYY-MM 形式。省略時は今月"),
    scope: str = Query(default="team", description="team / mine"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """
    成約/失注理由別集計。api-contract.md section 5 に準拠。

    - reasons: ラベルごとに主因(is_primary=1) / 副因(is_primary=0) の件数
    - memos: 主因ラベル・deal_id・一言メモ・closed_at（最新20件）
    - type=won|lost: close_reasons.type で絞り込み
    """
    _validate_scope(scope)
    if type is not None and type not in ("won", "lost"):
        raise HTTPException(status_code=422, detail="type は won または lost で指定してください")
    today = date.today()
    target_year, target_month = _parse_month(month, today)
    start_utc, end_utc = _jst_month_range_utc(target_year, target_month)

    deal_assign = "AND l.assigned_to = :uid" if scope == "mine" else ""
    scope_params: dict = {"uid": current_user.id} if scope == "mine" else {}
    type_filter = "AND cr.type = :rtype" if type is not None else ""
    type_params: dict = {"rtype": type} if type is not None else {}

    # ── 理由別 主因/副因 集計 ──
    agg_result = await db.execute(
        text(f"""
            SELECT
                cr.label,
                SUM(CASE WHEN dcr.is_primary THEN 1 ELSE 0 END) AS primary_count,
                SUM(CASE WHEN dcr.is_primary THEN 0 ELSE 1 END) AS secondary_count
            FROM deal_close_reasons dcr
            JOIN close_reasons cr ON cr.id = dcr.reason_id
            JOIN deals d ON d.id = dcr.deal_id
            LEFT JOIN leads l ON l.id = COALESCE(dcr.lead_id, d.lead_id)
            WHERE d.closed_at >= :start AND d.closed_at < :end
              AND d.closed_at IS NOT NULL
            {type_filter}
            {deal_assign}
            GROUP BY cr.label
            ORDER BY primary_count DESC
        """),
        {"start": start_utc, "end": end_utc, **type_params, **scope_params},
    )
    reasons: list[ReasonItem] = [
        ReasonItem(
            label=row["label"],
            primary_count=int(row["primary_count"] or 0),
            secondary_count=int(row["secondary_count"] or 0),
        )
        for row in agg_result.mappings().all()
    ]

    # ── メモ: 主因ラベル + deal_id + close_reason_memo + closed_at ──
    memo_result = await db.execute(
        text(f"""
            SELECT
                d.id AS deal_id,
                cr.label AS primary_label,
                d.close_reason_memo AS memo,
                d.closed_at
            FROM deals d
            JOIN deal_close_reasons dcr ON dcr.deal_id = d.id AND dcr.is_primary
            LEFT JOIN leads l ON l.id = COALESCE(dcr.lead_id, d.lead_id)
            JOIN close_reasons cr ON cr.id = dcr.reason_id
            WHERE d.closed_at >= :start AND d.closed_at < :end
              AND d.closed_at IS NOT NULL
              AND d.close_reason_memo IS NOT NULL
              AND d.close_reason_memo != ''
            {type_filter}
            {deal_assign}
            ORDER BY d.closed_at DESC
            LIMIT 20
        """),
        {"start": start_utc, "end": end_utc, **type_params, **scope_params},
    )
    memos: list[ReasonMemo] = [
        ReasonMemo(
            deal_id=int(row["deal_id"]),
            primary_label=row["primary_label"],
            memo=row["memo"],
            closed_at=str(row["closed_at"])[:10],
        )
        for row in memo_result.mappings().all()
    ]

    return ReasonsResponse(reasons=reasons, memos=memos)


# ─────────────────────────────────────────────
# /analytics/weekly-advisor-defensive
# W-1 復元（#2455 で誤削除 → 外科的復元）
# ─────────────────────────────────────────────

class WeeklyAdvisorReason(BaseModel):
    last_order_at: date | None = None
    last_contact_at: datetime | None = None
    avg_interval_days: float | None = None
    days_since_last_order: int | None = None
    days_since_contact: int | None = None
    pace_score: float | None = None
    contact_score: float | None = None
    decline_score: float | None = None
    total_score: float | None = None
    current_order_count: int | None = None
    previous_order_count: int | None = None
    current_revenue: float | None = None
    previous_revenue: float | None = None


class WeeklyAdvisorAction(BaseModel):
    rank: int
    type: str
    company_id: int
    company_name: str
    lead_id: int | None = None
    score: float
    expected_value: float
    suggested_action: str
    reason: WeeklyAdvisorReason


class WeeklyAdvisorResponse(BaseModel):
    period: str
    scope: str
    stale_days: int
    actions: list[WeeklyAdvisorAction]


def _normalize_date(value: object) -> date:
    """DB から返る date / datetime / str を date に正規化する。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    return date.fromisoformat(str(value)[:10])


def _customer_orders_period_bounds(period: str, today: date) -> tuple[object, object]:
    """customer-orders 用の期間境界を返す（_advisor_period_bounds の依存として復元）。"""
    if period == "1m":
        return _jst_month_range_utc(today.year, today.month)
    days_map = {"3m": 90, "6m": 180, "12m": 365}
    if period not in days_map:
        raise HTTPException(status_code=422, detail="period は 1m / 3m / 6m / 12m で指定してください")
    end = today + timedelta(days=1)
    return today - timedelta(days=days_map[period]), end


def _advisor_period_bounds(period: str, today: date) -> tuple[object, object, object, object]:
    """週次アドバイザー用に current / previous の期間境界を返す。"""
    current_start, current_end = _customer_orders_period_bounds(period, today)
    if period == "1m":
        prev_month = today.month - 1
        prev_year = today.year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1
        previous_start, previous_end = _jst_month_range_utc(prev_year, prev_month)
        return current_start, current_end, previous_start, previous_end

    window = current_end - current_start
    previous_end = current_start
    previous_start = previous_end - window
    return current_start, current_end, previous_start, previous_end


def _order_count_drop_score(current: int, previous: int) -> float:
    """受注数の落ち込みを 0 / 20 / 40 点で返す。"""
    if previous <= 0:
        return 0.0
    ratio = current / previous if previous > 0 else 1.0
    if ratio >= 0.9:
        return 0.0
    if ratio >= 0.7:
        return 20.0
    return 40.0


def _revenue_drop_score(current: float, previous: float) -> float:
    """売上の落ち込みを 0 / 20 / 40 点で返す。"""
    if previous <= 0:
        return 0.0
    ratio = current / previous if previous > 0 else 1.0
    if ratio >= 0.9:
        return 0.0
    if ratio >= 0.7:
        return 20.0
    return 40.0


def _pace_score(days_since_last_order: int, avg_interval_days: float | None) -> float:
    """受注ペースの超過度を 0〜60 点で返す。"""
    if avg_interval_days is None or avg_interval_days <= 0:
        return 0.0
    ratio = days_since_last_order / avg_interval_days
    if ratio <= 1.0:
        return 0.0
    if ratio <= 1.3:
        return round(((ratio - 1.0) / 0.3) * 30.0, 1)
    if ratio <= 2.0:
        return round(30.0 + (((ratio - 1.3) / 0.7) * 30.0), 1)
    return 60.0


def _contact_score(days_since_contact: int | None, stale_days: int) -> float:
    """接触途絶の強さを 0〜60 点で返す。"""
    if days_since_contact is None or days_since_contact < stale_days:
        return 0.0
    if days_since_contact <= stale_days + 30:
        return round(((days_since_contact - stale_days) / 30.0) * 30.0, 1)
    if days_since_contact <= stale_days + 60:
        return round(30.0 + (((days_since_contact - (stale_days + 30)) / 30.0) * 30.0), 1)
    return 60.0


def _normalized_urgency(score: float, cap: float) -> float:
    """score を cap で正規化し、最小 0.1 を確保する。"""
    if score <= 0:
        return 0.0
    return max(0.1, min(score / cap, 1.0))


@router.get(
    "/analytics/weekly-advisor-defensive",
    response_model=WeeklyAdvisorResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def weekly_advisor_defensive(
    period: str = Query(default="3m", description="1m / 3m / 6m / 12m"),
    scope: str = Query(default="mine", description="team / mine"),
    stale_days: int = Query(default=14, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """守り3種の打ち手を score 降順で返す read-only 集計 API。"""
    _validate_scope(scope)
    today = date.today()
    current_start, current_end, previous_start, previous_end = _advisor_period_bounds(period, today)

    if scope == "mine":
        scope_join = "JOIN deals d ON d.id = o.deal_id AND d.assigned_to = :uid"
        scope_params: dict = {"uid": current_user.id}
    else:
        scope_join = ""
        scope_params = {}

    combined_result = await db.execute(
        text(f"""
            SELECT
                o.company_id,
                COALESCE(c.name, '') AS company_name,
                c.lead_id,
                o.created_at,
                COALESCE(o.total_amount, 0) AS total_amount
            FROM orders o
            LEFT JOIN companies c ON c.id = o.company_id
            {scope_join}
            WHERE o.company_id IS NOT NULL
              AND o.created_at >= :previous_start
              AND o.created_at < :current_end
            ORDER BY o.company_id, o.created_at, o.id
        """),
        {"previous_start": previous_start, "current_end": current_end, **scope_params},
    )
    combined_rows = combined_result.mappings().all()

    grouped_names: dict[int, str] = {}
    grouped_lead_ids: dict[int, int | None] = {}
    grouped_orders: dict[int, list[dict[str, object]]] = {}
    candidate_company_ids: set[int] = set()
    for row in combined_rows:
        company_id = int(row["company_id"])
        candidate_company_ids.add(company_id)
        grouped_names.setdefault(company_id, str(row["company_name"] or ""))
        if company_id not in grouped_lead_ids:
            lead_id = row["lead_id"]
            grouped_lead_ids[company_id] = int(lead_id) if lead_id is not None else None
        grouped_orders.setdefault(company_id, []).append({
            "created_at": _normalize_date(row["created_at"]),
            "total_amount": float(row["total_amount"] or 0),
        })

    if not candidate_company_ids:
        return WeeklyAdvisorResponse(period=period, scope=scope, stale_days=stale_days, actions=[])

    contact_last_seen: dict[int, datetime] = {}
    try:
        contact_result = await db.execute(
            text("""
                SELECT company_id, MAX(occurred_at) AS last_conversation_at
                FROM conversation_logs
                WHERE company_id IS NOT NULL
                GROUP BY company_id
            """),
        )
        for row in contact_result.mappings().all():
            company_id = int(row["company_id"])
            if company_id in candidate_company_ids and row["last_conversation_at"] is not None:
                contact_last_seen[company_id] = row["last_conversation_at"]
    except Exception:
        contact_last_seen = {}

    actions: list[WeeklyAdvisorAction] = []
    churn_company_ids: set[int] = set()
    current_start_cmp = _normalize_date(current_start)
    current_end_cmp = _normalize_date(current_end)
    previous_start_cmp = _normalize_date(previous_start)
    previous_end_cmp = _normalize_date(previous_end)

    for company_id, orders in grouped_orders.items():
        orders_sorted = sorted(orders, key=lambda item: item["created_at"])
        if not orders_sorted:
            continue

        current_orders = [
            item for item in orders_sorted
            if current_start_cmp <= item["created_at"] < current_end_cmp
        ]
        previous_orders = [
            item for item in orders_sorted
            if previous_start_cmp <= item["created_at"] < previous_end_cmp
        ]

        all_order_count = len(orders_sorted)
        all_total_amount = sum(float(item["total_amount"] or 0) for item in orders_sorted)
        first_order_at = orders_sorted[0]["created_at"]
        last_order_at = orders_sorted[-1]["created_at"]
        days_since_last_order = (today - last_order_at).days
        avg_interval_days: float | None = None
        if all_order_count >= 2:
            intervals = [
                (orders_sorted[idx]["created_at"] - orders_sorted[idx - 1]["created_at"]).days
                for idx in range(1, all_order_count)
            ]
            avg_interval_days = round(sum(intervals) / len(intervals), 1)

        avg_order_amount = round(all_total_amount / all_order_count, 2)
        current_order_count = len(current_orders)
        previous_order_count = len(previous_orders)
        current_revenue = round(sum(float(item["total_amount"] or 0) for item in current_orders), 2)
        previous_revenue = round(sum(float(item["total_amount"] or 0) for item in previous_orders), 2)

        last_contact_at = contact_last_seen.get(company_id)
        days_since_contact = (today - _normalize_date(last_contact_at)).days if last_contact_at else None

        if avg_interval_days is not None and days_since_last_order >= avg_interval_days * 0.8:
            urgency = _normalized_urgency(
                days_since_last_order / max(avg_interval_days, 1.0) - 0.8,
                1.2,
            )
            score = round(avg_order_amount * 0.8 * urgency, 1)
            actions.append(WeeklyAdvisorAction(
                rank=0,
                type="reorder",
                company_id=company_id,
                company_name=grouped_names.get(company_id, ""),
                lead_id=grouped_lead_ids.get(company_id),
                score=score,
                expected_value=avg_order_amount,
                suggested_action="再受注の案内",
                reason=WeeklyAdvisorReason(
                    last_order_at=first_order_at if all_order_count == 1 else last_order_at,
                    avg_interval_days=avg_interval_days,
                    days_since_last_order=days_since_last_order,
                    last_contact_at=last_contact_at,
                    days_since_contact=days_since_contact,
                    current_order_count=current_order_count,
                    previous_order_count=previous_order_count,
                    current_revenue=current_revenue,
                    previous_revenue=previous_revenue,
                ),
            ))

        pace_score = _pace_score(days_since_last_order, avg_interval_days)
        contact_score = _contact_score(days_since_contact, stale_days)
        decline_score = max(
            _order_count_drop_score(current_order_count, previous_order_count),
            _revenue_drop_score(current_revenue, previous_revenue),
        )
        total_risk_score = round(pace_score + contact_score + decline_score, 1)
        if total_risk_score >= 60:
            churn_company_ids.add(company_id)
            urgency = _normalized_urgency(total_risk_score, 180.0)
            score = round(avg_order_amount * 0.5 * urgency, 1)
            actions.append(WeeklyAdvisorAction(
                rank=0,
                type="churn_risk",
                company_id=company_id,
                company_name=grouped_names.get(company_id, ""),
                lead_id=grouped_lead_ids.get(company_id),
                score=score,
                expected_value=avg_order_amount,
                suggested_action="状況確認の連絡",
                reason=WeeklyAdvisorReason(
                    last_order_at=last_order_at,
                    last_contact_at=last_contact_at,
                    avg_interval_days=avg_interval_days,
                    days_since_last_order=days_since_last_order,
                    days_since_contact=days_since_contact,
                    pace_score=pace_score,
                    contact_score=contact_score,
                    decline_score=decline_score,
                    total_score=total_risk_score,
                    current_order_count=current_order_count,
                    previous_order_count=previous_order_count,
                    current_revenue=current_revenue,
                    previous_revenue=previous_revenue,
                ),
            ))

        if (
            days_since_contact is not None
            and days_since_contact >= stale_days
            and company_id not in churn_company_ids
        ):
            urgency = _normalized_urgency(days_since_contact - stale_days, 60.0)
            score = round(avg_order_amount * 0.3 * urgency, 1)
            actions.append(WeeklyAdvisorAction(
                rank=0,
                type="comm_low",
                company_id=company_id,
                company_name=grouped_names.get(company_id, ""),
                lead_id=grouped_lead_ids.get(company_id),
                score=score,
                expected_value=avg_order_amount,
                suggested_action="近況確認の連絡",
                reason=WeeklyAdvisorReason(
                    last_order_at=last_order_at,
                    last_contact_at=last_contact_at,
                    days_since_contact=days_since_contact,
                    current_order_count=current_order_count,
                    previous_order_count=previous_order_count,
                    current_revenue=current_revenue,
                    previous_revenue=previous_revenue,
                ),
            ))

    actions.sort(
        key=lambda item: (
            item.score,
            item.expected_value,
            item.company_name,
            item.company_id,
        ),
        reverse=True,
    )
    ranked_actions: list[WeeklyAdvisorAction] = []
    for idx, action in enumerate(actions, start=1):
        ranked_actions.append(action.model_copy(update={"rank": idx}))

    return WeeklyAdvisorResponse(
        period=period,
        scope=scope,
        stale_days=stale_days,
        actions=ranked_actions,
    )
