from __future__ import annotations

"""
注文管理API（CRUD）。

テナントスキーマの orders テーブルに対する操作を提供する。

変更履歴:
  2026-04-17: Phase 2拡張（配送情報、invoice_id、ステータス拡張）
  2026-04-27: Phase 1-B-2 Step 5d — 旧 customer_id 系統撤去
    （resolver / customer 経路廃止、company_id + contact_id を唯一の正に）
  2026-05-11: ADR-021 Phase 1 / Sprint 1 — 受注一覧 MVP
    - GET /orders に search / sort_by / sort_order を追加し、
      companies / contacts への LEFT JOIN で会社名・担当者名を返す
    - GET /orders/group-counts を新設（OrderStatus 全値の件数 + 合計）
    DB スキーマは据え置き、JOIN クエリのみ拡張。multi-tenant は
    既存の require_permission + get_current_tenant + tenant スキーマ
    分離で担保（このモジュールは tenant スキーマ内 SQL のみ叩く）。
  2026-05-13: ADR-021 J1 fix — OrderStatus が 6 値化されたため、
    `?status=` の whitelist 検証を追加（旧 `confirmed` 等の許可外値は 400）。
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    tenant_table_ref,
)
from app.cache import invalidate_dashboard_cache
from app.database import get_db
from app.models import User
from app.schemas.order import (
    OrderCreate,
    OrderGroupCountsResponse,
    OrderListResponse,
    OrderItemCreate,
    OrderItemResponse,
    OrderPaidStatusUpdate,
    OrderResponse,
    OrderStatus,
    OrderUpdate,
)
from app.services.audit import record_audit_log

router = APIRouter()

# ADR-072 Phase 1: ローカル helper を削除し、`tenant_table_ref` を import 使用。


# ADR-021 Sprint 1: ソート許可カラムのホワイトリスト。
# 値はそのまま ORDER BY 句に埋め込まれるため、拡張時は SQL injection 対策
# として必ずこの enum 越しに通すこと（クエリパラメータの直挿入禁止）。
_SORTABLE_COLUMNS = {"created_at", "updated_at", "total_amount", "status"}

# ADR-021 J1 fix (2026-05-13): `?status=` パラメータの許可値ホワイトリスト。
# OrderStatus enum と完全一致。旧 `confirmed` を含む許可外値は 400 で reject する。
_ALLOWED_STATUS_VALUES = frozenset(s.value for s in OrderStatus)


def _validate_status_filter(status_filter: str | None) -> None:
    """`?status=` の値を OrderStatus 6 値のホワイトリストで検証する。

    None または空文字は「指定なし」として素通し。許可外なら 400。
    フロントから誤った値（旧 `confirmed` 含む）が来た場合に
    silently 0 件返すのを避け、エラーを明示する。
    """
    if status_filter is None or status_filter == "":
        return
    if status_filter not in _ALLOWED_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "指定された status は許可されていません。"
                f"許可値: {sorted(_ALLOWED_STATUS_VALUES)}"
            ),
        )

# 検索キーワードのサニタイズ用パターン。
# psycopg のパラメータ化バインディングで SQL injection は防げるが、
# ILIKE の特殊文字（% と _）は意図しない 0/全件マッチを生むのでエスケープする。
# また NUL バイト等の制御文字は弾く（PostgreSQL がエラーを返す前段で除去）。
_LIKE_ESCAPE_RE = re.compile(r"([\\%_])")


def _sanitize_search(keyword: str | None) -> str | None:
    """search キーワードを ILIKE 用にサニタイズする。

    - 前後空白除去
    - 空文字 / None は None を返す（条件未指定として扱う）
    - 制御文字（\\x00 等）は除去
    - LIKE のメタ文字 (%, _, \\) はエスケープ
    """
    if not keyword:
        return None
    cleaned = keyword.strip()
    if not cleaned:
        return None
    # 制御文字除去（NUL や ESC など）
    cleaned = "".join(ch for ch in cleaned if ch.isprintable() or ch == " ")
    if not cleaned:
        return None
    # LIKE メタ文字エスケープ
    return _LIKE_ESCAPE_RE.sub(r"\\\1", cleaned)

_SELECT_COLS = """
    id, company_id, contact_id, deal_id, invoice_id, order_number,
    total_amount, currency, status,
    shipping_carrier, shipping_fee, tracking_number,
    shipped_at, delivered_at, shipping_country,
    paid_at, notes, created_at, updated_at
"""

# company_id / contact_id / deal_id / invoice_id は作成後の変更を禁止（FK整合性保護）
_UPDATABLE_COLUMNS = {
    "order_number", "total_amount", "currency", "status",
    "shipping_carrier", "shipping_fee", "tracking_number",
    "shipping_country", "notes",
}


def _build_orders_filters(
    status_filter: str | None,
    company_id: int | None,
    contact_id: int | None,
    search: str | None,
) -> tuple[list[str], dict]:
    """list_orders / orders_group_counts で共通の WHERE 条件を組み立てる。

    返り値: (conditions, params)
    """
    conditions: list[str] = []
    params: dict = {}
    if status_filter:
        conditions.append("o.status = :status")
        params["status"] = status_filter
    if company_id:
        conditions.append("o.company_id = :company_id")
        params["company_id"] = company_id
    if contact_id:
        conditions.append("o.contact_id = :contact_id")
        params["contact_id"] = contact_id
    sanitized = _sanitize_search(search)
    if sanitized is not None:
        # OR 部分一致: order_number / company.name / contact.display_name
        # ILIKE はテストの SQLite では LIKE に rewrite される（conftest の hook 参照）
        conditions.append(
            "(o.order_number ILIKE :search "
            "OR c.name ILIKE :search "
            "OR ct.display_name ILIKE :search)"
        )
        params["search"] = f"%{sanitized}%"
    return conditions, params


async def _get_order_items(db: AsyncSession, tenant_id: int, order_id: int) -> list[dict]:
    order_items_t = tenant_table_ref(db, tenant_id, "order_items")
    result = await db.execute(
        text(
            f"""
            SELECT
                id, order_id, product_id, product_name, name_en, condition, unit, sku,
                quantity, unit_price, subtotal, weight, hs_code, usd_unit_value,
                exchange_rate_usd, sort_order
            FROM {order_items_t}
            WHERE order_id = :order_id
            ORDER BY sort_order, id
            """
        ),
        {"order_id": order_id},
    )
    return [dict(row) for row in result.mappings().all()]


@router.get("/orders", response_model=list[OrderListResponse],
            dependencies=[Depends(require_permission("orders.view"))])
async def list_orders(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: int | None = Query(default=None),
    contact_id: int | None = Query(default=None),
    search: str | None = Query(
        default=None,
        max_length=200,
        description="order_number / company.name / contact.display_name の OR 部分一致",
    ),
    sort_by: str = Query(
        default="updated_at",
        description="ソート対象カラム（updated_at / created_at / total_amount / status）",
    ),
    sort_order: str = Query(
        default="desc",
        description="ソート方向（asc / desc, 大文字小文字不問）",
    ),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """注文一覧を取得する。

    ADR-021 Sprint 1:
      - search: order_number / company.name / contact.display_name の OR 部分一致
      - sort_by + sort_order: 並び順切替（デフォルト updated_at desc）
      - LEFT JOIN で会社名・担当者名を同梱
    マルチテナント分離は既存通りテナントスキーマ + RLS で担保。
    """
    if sort_by not in _SORTABLE_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"sort_by は {sorted(_SORTABLE_COLUMNS)} のいずれかを指定してください",
        )
    sort_order_lc = (sort_order or "desc").lower()
    if sort_order_lc not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_order は asc / desc を指定してください",
        )
    sort_dir = "DESC" if sort_order_lc == "desc" else "ASC"

    # ADR-021 J1 fix: status の whitelist 検証（旧 `confirmed` は 400）
    _validate_status_filter(status_filter)

    offset = (page - 1) * per_page
    conditions, params = _build_orders_filters(
        status_filter, company_id, contact_id, search,
    )
    params["limit"] = per_page
    params["offset"] = offset

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # ORDER BY のカラム名はホワイトリスト経由のみ。f-string で埋めても安全。
    # NULL の安定ソートのため total_amount のみ NULLS LAST 相当の挙動を
    # 既存挙動（PostgreSQL のデフォルト）に委ねる。
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    companies_t = tenant_table_ref(db, tenant_id, "companies")
    contacts_t = tenant_table_ref(db, tenant_id, "contacts")
    # 区切り4: 一覧「発送先」列用に発送情報（city / country_code）を LEFT JOIN。
    # 受注 1 件 = 発送情報 1 件（order_id UNIQUE）のため JOIN で行数は増えない。
    shipping_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
    result = await db.execute(
        text(f"""
            SELECT
                o.id, o.company_id, o.contact_id, o.deal_id, o.invoice_id,
                o.order_number, o.total_amount, o.currency, o.status,
                o.shipping_carrier, o.shipping_fee, o.tracking_number,
                o.shipped_at, o.delivered_at, o.shipping_country,
                o.paid_at, o.notes, o.created_at, o.updated_at,
                c.name AS company_name,
                ct.display_name AS contact_display_name,
                sd.city AS shipping_city,
                sd.country_code AS shipping_country_code
            FROM {orders_t} o
            LEFT JOIN {companies_t} c ON c.id = o.company_id
            LEFT JOIN {contacts_t} ct ON ct.id = o.contact_id
            LEFT JOIN {shipping_t} sd ON sd.order_id = o.id
            {where_clause}
            ORDER BY o.{sort_by} {sort_dir}, o.id DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.mappings().all()
    return [OrderListResponse(**row) for row in rows]


@router.get(
    "/orders/group-counts",
    response_model=OrderGroupCountsResponse,
    dependencies=[Depends(require_permission("orders.view"))],
)
async def get_orders_group_counts(
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: int | None = Query(default=None),
    contact_id: int | None = Query(default=None),
    search: str | None = Query(
        default=None,
        max_length=200,
        description="一覧と同じ search 条件下での集計",
    ),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """ステータスごとの受注件数 + 合計を返す（ADR-021 Sprint 1）。

    OrderFlow `calculateGroupCounts_` 相当。`?search=` 等の他パラメータも
    一覧と同じ条件で適用するため、画面上の件数バッジが検索結果と連動する。
    OrderStatus enum 全値を 0 埋めで返すため、フロントは undefined を
    気にせずバッジを並べられる。
    """
    # ADR-021 J1 fix: status の whitelist 検証（旧 `confirmed` は 400）
    _validate_status_filter(status_filter)

    conditions, params = _build_orders_filters(
        status_filter, company_id, contact_id, search,
    )
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # JOIN は search のときだけ必要だが、status_filter 単独でも JOIN しておく方が
    # 一覧と同じプランで集計できるので常に LEFT JOIN（テナント内の小規模テーブル想定）。
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    companies_t = tenant_table_ref(db, tenant_id, "companies")
    contacts_t = tenant_table_ref(db, tenant_id, "contacts")
    result = await db.execute(
        text(f"""
            SELECT o.status AS status, COUNT(*) AS cnt
            FROM {orders_t} o
            LEFT JOIN {companies_t} c ON c.id = o.company_id
            LEFT JOIN {contacts_t} ct ON ct.id = o.contact_id
            {where_clause}
            GROUP BY o.status
        """),
        params,
    )
    rows = result.mappings().all()

    # OrderStatus enum 全値で 0 埋め
    counts: dict[str, int] = {s.value: 0 for s in OrderStatus}
    total = 0
    for row in rows:
        key = row["status"]
        cnt = int(row["cnt"]) if row["cnt"] is not None else 0
        # 想定外の status 値（migration 未対応の異常値等）も拾うが、
        # OrderStatus に無い値は別キーとして残す（落とすと total と差が出るため）。
        counts[key] = counts.get(key, 0) + cnt
        total += cnt

    return OrderGroupCountsResponse(counts=counts, total=total)


@router.get("/orders/{order_id}", response_model=OrderResponse,
            dependencies=[Depends(require_permission("orders.view"))])
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """注文詳細を取得する"""
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    result = await db.execute(
        text(f"SELECT {_SELECT_COLS} FROM {orders_t} WHERE id = :id"),
        {"id": order_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")
    return OrderResponse(**row)


@router.get(
    "/orders/{order_id}/items",
    response_model=list[OrderItemResponse],
    dependencies=[Depends(require_permission("orders.view"))],
)
async def list_order_items(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    exists = await db.execute(
        text(f"SELECT id FROM {orders_t} WHERE id = :id"),
        {"id": order_id},
    )
    if exists.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")
    return [OrderItemResponse(**item) for item in await _get_order_items(db, tenant_id, order_id)]


@router.post(
    "/orders/{order_id}/items",
    response_model=list[OrderItemResponse],
    status_code=201,
    dependencies=[Depends(require_permission("orders.update"))],
)
async def create_order_items(
    order_id: int,
    items: list[OrderItemCreate],
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    order_items_t = tenant_table_ref(db, tenant_id, "order_items")
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="items を1件以上指定してください")
    exists = await db.execute(
        text(f"SELECT id FROM {orders_t} WHERE id = :id"),
        {"id": order_id},
    )
    if exists.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")

    for item in items:
        await db.execute(
            text(
                f"""
                INSERT INTO {order_items_t} (
                    tenant_id, order_id, product_id, product_name, name_en, condition, unit,
                    sku, quantity, unit_price, subtotal, weight, hs_code, usd_unit_value,
                    exchange_rate_usd, sort_order
                )
                VALUES (
                    :tenant_id, :order_id, :product_id, :product_name, :name_en, :condition, :unit,
                    :sku, :quantity, :unit_price, :subtotal, :weight, :hs_code, :usd_unit_value,
                    :exchange_rate_usd, :sort_order
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "order_id": order_id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "name_en": item.name_en,
                "condition": item.condition,
                "unit": item.unit,
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
                "weight": item.weight,
                "hs_code": item.hs_code,
                "usd_unit_value": item.usd_unit_value,
                "exchange_rate_usd": item.exchange_rate_usd,
                "sort_order": item.sort_order,
            },
        )

    await db.commit()
    return [OrderItemResponse(**item) for item in await _get_order_items(db, tenant_id, order_id)]


@router.post("/orders", response_model=OrderResponse, status_code=201,
             dependencies=[Depends(require_permission("orders.create"))])
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """注文を登録する"""
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    contacts_t = tenant_table_ref(db, tenant_id, "contacts")
    deals_t = tenant_table_ref(db, tenant_id, "deals")
    # 便1a: deal 必須（背骨）。company は deal から自動導出（S2）
    deal_row = (await db.execute(
        text(f"SELECT company_id FROM {deals_t} WHERE id = :id"), {"id": data.deal_id})).first()
    if not deal_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された商談が存在しません")
    derived_company_id = deal_row[0]
    if derived_company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail="この商談にはまだ会社が登録されていません（先に登録フォームで会社を作成してください）")
    if data.company_id is not None and data.company_id != derived_company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail="company_id が商談の会社と一致しません（省略可・自動導出されます）")
    if data.contact_id is not None:
        contact_row = (await db.execute(
            text(f"SELECT company_id FROM {contacts_t} WHERE id = :id"), {"id": data.contact_id})).first()
        if not contact_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された担当者が存在しません")
        if contact_row[0] != derived_company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された担当者は商談の会社に所属していません")

    # 注文番号の重複チェック
    dup = await db.execute(
        text(f"SELECT id FROM {orders_t} WHERE order_number = :order_number"),
        {"order_number": data.order_number},
    )
    if dup.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="この注文番号は既に使用されています")

    result = await db.execute(
        text(f"""
            INSERT INTO {orders_t} (
                tenant_id, company_id, contact_id, deal_id, invoice_id, order_number,
                total_amount, currency, status,
                shipping_carrier, shipping_fee, shipping_country, notes
            )
            VALUES (
                :tenant_id, :company_id, :contact_id, :deal_id, :invoice_id, :order_number,
                :total_amount, :currency, :status,
                :shipping_carrier, :shipping_fee, :shipping_country, :notes
            )
            RETURNING {_SELECT_COLS}
        """),
        {
            "tenant_id": tenant_id,
            "company_id": derived_company_id,
            "contact_id": data.contact_id,
            "deal_id": data.deal_id,
            "invoice_id": data.invoice_id,
            "order_number": data.order_number,
            "total_amount": data.total_amount,
            "currency": data.currency,
            "status": data.status.value,
            "shipping_carrier": data.shipping_carrier,
            "shipping_fee": data.shipping_fee,
            "shipping_country": data.shipping_country,
            "notes": data.notes,
        },
    )
    row = result.mappings().first()

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="create", table_name="orders", record_id=row["id"],
        new_data=data.model_dump(exclude_none=True, mode="json"),
    )
    await db.commit()
    await invalidate_dashboard_cache(tenant_id)

    return OrderResponse(**row)


@router.patch("/orders/{order_id}", response_model=OrderResponse,
              dependencies=[Depends(require_permission("orders.update"))])
async def update_order(
    order_id: int,
    data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """注文情報を更新する（部分更新）"""
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    old_result = await db.execute(
        text(f"SELECT {_SELECT_COLS} FROM {orders_t} WHERE id = :id"),
        {"id": order_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")

    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")

    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value

    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = order_id

    result = await db.execute(
        text(f"""
            UPDATE {orders_t} SET {set_clauses}, updated_at = NOW()
            WHERE id = :id
            RETURNING {_SELECT_COLS}
        """),
        update_data,
    )
    row = result.mappings().first()

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="update", table_name="orders", record_id=order_id,
        old_data=dict(old_row), new_data=update_data,
    )
    await db.commit()
    await invalidate_dashboard_cache(tenant_id)

    return OrderResponse(**row)


@router.patch("/orders/{order_id}/paid", response_model=OrderResponse,
              dependencies=[Depends(require_permission("orders.update"))])
async def set_order_paid(
    order_id: int,
    data: OrderPaidStatusUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """受注の支払済フラグ（paid_at）を切り替える（区切り4）。

    paid=true で paid_at=NOW()、paid=false で paid_at=NULL に戻す。
    受注ステータスフローの「支払済にする」ボタンから呼ばれる。
    将来は発注書送付フローと連動予定（現状は手動フラグ）。
    """
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    old_result = await db.execute(
        text(f"SELECT {_SELECT_COLS} FROM {orders_t} WHERE id = :id"),
        {"id": order_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")

    if data.paid:
        set_clause = "paid_at = NOW()"
    else:
        set_clause = "paid_at = NULL"

    result = await db.execute(
        text(f"""
            UPDATE {orders_t} SET {set_clause}, updated_at = NOW()
            WHERE id = :id
            RETURNING {_SELECT_COLS}
        """),
        {"id": order_id},
    )
    row = result.mappings().first()

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="update", table_name="orders", record_id=order_id,
        old_data=dict(old_row), new_data={"paid": data.paid},
    )
    await db.commit()
    await invalidate_dashboard_cache(tenant_id)

    return OrderResponse(**row)


@router.delete("/orders/{order_id}", status_code=204,
               dependencies=[Depends(require_permission("orders.delete"))])
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """注文を削除する"""
    orders_t = tenant_table_ref(db, tenant_id, "orders")
    old_result = await db.execute(
        text(f"SELECT {_SELECT_COLS} FROM {orders_t} WHERE id = :id"),
        {"id": order_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")

    await db.execute(text(f"DELETE FROM {orders_t} WHERE id = :id"), {"id": order_id})

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="delete", table_name="orders", record_id=order_id,
        old_data=dict(old_row),
    )
    await db.commit()
    await invalidate_dashboard_cache(tenant_id)
