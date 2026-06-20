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


class CustomerOrderItem(BaseModel):
    company_id: int
    company_name: str
    order_count: int
    first_order_at: date
    last_order_at: date
    days_since_last_order: int
    continuation_days: int
    avg_interval_days: float | None
    avg_order_amount: float
    total_amount: float
    predicted_next_order_at: date | None


class CustomerOrdersResponse(BaseModel):
    items: list[CustomerOrderItem]


class CustomerContactItem(BaseModel):
    company_id: int
    company_name: str
    contact_count: int
    last_contact_at: str | None
    days_since_last_contact: int | None
    is_communication_low: bool


class CustomerContactsResponse(BaseModel):
    period: str
    scope: str
    stale_days: int
    items: list[CustomerContactItem]


class GoalAdviceInputs(BaseModel):
    monthly_kgi: float
    kgi_type: Literal["revenue", "wins"]
    period: str
    scope: str


class GoalAdviceRatesUsed(BaseModel):
    unit_price: float | None
    win_rate: float | None
    deal_rate: float | None


class GoalAdviceRequired(BaseModel):
    wins: float | None
    deals: float | None
    leads: float | None


class GoalAdviceWorkingDays(BaseModel):
    remaining_month: int
    remaining_week: int
    shift_status: Literal["submitted", "not_submitted"]


class GoalAdviceResponse(BaseModel):
    inputs: GoalAdviceInputs
    rates_used: GoalAdviceRatesUsed
    monthly_required: GoalAdviceRequired
    weekly_required: GoalAdviceRequired
    working_days: GoalAdviceWorkingDays
    data_sufficient: bool


class WeeklyAdvisorAction(BaseModel):
    type: Literal["reorder", "churn_risk", "comm_low"]
    company_id: int
    company_name: str
    score: float
    expected_value: float
    reason: dict[str, object]
    suggested_action: str


class WeeklyAdvisorResponse(BaseModel):
    actions: list[WeeklyAdvisorAction]


class RevenueSegmentStat(BaseModel):
    revenue: float
    order_count: int
    avg_order_amount: float | None
    customer_count: int
    share: float


class RevenueSegmentSummary(BaseModel):
    revenue: float
    order_count: int
    customer_count: int


class RevenueSegmentsResponse(BaseModel):
    period: str
    scope: str
    new: RevenueSegmentStat
    repeat: RevenueSegmentStat
    total: RevenueSegmentSummary


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
    """customer-orders 用の期間境界を返す。"""
    if period == "1m":
        return _jst_month_range_utc(today.year, today.month)
    days_map = {"3m": 90, "6m": 180, "12m": 365}
    if period not in days_map:
        raise HTTPException(status_code=422, detail="period は 1m / 3m / 6m / 12m で指定してください")
    end = today + timedelta(days=1)
    return today - timedelta(days=days_map[period]), end


def _count_inclusive_weekdays(start: date, end: date) -> int:
    """start から end までの平日数を両端含みで数える。"""
    if end < start:
        return 0
    total = 0
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            total += 1
        cursor += timedelta(days=1)
    return total


def _month_end_date(today: date) -> date:
    """today が属する月の月末日を返す。"""
    import calendar

    return date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])


def _week_end_date(today: date) -> date:
    """today が属する週の日曜を返す。"""
    return today + timedelta(days=(6 - today.weekday()))


_WEEKLY_REORDER_THRESHOLD = 0.8
_WEEKLY_REORDER_CERTAINTY = 0.8
_WEEKLY_CHURN_CERTAINTY = 0.5
_WEEKLY_COMM_LOW_CERTAINTY = 0.3
_WEEKLY_COMM_LOW_THRESHOLD_DAYS = 14
_WEEKLY_COMM_LOW_URGENCY_WINDOW_DAYS = 60.0
_WEEKLY_CHURN_PACE_MAX_DAYS_RATIO = 2.0
_WEEKLY_CHURN_CONTACT_WARN_DAYS = 30
_WEEKLY_CHURN_CONTACT_MAX_DAYS = 60
_WEEKLY_CHURN_DECLINE_RATIO = 0.67


def _order_scope_clause(scope: str, user_id: int) -> tuple[str, dict[str, int]]:
    """order / deal 集計で使う scope 句を返す。"""
    if scope == "mine":
        return "JOIN deals d ON d.id = o.deal_id AND d.assigned_to = :uid", {"uid": user_id}
    return "", {}


def _previous_period_bounds(start: object, end: object) -> tuple[object, object]:
    """current period と同じ長さの直前期間を返す。"""
    span = end - start
    return start - span, start


def _pace_score(days_since_last_order: int, avg_interval_days: float) -> float:
    """発注ペースの加点（0-60）。1.0倍で0点、1.3倍で約30点、2.0倍で満点。"""
    if avg_interval_days <= 0:
        return 0.0
    ratio = days_since_last_order / avg_interval_days
    if ratio <= 1.0:
        return 0.0
    if ratio <= 1.3:
        return round((ratio - 1.0) / 0.3 * 30, 1)
    if ratio <= _WEEKLY_CHURN_PACE_MAX_DAYS_RATIO:
        return round(30 + (ratio - 1.3) / (_WEEKLY_CHURN_PACE_MAX_DAYS_RATIO - 1.3) * 30, 1)
    return 60.0


def _contact_score(days_since_last_contact: int | None) -> float:
    """接触途絶の加点（0-60）。"""
    if days_since_last_contact is None:
        return 0.0
    if days_since_last_contact < _WEEKLY_CHURN_CONTACT_WARN_DAYS:
        return 0.0
    if days_since_last_contact >= _WEEKLY_CHURN_CONTACT_MAX_DAYS:
        return 60.0
    return 30.0


def _decline_score(
    *,
    current_order_count: int,
    current_revenue: float,
    previous_order_count: int,
    previous_revenue: float,
) -> float:
    """受注の落ち込みスコア（0-40）。"""
    if previous_order_count <= 0 and previous_revenue <= 0:
        return 0.0

    count_ratio = (current_order_count / previous_order_count) if previous_order_count > 0 else 1.0
    revenue_ratio = (current_revenue / previous_revenue) if previous_revenue > 0 else 1.0
    weakest_ratio = min(count_ratio, revenue_ratio)

    if weakest_ratio >= 1.0:
        return 0.0
    if weakest_ratio >= _WEEKLY_CHURN_DECLINE_RATIO:
        return 20.0
    return 40.0


async def _count_shift_dates(
    db: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    start: date,
    end: date,
) -> int:
    """指定範囲内の shifts.shift_date を distinct 件数で数える。"""
    result = await db.execute(
        text("""
            SELECT COUNT(DISTINCT shift_date) AS cnt
            FROM shifts
            WHERE tenant_id = :tenant_id
              AND user_id = :user_id
              AND shift_date >= :start_date
              AND shift_date <= :end_date
        """),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
    )
    row = result.mappings().first() or {}
    return int(row.get("cnt", 0) or 0)


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


@router.get(
    "/analytics/customer-orders",
    response_model=CustomerOrdersResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def customer_orders_report(
    period: str = Query(default="3m", description="1m / 3m / 6m / 12m"),
    scope: str = Query(default="team", description="team / mine"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """顧客別の受注履歴と再受注予測を返す read-only 集計API。"""
    _validate_scope(scope)
    today = date.today()
    start, end = _customer_orders_period_bounds(period, today)

    if scope == "mine":
        order_scope_join = "JOIN deals d ON d.id = o.deal_id AND d.assigned_to = :uid"
        order_scope_params: dict = {"uid": current_user.id}
    else:
        order_scope_join = ""
        order_scope_params = {}

    result = await db.execute(
        text(f"""
            SELECT
                o.company_id,
                COALESCE(c.name, '') AS company_name,
                o.created_at,
                o.total_amount
            FROM orders o
            LEFT JOIN companies c ON c.id = o.company_id
            {order_scope_join}
            WHERE o.company_id IS NOT NULL
              AND o.created_at >= :start
              AND o.created_at < :end
            ORDER BY o.company_id, o.created_at, o.id
        """),
        {"start": start, "end": end, **order_scope_params},
    )
    rows = result.mappings().all()

    grouped_names: dict[int, str] = {}
    grouped_orders: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        company_id = int(row["company_id"])
        grouped_names.setdefault(company_id, str(row["company_name"] or ""))
        grouped_orders.setdefault(company_id, []).append({
            "created_at": _normalize_date(row["created_at"]),
            "total_amount": float(row["total_amount"] or 0),
        })

    items: list[CustomerOrderItem] = []
    for company_id, orders in grouped_orders.items():
        orders = sorted(orders, key=lambda x: x["created_at"])
        if not orders:
            continue
        first_order = orders[0]["created_at"]
        last_order = orders[-1]["created_at"]
        order_count = len(orders)
        total_amount = sum(order["total_amount"] for order in orders)
        avg_order_amount = round(total_amount / order_count, 2)
        continuation_days = (last_order - first_order).days
        days_since_last_order = (today - last_order).days

        avg_interval_days: float | None = None
        predicted_next_order_at: date | None = None
        if order_count >= 2:
            intervals = [
                (orders[idx]["created_at"] - orders[idx - 1]["created_at"]).days
                for idx in range(1, order_count)
            ]
            avg_interval_days = round(sum(intervals) / len(intervals), 1)
            predicted_next_order_at = last_order + timedelta(days=max(1, int(round(avg_interval_days))))

        items.append(CustomerOrderItem(
            company_id=company_id,
            company_name=grouped_names.get(company_id, ""),
            order_count=order_count,
            first_order_at=first_order,
            last_order_at=last_order,
            days_since_last_order=days_since_last_order,
            continuation_days=continuation_days,
            avg_interval_days=avg_interval_days,
            avg_order_amount=avg_order_amount,
            total_amount=round(total_amount, 2),
            predicted_next_order_at=predicted_next_order_at,
        ))

    items.sort(key=lambda item: (item.last_order_at, item.total_amount, item.company_id), reverse=True)
    return CustomerOrdersResponse(items=items)


@router.get(
    "/analytics/customer-contacts",
    response_model=CustomerContactsResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def customer_contacts_report(
    period: str = Query(default="3m", description="1m / 3m / 6m / 12m"),
    scope: str = Query(default="team", description="team / mine"),
    stale_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """顧客別の接触履歴とコミュニケーション低下フラグを返す read-only 集計API。"""
    _validate_scope(scope)
    today = date.today()
    start, end = _customer_orders_period_bounds(period, today)

    company_scope_filter = "AND c.sales_rep_id = :uid" if scope == "mine" else ""
    company_scope_params: dict = {"uid": current_user.id} if scope == "mine" else {}

    result = await db.execute(
        text(f"""
            SELECT
                c.id AS company_id,
                COALESCE(c.name, '') AS company_name,
                COALESCE(
                    SUM(
                        CASE
                            WHEN cl.occurred_at >= :start AND cl.occurred_at < :end THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS contact_count,
                MAX(cl.occurred_at) AS last_conversation_at
            FROM companies c
            LEFT JOIN conversation_logs cl ON cl.company_id = c.id
            WHERE 1 = 1
              {company_scope_filter}
            GROUP BY c.id, c.name
            ORDER BY
                CASE WHEN MAX(cl.occurred_at) IS NULL THEN 1 ELSE 0 END DESC,
                MAX(cl.occurred_at) ASC,
                c.id
        """),
        {"start": start, "end": end, **company_scope_params},
    )
    rows = result.mappings().all()

    items: list[CustomerContactItem] = []
    for row in rows:
        last_contact_raw = row["last_conversation_at"]
        last_contact_at: str | None = None
        days_since_last_contact: int | None = None
        is_communication_low = True
        if last_contact_raw is not None:
            last_contact_date = _normalize_date(last_contact_raw)
            last_contact_at = last_contact_date.isoformat()
            days_since_last_contact = (today - last_contact_date).days
            is_communication_low = days_since_last_contact >= stale_days

        items.append(CustomerContactItem(
            company_id=int(row["company_id"]),
            company_name=str(row["company_name"] or ""),
            contact_count=int(row["contact_count"] or 0),
            last_contact_at=last_contact_at,
            days_since_last_contact=days_since_last_contact,
            is_communication_low=is_communication_low,
        ))

    return CustomerContactsResponse(
        period=period,
        scope=scope,
        stale_days=stale_days,
        items=items,
    )


@router.get(
    "/analytics/revenue-segments",
    response_model=RevenueSegmentsResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def revenue_segments_report(
    period: str = Query(default="3m", description="1m / 3m / 6m / 12m"),
    scope: str = Query(default="team", description="team / mine"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """新規/既存セグメント別の売上サマリーを返す read-only 集計API。"""
    _validate_scope(scope)
    today = date.today()
    start, end = _customer_orders_period_bounds(period, today)

    if scope == "mine":
        order_scope_join = "JOIN deals d ON d.id = o.deal_id AND d.assigned_to = :uid"
        order_scope_params: dict = {"uid": current_user.id}
    else:
        order_scope_join = ""
        order_scope_params = {}

    split_result = await db.execute(
        text(f"""
            SELECT
                o.company_id,
                COALESCE(SUM(o.total_amount), 0) AS total_amount,
                COUNT(*) AS order_count
            FROM orders o
            {order_scope_join}
            WHERE o.company_id IS NOT NULL
              AND o.created_at >= :start
              AND o.created_at < :end
            GROUP BY o.company_id
            ORDER BY o.company_id
        """),
        {"start": start, "end": end, **order_scope_params},
    )
    split_rows = split_result.mappings().all()

    new_revenue = 0.0
    repeat_revenue = 0.0
    new_order_count = 0
    repeat_order_count = 0
    new_customer_ids: set[int] = set()
    repeat_customer_ids: set[int] = set()

    for row in split_rows:
        company_id = int(row["company_id"])
        revenue = float(row["total_amount"] or 0)
        order_count = int(row["order_count"] or 0)

        prior_result = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM orders WHERE company_id = :cid AND created_at < :start"),
            {"cid": company_id, "start": start},
        )
        prior_cnt = int((prior_result.mappings().first() or {}).get("cnt", 0) or 0)

        if prior_cnt == 0:
            new_revenue += revenue
            new_order_count += order_count
            new_customer_ids.add(company_id)
        else:
            repeat_revenue += revenue
            repeat_order_count += order_count
            repeat_customer_ids.add(company_id)

    total_revenue = round(new_revenue + repeat_revenue, 2)
    total_order_count = new_order_count + repeat_order_count
    total_customer_count = len(new_customer_ids | repeat_customer_ids)

    def _segment_payload(
        revenue: float,
        order_count: int,
        customer_count: int,
    ) -> RevenueSegmentStat:
        avg_order_amount = round(revenue / order_count, 2) if order_count > 0 else None
        share = round((revenue / total_revenue * 100), 1) if total_revenue > 0 else 0.0
        return RevenueSegmentStat(
            revenue=round(revenue, 2),
            order_count=order_count,
            avg_order_amount=avg_order_amount,
            customer_count=customer_count,
            share=share,
        )

    return RevenueSegmentsResponse(
        period=period,
        scope=scope,
        new=_segment_payload(new_revenue, new_order_count, len(new_customer_ids)),
        repeat=_segment_payload(repeat_revenue, repeat_order_count, len(repeat_customer_ids)),
        total=RevenueSegmentSummary(
            revenue=total_revenue,
            order_count=total_order_count,
            customer_count=total_customer_count,
        ),
    )


@router.get(
    "/analytics/new-goal-advice",
    response_model=GoalAdviceResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def new_goal_advice(
    monthly_kgi: float = Query(default=..., ge=0),
    kgi_type: Literal["revenue", "wins"] = Query(default=..., description="revenue / wins"),
    scope: str = Query(default="team", description="team / mine"),
    period: str = Query(default="3m", description="1m / 3m / 6m / 12m"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """新規モード向けの逆算アドバイスを返す read-only API。"""
    _validate_scope(scope)
    today = date.today()

    segments = await revenue_segments_report(
        period=period,
        scope=scope,
        db=db,
        tenant_id=tenant_id,
        current_user=current_user,
    )
    unit_price = segments.new.avg_order_amount

    if scope == "mine":
        lead_assign_filter = "AND assigned_to = :uid"
        deal_assign_filter = "AND assigned_to = :uid"
        scope_params: dict = {"uid": current_user.id}
    else:
        lead_assign_filter = ""
        deal_assign_filter = ""
        scope_params = {}

    start, end = _customer_orders_period_bounds(period, today)

    win_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) FILTER (WHERE status = 'won') AS won,
                COUNT(*) AS total
            FROM deals
            WHERE created_at >= :start
              AND created_at < :end
              {deal_assign_filter}
        """),
        {"start": start, "end": end, **scope_params},
    )
    win_row = win_result.mappings().first() or {}
    total_deals = int(win_row.get("total", 0) or 0)
    won_deals = int(win_row.get("won", 0) or 0)
    win_rate = round(won_deals / total_deals * 100, 1) if total_deals > 0 else 0.0

    deal_result = await db.execute(
        text(f"""
            SELECT
                COUNT(*) FILTER (WHERE converted_deal_id IS NOT NULL) AS converted,
                COUNT(*) AS total
            FROM leads
            WHERE created_at >= :start
              AND created_at < :end
              {lead_assign_filter}
        """),
        {"start": start, "end": end, **scope_params},
    )
    deal_row = deal_result.mappings().first() or {}
    total_leads = int(deal_row.get("total", 0) or 0)
    converted_leads = int(deal_row.get("converted", 0) or 0)
    deal_rate = round(converted_leads / total_leads * 100, 1) if total_leads > 0 else 0.0

    month_end = _month_end_date(today)
    week_end = _week_end_date(today)
    month_start = today.replace(day=1)
    month_shift_days = await _count_shift_dates(
        db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        start=month_start,
        end=month_end,
    )
    shift_status: Literal["submitted", "not_submitted"]
    if month_shift_days > 0:
        shift_status = "submitted"
        remaining_month = await _count_shift_dates(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            start=today,
            end=month_end,
        )
        remaining_week = await _count_shift_dates(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            start=today,
            end=week_end,
        )
    else:
        shift_status = "not_submitted"
        remaining_month = _count_inclusive_weekdays(today, month_end)
        remaining_week = _count_inclusive_weekdays(today, week_end)

    remaining_month = max(remaining_month, 1)

    data_sufficient = (
        win_rate > 0
        and deal_rate > 0
        and (kgi_type == "wins" or (unit_price is not None and unit_price > 0))
    )

    def _empty_required() -> GoalAdviceRequired:
        return GoalAdviceRequired(wins=None, deals=None, leads=None)

    def _calc_required(monthly_wins: float | None) -> GoalAdviceRequired:
        if monthly_wins is None:
            return _empty_required()
        monthly_deals = monthly_wins / (win_rate / 100.0)
        monthly_leads = monthly_deals / (deal_rate / 100.0)
        return GoalAdviceRequired(
            wins=round(monthly_wins, 2),
            deals=round(monthly_deals, 2),
            leads=round(monthly_leads, 2),
        )

    monthly_required: GoalAdviceRequired
    weekly_required: GoalAdviceRequired
    if data_sufficient:
        if kgi_type == "revenue":
            monthly_wins = monthly_kgi / float(unit_price or 1)
        else:
            monthly_wins = monthly_kgi
        monthly_required = _calc_required(monthly_wins)
        weekly_required = GoalAdviceRequired(
            wins=round(monthly_required.wins / remaining_month * remaining_week, 2) if monthly_required.wins is not None else None,
            deals=round(monthly_required.deals / remaining_month * remaining_week, 2) if monthly_required.deals is not None else None,
            leads=round(monthly_required.leads / remaining_month * remaining_week, 2) if monthly_required.leads is not None else None,
        )
    else:
        monthly_required = _empty_required()
        weekly_required = _empty_required()

    return GoalAdviceResponse(
        inputs=GoalAdviceInputs(
            monthly_kgi=monthly_kgi,
            kgi_type=kgi_type,
            period=period,
            scope=scope,
        ),
        rates_used=GoalAdviceRatesUsed(
            unit_price=round(float(unit_price), 2) if unit_price is not None else None,
            win_rate=win_rate if total_deals > 0 else None,
            deal_rate=deal_rate if total_leads > 0 else None,
        ),
        monthly_required=monthly_required,
        weekly_required=weekly_required,
        working_days=GoalAdviceWorkingDays(
            remaining_month=remaining_month,
            remaining_week=remaining_week,
            shift_status=shift_status,
        ),
        data_sufficient=data_sufficient,
    )


# ─────────────────────────────────────────────
# 守り3種ランキング
# ─────────────────────────────────────────────

@router.get(
    "/analytics/weekly-advisor-defensive",
    response_model=WeeklyAdvisorResponse,
    dependencies=[Depends(require_permission("dashboard.view"))],
)
async def weekly_advisor_defensive(
    scope: str = Query(default="team", description="team / mine"),
    period: str = Query(default="3m", description="1m / 3m / 6m / 12m"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """守り3種（そろそろ受注 / 離脱リスク / コミュ低下）を rank 済みで返す read-only API。"""
    _validate_scope(scope)
    today = date.today()

    orders_report = await customer_orders_report(
        period=period,
        scope=scope,
        db=db,
        tenant_id=tenant_id,
        current_user=current_user,
    )
    contacts_report = await customer_contacts_report(
        period=period,
        scope=scope,
        stale_days=_WEEKLY_COMM_LOW_THRESHOLD_DAYS,
        db=db,
        tenant_id=tenant_id,
        current_user=current_user,
    )

    orders_by_company = {item.company_id: item for item in orders_report.items}
    contacts_by_company = {item.company_id: item for item in contacts_report.items}

    start, end = _customer_orders_period_bounds(period, today)
    prev_start, prev_end = _previous_period_bounds(start, end)
    order_scope_join, order_scope_params = _order_scope_clause(scope, current_user.id)
    prev_result = await db.execute(
        text(f"""
            SELECT
                o.company_id,
                COALESCE(SUM(o.total_amount), 0) AS total_amount,
                COUNT(*) AS order_count
            FROM orders o
            {order_scope_join}
            WHERE o.company_id IS NOT NULL
              AND o.created_at >= :prev_start
              AND o.created_at < :prev_end
            GROUP BY o.company_id
        """),
        {"prev_start": prev_start, "prev_end": prev_end, **order_scope_params},
    )
    prev_rows = prev_result.mappings().all()
    prev_by_company = {
        int(row["company_id"]): {
            "total_amount": float(row["total_amount"] or 0),
            "order_count": int(row["order_count"] or 0),
        }
        for row in prev_rows
    }

    actions: list[WeeklyAdvisorAction] = []
    churn_company_ids: set[int] = set()

    for item in orders_report.items:
        if item.avg_interval_days is None or item.avg_interval_days <= 0:
            continue

        expected_value = float(item.avg_order_amount or 0)
        if expected_value <= 0:
            continue

        pace_ratio = item.days_since_last_order / item.avg_interval_days
        if pace_ratio >= _WEEKLY_REORDER_THRESHOLD:
            urgency = min(max(pace_ratio / 2.0, 0.0), 1.0)
            score = round(expected_value * _WEEKLY_REORDER_CERTAINTY * urgency, 2)
            if score > 0:
                actions.append(WeeklyAdvisorAction(
                    type="reorder",
                    company_id=item.company_id,
                    company_name=item.company_name,
                    score=score,
                    expected_value=round(expected_value, 2),
                    reason={
                        "last_order_at": item.last_order_at.isoformat(),
                        "avg_interval_days": item.avg_interval_days,
                        "days_since_last_order": item.days_since_last_order,
                    },
                    suggested_action="再発注の案内を送る",
                ))

        contact_item = contacts_by_company.get(item.company_id)
        contact_score = _contact_score(contact_item.days_since_last_contact if contact_item else None)
        previous = prev_by_company.get(item.company_id, {"total_amount": 0.0, "order_count": 0})
        decline_score = _decline_score(
            current_order_count=item.order_count,
            current_revenue=float(item.total_amount or 0),
            previous_order_count=int(previous["order_count"]),
            previous_revenue=float(previous["total_amount"]),
        )
        pace_risk_score = _pace_score(item.days_since_last_order, item.avg_interval_days)
        total_risk_score = round(pace_risk_score + contact_score + decline_score, 1)
        if total_risk_score <= 0:
            continue

        churn_company_ids.add(item.company_id)
        risk_urgency = min(total_risk_score / 100.0, 1.0)
        score = round(expected_value * _WEEKLY_CHURN_CERTAINTY * risk_urgency, 2)
        if score <= 0:
            continue

        actions.append(WeeklyAdvisorAction(
            type="churn_risk",
            company_id=item.company_id,
            company_name=item.company_name,
            score=score,
            expected_value=round(expected_value, 2),
            reason={
                "pace_score": pace_risk_score,
                "contact_score": contact_score,
                "decline_score": decline_score,
                "total_score": total_risk_score,
                "days_since_last_order": item.days_since_last_order,
                "avg_interval_days": item.avg_interval_days,
                "days_since_contact": contact_item.days_since_last_contact if contact_item else None,
                "last_order_at": item.last_order_at.isoformat(),
            },
            suggested_action="状況確認と再提案を行う",
        ))

    for contact_item in contacts_report.items:
        if contact_item.company_id in churn_company_ids:
            continue
        if contact_item.days_since_last_contact is None or contact_item.days_since_last_contact < _WEEKLY_COMM_LOW_THRESHOLD_DAYS:
            continue

        order_item = orders_by_company.get(contact_item.company_id)
        expected_value = float(order_item.avg_order_amount if order_item else 0) if order_item else 0.0
        if expected_value <= 0:
            continue

        urgency = min(contact_item.days_since_last_contact / _WEEKLY_COMM_LOW_URGENCY_WINDOW_DAYS, 1.0)
        score = round(expected_value * _WEEKLY_COMM_LOW_CERTAINTY * urgency, 2)
        if score <= 0:
            continue

        actions.append(WeeklyAdvisorAction(
            type="comm_low",
            company_id=contact_item.company_id,
            company_name=contact_item.company_name,
            score=score,
            expected_value=round(expected_value, 2),
            reason={
                "days_since_contact": contact_item.days_since_last_contact,
                "last_contact_at": contact_item.last_contact_at,
                "stale_days": _WEEKLY_COMM_LOW_THRESHOLD_DAYS,
            },
            suggested_action="最近の状況確認の連絡をする",
        ))

    actions.sort(key=lambda item: (item.score, item.expected_value, item.company_id), reverse=True)
    return WeeklyAdvisorResponse(actions=actions)


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

    deal_assign = "AND d.assigned_to = :uid" if scope == "mine" else ""
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
