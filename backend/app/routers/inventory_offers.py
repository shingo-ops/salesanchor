"""中央 admin 用 public.inventory CRUD ルーター (spec.md v1.3 F11 / AC11.5)。

API:
  GET    /api/v1/super-admin/inventory-offers           list (filter + paginate)
  POST   /api/v1/super-admin/inventory-offers           create (409 on UNIQUE 衝突)
  PATCH  /api/v1/super-admin/inventory-offers/{id}      update (quantity/unit_price/status/notes/expires_at)
  DELETE /api/v1/super-admin/inventory-offers/{id}      hard delete

AC11.5 の admin 編集を満たす最小 CRUD。UPSERT は別経路で処理する設計のため
（2026-10-02 削除済み: 旧 F6 承認フロー `apply_inbound_items`）、
本ルーターでは INSERT は UNIQUE 衝突時 409 を返し、admin は明示的に PATCH を選ぶ。
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission, require_super_admin
from app.database import get_db
from app.schemas.inventory_offers import (
    InventoryListResponse,
    InventoryOfferCreate,
    InventoryOfferListResponse,
    InventoryOfferResponse,
    InventoryOfferUpdate,
    InventoryRow,
    InventorySupplierFacet,
)
from app.services.inventory_axes import (
    build_condition_filter_clause,
    log_axis_isolation,
    project_inventory_axes,
    resolve_condition_view,
)
from app.services.tcg_distribution_svc import (
    _age_window,
    _max_age_hours,
    distribution_rows_sql,
    load_distribution_settings,
)

router = APIRouter()
logger = logging.getLogger(__name__)


_BASE_SELECT = """
    SELECT i.id, i.supplier_id, i.product_id, i.raw_condition, i.quantity,
           i.unit_price, i.unit, i.offer_type, i.ship_timing,
           i.seal, i.search_cond, i.grade, i.damage,
           i.status, i.notes_ja, i.notes_en,
           i.offered_at, i.expires_at, i.source,
           i.created_at, i.updated_at,
           s.name AS supplier_name,
           p.product_code AS product_code,
           p.name AS product_name,
           p.name_en AS name_en,
           p.category AS category,
           p.mark AS mark,
           p.tcg_type AS tcg_type
    FROM public.inventory i
    LEFT JOIN public.suppliers s ON s.id = i.supplier_id
    LEFT JOIN public.products  p ON p.id = i.product_id
"""

_UPDATABLE_COLS = {
    "quantity",
    "unit_price",
    "unit",
    # ADR-093 Phase 3: 区分/発送日も admin が編集可（UNIQUE キー要素のため衝突時は 409）
    "offer_type",
    "ship_timing",
    "status",
    "notes_ja",
    "notes_en",
    "expires_at",
}


async def _load_offer(db: AsyncSession, offer_id: int) -> dict | None:
    row = (
        await db.execute(
            text(f"{_BASE_SELECT} WHERE i.id = :id"),
            {"id": offer_id},
        )
    ).mappings().first()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# 最終ユーザー向け在庫表ビュー GET /inventory（ADR-093 Phase 2）
# 各クライアントの営業担当ロール以上（products.view）が閲覧。読み取り専用。
# ---------------------------------------------------------------------------

# 区分（offer_type）と LINE 解析の status の対応。1つの定数で持ち、絞り込みは逆引きに使う。
OFFER_TYPE_TO_STATUS: dict[str, str] = {"in_stock": "In Stock", "pre_order": "Pre-order"}
_STATUS_TO_OFFER_TYPE = {status_value: offer for offer, status_value in OFFER_TYPE_TO_STATUS.items()}


def round_half_up(value: object) -> int:
    """SQL の ROUND(numeric) と同じ丸め（0.5 は0から遠い側）。Python の round は銀行丸めなので使わない。"""
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def status_to_offer_type(status_value: str | None) -> str | None:
    """LINE 解析の status を区分に写す。対応に無い status は None。"""
    return _STATUS_TO_OFFER_TYPE.get(status_value or "")


# 在庫表の全列ソート用ホワイトリスト（sort キー → 配信行の列。SQLi 防止）。d は distribution_rows_sql の副問い合わせ。
_SORT_COLUMNS = {
    "name": "d.japanese_title",
    "category": "d.category",
    "mark": "NULLIF(d.mark, '')",
    "condition": "d.condition",
    "unit": "NULLIF(d.unit_canonical, '')",
    "offer_type": "d.status",
    "quantity": "d.qty_num",
    "unit_price": "d.price_num",
    "supplier": "d.provider",
    "offered_at": "d.posted_ts",
    "release_date": "NULLIF(d.release_date, '')",
}


def _split_csv(raw: str | None) -> list[str]:
    return [tok.strip() for tok in (raw or "").split(",") if tok.strip()]


def _project_inventory_rows(raw_rows: list[dict[str, object]]) -> list[InventoryRow]:
    projected: list[InventoryRow] = []
    for row in raw_rows:
        quantity = row.get("qty_num")
        status_value = row.get("status") or None
        projected.append(
            InventoryRow(
                id=str(row["row_key"]),
                product_id=int(row["product_id"]),
                product_name=row.get("japanese_title") or None,
                name_en=row.get("english_title") or None,
                category=row.get("category"),
                mark=row.get("mark") or None,
                condition=str(row.get("condition") or ""),
                unit=row.get("unit_canonical") or None,
                offer_type=status_to_offer_type(status_value),
                ship_timing=None,
                supplier_id=int(row["supplier_id"]),
                supplier_name=row.get("provider") or None,
                unit_price=round_half_up(row["price_num"] or 0),
                quantity=None if quantity is None else round_half_up(quantity),
                tcg_type=row.get("tcg_type"),
                offered_at=row["posted_ts"],
                posted_at=row["posted_ts"],
                release_date=row.get("release_date") or None,
                note_ja=row.get("note_ja") or None,
                ship_ja=row.get("ship_ja") or None,
                status=status_value,
                merged_count=int(row.get("merged_count") or 1),
            )
        )
    return projected


def _build_view_filters(
    *, q, tcg_type, category, offer_type, hide_supplier_ids, hide_categories, condition, condition_in,
    unit_in, offer_type_in, qty_min, qty_max, price_min, price_max,
) -> tuple[list[str], dict]:
    """問い合わせ値を、配信行の列（d.*）への WHERE 条件と bind に変える。値は必ず bind で渡す。"""
    conditions: list[str] = []
    params: dict = {}
    if tcg_type:
        conditions.append("d.tcg_type = :tcg_type")
        params["tcg_type"] = tcg_type
    if category:
        conditions.append("d.category = :category")
        params["category"] = category
    if q:
        conditions.append(
            "(d.provider ILIKE :q OR d.japanese_title ILIKE :q OR d.english_title ILIKE :q "
            "OR d.product_id::text ILIKE :q OR d.category ILIKE :q OR d.mark ILIKE :q)"
        )
        params["q"] = f"%{q}%"
    # 「仕入元 非表示」（CSV → NOT IN、整数のみ採用で SQLi 防止）。supplier_id は public.suppliers の id。
    hidden_ids = [int(tok) for tok in _split_csv(hide_supplier_ids) if tok.lstrip("-").isdigit()]
    if hidden_ids:
        placeholders = ", ".join(f":hsid{i}" for i in range(len(hidden_ids)))
        conditions.append(f"d.supplier_id NOT IN ({placeholders})")
        params.update({f"hsid{i}": sid for i, sid in enumerate(hidden_ids)})
    hidden_cats = _split_csv(hide_categories)
    if hidden_cats:
        placeholders = ", ".join(f":hcat{i}" for i in range(len(hidden_cats)))
        conditions.append(f"d.category NOT IN ({placeholders})")
        params.update({f"hcat{i}": c for i, c in enumerate(hidden_cats)})
    requested_conditions = [c.strip() for c in [condition or "", *_split_csv(condition_in)] if c.strip()]
    if requested_conditions:
        placeholders = ", ".join(f":cond{i}" for i in range(len(requested_conditions)))
        conditions.append(f"d.condition IN ({placeholders})")
        params.update({f"cond{i}": c for i, c in enumerate(requested_conditions)})
    unit_list = _split_csv(unit_in)
    if unit_list:
        placeholders = ", ".join(f":unit{i}" for i in range(len(unit_list)))
        conditions.append(f"d.unit_canonical IN ({placeholders})")
        params.update({f"unit{i}": u for i, u in enumerate(unit_list)})
    for index, requested in enumerate([[offer_type] if offer_type else [], _split_csv(offer_type_in)]):
        if not requested:
            continue
        statuses = [OFFER_TYPE_TO_STATUS[o] for o in requested if o in OFFER_TYPE_TO_STATUS]
        if not statuses:  # 対応に無い区分だけが指定された: 出す行は無い
            conditions.append("FALSE")
            continue
        placeholders = ", ".join(f":ot{index}_{i}" for i in range(len(statuses)))
        conditions.append(f"d.status IN ({placeholders})")
        params.update({f"ot{index}_{i}": st for i, st in enumerate(statuses)})
    # 数量・単価の範囲は、まとめた後の値で判定する。数量が空の行は、範囲指定があれば出さない。
    for column, name, value, op in (
        ("d.qty_num", "qty_min", qty_min, ">="), ("d.qty_num", "qty_max", qty_max, "<="),
        ("d.price_num", "price_min", price_min, ">="), ("d.price_num", "price_max", price_max, "<="),
    ):
        if value is not None:
            conditions.append(f"{column} {op} CAST(:{name} AS integer)")
            params[name] = value
    return conditions, params


@router.get(
    "/inventory",
    response_model=InventoryListResponse,
    dependencies=[Depends(require_permission("products.view"))],
)
async def list_inventory_view(
    q: str | None = Query(default=None, max_length=255, description="商品名/英名/コード/カテゴリ/マーク/仕入元の部分一致"),
    tcg_type: str | None = Query(default=None, max_length=50, description="TCG種別 (public.products.tcg_type)"),
    category: str | None = Query(default=None, max_length=100, description="カテゴリー絞り込み (public.products.category)"),
    offer_type: str | None = Query(default=None, pattern="^(in_stock|pre_order)$", description="区分: in_stock(在庫) / pre_order(予約)"),
    hide_supplier_ids: str | None = Query(default=None, max_length=2000, description="非表示にする仕入元IDのCSV（ユーザー別フィルタ用）"),
    hide_categories: str | None = Query(default=None, max_length=2000, description="非表示にするカテゴリーのCSV（ユーザー別フィルタ用）"),
    # 状態/形態/区分の複数選択（CSV → IN）。未指定なら絞り込まない。
    condition: str | None = Query(default=None, max_length=2000, description="表示する状態(condition)の単一指定"),
    condition_in: str | None = Query(default=None, max_length=2000, description="表示する状態(condition)のCSV"),
    unit_in: str | None = Query(default=None, max_length=2000, description="表示する形態(unit)のCSV"),
    offer_type_in: str | None = Query(default=None, max_length=100, description="表示する区分(offer_type)のCSV"),
    qty_min: int | None = Query(default=None, ge=0, description="数量の下限（以上）"),
    qty_max: int | None = Query(default=None, ge=0, description="数量の上限（以下）"),
    price_min: int | None = Query(default=None, ge=0, description="単価の下限（以上）"),
    price_max: int | None = Query(default=None, ge=0, description="単価の上限（以下）"),
    merge_same_post: bool = Query(default=True, description="同じ投稿のランク違いを1行にまとめる"),
    sort: str = Query(
        default="release_date",
        pattern="^(name|category|mark|condition|unit|offer_type|quantity|unit_price|supplier|offered_at|release_date)$",
        description="ソート列。全列対応（ADR-093 在庫表改修）",
    ),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """在庫表（最終ユーザー向け）。LINE 解析の配信行（GAS 在庫一覧と同じ行）を返す。

    行の定義は tcg_distribution_svc.distribution_rows_sql の1か所だけ（ここに配信の WHERE は書かない）。
    - 権限: products.view（各クライアントの営業担当ロール以上）。読み取り専用。
    - max_age_hours が未設定または不正なら GAS と同じく配信しない（items 空・window_hours null）。
    - merge_same_post=true で、同じ投稿のランク違いの行を1行にまとめる（数量は合計・単価は最大）。
    """
    settings = await load_distribution_settings(db)
    max_age_hours = _max_age_hours(settings)
    if max_age_hours is None:
        return InventoryListResponse(items=[], total=0, page=page, per_page=per_page, window_hours=None)
    include_flag_single = settings.get("include_flag_single", "false").lower() == "true"
    age_condition, age_params = _age_window(max_age_hours)

    def rows_sql(merge: bool) -> str:
        return distribution_rows_sql(
            include_flag_single=include_flag_single, age_condition=age_condition, merge_same_post=merge,
        )

    conditions, filter_params = _build_view_filters(
        q=q, tcg_type=tcg_type, category=category, offer_type=offer_type,
        hide_supplier_ids=hide_supplier_ids, hide_categories=hide_categories, condition=condition,
        condition_in=condition_in, unit_in=unit_in, offer_type_in=offer_type_in,
        qty_min=qty_min, qty_max=qty_max, price_min=price_min, price_max=price_max,
    )
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params = {**age_params, **filter_params}
    order_dir = "ASC" if order == "asc" else "DESC"
    sort_col = _SORT_COLUMNS.get(sort, "d.japanese_title")
    inner = rows_sql(merge_same_post)

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM ({inner}) d {where}"), params)
    ).scalar_one()
    result = await db.execute(
        text(
            f"SELECT d.* FROM ({inner}) d {where} "
            f"ORDER BY {sort_col} {order_dir} NULLS LAST, d.sort_ord ASC "
            "LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": per_page, "offset": (page - 1) * per_page},
    )
    items = _project_inventory_rows([dict(r) for r in result.mappings().all()])

    # フィルタ UI の候補は、まとめなし・絞り込みなしの配信行から作る（非表示にした候補も残る）。
    facet_rows = (
        await db.execute(
            text(
                "SELECT DISTINCT d.supplier_id, d.provider, d.category, d.condition, d.unit_canonical "
                f"FROM ({rows_sql(False)}) d"
            ),
            age_params,
        )
    ).mappings().all()
    supplier_names = {r["supplier_id"]: r["provider"] or None for r in facet_rows}
    suppliers = [
        InventorySupplierFacet(id=sid, name=name)
        for sid, name in sorted(supplier_names.items(), key=lambda kv: (kv[1] is None, kv[1] or ""))
    ]
    categories = sorted({r["category"] for r in facet_rows if r["category"]})
    condition_facet = sorted({r["condition"] for r in facet_rows if r["condition"]})
    unit_facet = sorted({r["unit_canonical"] for r in facet_rows if r["unit_canonical"]})
    return InventoryListResponse(
        items=items,
        total=int(total or 0),
        page=page,
        per_page=per_page,
        suppliers=suppliers,
        categories=categories,
        conditions=condition_facet,
        units=unit_facet,
        window_hours=max_age_hours,
    )


@router.get(
    "/super-admin/inventory-offers",
    response_model=InventoryOfferListResponse,
    dependencies=[Depends(require_super_admin)],
)
async def list_offers(
    supplier_id: int | None = Query(default=None, gt=0),
    product_id: int | None = Query(default=None, gt=0),
    condition: str | None = Query(default=None, max_length=50),
    status_filter: str | None = Query(default=None, alias="status", max_length=20),
    q: str | None = Query(default=None, max_length=255, description="supplier_name / product_name / product_code 部分一致"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """仕入元現在オファー一覧 (AC11.5)。"""
    offset = (page - 1) * per_page
    conditions: list[str] = []
    params: dict = {"limit": per_page, "offset": offset}

    if supplier_id is not None:
        conditions.append("i.supplier_id = :supplier_id")
        params["supplier_id"] = supplier_id
    if product_id is not None:
        conditions.append("i.product_id = :product_id")
        params["product_id"] = product_id
    if condition:
        condition_clause, condition_params = build_condition_filter_clause([condition])
        if condition_clause is not None:
            conditions.append(condition_clause)
            params.update(condition_params)
    if status_filter:
        conditions.append("i.status = :status_filter")
        params["status_filter"] = status_filter
    if q:
        conditions.append(
            "(s.name ILIKE :q OR p.name ILIKE :q OR p.id::text ILIKE :q)"
        )
        params["q"] = f"%{q}%"

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total_row = await db.execute(
        text(f"SELECT COUNT(*) AS c FROM public.inventory i "
             f"LEFT JOIN public.suppliers s ON s.id = i.supplier_id "
             f"LEFT JOIN public.products  p ON p.id = i.product_id {where}"),
        params,
    )
    total = int(total_row.scalar_one() or 0)

    result = await db.execute(
        text(
            f"{_BASE_SELECT} {where} "
            "ORDER BY i.offered_at DESC, i.id DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    items = [
        InventoryOfferResponse(
            **{
                **dict(r),
                "condition": str(resolve_condition_view(r) or r.get("raw_condition") or ""),
            }
        )
        for r in result.mappings().all()
    ]
    return InventoryOfferListResponse(
        items=items, total=total, page=page, per_page=per_page
    )


@router.post(
    "/super-admin/inventory-offers",
    response_model=InventoryOfferResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_super_admin)],
)
async def create_offer(
    payload: InventoryOfferCreate,
    db: AsyncSession = Depends(get_db),
):
    """新規オファーを admin が手動追加 (AC11.5)。"""
    projection = project_inventory_axes(payload.condition, payload.unit)
    log_axis_isolation(
        logger_=logger,
        condition=payload.condition,
        unit=payload.unit,
        context="inventory_offers.create_offer",
        projection=projection,
    )
    try:
        new_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO public.inventory
                        (supplier_id, product_id, raw_condition, quantity, unit_price, unit,
                         seal, search_cond, grade, damage,
                         offer_type, ship_timing,
                         status, notes_ja, notes_en, expires_at, source)
                    VALUES (:supplier_id, :product_id, :raw_condition, :quantity, :unit_price, :unit,
                            :seal, :search_cond, :grade, :damage,
                            :offer_type, :ship_timing,
                            :status, :notes_ja, :notes_en, :expires_at, :source)
                    RETURNING id
                    """
                ),
                {
                    **payload.model_dump(exclude={"condition"}),
                    "raw_condition": payload.condition,
                    "seal": projection.seal,
                    "search_cond": projection.search_cond,
                    "grade": projection.grade,
                    "damage": projection.damage if projection.damage is not None else False,
                },
            )
        ).scalar_one()
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "同じ 仕入元×商品×状態×形態×区分×発送日 のオファーが既に存在します。"
                "PATCH で更新するか、いずれかの軸を変えて作成してください。"
            ),
        ) from e

    offer = await _load_offer(db, int(new_id))
    if offer is None:
        raise HTTPException(status_code=500, detail="INSERT 直後の取得に失敗しました")
    offer["condition"] = str(resolve_condition_view(offer) or offer.get("raw_condition") or "")
    return InventoryOfferResponse(**offer)


@router.patch(
    "/super-admin/inventory-offers/{offer_id}",
    response_model=InventoryOfferResponse,
    dependencies=[Depends(require_super_admin)],
)
async def update_offer(
    offer_id: int,
    payload: InventoryOfferUpdate,
    db: AsyncSession = Depends(get_db),
):
    """admin が在庫数 / 単価 / 形態 / 区分 / 発送日 / status / メモ / 期限を編集 (AC11.5)。

    supplier_id / product_id / condition は変更不可。unit / offer_type / ship_timing は
    UNIQUE キー要素のため、変更により他オファーと衝突する場合は 409 を返す（ADR-093 Phase 3）。
    """
    update_data = payload.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLS}
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新するフィールドを指定してください",
        )

    set_clause = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = offer_id

    try:
        result = await db.execute(
            text(f"UPDATE public.inventory SET {set_clause} WHERE id = :id RETURNING id"),
            update_data,
        )
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "形態 / 区分 / 発送日 の変更で同一キー（仕入元×商品×状態×形態×区分×発送日）の"
                "オファーと衝突しました。既存行を確認してください。"
            ),
        ) from e
    if result.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたオファーが見つかりません",
        )

    offer = await _load_offer(db, offer_id)
    if offer is None:
        raise HTTPException(status_code=500, detail="UPDATE 直後の取得に失敗しました")

    source_condition = resolve_condition_view(offer) or offer.get("raw_condition")
    projection = project_inventory_axes(source_condition, offer.get("unit"))
    log_axis_isolation(
        logger_=logger,
        condition=source_condition,
        unit=offer.get("unit"),
        context="inventory_offers.update_offer",
        projection=projection,
    )
    await db.execute(
        text(
            """
            UPDATE public.inventory
               SET seal = :seal,
                   search_cond = :search_cond,
                   grade = :grade,
                   damage = :damage,
                   updated_at = NOW()
             WHERE id = :id
            """
        ),
        {
            "id": offer_id,
            "seal": projection.seal,
            "search_cond": projection.search_cond,
            "grade": projection.grade,
            "damage": projection.damage if projection.damage is not None else False,
        },
    )
    await db.commit()

    offer = await _load_offer(db, offer_id)
    if offer is None:
        raise HTTPException(status_code=500, detail="UPDATE 直後の取得に失敗しました")
    offer["condition"] = str(resolve_condition_view(offer) or offer.get("raw_condition") or "")
    return InventoryOfferResponse(**offer)


@router.delete(
    "/super-admin/inventory-offers/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_super_admin)],
)
async def delete_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
):
    """オファーを物理削除 (AC11.5)。再投入は F6 承認 or POST で。"""
    result = await db.execute(
        text("DELETE FROM public.inventory WHERE id = :id RETURNING id"),
        {"id": offer_id},
    )
    if result.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたオファーが見つかりません",
        )
    await db.commit()
