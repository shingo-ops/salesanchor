from __future__ import annotations

"""
受注ごとの売上情報 API（order_financials）。

ADR-021 Phase 2 / Sprint 2: 売上計算 MVP
  - POST   /orders/{order_id}/financial — 新規作成（既存があれば 409）
  - GET    /orders/{order_id}/financial — 取得（不存在 404）
  - PATCH  /orders/{order_id}/financial — 部分更新（自動 updated_at）
  - DELETE /orders/{order_id}/financial — 削除（CASCADE 任せでも済むが明示削除用）
  - GET    /financials/monthly?year=&month=&staff_id= — 月次集計
    （staff_id は Phase 5 で活きる stub。受け取って全件集計する）

権限・テナント:
  - require_permission("orders.view") for GET 系
  - require_permission("orders.update") for write 系
  - Depends(get_current_tenant) で tenant スキーマを切替（既存 orders と同じ経路）

導出列 (cost_total / gross_profit / gross_profit_rate /
operating_profit_with_tax_refund) は Python 側で計算し、レスポンスに同梱する。
詳細は schemas.order_financial.compute_derived を参照。

変更履歴:
  2026-05-11: 初版（ADR-021 Phase 2 / Sprint 2）
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    tenant_table_ref,
)
from app.database import get_db
from app.models import User
from app.schemas.order_financial import (
    MonthlySummaryResponse,
    OrderFinancialCreate,
    OrderFinancialResponse,
    OrderFinancialUpdate,
    SalesListResponse,
    SalesOrderItem,
    compute_derived,
)
from app.services.audit import record_audit_log
from app.services.time import _jst_month_range_utc

router = APIRouter()

# ADR-072 Phase 1: ローカル helper を削除し、`tenant_table_ref` を import 使用。


# DB 列のうち入出力対象のホワイトリスト。動的 UPDATE の組み立ては必ずこの集合
# 越しに通すこと（外部キー以外の任意フィールド書き換えを防ぐ）。
_NUMERIC_INPUT_COLUMNS: tuple[str, ...] = (
    "revenue_amount",
    "purchase_cost",
    "purchase_shipping",
    "paypal_fee",
    "wise_fee",
    "exchange_fee",
    "outsource_fee",
    "packing_fee",
    "ad_cost",
    "return_fee",
    "refund_amount",
    "commission_base_amount",
    "tax_refund",
)
_UPDATABLE_COLUMNS: frozenset[str] = frozenset(_NUMERIC_INPUT_COLUMNS + ("notes",))

_SELECT_COLS = """
    id, order_id, tenant_id,
    revenue_amount, purchase_cost, purchase_shipping,
    paypal_fee, wise_fee, exchange_fee,
    outsource_fee, packing_fee, ad_cost,
    return_fee, refund_amount,
    commission_base_amount, tax_refund,
    notes, created_at, updated_at
"""


async def _ensure_order_exists(db: AsyncSession, order_id: int, tenant_id: int) -> None:
    """受注の存在を確認する (Issue #565: schema prefix 明示)。"""
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    res = await db.execute(
        text(f"SELECT id FROM {orders_t} WHERE id = :id"),
        {"id": order_id},
    )
    if not res.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="注文が見つかりません",
        )


async def _fetch_financial_row(db: AsyncSession, order_id: int, tenant_id: int) -> dict | None:
    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
    res = await db.execute(
        text(f"SELECT {_SELECT_COLS} FROM {order_financials_t} WHERE order_id = :order_id"),
        {"order_id": order_id},
    )
    row = res.mappings().first()
    return dict(row) if row else None


def _build_response(row: dict) -> OrderFinancialResponse:
    """DB row から導出列を計算してレスポンスを組み立てる。"""
    enriched = dict(row)
    enriched.update(compute_derived(enriched))
    return OrderFinancialResponse(**enriched)


@router.post(
    "/orders/{order_id}/financial",
    response_model=OrderFinancialResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("orders.update"))],
)
async def create_order_financial(
    order_id: int,
    data: OrderFinancialCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """受注に売上情報を新規登録する。既存があれば 409。"""
    await _ensure_order_exists(db, order_id, tenant_id)

    existing = await _fetch_financial_row(db, order_id, tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この受注の売上情報は既に登録されています",
        )

    payload = data.model_dump()
    params = {
        "tenant_id": tenant_id,
        "order_id": order_id,
        **{k: payload[k] for k in _NUMERIC_INPUT_COLUMNS},
        "notes": payload.get("notes"),
    }

    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
    insert_sql = text(f"""
        INSERT INTO {order_financials_t} (
            tenant_id, order_id,
            revenue_amount, purchase_cost, purchase_shipping,
            paypal_fee, wise_fee, exchange_fee,
            outsource_fee, packing_fee, ad_cost,
            return_fee, refund_amount,
            commission_base_amount, tax_refund,
            notes
        ) VALUES (
            :tenant_id, :order_id,
            :revenue_amount, :purchase_cost, :purchase_shipping,
            :paypal_fee, :wise_fee, :exchange_fee,
            :outsource_fee, :packing_fee, :ad_cost,
            :return_fee, :refund_amount,
            :commission_base_amount, :tax_refund,
            :notes
        )
        RETURNING {_SELECT_COLS}
    """)
    result = await db.execute(insert_sql, params)
    row = result.mappings().first()

    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="create",
        table_name="order_financials",
        record_id=row["id"],
        new_data=data.model_dump(mode="json"),
    )
    await db.commit()

    return _build_response(dict(row))


@router.get(
    "/orders/{order_id}/financial",
    response_model=OrderFinancialResponse,
    dependencies=[Depends(require_permission("orders.view"))],
)
async def get_order_financial(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """受注の売上情報を取得する。"""
    row = await _fetch_financial_row(db, order_id, tenant_id)
    if not row:
        # 受注の有無は問わず 404（情報量を最小化）。
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="売上情報が見つかりません",
        )
    return _build_response(row)


@router.patch(
    "/orders/{order_id}/financial",
    response_model=OrderFinancialResponse,
    dependencies=[Depends(require_permission("orders.update"))],
)
async def update_order_financial(
    order_id: int,
    data: OrderFinancialUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """受注の売上情報を部分更新する（自動 updated_at）。"""
    old_row = await _fetch_financial_row(db, order_id, tenant_id)
    if not old_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="売上情報が見つかりません",
        )

    update_data = data.model_dump(exclude_unset=True)
    # ホワイトリスト経由でのみ列を許可（FK / id / tenant_id / *_at は変更不可）
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新するフィールドを指定してください",
        )

    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    params = dict(update_data)
    params["order_id"] = order_id

    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
    update_sql = text(f"""
        UPDATE {order_financials_t}
        SET {set_clauses}, updated_at = NOW()
        WHERE order_id = :order_id
        RETURNING {_SELECT_COLS}
    """)
    result = await db.execute(update_sql, params)
    new_row = result.mappings().first()

    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="update",
        table_name="order_financials",
        record_id=old_row["id"],
        old_data=old_row,
        new_data=update_data,
    )
    await db.commit()

    return _build_response(dict(new_row))


@router.delete(
    "/orders/{order_id}/financial",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("orders.update"))],
)
async def delete_order_financial(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """受注の売上情報を削除する（受注本体は残る）。"""
    old_row = await _fetch_financial_row(db, order_id, tenant_id)
    if not old_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="売上情報が見つかりません",
        )

    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
    await db.execute(
        text(f"DELETE FROM {order_financials_t} WHERE order_id = :order_id"),
        {"order_id": order_id},
    )

    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="delete",
        table_name="order_financials",
        record_id=old_row["id"],
        old_data=old_row,
    )
    await db.commit()


@router.get(
    "/financials/monthly",
    response_model=MonthlySummaryResponse,
    dependencies=[Depends(require_permission("orders.view"))],
)
async def get_monthly_summary(
    year: int = Query(..., ge=2000, le=2999, description="集計対象年"),
    month: int = Query(..., ge=1, le=12, description="集計対象月（1-12）"),
    staff_id: int | None = Query(
        default=None,
        ge=1,
        description="担当者ID。Phase 5 で活きる stub（本 Sprint は受け取って全件集計）",
    ),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """月次集計（売上合計 / 仕入原価合計 / 粗利合計 / 件数 / 利益率）を返す。

    ADR-021 第 4 節 AC-004 の最小実装。集計範囲は order_financials.created_at が
    指定月内のレコードのみ。staff_id は Phase 5 で受注 → 担当者紐付けが入った
    時点で WHERE 条件を追加するため、本 Sprint では stub 受け取りのみ。
    """
    # 期間境界（[start, end)）。
    # ADR-021 J2 fix (2026-05-13): JST 暦月境界を UTC 等価で計算する。
    # 例: month=5 → JST 2026-05-01 00:00 〜 6-01 00:00（= UTC 04-30 15:00 〜 05-31 15:00）。
    start, end = _jst_month_range_utc(year, month)

    # 集計クエリ。COALESCE で空期間時の NULL を 0 に丸める。
    # SUM の戻りは数値型 / NULL のいずれか（PostgreSQL）/ 文字列 (SQLite テスト) もあり得るが、
    # _to_decimal で吸収する。
    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
    sql = text(f"""
        SELECT
            COUNT(*) AS cnt,
            COALESCE(SUM(revenue_amount), 0) AS revenue_total,
            COALESCE(SUM(
                purchase_cost + purchase_shipping +
                paypal_fee + wise_fee + exchange_fee +
                outsource_fee + packing_fee + ad_cost +
                return_fee + refund_amount
            ), 0) AS cost_total
        FROM {order_financials_t}
        WHERE created_at >= :start AND created_at < :end
    """)
    res = await db.execute(sql, {"start": start, "end": end})
    row = res.mappings().first()

    cnt = int(row["cnt"]) if row and row["cnt"] is not None else 0
    revenue_total = Decimal(str(row["revenue_total"] if row and row["revenue_total"] is not None else 0))
    cost_total = Decimal(str(row["cost_total"] if row and row["cost_total"] is not None else 0))
    gross_profit_total = revenue_total - cost_total
    if revenue_total == 0:
        rate: Decimal | None = None
    else:
        rate = (gross_profit_total / revenue_total).quantize(Decimal("0.000001"))

    return MonthlySummaryResponse(
        year=year,
        month=month,
        count=cnt,
        revenue_total=revenue_total,
        cost_total=cost_total,
        gross_profit_total=gross_profit_total,
        gross_profit_rate=rate,
        staff_id=staff_id,
    )


# cost_total を構成するカラム（SQL 集計用）。schema の _COST_FIELDS と一致させる。
_COST_SQL_EXPR = (
    "purchase_cost + purchase_shipping + paypal_fee + wise_fee + exchange_fee + "
    "outsource_fee + packing_fee + ad_cost + return_fee + refund_amount"
)


@router.get(
    "/financials/orders",
    response_model=SalesListResponse,
    dependencies=[Depends(require_permission("orders.view"))],
)
async def list_sales_orders(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """売上管理一覧（区切り4）。

    受注ごとに order_financials を LEFT JOIN し、売上 / 原価 / 粗利 / 粗利率を
    1 クエリで返す（一覧の N+1 を避ける）。全体集計も同梱する。
    導出値（gross_profit / gross_profit_rate）は SQL 側で計算する。
    売上情報未登録の受注は revenue 等が NULL のまま行として返す。
    """
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    companies_t = tenant_table_ref(db, tenant_id, "companies")
    contacts_t = tenant_table_ref(db, tenant_id, "contacts")
    financials_t = tenant_table_ref(db, tenant_id, "order_financials")

    result = await db.execute(
        text(f"""
            SELECT
                o.id AS order_id,
                o.order_number,
                o.currency,
                o.created_at,
                c.name AS company_name,
                ct.display_name AS contact_display_name,
                f.revenue_amount AS revenue_amount,
                ({_COST_SQL_EXPR}) AS cost_total
            FROM {orders_t} o
            LEFT JOIN {companies_t} c ON c.id = o.company_id
            LEFT JOIN {contacts_t} ct ON ct.id = o.contact_id
            LEFT JOIN {financials_t} f ON f.order_id = o.id
            ORDER BY o.created_at DESC, o.id DESC
        """),
    )
    rows = result.mappings().all()

    items: list[SalesOrderItem] = []
    revenue_total = Decimal(0)
    cost_total_sum = Decimal(0)
    for row in rows:
        has_financial = row["revenue_amount"] is not None or row["cost_total"] is not None
        if has_financial:
            revenue = Decimal(str(row["revenue_amount"])) if row["revenue_amount"] is not None else Decimal(0)
            cost = Decimal(str(row["cost_total"])) if row["cost_total"] is not None else Decimal(0)
            gross = revenue - cost
            rate = (gross / revenue).quantize(Decimal("0.000001")) if revenue != 0 else None
            revenue_total += revenue
            cost_total_sum += cost
        else:
            revenue = cost = gross = None  # type: ignore[assignment]
            rate = None

        items.append(
            SalesOrderItem(
                order_id=row["order_id"],
                order_number=row["order_number"],
                company_name=row["company_name"],
                contact_display_name=row["contact_display_name"],
                currency=row["currency"],
                created_at=row["created_at"],
                revenue_amount=revenue,
                cost_total=cost,
                gross_profit=gross,
                gross_profit_rate=rate,
            )
        )

    gross_profit_total = revenue_total - cost_total_sum
    total_rate = (
        (gross_profit_total / revenue_total).quantize(Decimal("0.000001"))
        if revenue_total != 0
        else None
    )

    return SalesListResponse(
        items=items,
        count=len(items),
        revenue_total=revenue_total,
        cost_total=cost_total_sum,
        gross_profit_total=gross_profit_total,
        gross_profit_rate=total_rate,
    )
