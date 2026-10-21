from __future__ import annotations

"""
商品・在庫管理API（CRUD + 在庫チェック）。

変更履歴:
  2026-04-17: 初版作成（Phase 2）
  2026-04-28: Phase 1-C M-MVP（Q4/Q5/Q9 確定）
              - 11 列対応（jan_code, card_number, expansion_code, rarity, language,
                unit_price_usd, unit_price_eur, image_url, is_archived,
                archived_at, supplier_default_id）
              - is_archived フィルタ追加（default false）
              - DELETE で FK 参照あり時は 409 + アーカイブ推奨（Q9）
              - PATCH で is_archived=true → archived_at 自動設定
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    is_postgresql,
    require_permission,
    reset_tenant_context,
)
from app.cache import invalidate_dashboard_cache
from app.database import get_admin_db, get_db
from app.models import User
from app.schemas.product import (
    InventoryCheckResponse,
    ProductArchiveResponse,
    ProductCreate,
    ProductPackagingOut,
    ProductResponse,
    ProductUpdate,
)
from app.services.audit import record_audit_log
from app.services.product_packagings import (
    LEGACY_FIELDS,
    legacy_field_sql,
    load_packagings,
    save_legacy_fields,
)
from app.services.tcg_product_master_svc import check_required_fields, find_cleared_fields

router = APIRouter()

# ADR-072 Phase 1: ローカル helper を削除し、`is_postgresql` / `tenant_table_ref`
# を import 使用。`_check_product_references` は dialect 分岐で SQLite フォール
# バックを行うため `is_postgresql` も使う。


_UPDATABLE_COLUMNS = {
    "name_ja", "name_en", "category", "mark", "status",
    "unit_price", "quantity", "weight", "notes", "release_date",
    # Phase 1-C M-MVP
    "jan_code", "card_number", "expansion_code", "rarity", "language",
    "unit_price_usd", "unit_price_eur", "image_url",
    "is_archived", "supplier_default_id",
    # ADR-093: 商品種類（最上位ジャンル区分）+ セット種別
    "product_kind", "set_type",
    # ADR-093 Phase 1: 商品マスタ全項目（Box 属性 + 発送ラベル + 検索/分類）
    # 入数・重さ4項目は荷姿の表へ書く（ADR-1028。services/product_packagings.py）
    "volume_weight", "moq", "hs_code", "material", "item",
    "required_output_value", "search_keywords", "exclude_keywords",
    "related_series",
    # 手動並び替え（行ドラッグ）順
    "display_order",
}

# ADR-090: products を public 中央テーブルへ一本化。
# - PostgreSQL 本番: public.products（実列は name / stock_quantity）。Discord取込もここに入るため
#   在庫表(/products)が public を読むことで取込が在庫表に反映される。
# - SQLite (pytest): schema 概念が無く conftest の products（実列は name_ja / quantity）を使うため
#   dialect で参照テーブル名と列名を分岐する（応答契約 name_ja / quantity は alias で維持）。
def _products_ctx(db: AsyncSession) -> dict[str, str]:
    if is_postgresql(db):
        return {"ref": "public.products", "name": "name", "qty": "stock_quantity", "dialect": "postgresql"}
    return {"ref": "products", "name": "name_ja", "qty": "quantity", "dialect": "sqlite"}


def _select_columns(ctx: dict[str, str]) -> str:
    """応答契約（name_ja / quantity）を維持しつつ実列を alias した SELECT 列リストを返す。"""
    # 入数・重さ4項目は荷姿の表から組み立てる（ADR-1028）。SQLite には表が無いので NULL。
    tm_ref = "public.type_master" if ctx["dialect"] == "postgresql" else "type_master"
    if ctx["dialect"] == "postgresql":
        legacy4 = ", ".join(
            f"{legacy_field_sql(f, ctx['ref'] + '.id')} AS {f}"
            for f in LEGACY_FIELDS
        )
    else:
        legacy4 = ", ".join(f"NULL AS {f}" for f in LEGACY_FIELDS)
    return (
        f"id, product_code, {ctx['name']} AS name_ja, name_en, category, mark, "
        f"status, unit_price, {ctx['qty']} AS quantity, weight, "
        "notes, release_date, created_at, updated_at, "
        "jan_code, card_number, expansion_code, rarity, language, "
        "unit_price_usd, unit_price_eur, image_url, "
        "is_archived, archived_at, supplier_default_id, "
        # 作品の符号は products.work_id → type_master.code（写しの列は持たない。ADR-1030）
        f"(SELECT tm.code FROM {tm_ref} tm WHERE tm.id = {ctx['ref']}.work_id) AS work_code, "
        # ADR-093 Phase 1: 商品マスタ全項目
        f"{legacy4}, "
        "volume_weight, moq, hs_code, material, item, required_output_value, "
        "search_keywords, exclude_keywords, related_series, "
        # ADR-093: 商品種類（最上位ジャンル区分。値='TCG' 等）+ セット種別
        "product_kind, set_type, "
        # 手動並び替え順（行ドラッグ。NULL=未設定）
        "display_order"
    )


async def _build_responses(db: AsyncSession, ctx: dict[str, str], rows) -> list[ProductResponse]:
    """行から応答を組み、PostgreSQL では荷姿（packagings）を1回の SELECT でまとめて詰める。"""
    rows = [dict(r) for r in rows]
    packs: dict[int, list[dict]] = {}
    if ctx["dialect"] == "postgresql":
        packs = await load_packagings(db, [r["id"] for r in rows])
    return [
        ProductResponse(**r, packagings=[ProductPackagingOut(**p) for p in packs.get(r["id"], [])])
        for r in rows
    ]


@router.get(
    "/products",
    response_model=list[ProductResponse],
    dependencies=[Depends(require_permission("products.view"))],
)
async def list_products(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    category: str | None = Query(default=None, max_length=100),
    work_code: str | None = Query(default=None, max_length=50, description="作品の符号で絞り込み（products.work_id → type_master.code）"),
    status_filter: str | None = Query(default=None, alias="status"),
    sort: str | None = Query(
        default=None,
        description="name_asc / name_desc。未指定は updated_at DESC（従来順）",
    ),
    archived: bool = Query(
        default=False,
        description="true で廃番(is_archived=true)も含む。default は非表示",
    ),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    ctx = _products_ctx(db)
    offset = (page - 1) * per_page
    conditions = []
    params: dict = {"limit": per_page, "offset": offset}

    # 検索の関連度スコア（ORDER BY 用）。検索時のみ設定。
    search_score_sql: str | None = None
    if search:
        # QA r6 I-02: 「タイプ」列 (category) もユーザーから見える列のため部分一致対象に含める。
        # language / rarity / expansion_code も検索可能列として一般的なため同時に対象。
        # 広範マッチ（2026-06-05）: 入力を空白（半角/全角 U+3000）で語句分割し、各語句を
        # 「いずれかの検索対象列に部分一致」（OR）させ、語句間も OR で広く候補化する。
        # これにより語順・余分な空白・一部語句の欠落があっても近い候補を提示できる
        # （解析レビューの「商品マスタから選択」が前方一致的に取りこぼす問題の解消）。
        # 関連度（2026-06-05 改善）: 一致語句数の単純加算だと「ポケモンカード」のような
        # ありふれた語に一致しただけの大量の商品と、「メガブレイブ」のような希少語に一致した
        # 目的商品が同点になり埋もれる。そこで語句の希少度で重み付けする（IDF 風）:
        #   重み = 1000.0 / (1 + その語句に一致する商品件数)
        # ありふれた語ほど件数が多く軽く、希少語ほど件数が少なく重い。結果、希少語に一致した
        # 商品が上位に来る（汎用語に埋もれない）。一致しない語は 0。
        search_cols = (
            ctx["name"], "name_en", "product_code", "mark", "jan_code",
            "card_number", "category", "rarity", "expansion_code", "language",
        )
        ref = ctx["ref"]
        tokens = [tok for tok in re.split(r"[\s　]+", search) if tok]
        if not tokens:
            tokens = [search]
        token_groups: list[str] = []   # 各語句の OR グループ（WHERE 用）
        score_terms: list[str] = []    # 希少度重み付きスコア（ORDER BY 用）
        for i, tok in enumerate(tokens):
            key = f"search_{i}"
            params[key] = f"%{tok}%"
            ors = " OR ".join(f"{col} ILIKE :{key}" for col in search_cols)
            token_groups.append(f"({ors})")
            # df = その語句に一致する商品件数（uncorrelated サブクエリ＝語句ごとに 1 回算出）。
            df = f"(SELECT COUNT(*) FROM {ref} WHERE {ors})"
            score_terms.append(
                f"(CASE WHEN ({ors}) THEN (1000.0 / (1 + {df})) ELSE 0 END)"
            )
        # いずれかの語句にマッチすれば候補（広範マッチ）。
        conditions.append("(" + " OR ".join(token_groups) + ")")
        search_score_sql = " + ".join(score_terms)
    if category:
        conditions.append("category = :category")
        params["category"] = category
    if work_code:
        tm_ref = "public.type_master" if ctx["dialect"] == "postgresql" else "type_master"
        conditions.append(f"work_id = (SELECT tm.id FROM {tm_ref} tm WHERE tm.code = :work_code)")
        params["work_code"] = work_code
    if status_filter:
        conditions.append("status = :status")
        params["status"] = status_filter
    if not archived:
        conditions.append("(is_archived = FALSE OR is_archived IS NULL)")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # 名前ソート（在庫表ヘッダーのトグル用）。ホワイトリストで SQL インジェクション防止。
    # 未指定は従来どおり updated_at DESC。
    _SORT_MAP = {
        "name_asc": f"{ctx['name']} ASC",
        "name_desc": f"{ctx['name']} DESC",
        # ADR-093 商品マスタ: 発売日ソート（NULL は末尾）
        "release_date_asc": "release_date ASC NULLS LAST",
        "release_date_desc": "release_date DESC NULLS LAST",
        # 手動並び替え（行ドラッグ）: display_order 昇順、未設定(NULL)は末尾、同値は id 昇順で安定。
        "manual": "display_order ASC NULLS LAST, id ASC",
    }
    explicit_sort = _SORT_MAP.get(sort or "")
    if explicit_sort:
        # 明示ソート（在庫表ヘッダーのトグル等）が最優先。
        order_by = explicit_sort
    elif search_score_sql:
        # 検索かつ明示ソート無し → 一致語句数の多い順（関連度）、同点は更新日時降順。
        order_by = f"({search_score_sql}) DESC, updated_at DESC"
    else:
        order_by = "updated_at DESC"

    result = await db.execute(
        text(f"SELECT {_select_columns(ctx)} FROM {ctx['ref']} {where} ORDER BY {order_by} LIMIT :limit OFFSET :offset"),
        params,
    )
    return await _build_responses(db, ctx, result.mappings().all())


@router.get(
    "/products/tcg-types",
    dependencies=[Depends(require_permission("products.view"))],
)
async def list_product_tcg_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """在庫表の TCG 絞り込みフィルタ用に、有効な TCG 種別マスタ一覧を返す（ADR-090 PR5a）。
    super_admin_tcg の CRUD は super_admin 限定のため、products.view 権限で読める軽量版。
    `/products/{product_id}` より前に登録すること（path 競合防止）。
    """
    # マスタ未投入環境（SQLite テスト等）では空配列を返す。
    if is_postgresql(db):
        exists = await db.execute(text("SELECT to_regclass('public.type_master') IS NOT NULL"))
        if not exists.scalar():
            return []
        ref = "public.type_master"
    else:
        exists = await db.execute(
            text("SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='type_master')")
        )
        if not exists.scalar():
            return []
        ref = "type_master"
    result = await db.execute(
        text(f"SELECT code, name_ja FROM {ref} WHERE is_active ORDER BY sort_order, code")
    )
    return [{"code": r["code"], "name_ja": r["name_ja"]} for r in result.mappings().all()]


@router.get(
    "/products/attribute-options",
    dependencies=[Depends(require_permission("products.view"))],
)
async def list_product_attribute_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """各種マスタ(public.product_attribute_masters)の有効な選択肢を属性別に返す。

    商品マスタフォームのプルダウン候補として使う。編集は super_admin の「各種マスタ」
    のみだが、読取は products.view で可能にする（/products/tcg-types と同方針）。
    `/products/{product_id}` より前に登録すること（path 競合防止）。
    返却例: {"product_kind": [{"code","label_ja","label_en"}], "rarity": [...], ...}
    """
    if is_postgresql(db):
        exists = await db.execute(
            text("SELECT to_regclass('public.product_attribute_masters') IS NOT NULL")
        )
        if not exists.scalar():
            return {}
        ref = "public.product_attribute_masters"
    else:
        exists = await db.execute(
            text(
                "SELECT EXISTS(SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='product_attribute_masters')"
            )
        )
        if not exists.scalar():
            return {}
        ref = "product_attribute_masters"
    result = await db.execute(
        text(
            f"SELECT attribute, code, label_ja, label_en FROM {ref} "
            f"WHERE is_active ORDER BY attribute, sort_order, id"
        )
    )
    grouped: dict[str, list[dict]] = {}
    for r in result.mappings().all():
        grouped.setdefault(r["attribute"], []).append(
            {"code": r["code"], "label_ja": r["label_ja"], "label_en": r["label_en"]}
        )
    return grouped


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_permission("products.view"))],
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    ctx = _products_ctx(db)
    result = await db.execute(
        text(f"SELECT {_select_columns(ctx)} FROM {ctx['ref']} WHERE id = :id"),
        {"id": product_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")
    return (await _build_responses(db, ctx, [row]))[0]


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    dependencies=[Depends(require_permission("products.create"))],
)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    ctx = _products_ctx(db)
    payload = data.model_dump()
    # 入数・重さ4項目は products の列ではなく荷姿の表へ書く（ADR-1028）
    packaging_fields = {k: payload.pop(k) for k in LEGACY_FIELDS if payload.get(k) is not None}
    for k in LEGACY_FIELDS:
        payload.pop(k, None)
    if payload.get("status") is not None:
        payload["status"] = payload["status"].value if hasattr(payload["status"], "value") else payload["status"]
    # ADR-090: public.products は中央カタログ（tenant_id=NULL）。SQLite テスト表は
    # tenant_id NOT NULL のため従来どおり tenant_id を入れる。
    payload["tenant_id"] = None if is_postgresql(db) else tenant_id

    # ADR-1020: 共用の表（public.products）に作るときは9項目を検査する。
    # この口は中分類・細分類・商品区分を受け取らず、検索・除外ワードの正本の表にも書かないので、それらは「無い」として渡す。
    if is_postgresql(db):
        missing = check_required_fields({
            "name": payload.get("name_ja"),
            "name_en": payload.get("name_en"),
            "mark": payload.get("mark"),
            "release_date": payload.get("release_date"),
            "search_keywords": None,
            "exclude_keywords": None,
            "work_id": None,
            "product_format_id": None,
            "product_category_id": None,
        }, set())
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="REQUIRED_FIELDS_MISSING:" + ",".join(missing),
            )

    result = await db.execute(
        text(f"""
            INSERT INTO {ctx['ref']} (
                tenant_id, {ctx['name']}, name_en, category, mark,
                status, unit_price, {ctx['qty']}, weight,
                notes, release_date,
                jan_code, card_number, expansion_code, rarity, language,
                unit_price_usd, unit_price_eur, image_url,
                is_archived, supplier_default_id,
                volume_weight, moq, hs_code, material, item,
                required_output_value, search_keywords, exclude_keywords,
                related_series, product_kind, set_type
            ) VALUES (
                :tenant_id, :name_ja, :name_en, :category, :mark,
                :status, :unit_price, :quantity, :weight,
                :notes, :release_date,
                :jan_code, :card_number, :expansion_code, :rarity, :language,
                :unit_price_usd, :unit_price_eur, :image_url,
                :is_archived, :supplier_default_id,
                :volume_weight, :moq, :hs_code, :material, :item,
                :required_output_value, :search_keywords, :exclude_keywords,
                :related_series, :product_kind, :set_type
            ) RETURNING id
        """),
        payload,
    )
    new_id = result.scalar_one()

    await db.execute(
        text(f"UPDATE {ctx['ref']} SET product_code = :code WHERE id = :id"),
        {"code": f"PD-{new_id:05d}", "id": new_id},
    )

    if packaging_fields and ctx["dialect"] == "postgresql":
        await save_legacy_fields(db, new_id, packaging_fields, f"user:{current_user.id}")

    fetched = await db.execute(
        text(f"SELECT {_select_columns(ctx)} FROM {ctx['ref']} WHERE id = :id"),
        {"id": new_id},
    )
    row = fetched.mappings().first()
    response = (await _build_responses(db, ctx, [row]))[0]

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="create", table_name="products", record_id=new_id,
        new_data=data.model_dump(exclude_none=True, mode="json"),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)

    return response


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_permission("products.update"))],
)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    ctx = _products_ctx(db)
    old_result = await db.execute(
        text(f"SELECT {_select_columns(ctx)} FROM {ctx['ref']} WHERE id = :id"),
        {"id": product_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")

    update_data = data.model_dump(exclude_unset=True)
    packaging_fields = {k: v for k, v in update_data.items() if k in LEGACY_FIELDS}
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
    if not update_data and not packaging_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")

    if packaging_fields and ctx["dialect"] == "postgresql":
        tenant_of_row = (await db.execute(
            text("SELECT tenant_id FROM public.products WHERE id = :id"), {"id": product_id}
        )).scalar_one_or_none()
        if tenant_of_row is not None:
            # 荷姿の表の RLS はテナントを持たない共用の行だけが対象（ADR-1028）
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="PACKAGING_SHARED_ONLY",
            )

    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value if hasattr(update_data["status"], "value") else update_data["status"]

    # ADR-1020: 共用の行で、値か印があった項目を空にする更新は止める（古い空欄は止めない）。
    if is_postgresql(db):
        shared = (await db.execute(
            text("SELECT 1 FROM public.products WHERE id = :id AND tenant_id IS NULL"),
            {"id": product_id},
        )).first()
        if shared is not None:
            marks = {r[0] for r in (await db.execute(
                text("SELECT field_code FROM public.product_blank_confirmations WHERE product_id = :id"),
                {"id": product_id},
            )).all()}
            keys = {"name": "name_ja", "name_en": "name_en", "mark": "mark", "release_date": "release_date"}
            before = {f: old_row.get(k) for f, k in keys.items()}
            after = {f: (update_data[k] if k in update_data else old_row.get(k)) for f, k in keys.items()}
            cleared = find_cleared_fields(before, marks, after, marks)
            if cleared:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="REQUIRED_FIELDS_CLEARED:" + ",".join(cleared),
                )

    # 応答契約の name_ja / quantity を実列(ctx)へマッピングして SET 句を組む（param キーは据え置き）。
    _col = {"name_ja": ctx["name"], "quantity": ctx["qty"]}
    # is_archived=true への遷移時に archived_at を自動設定
    set_parts = [f"{_col.get(k, k)} = :{k}" for k in update_data]
    if update_data.get("is_archived") is True and not old_row.get("is_archived"):
        set_parts.append("archived_at = NOW()")
    elif update_data.get("is_archived") is False and old_row.get("is_archived"):
        set_parts.append("archived_at = NULL")
    set_parts.append("updated_at = NOW()")
    set_clauses = ", ".join(set_parts)

    update_data["id"] = product_id

    # products の UPDATE は常に流す（RLS の判定を今と同じにするため）
    result = await db.execute(
        text(f"""
            UPDATE {ctx['ref']} SET {set_clauses}
            WHERE id = :id
            RETURNING {_select_columns(ctx)}
        """),
        update_data,
    )
    row = result.mappings().first()
    if row is None:
        # RLS で共用の行に書けない（UPDATE 0 行）。rollback は get_db が行う
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="PRODUCT_NOT_WRITABLE")

    if packaging_fields and ctx["dialect"] == "postgresql":
        await save_legacy_fields(db, product_id, packaging_fields, f"user:{current_user.id}")
        row = (await db.execute(
            text(f"SELECT {_select_columns(ctx)} FROM {ctx['ref']} WHERE id = :id"),
            {"id": product_id},
        )).mappings().first()
    response = (await _build_responses(db, ctx, [row]))[0]

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="update", table_name="products", record_id=product_id,
        old_data=dict(old_row), new_data={**update_data, **packaging_fields},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)

    return response


# 削除時に検査する下流テーブルの allowlist。
# 識別子は文字列リテラルのみ、tenant スキーマは search_path から解決される。
#
# TODO(M3 / docs/products_design.md §5-2): product_inventory を追加する。
#   - 在庫履歴があれば削除拒否がポリシー（履歴は監査証跡）
#   - product_inventory.product_id への参照を 'product_inventory' エントリで検出
# TODO(M4 / docs/products_design.md §5-3): product_supplier_mappings を追加する。
#   - 仕入先マッピングがあれば削除拒否（CASCADE は危険）
_DOWNSTREAM_TABLES_TO_CHECK = (
    "quote_items",
    "invoice_items",
    "purchase_order_items",
)


async def _check_product_references(
    db: AsyncSession,
    product_id: int,
    tenant_id: int,
    admin_db: AsyncSession | None = None,
) -> list[str]:
    """指定 product_id を参照している下流テーブルのリストを返す。

    Phase 1-C M-MVP Q9: FK 参照ありの場合は物理削除せず 409 を返す。

    SA-18 Phase2: pg_namespace 走査と各テナント schema の SELECT は
    admin_db（管理者セッション）で実行する。salesanchor_app ロールでは
    RLS により他テナント schema をまたいだ走査ができないため。
    admin_db が None の場合は db にフォールバック（後方互換）。

    実装方針（PR #173 review Major 1 対応）:
        - テーブル存在チェックは to_regclass で先取り（schema 修飾名で存在確認）
        - 例外握り潰しを廃止、DB 例外は呼び出し側に伝播
        - 識別子はモジュール定数 _DOWNSTREAM_TABLES_TO_CHECK の allowlist のみ使用

    Issue #565: search_path 依存をやめて schema prefix を明示する。
    SQLite (pytest) は to_regclass 未対応のため prefix なしの dialect 分岐に倒す。
    """
    # SA-18 Phase2: クロステナント走査は admin_db を使用
    scan_db = admin_db if admin_db is not None else db
    blocking: list[str] = []
    if is_postgresql(db):
        # ADR-090: products は public 中央テーブルになったため、削除時は全テナント schema の
        # 下流参照を確認する（どこか 1 テナントでも参照していれば物理削除を拒否）。
        schemas_result = await scan_db.execute(
            text("SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname"),
        )
        schemas = [r[0] for r in schemas_result.all()]
        for table in _DOWNSTREAM_TABLES_TO_CHECK:
            for schema in schemas:
                # schema は pg_namespace 由来 + table は allowlist 確定済。:id のみバインド。
                qualified = f"{schema}.{table}"
                exists_result = await scan_db.execute(
                    text("SELECT to_regclass(:qname) IS NOT NULL"),
                    {"qname": qualified},
                )
                if not exists_result.scalar():
                    continue
                result = await scan_db.execute(
                    text(f"SELECT EXISTS(SELECT 1 FROM {qualified} WHERE product_id = :id)"),
                    {"id": product_id},
                )
                if result.scalar():
                    blocking.append(table)
                    break  # この table はいずれかのテナントで参照済 → 次の table へ
    else:
        # SQLite (pytest): schema 概念なし。単一 products / 下流テーブルを確認。
        for table in _DOWNSTREAM_TABLES_TO_CHECK:
            exists_result = await db.execute(
                text("SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name = :n)"),
                {"n": table},
            )
            if not exists_result.scalar():
                continue
            result = await db.execute(
                text(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE product_id = :id)"),
                {"id": product_id},
            )
            if result.scalar():
                blocking.append(table)
    return blocking


@router.delete(
    "/products/{product_id}",
    status_code=204,
    dependencies=[Depends(require_permission("products.delete"))],
    responses={
        409: {
            "model": ProductArchiveResponse,
            "description": "下流テーブルから参照されているため物理削除不可。is_archived=true でアーカイブを推奨",
        },
    },
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin_db: AsyncSession = Depends(get_admin_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """商品を物理削除する。

    Q9（2026-04-28 確定）: FK 参照あり時は 409 を返し、is_archived=true の
    アーカイブ運用に誘導する。参照なしのときだけ物理削除する。
    """
    ctx = _products_ctx(db)
    old_result = await db.execute(
        text(f"SELECT {_select_columns(ctx)} FROM {ctx['ref']} WHERE id = :id"),
        {"id": product_id},
    )
    old_row = old_result.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")

    blocking = await _check_product_references(db, product_id, tenant_id, admin_db=admin_db)
    if blocking:
        # PR #173 review Minor 6 follow-up: 失敗 DELETE 試行も audit_log に残す。
        # 「誰がいつ削除を試みたが下流参照で拒否された」を運用側で追えるようにする。
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="delete_blocked", table_name="products", record_id=product_id,
            old_data=dict(old_row),
            new_data={"blocking_references": blocking, "result": "409_conflict"},
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "id": product_id,
                "name_ja": old_row["name_ja"],
                "is_archived": bool(old_row.get("is_archived")),
                "blocking_references": blocking,
                "detail": (
                    f"以下のテーブルから参照されているため物理削除できません: "
                    f"{', '.join(blocking)}。"
                    f"is_archived=true で論理削除（アーカイブ）を推奨します"
                ),
            },
        )

    # PR #173 review Major 2 対応: _check_product_references の網羅漏れ
    # （M3/M4 で増える FK や allowlist 外の下流参照）に備え、IntegrityError を
    # キャッチして同じ 409 構造で返す + rollback で aborted transaction を
    # 残さない。
    try:
        await db.execute(text(f"DELETE FROM {ctx['ref']} WHERE id = :id"), {"id": product_id})
        await record_audit_log(
            db=db, tenant_id=tenant_id, user_id=current_user.id,
            action="delete", table_name="products", record_id=product_id,
            old_data=dict(old_row),
        )
        await db.commit()
        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "delete_product IntegrityError fallback: tenant=%d product=%d err=%s",
            tenant_id, product_id, exc.orig,
        )
        # IntegrityError fallback も監査ログに残す（参照先未特定で拒否された記録）
        try:
            await record_audit_log(
                db=db, tenant_id=tenant_id, user_id=current_user.id,
                action="delete_blocked", table_name="products", record_id=product_id,
                old_data=dict(old_row),
                new_data={"blocking_references": ["unknown"], "result": "409_integrity_error"},
            )
            await db.commit()
            await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
        except Exception:
            # audit log 自体の失敗で 500 を返さない（ベストエフォート）
            await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "id": product_id,
                "name_ja": old_row["name_ja"],
                "is_archived": bool(old_row.get("is_archived")),
                # _check_product_references で検出できなかった参照
                "blocking_references": ["unknown"],
                "detail": (
                    "下流参照があるため物理削除できません（参照先未特定）。"
                    "is_archived=true で論理削除（アーカイブ）を推奨します"
                ),
            },
        )

    await invalidate_dashboard_cache(tenant_id)


@router.get(
    "/products/{product_id}/check-inventory",
    response_model=InventoryCheckResponse,
    dependencies=[Depends(require_permission("products.view"))],
)
async def check_inventory(
    product_id: int,
    quantity: int = Query(ge=1),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """指定商品の在庫が要求数量を満たすか確認する"""
    ctx = _products_ctx(db)
    result = await db.execute(
        text(f"SELECT id, {ctx['name']} AS name_ja, {ctx['qty']} AS quantity FROM {ctx['ref']} WHERE id = :id"),
        {"id": product_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")

    return InventoryCheckResponse(
        product_id=row["id"],
        product_name=row["name_ja"],
        available=row["quantity"] >= quantity,
        current_quantity=row["quantity"],
        requested_quantity=quantity,
    )
