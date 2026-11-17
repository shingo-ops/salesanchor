# card-R2: 請求書・見積の商品行の在庫を返す道を足す（invoice-create-portfolio 便 R2）

作成: Opus（Planner）2026-11-17。設計: docs/handoff/invoice-create-portfolio/design-v2.md 第6版 §3-4・§4 R2・§8・K10・K17・K23（設計審査 5回目 APPROVE）。
実装承認: PO は 2026-11-17 に p1〜p8 を「見本どおり」、単価を「在庫表の値段を初期値・手で変更可」と決め、PR マージ・デプロイまでの完走を委ねた（ccopusgo の委任の範囲）。
枝: release/invoice-portfolio-r2-inventory（origin/main から）。移行（migrations/）なし・deploy.yml なし・scripts/ なし。

注: §2-4 の試験は CI の使い捨ての試験 DB に試験用の商品を入れて終わりに消すだけ。共用商品マスタへの登録ではない（docs/specs/shared-product-master の新規登録ルールは読んだうえで対象外と判断）。
# rules-ack: d5738ef7

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-portfolio-R2 HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 道は `GET /invoices/draft-inventory?category=<code>`。権限は `require_permission("invoices.create", "quotes.create")`（どちらか1つで通る）。読むだけ。登録は draft-context の直後・preview の前に置く（`/invoices/{invoice_id}` より前。design-v2 §3-4）。
- D2 中身は在庫表と同じ関数を同じ順に呼ぶ: `_load_products_with_stock`・`_load_inventory_offers(mask_stock=False)`・`load_aggregation_rules`・`aggregate_inventory_offers`（backend/app/services/inventory_aggregated_service.py:122-147）。違いは集計の鍵だけ。集計に渡す行に `product_id` と `series=str(product_id)` を入れる（集計は series と状態で束ねる。product_id は結果 AggregationResult.product_id にそのまま渡る。backend/app/services/inventory_aggregation.py:52-72・307-）。同じ名前の商品が2つあっても混ざらない。
- D3 今の在庫表の関数（`_ProductMeta`・`_load_products_with_stock`・`_build_aggregation_offers`・`_pivot`・`get_aggregated_inventory`）と今の型（`ConditionCell`・`AggregatedRow`・`InventoryAggregatedResponse`）は1文字も変えない。新しい関数と型は各ファイルの末尾に足す。新しい型は `ConditionCell` をそのまま使う（値段と数の形を1か所に保つ）。
- D4 中分類（categories）は、在庫が集計に残った商品の作品の符号から作り、名前と並びは public.type_master の name_ja・sort_order で引く（sort_order が同じなら code 順）。category を付けても categories は絞らない（画面の選択肢は常に全部）。items だけ絞る。
- D5 重さは legacy_field_sql（backend/app/services/product_packagings.py:15-20・40-57）で読む。今の商品検索（backend/app/services/inventory_search.py）と同じく float に直す。英語名・型番は products.name_en・products.mark。
- D6 仕入元名・採用の理由は返さない（今の在庫表と同じ境界）。
- D7 試験は今の在庫表の試験ファイル backend/tests/test_inventory_aggregated.py の末尾に足す（同じ準備 `seed_aggregated_dataset` を使う。今の試験は変えない）。荷姿の表を読む試験は、荷姿の表を作る準備 `seed_draft_four`（`ensure_product_packagings` を呼ぶ）を使う。K17 は試験（応答の形と値が新しい道と同じ）と、手順6 の API の形の比べ（今の在庫表の道と型の書き出しが main と同じ）の両方で確かめる。

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順8） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-2. 実装前点検（手順2 で流す。外れたら実装せず停止して BLOCKED: で報告）

- P1 `async def get_aggregated_inventory(` が backend/app/services/inventory_aggregated_service.py に 1。
- P2 `    return _pivot(results, products)` が同じファイルに 1。
- P3 `class ConditionCell(BaseModel):` が backend/app/schemas/inventory_aggregated.py に 1。
- P4 `incoterms=await invoice_totals.load_incoterms(db, tenant_id),` が backend/app/routers/invoices.py に 1。
- P5 `draft-inventory` が invoices.py に 0。
- P6 `def legacy_field_sql(` が backend/app/services/product_packagings.py に 1。
- P7 `async def ensure_product_packagings(` が backend/tests/rls_bootstrap.py に 1。
- P8 `def _make_app_client(pg_engine):` が backend/tests/test_inventory_aggregated.py に 1。
- P9 `境界違反` が backend/tests/test_inventory_aggregated.py に 1。

## 1. 触るファイル

- backend/app/services/inventory_aggregated_service.py（2-1）
- backend/app/schemas/inventory_aggregated.py（2-2）
- backend/app/routers/invoices.py（2-3）
- backend/tests/test_inventory_aggregated.py（2-4）
- frontend/api-contract/openapi.json（手順6 で作る）

## 2. 変更

### 2-1. services/inventory_aggregated_service.py

(1) 変更前:
```
from app.services.inventory_search import OfferSummary, _load_inventory_offers
```
変更後:
```
from app.services.inventory_search import OfferSummary, _load_inventory_offers
from app.services.product_packagings import legacy_field_sql
```
(2) ファイルの末尾。変更前:
```
    # 5. ピボット
    return _pivot(results, products)
```
変更後:
```
    # 5. ピボット
    return _pivot(results, products)


# ---------------------------------------------------------------------------
# 請求書・見積の商品行の在庫（invoice-create-portfolio R2・design-v2 §3-4）
# 上の在庫表と同じ関数で作り、集計の鍵だけを商品の番号にする。上の関数は変えない。
# ---------------------------------------------------------------------------


def _build_draft_offers(
    products: list[_ProductMeta],
    offers_by_product: dict[int, list[OfferSummary]],
) -> list[dict]:
    """集計に渡す行。series に商品の番号を入れ、同じ名前の商品を混ぜない。"""
    rows: list[dict] = []
    product_by_id = {p.product_id: p for p in products}
    for pid, offers in offers_by_product.items():
        product = product_by_id.get(pid)
        if product is None:
            continue
        for offer in offers:
            rows.append(
                {
                    "product_id": pid,
                    "series": str(pid),
                    "condition": offer.condition,
                    "quantity": offer.quantity if offer.quantity is not None else 0,
                    "unit_price": offer.unit_price if offer.unit_price is not None else 0,
                    "status": offer.status,
                    "supplier_name": offer.supplier_name,
                    "work_code": product.work_code,
                }
            )
    return rows


def _pivot_by_product(results: list[AggregationResult]) -> dict[int, dict[str, dict]]:
    """商品の番号 -> {状態: {price, quantity}}。仕入元名・理由は出さない。"""
    cells_by_product: dict[int, dict[str, dict]] = {}
    for r in results:
        if r.product_id is None:
            continue
        cells = cells_by_product.setdefault(int(r.product_id), {})
        cells[r.condition] = {"price": r.unit_price, "quantity": r.quantity}
    return cells_by_product


async def _load_draft_categories(db: AsyncSession, codes: set[str]) -> list[dict]:
    """在庫のある中分類の名前（type_master.name_ja）。sort_order 順・同じなら code 順。"""
    if not codes:
        return []
    result = await db.execute(
        text(
            "SELECT code, name_ja FROM public.type_master "
            "WHERE code = ANY(:codes) ORDER BY sort_order ASC, code ASC"
        ),
        {"codes": sorted(codes)},
    )
    return [{"code": row["code"], "name_ja": row["name_ja"]} for row in result.mappings().all()]


async def _load_draft_product_extras(db: AsyncSession, product_ids: list[int]) -> dict[int, dict]:
    """英語名・型番と、荷姿の表の BOX・ケースの重さ（ADR-1028。商品検索と同じ読み方）。"""
    if not product_ids:
        return {}
    result = await db.execute(
        text(
            f"""
            SELECT p.id, p.name_en, p.mark,
                   {legacy_field_sql("box_weight_kg", "p.id")} AS box_weight_kg,
                   {legacy_field_sql("case_weight_kg", "p.id")} AS case_weight_kg
            FROM public.products p
            WHERE p.id = ANY(:ids)
            """
        ),
        {"ids": product_ids},
    )
    extras: dict[int, dict] = {}
    for row in result.mappings().all():
        extras[int(row["id"])] = {
            "name_en": row["name_en"],
            "mark": row["mark"],
            "box_weight_kg": float(row["box_weight_kg"]) if row["box_weight_kg"] is not None else None,
            "case_weight_kg": float(row["case_weight_kg"]) if row["case_weight_kg"] is not None else None,
        }
    return extras


async def get_draft_inventory(
    db: AsyncSession,
    category: str | None,
) -> tuple[list[dict], list[dict]]:
    """請求書・見積の商品行の在庫。(categories, items) を返す。category は items だけを絞る。"""
    products = await _load_products_with_stock(db, None)
    if not products:
        return [], []

    product_ids = [p.product_id for p in products]
    offers_by_product = await _load_inventory_offers(db, product_ids, mask_stock=False)
    offer_rows = _build_draft_offers(products, offers_by_product)
    if not offer_rows:
        return [], []

    rules = await load_aggregation_rules(db)
    cells_by_product = _pivot_by_product(aggregate_inventory_offers(offer_rows, rules))

    stocked = [p for p in products if p.product_id in cells_by_product]
    categories = await _load_draft_categories(db, {p.work_code for p in stocked if p.work_code})
    picked = [p for p in stocked if category is None or p.work_code == category]
    extras = await _load_draft_product_extras(db, [p.product_id for p in picked])

    items: list[dict] = []
    for p in picked:
        extra = extras.get(p.product_id, {})
        items.append(
            {
                "product_id": p.product_id,
                "name": p.name,
                "name_en": extra.get("name_en"),
                "mark": extra.get("mark"),
                "work_code": p.work_code,
                "box_weight_kg": extra.get("box_weight_kg"),
                "case_weight_kg": extra.get("case_weight_kg"),
                "cells": cells_by_product[p.product_id],
            }
        )
    return categories, items
```

### 2-2. schemas/inventory_aggregated.py（ファイルの末尾）

変更前:
```
    rows: list[AggregatedRow] = Field(description="series 単位の集計行。")
```
変更後:
```
    rows: list[AggregatedRow] = Field(description="series 単位の集計行。")


# invoice-create-portfolio R2（design-v2 §3-4）: 請求書・見積の商品行の在庫。値段と数の形は ConditionCell を使う。
class DraftInventoryCategory(BaseModel):
    code: str = Field(description="中分類の符号（type_master.code）。")
    name_ja: str | None = Field(default=None, description="中分類の日本語名（type_master.name_ja）。")


class DraftInventoryItem(BaseModel):
    product_id: int
    name: str = Field(description="商品名 (products.name)。")
    name_en: str | None = None
    mark: str | None = Field(default=None, description="型番 (products.mark)。")
    work_code: str | None = None
    box_weight_kg: float | None = Field(default=None, description="BOX の重さ（荷姿の表）。")
    case_weight_kg: float | None = Field(default=None, description="ケースの重さ（荷姿の表）。")
    cells: dict[str, ConditionCell] = Field(default_factory=dict, description="状態別の集計。在庫表と同じ。")


class DraftInventoryResponse(BaseModel):
    categories: list[DraftInventoryCategory] = Field(description="在庫のある中分類（sort_order 順）。category で絞らない。")
    items: list[DraftInventoryItem] = Field(description="商品ごとの在庫（商品の番号の順）。category で絞る。")
```

### 2-3. routers/invoices.py

(1) 変更前:
```
from app.schemas.invoice import (
```
変更後:
```
from app.schemas.inventory_aggregated import DraftInventoryResponse
from app.schemas.invoice import (
```
(2) 変更前:
```
from app.services.fx_currencies import list_invoice_currencies
```
変更後:
```
from app.services.fx_currencies import list_invoice_currencies
from app.services.inventory_aggregated_service import get_draft_inventory
```
(3) 変更前:
```
        incoterms=await invoice_totals.load_incoterms(db, tenant_id),
    )


@router.post(
    "/invoices/preview",
```
変更後:
```
        incoterms=await invoice_totals.load_incoterms(db, tenant_id),
    )


@router.get(
    "/invoices/draft-inventory",
    response_model=DraftInventoryResponse,
    dependencies=[Depends(require_permission("invoices.create", "quotes.create"))],
)
async def get_invoice_draft_inventory(
    category: str | None = Query(None, description="中分類の符号（type_master.code）。無ければ全部。"),
    db: AsyncSession = Depends(get_db),
) -> DraftInventoryResponse:
    """請求書・見積の商品行の在庫（invoice-create-portfolio R2・design-v2 §3-4）。読むだけ。"""
    categories, items = await get_draft_inventory(db, category)
    return DraftInventoryResponse(categories=categories, items=items)


@router.post(
    "/invoices/preview",
```
(2) の行が見つからないとき（import の名前が違うとき）は、`from app.services.fx_currencies import` で始まる行の直後に `from app.services.inventory_aggregated_service import get_draft_inventory` を1行足す。その行も無ければ `BLOCKED: invoices.py import`。

### 2-4. backend/tests/test_inventory_aggregated.py（ファイルの末尾に足す。今の試験は変えない）

変更前:
```
            assert f'"{key}"' not in raw_json, (
                f'境界違反: "{key}" が JSON 応答に含まれています'
            )
```
変更後:
```
            assert f'"{key}"' not in raw_json, (
                f'境界違反: "{key}" が JSON 応答に含まれています'
            )


# ---------------------------------------------------------------------------
# invoice-create-portfolio R2: GET /invoices/draft-inventory（design-v2 §3-4・K10・K17・K23）
# ---------------------------------------------------------------------------


def test_draft_pivot_by_product_keeps_same_name_apart():
    from app.services.inventory_aggregated_service import _pivot_by_product
    from app.services.inventory_aggregation import AggregationResult

    def _result(pid: int, price: int) -> AggregationResult:
        return AggregationResult(
            row_id=None,
            product_id=pid,
            supplier_id=1,
            supplier_name="Supplier X",
            series=str(pid),
            condition="Sealed box",
            quantity=3,
            unit_price=price,
            status="In Stock",
            reason_category="lowest_price",
            reason="r",
        )

    cells = _pivot_by_product([_result(1, 100), _result(2, 200)])
    assert cells == {
        1: {"Sealed box": {"price": 100, "quantity": 3}},
        2: {"Sealed box": {"price": 200, "quantity": 3}},
    }


@pytest_asyncio.fixture
async def seed_draft_four(seed_aggregated_dataset):
    """4つの状態と BOX・ケースの重さを持つ試験用の商品を1つ足す（pokemon_booster_box）。終わりに消す。"""
    from sqlalchemy import text

    from tests.rls_bootstrap import ensure_product_packagings

    data = seed_aggregated_dataset
    eng = data["engine"]
    tag = data["tag"]
    await ensure_product_packagings(eng)
    async with eng.begin() as conn:
        pid = (
            await conn.execute(
                text(
                    "INSERT INTO public.products (name, name_en, mark, work_id, is_archived) "
                    "VALUES (:n, :ne, :m, (SELECT id FROM public.type_master WHERE code = 'pokemon_booster_box'), false) "
                    "RETURNING id"
                ),
                {"n": f"ポケカD_{tag}", "ne": f"PokeD_{tag}", "m": f"MK-{tag}"},
            )
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO public.inventory"
                " (supplier_id, product_id, condition, raw_condition, quantity, unit_price, status)"
                " VALUES (:s, :p, 'Case', 'Case', 1, 60000, 'in_stock'),"
                "        (:s, :p, 'Sealed box', 'Sealed box', 7, 5000, 'in_stock'),"
                "        (:s, :p, 'Damaged sealed box', 'Damaged sealed box', 2, 4000, 'in_stock'),"
                "        (:s, :p, 'No shrink box', 'No shrink box', 3, 4500, 'in_stock')"
            ),
            {"s": data["sup_id"], "p": pid},
        )
        await conn.execute(
            text(
                "INSERT INTO public.product_packagings (product_id, unit_id, weight_kg, weight_source) "
                "SELECT :p, id, CASE code WHEN 'BOX' THEN 0.5 ELSE 6.0 END, 'legacy' "
                "FROM public.quantity_units WHERE code IN ('BOX', 'CASE')"
            ),
            {"p": pid},
        )

    yield {**data, "poke4_id": pid, "poke4_name": f"ポケカD_{tag}"}

    async with eng.begin() as conn:
        await conn.execute(text("DELETE FROM public.product_packagings WHERE product_id = :p"), {"p": pid})
        await conn.execute(text("DELETE FROM public.inventory WHERE product_id = :p"), {"p": pid})
        await conn.execute(text("DELETE FROM public.products WHERE id = :p"), {"p": pid})


def _make_invoice_client(pg_engine, perms: set[str]):
    """請求書の道の試験用クライアント。require_permission が読む権限を perms に差し替える。"""
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.database import get_db
    from app.main import app
    from app.models import User
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    mock_user = User(id=1, tenant_id=1, email="ci-test@test.com")

    async def mock_load_perms(*args, **kwargs):
        return frozenset(perms)

    @asynccontextmanager
    async def _ctx():
        app.dependency_overrides = {}
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_tenant] = lambda: 1
        app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch("app.auth.dependencies.load_user_permissions", mock_load_perms):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                yield client
        app.dependency_overrides = {}

    return _ctx()


@pytest.mark.asyncio
@pytestmark_pg
async def test_draft_inventory_four_conditions_weights_and_category(seed_draft_four):
    """§3-4・K10: 4つの状態・重さ・英語名・型番を返す。category で items だけ絞る。仕入元名と理由は出さない。"""
    from sqlalchemy import text

    data = seed_draft_four
    tag = data["tag"]
    async with _make_invoice_client(data["engine"], {"invoices.create"}) as client:
        resp = await client.get("/api/v1/invoices/draft-inventory?category=pokemon_booster_box")
        assert resp.status_code == 200, resp.text
        for key in ("supplier_name", "reason", "reason_category"):
            assert f'"{key}"' not in resp.text, key
        body = resp.json()
        all_resp = await client.get("/api/v1/invoices/draft-inventory")
        assert all_resp.status_code == 200, all_resp.text
        all_body = all_resp.json()

    items = body["items"]
    ids = {it["product_id"] for it in items}
    assert {data["poke1_id"], data["poke2_id"], data["poke4_id"]} <= ids
    assert data["yugi_id"] not in ids
    assert all(it["work_code"] == "pokemon_booster_box" for it in items)
    assert [it["product_id"] for it in items] == sorted(ids)

    d = next(it for it in items if it["product_id"] == data["poke4_id"])
    assert d["name"] == data["poke4_name"]
    assert (d["name_en"], d["mark"]) == (f"PokeD_{tag}", f"MK-{tag}")
    assert (d["box_weight_kg"], d["case_weight_kg"]) == (0.5, 6.0)
    assert d["cells"] == {
        "Case": {"price": 60000, "quantity": 1},
        "Sealed box": {"price": 5000, "quantity": 7},
        "Damaged sealed box": {"price": 4000, "quantity": 2},
        "No shrink box": {"price": 4500, "quantity": 3},
    }

    # category を付けても categories は絞らない。名前と並びは type_master から引いた値と同じ
    assert body["categories"] == all_body["categories"]
    codes = [c["code"] for c in body["categories"]]
    assert {"pokemon_booster_box", "yugioh"} <= set(codes)
    async with data["engine"].connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT code, name_ja FROM public.type_master "
                    "WHERE code = ANY(:c) ORDER BY sort_order ASC, code ASC"
                ),
                {"c": codes},
            )
        ).all()
    assert [{"code": r[0], "name_ja": r[1]} for r in rows] == body["categories"]
    assert data["yugi_id"] in {it["product_id"] for it in all_body["items"]}


@pytest.mark.asyncio
@pytestmark_pg
async def test_draft_inventory_quote_only_user_gets_200(seed_draft_four):
    """K23: 見積を作る権限だけでも 200。どちらの権限も無ければ 403。"""
    eng = seed_draft_four["engine"]
    async with _make_invoice_client(eng, {"quotes.create"}) as client:
        resp = await client.get("/api/v1/invoices/draft-inventory")
        assert resp.status_code == 200, resp.text
    async with _make_invoice_client(eng, {"products.view"}) as client:
        resp = await client.get("/api/v1/invoices/draft-inventory")
        assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
@pytestmark_pg
async def test_stock_table_unchanged_and_same_cells_as_draft(seed_draft_four):
    """K17: 在庫表の道の形はそのまま（tabs・rows、行は series・work_code・cells）。値段と数は新しい道と同じ。"""
    data = seed_draft_four
    async with _make_app_client(data["engine"]) as client:
        resp = await client.get("/api/v1/inventory/aggregated")
        assert resp.status_code == 200, resp.text
        agg = resp.json()
    async with _make_invoice_client(data["engine"], {"invoices.create"}) as client:
        resp = await client.get("/api/v1/invoices/draft-inventory")
        assert resp.status_code == 200, resp.text
        draft = resp.json()

    assert set(agg) == {"tabs", "rows"}
    assert all(set(r) == {"series", "work_code", "cells"} for r in agg["rows"])
    by_id = {it["product_id"]: it for it in draft["items"]}
    for key in ("poke1", "poke2", "yugi", "poke4"):
        row = next(r for r in agg["rows"] if r["series"] == data[f"{key}_name"])
        assert row["cells"] == by_id[data[f"{key}_id"]]["cells"], key
```

## 3. 手順

手順1 作業場所を公式の台本で作る（ホームに clone した別の場所は使わない）。1 つずつ流し、出力を報告に書く。リポジトリの場所が `/home/user/salesanchor` でないときは、実際の場所に読み替えて同じ命令を流し、読み替えたことを書く。
    cd /home/user/salesanchor && git fetch origin main
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-r2-inventory
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-r2-inventory
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git rev-parse HEAD
  期待: 2行目の出力が空（空でなければ `BLOCKED: 手順1 枝が既にある`）。4行目に `worktrees/salesanchor/release-invoice-portfolio-r2-inventory` が出る（出なければ `BLOCKED: 手順1 作業場所`）。5行目 `is-ancestor exit=0`。台本が作る .claude-pipeline/active-work.d/ の未追跡ファイルは add しない。

手順2 実装前点検 P1〜P9
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "async def get_aggregated_inventory(" backend/app/services/inventory_aggregated_service.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "    return _pivot(results, products)" backend/app/services/inventory_aggregated_service.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "class ConditionCell(BaseModel):" backend/app/schemas/inventory_aggregated.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "incoterms=await invoice_totals.load_incoterms(db, tenant_id)," backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "draft-inventory" backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "def legacy_field_sql(" backend/app/services/product_packagings.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "async def ensure_product_packagings(" backend/tests/rls_bootstrap.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "def _make_app_client(pg_engine):" backend/tests/test_inventory_aggregated.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c "境界違反" backend/tests/test_inventory_aggregated.py
  期待（命令の順）: 1、1、1、1、0、1、1、1、1。

手順3 §2 の変更をする（2-1 から順に。すべて Edit ツール）

手順4 道具を入れる（作業場所の外 ~/venv312。素の pip は見張りが止めるので使わない）
    cd ~ && python3.12 -m venv ~/venv312 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
  python3.12 が無いときだけ 1行目の代わりに `cd ~ && uv venv --python 3.12 ~/venv312` と `cd ~ && ~/venv312/bin/python -m ensurepip` を流す（それも失敗したら `BLOCKED: python3.12 なし`）。

手順5 形と試験
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && ~/venv312/bin/ruff check backend/app/services/inventory_aggregated_service.py backend/app/schemas/inventory_aggregated.py backend/app/routers/invoices.py backend/tests/test_inventory_aggregated.py 2>&1 | tail -10
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_inventory_aggregated.py 2>&1 | tail -15
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_inventory_aggregation.py tests/test_invoices.py tests/test_error_detail_guard.py 2>&1 | tail -15
  期待: ruff `All checks passed!`。2行目は `4 passed` と `6 skipped`（PG の6本は CI だけで動く）。3行目は failed 0・error 0（本数はそのまま書く）。

手順6 API の形を書き出し、今の在庫表の道が変わっていないことを比べる（K17）
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git diff --numstat frontend/api-contract/openapi.json | tail -1
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && grep -c '"/api/v1/invoices/draft-inventory"' frontend/api-contract/openapi.json
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git show origin/main:frontend/api-contract/openapi.json > ~/oa-main.json && ~/venv312/bin/python -c "import json,os; a=json.load(open(os.path.expanduser('~/oa-main.json'))); b=json.load(open('frontend/api-contract/openapi.json')); p='/api/v1/inventory/aggregated'; ks=['ConditionCell','AggregatedRow','InventoryAggregatedResponse']; print('K17 path same:', a['paths'][p]==b['paths'][p]); print('K17 schemas same:', all(a['components']['schemas'][k]==b['components']['schemas'][k] for k in ks))"
  期待: 1行目は何も出ない。2行目は足した行が 0 より大きい。3行目 1。4行目 `K17 path same: True` と `K17 schemas same: True`。

手順7 変えたファイル
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git status --short | tail -20
  期待: §1 の 5 ファイルだけ（.claude-pipeline/active-work.d/ の未追跡は除く）。ほかが出たら `BLOCKED: 範囲外のファイル`。

手順8 記録と送り出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git add backend/app/services/inventory_aggregated_service.py backend/app/schemas/inventory_aggregated.py backend/app/routers/invoices.py backend/tests/test_inventory_aggregated.py frontend/api-contract/openapi.json && git status --short | tail -20
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(invoices): add draft-inventory route that returns in-stock items per product id for invoice and quote lines (invoice-portfolio R2)" && git log --oneline -1 | tail -1
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git push -u origin release/invoice-portfolio-r2-inventory 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r2-inventory && git rev-parse HEAD
  push は --no-verify・force を付けない。push が止められたら言い換えず `BLOCKED: push`。

## 4. 想定される分かれ道

- 停止する（その場で停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P9 のどれかが外れた → `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所以上当たる（2-3 (2) は §2-3 の注のとおり）→ `BLOCKED: ファイル名 変更前の文`。
  - 手順5 で failed か error が出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。カードからの書き写し間違い（字・字下げ）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。
  - 手順6 の 4行目が True でない・KeyError が出た → 直さず `BLOCKED: K17 在庫表の形が変わる`。
  - 手順6 のほかの期待が外れた → `BLOCKED: 手順6`。
- 記録して続ける: ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して結果を書く。I 以外なら `BLOCKED: ruff`。skipped・警告はそのまま書く。

## 5. 報告の形

- 宛先: クラウドの実行の最後の返事。ファイルに書かない。
- 1 行目: 受領確認の行。2 行目: 「本報告はカード 便R2 請求書・見積の商品行の在庫を返す道を足す の実行結果である」。
- 手順1・2・5・6・7・8 の出力をそのまま貼る（要約しない）。全体で 1500 字を超えるときは、手順5・手順6・手順8 を優先して貼り、ほかは期待と合ったかを ○× で書く。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。CI の結果は Opus が見る。PR は作らない（Opus が作る）。
- ファイルの編集は Edit ツール。ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 触らない範囲

§1 以外のファイル。在庫表の今の関数（`_ProductMeta`・`_load_products_with_stock`・`_build_aggregation_offers`・`_pivot`・`get_aggregated_inventory`）と今の型（`ConditionCell`・`AggregatedRow`・`InventoryAggregatedResponse`）。backend/app/routers/inventory_aggregated.py。backend/app/services/inventory_aggregation.py・inventory_search.py。今の試験の中身と期待値（末尾に足すだけ）。migrations/・deploy.yml・scripts/。

## 8. 設計 §8 の役割の数え（Opus が実施・カードの実行役の作業ではない）

- 実施: 2026-11-17 20:40 JST、本番の読む道（ADR-1024 の reader 鍵・ai_ro のビュー・会社ごとに1文）。
- 読んだもの: 全5社（tenant_001・003・004・005・006）の roles・role_permissions・user_roles と public.permissions。権限の名前が invoices.* ・quotes.* ・products.view ・inventory.visibility.* のものだけ。会社ごとの行数は 37・34・43・43・43（上限200に届かず切れていない）。
- 判定: 「invoices.create か quotes.create を持ち、products.view も inventory.visibility.* も持たない役割」を数えた。
- 結果: **0 件**。作る権限を持つ役割（オーナー・システム管理者・営業）は、すべて在庫を見る権限も持っている。在庫の値段と数が見える人は、この道で増えない。
- そのため設計 §8 の「0でなければ PO に伝えてから R2 を出す」の条件には当たらない。

END OF CARD
