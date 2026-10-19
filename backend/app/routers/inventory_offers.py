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
import unicodedata
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
    InventoryRawTextsResponse,
    InventoryRow,
    InventorySupplierFacet,
)
from app.services import tcg_distribution_svc as _distribution
from app.services.inventory_axes import (
    build_condition_filter_clause,
    log_axis_isolation,
    project_inventory_axes,
    resolve_condition_view,
)
from app.services.tcg_distribution_svc import (
    _STATUS_TO_OFFER_TYPE,  # noqa: F401  テストが io._STATUS_TO_OFFER_TYPE として読めるように残す
    FRESH_WINDOW_HOURS,
    OFFER_TYPE_TO_STATUS,
    _age_window,
    _max_age_hours,
    distribution_final_select_plain,
    distribution_rows_parts,
    load_distribution_settings,
    status_to_offer_type,
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
           tm.code AS work_code
    FROM public.inventory i
    LEFT JOIN public.suppliers s ON s.id = i.supplier_id
    LEFT JOIN public.products  p ON p.id = i.product_id
    LEFT JOIN public.type_master tm ON tm.id = p.work_id
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


def round_half_up(value: object) -> int:
    """SQL の ROUND(numeric) と同じ丸め（0.5 は0から遠い側）。Python の round は銀行丸めなので使わない。"""
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


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


# 検索の語数の上限（GAS の在庫一覧と同じ「空白区切りAND」。多すぎる語で SQL を膨らませない）
_SEARCH_MAX_TERMS = 10
# ひらがな U+3041〜U+3096 → カタカナ U+30A1〜U+30F6（86文字ずつ）。SQL の translate() に渡す。
_KANA_FROM = "".join(chr(c) for c in range(0x3041, 0x3097))
_KANA_TO = "".join(chr(c + 0x60) for c in range(0x3041, 0x3097))


def normalize_search_text(s: str) -> str:
    """検索語の正規化。NFKC → 小文字 → ひらがなをカタカナへ（GAS 在庫一覧の normalizeForSearch と同じ）。

    SQL 側の translate(lower(normalize(.., NFKC)), :kana_from, :kana_to) と同じ結果になること。
    共通テストベクタ: frontend/src/features/inventory/searchNormalize.vectors.json（変えるときは両方のテストを触る）。
    """
    return unicodedata.normalize("NFKC", s).lower().translate(
        {c: c + 0x60 for c in range(0x3041, 0x3097)}
    )


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
                work_code=row.get("work_code"),
                offered_at=row["posted_ts"],
                posted_at=row["posted_ts"],
                release_date=row.get("release_date") or None,
                note_ja=row.get("note_ja") or None,
                ship_ja=row.get("ship_ja") or None,
                status=status_value,
                merged_count=int(row.get("merged_count") or 1),
                badge_cheapest=bool(row.get("badge_cheapest")),
                badge_most_stock=bool(row.get("badge_most_stock")),
                extraction_item_ids=[str(v) for v in (row.get("extraction_item_ids") or [])],
            )
        )
    return projected


def _build_view_filters(
    *, q, work_code, category, offer_type, hide_supplier_ids, hide_categories, condition, condition_in,
    unit_in, offer_type_in, qty_min, qty_max, price_min, price_max,
    supplier_ids: str | None = None,
) -> tuple[list[str], dict]:
    """問い合わせ値を、配信行の列（d.*）への WHERE 条件と bind に変える。値は必ず bind で渡す。"""
    conditions: list[str] = []
    params: dict = {}
    if work_code:
        conditions.append("d.work_code = :work_code")
        params["work_code"] = work_code
    if category:
        conditions.append("d.category = :category")
        params["category"] = category
    # 語ごとに「日本語名・英語名・型番(mark)・検索ワード」のどれかに含まれる、を AND（GAS と同じ正規化）
    terms = [t for t in normalize_search_text(q or "").split() if t][:_SEARCH_MAX_TERMS]
    if terms:
        params["kana_from"] = _KANA_FROM
        params["kana_to"] = _KANA_TO
        haystack = (
            "translate(lower(normalize(concat_ws(E'\\n', d.japanese_title, d.english_title, d.mark, "
            "d.search_keywords), NFKC)), CAST(:kana_from AS text), CAST(:kana_to AS text))"
        )
        for i, term in enumerate(terms):
            conditions.append(f"strpos({haystack}, CAST(:qt{i} AS text)) > 0")
            params[f"qt{i}"] = term
    # 「提供者（選んだ仕入元だけ）」。整数のみ採用、整数が1つも無ければ絞らない。
    shown_ids = [int(tok) for tok in _split_csv(supplier_ids) if tok.lstrip("-").isdigit()]
    if shown_ids:
        placeholders = ", ".join(f":sid{i}" for i in range(len(shown_ids)))
        conditions.append(f"d.supplier_id IN ({placeholders})")
        params.update({f"sid{i}": sid for i, sid in enumerate(shown_ids)})
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


def _build_view_order_by(*, sort_col: str, order_dir: str) -> str:
    """GET /inventory の ORDER BY（ADR-1014 改訂 2026-10-18）。sort_col / order_dir は信頼できる断片のみ。

    まとまり（商品）の順: 発売日（空欄は末尾）→ 英語名 → 日本語名 → product_id。発売日の向きは release_date を選んだときだけ order_dir。ほかの並び替えでは既定と同じ DESC（ADR-1014 改訂 2026-10-19）。
    まとまりの中: 状態のまとまり（cond_block = 同じ商品・同じ状態の最小 sort_ord。価値順 ADR-1023）→ 選んだ列（release_date なら sort_ord のみ）。
    価格・数量などの並び替えは同じ商品・同じ状態の中だけで効く（ADR-1014 改訂 2026-10-19（5））。タイトル列（name）は変更前の式のまま。
    """
    if sort_col == _SORT_COLUMNS["name"]:
        return f"ORDER BY d.english_title {order_dir}, d.japanese_title {order_dir} NULLS LAST, d.sort_ord ASC"
    group_dir = order_dir if sort_col == _SORT_COLUMNS["release_date"] else "DESC"
    group = (
        f"NULLIF(d.release_date, '') {group_dir} NULLS LAST, d.english_title ASC, "
        "d.japanese_title ASC NULLS LAST, d.product_id ASC"
    )
    if sort_col == _SORT_COLUMNS["release_date"]:
        return f"ORDER BY {group}, d.sort_ord ASC"
    return f"ORDER BY {group}, d.cond_block ASC, {sort_col} {order_dir} NULLS LAST, d.sort_ord ASC"


def _build_inventory_view_sql(
    *, head: str, final_main: str, merge: bool, where: str, sort_col: str, order_dir: str,
    expiry: bool = False,
) -> str:
    """GET /inventory の1文。dist_base（配信行の重い計算）を1回だけ計算し、件数・ページ・絞り込み候補を UNION ALL で返す。

    head は distribution_rows_parts の WITH 句（そのまま使う）。where / sort_col / order_dir は
    _build_view_filters と _SORT_COLUMNS が作った信頼できる断片で、利用者入力の値は bind のみ。
    列並び（3枝共通）: __kind, __total, <配信行+work_code+category+cond_block の全列>, __ord, __badge_cheapest, __badge_most_stock, __expiry_s, __f_* の5列。
    __badge_* は同じ product_id・status・condition のまとまり（絞り込み後・ページ前）で最安／在庫最多か（ADR-1014 改訂 2026-10-19（3））。
    expiry が真のとき __expiry_s（total 枝のみ）は、まとめ前・絞り込み前の行が次に時間の枠から外れるまでの秒数（:expiry_hours が必要）。
    """
    order_by = _build_view_order_by(sort_col=sort_col, order_dir=order_dir)
    join = "LEFT JOIN public.products pp ON pp.id = x.product_id LEFT JOIN public.type_master tm ON tm.id = pp.work_id"
    ctes = [f"rows_main AS ({final_main})"]
    if merge:
        ctes.append(f"rows_plain AS ({distribution_final_select_plain()})")
    ctes.append(
        "rows_x AS (SELECT x.*, tm.code AS work_code, pp.category AS category, "
        f"MIN(x.sort_ord) OVER (PARTITION BY x.product_id, x.condition) AS cond_block FROM rows_main x {join})"
    )
    if merge:
        ctes.append(f"rows_xp AS (SELECT x.*, tm.code AS work_code, pp.category AS category FROM rows_plain x {join})")
    facet_src = "rows_xp" if merge else "rows_x"  # merge=False は rows_main == rows_plain なので共用
    ctes.append(f"rows_f AS (SELECT * FROM rows_x d {where})")
    # 型は実物の列から: LEFT JOIN ON FALSE で rows_x と同じ型の NULL 1行を得る
    ctes.append("rows_nx AS (SELECT o.* FROM (SELECT 1) one LEFT JOIN rows_x o ON FALSE)")
    badge_cheapest = (
        "(d.product_id IS NOT NULL AND d.price_num IS NOT NULL "
        "AND COUNT(d.price_num) OVER (PARTITION BY d.product_id, d.status, d.condition) >= 2 "
        "AND MIN(ROUND(d.price_num)) OVER (PARTITION BY d.product_id, d.status, d.condition) < MAX(ROUND(d.price_num)) OVER (PARTITION BY d.product_id, d.status, d.condition) "
        "AND ROUND(d.price_num) = MIN(ROUND(d.price_num)) OVER (PARTITION BY d.product_id, d.status, d.condition)) AS __badge_cheapest"
    )
    badge_most_stock = (
        "(d.product_id IS NOT NULL AND d.qty_num IS NOT NULL "
        "AND COUNT(d.qty_num) OVER (PARTITION BY d.product_id, d.status, d.condition) >= 2 "
        "AND MIN(ROUND(d.qty_num)) OVER (PARTITION BY d.product_id, d.status, d.condition) < MAX(ROUND(d.qty_num)) OVER (PARTITION BY d.product_id, d.status, d.condition) "
        "AND ROUND(d.qty_num) = MAX(ROUND(d.qty_num)) OVER (PARTITION BY d.product_id, d.status, d.condition)) AS __badge_most_stock"
    )
    ctes.append(
        f"rows_pg AS (SELECT d.*, ROW_NUMBER() OVER ({order_by}) AS __ord, {badge_cheapest}, {badge_most_stock} "
        f"FROM rows_f d {order_by} LIMIT :limit OFFSET :offset)"
    )
    expiry_expr = (
        "(SELECT CEIL(EXTRACT(EPOCH FROM (MIN(d.posted_ts) + make_interval(hours => :expiry_hours) - NOW())))::bigint "
        f"FROM {facet_src} d)"
        if expiry else "NULL::bigint"
    )
    q_total = (
        "SELECT 'total'::text AS __kind, (SELECT COUNT(*) FROM rows_f)::bigint AS __total, nx.*, "
        f"NULL::bigint AS __ord, NULL::boolean AS __badge_cheapest, NULL::boolean AS __badge_most_stock, "
        f"{expiry_expr} AS __expiry_s, nx.supplier_id AS __f_supplier_id, nx.provider AS __f_provider, "
        "nx.category AS __f_category, nx.condition AS __f_condition, nx.unit_canonical AS __f_unit "
        "FROM rows_nx nx"
    )
    q_page = (
        "SELECT 'page'::text, NULL::bigint, pg.*, NULL::bigint, nx.supplier_id, nx.provider, nx.category, nx.condition, "
        "nx.unit_canonical FROM rows_pg pg CROSS JOIN rows_nx nx"
    )
    q_facet = (
        "SELECT 'facet'::text, NULL::bigint, nx.*, NULL::bigint, NULL::boolean, NULL::boolean, NULL::bigint, fd.supplier_id, fd.provider, fd.category, "
        "fd.condition, fd.unit_canonical FROM (SELECT DISTINCT d.supplier_id, d.provider, d.category, "
        f"d.condition, d.unit_canonical FROM {facet_src} d) fd CROSS JOIN rows_nx nx"
    )
    return head + ",\n" + ",\n".join(ctes) + f"\n{q_total}\nUNION ALL\n{q_page}\nUNION ALL\n{q_facet}"


@router.get(
    "/inventory",
    response_model=InventoryListResponse,
    dependencies=[Depends(require_permission("products.view"))],
)
async def list_inventory_view(
    q: str | None = Query(default=None, max_length=255, description="日本語名/英語名/型番/検索ワード（NFKC・かな同一視・空白区切りAND）"),
    work_code: str | None = Query(default=None, max_length=50, description="作品の符号（products.work_id → type_master.code）"),
    category: str | None = Query(default=None, max_length=100, description="カテゴリー絞り込み (public.products.category)"),
    offer_type: str | None = Query(default=None, pattern="^(in_stock|pre_order)$", description="区分: in_stock(在庫) / pre_order(予約)"),
    hide_supplier_ids: str | None = Query(default=None, max_length=2000, description="非表示にする仕入元IDのCSV（ユーザー別フィルタ用）"),
    supplier_ids: str | None = Query(default=None, max_length=2000, description="表示する仕入元IDのCSV（選んだ仕入元だけ）"),
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
    merge_same_post: bool = Query(default=False, description="同じ投稿のランク違いを1行にまとめる"),
    fresh_only: bool = Query(default=False, description="LINE 投稿が24時間以内の行だけ出す"),
    sort: str = Query(
        default="release_date",
        pattern="^(name|category|mark|condition|unit|offer_type|quantity|unit_price|supplier|offered_at|release_date)$",
        description="ソート列。全列対応（ADR-093 在庫表改修）",
    ),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
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
        return InventoryListResponse(
            items=[], total=0, page=page, per_page=per_page, window_hours=None,
            fresh_window_hours=FRESH_WINDOW_HOURS,
        )
    include_flag_single = settings.get("include_flag_single", "false").lower() == "true"
    window_hours = max_age_hours
    if fresh_only:  # 「24時間以内」は配信行の計算の内側で絞る（便2・ADR-1014 改訂 2026-10-18（3））
        # max_age_hours は 0 以上の int（None は上で返却済み）。0 は「絞らない」なので 24h にする
        window_hours = min(max_age_hours, FRESH_WINDOW_HOURS) if max_age_hours else FRESH_WINDOW_HOURS
    age_condition, age_params = _age_window(window_hours)

    conditions, filter_params = _build_view_filters(
        q=q, work_code=work_code, category=category, offer_type=offer_type,
        hide_supplier_ids=hide_supplier_ids, hide_categories=hide_categories, condition=condition,
        condition_in=condition_in, unit_in=unit_in, offer_type_in=offer_type_in,
        qty_min=qty_min, qty_max=qty_max, price_min=price_min, price_max=price_max,
        supplier_ids=supplier_ids,
    )
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params = {**age_params, **filter_params}
    expiry = bool(window_hours)  # 実効の窓（応答の window_hours とは別）。0 は絞らないので期限なし
    if expiry:
        params["expiry_hours"] = window_hours
    order_dir = "ASC" if order == "asc" else "DESC"
    sort_col = _SORT_COLUMNS.get(sort, "d.japanese_title")
    head, final_main = distribution_rows_parts(
        include_flag_single=include_flag_single, age_condition=age_condition, merge_same_post=merge_same_post,
    )
    sql = _build_inventory_view_sql(
        head=head, final_main=final_main, merge=merge_same_post, where=where, sort_col=sort_col, order_dir=order_dir,
        expiry=expiry,
    )
    result = await db.execute(
        text(sql), {**params, "limit": per_page, "offset": (page - 1) * per_page},
    )
    total = 0
    expiry_s: int | None = None
    page_rows: list[tuple[int, dict]] = []
    facet_rows: list[dict] = []
    for r in result.mappings().all():
        row = dict(r)
        kind = row["__kind"]
        if kind == "total":
            total = int(row["__total"] or 0)
            expiry_s = int(row["__expiry_s"]) if row["__expiry_s"] is not None else None
        elif kind == "page":
            page_rows.append((row["__ord"], {
                **{k: v for k, v in row.items() if not k.startswith("__")},
                "badge_cheapest": bool(row["__badge_cheapest"]),
                "badge_most_stock": bool(row["__badge_most_stock"]),
            }))
        elif kind == "facet":
            facet_rows.append({
                "supplier_id": row["__f_supplier_id"], "provider": row["__f_provider"],
                "category": row["__f_category"], "condition": row["__f_condition"],
                "unit_canonical": row["__f_unit"],
            })
    page_rows.sort(key=lambda t: t[0])
    items = _project_inventory_rows([r for _, r in page_rows])

    # フィルタ UI の候補は、まとめなし・絞り込みなしの配信行から作る（非表示にした候補も残る）。
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
        total=total,
        page=page,
        per_page=per_page,
        suppliers=suppliers,
        categories=categories,
        conditions=condition_facet,
        units=unit_facet,
        window_hours=max_age_hours,
        fresh_window_hours=FRESH_WINDOW_HOURS,
        next_expiry_in_seconds=expiry_s,
    )


@router.get(
    "/inventory/raw-texts",
    response_model=InventoryRawTextsResponse,
    dependencies=[Depends(require_permission("products.view"))],
)
async def list_inventory_raw_texts(
    extraction_item_ids: list[str] = Query(min_length=1, max_length=50, description="extraction_items.id（1〜50件）"),
    db: AsyncSession = Depends(get_db),
):
    """在庫表スライドの原文タブ。配信行（dist_base）に入る extraction_item だけの原文を返す。

    行の定義は distribution_rows_parts の1か所だけ（ここに配信の WHERE は書かない。ADR-1014）。
    配信行に無い ID・該当 0 件は 404。返す項目は extraction_item_id・raw_text・line_start・line_end のみ。
    """
    settings = await load_distribution_settings(db)
    max_age_hours = _max_age_hours(settings)
    if max_age_hours is None:
        raise HTTPException(status_code=404, detail="not_found")
    include_flag_single = settings.get("include_flag_single", "false").lower() == "true"
    age_condition, age_params = _age_window(max_age_hours)
    head, _final = distribution_rows_parts(
        include_flag_single=include_flag_single, age_condition=age_condition, merge_same_post=False,
    )
    sql = (
        head
        + ",\n    raw_ok AS (SELECT DISTINCT item_key FROM dist_base WHERE item_key = ANY(:raw_item_ids))\n"
        + f"""SELECT ei.id::text AS extraction_item_id, sm.raw_text, ei.line_start, ei.line_end
        FROM raw_ok
        JOIN {_distribution.TCG_SCHEMA}.extraction_items ei ON ei.id::text = raw_ok.item_key
        JOIN {_distribution.TCG_SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN {_distribution.TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id"""
    )
    result = await db.execute(text(sql), {**age_params, "raw_item_ids": list(extraction_item_ids)})
    rows = [dict(r) for r in result.mappings().all()]
    if not rows:
        raise HTTPException(status_code=404, detail="not_found")
    return InventoryRawTextsResponse(items=[
        {
            "extraction_item_id": r["extraction_item_id"], "raw_text": r["raw_text"] or "",
            "line_start": r["line_start"], "line_end": r["line_end"],
        }
        for r in rows
    ])


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
