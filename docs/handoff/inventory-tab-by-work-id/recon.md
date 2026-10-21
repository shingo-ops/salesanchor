# recon: 在庫表のタブを work_id（中分類）で絞り、products.tcg_type 列を消す

> 何の文書か（1行）: 在庫表のタブの絞り込みと products.tcg_type 列を使っている場所・本番 DB の状態を、実物で調べた記録。事実のみ。提案・設計は書かない。
> 親: [docs/specs/master-ssot-migration/design.md](../../specs/master-ssot-migration/design.md)（作品の正本は products.work_id）／前例: [drop-products-type-master-id](../drop-products-type-master-id/recon.md)

基準: origin/main 222f07098488b2763d1e53f79169d61014768868（PR #4507 マージ）。本番 DB は ADR-1024 の読み取りの道（ai_ro ビューとカタログ）。生出力は /Users/tanizawashingo/CC報告ファイル-keep/inventory-tab-work-id/（g_tcg_type_all.txt、adr_grep.txt、gas_grep.txt、r1〜r9.txt=コード抜粋、c*/d*/e*/f*.sql と .out=DB）。
PO 決定: 2026-10-18「在庫表のタブは中分類 work_id で絞る」「SSOT したいので不要なら列を消してくれ」。
行番号はすべて上記 SHA の worktree 上の値。

## 0. 指示文との食い違い（実物）
- 指示文は「配信 SQL（tcg_distribution_svc.py）の d.tcg_type」としたが、backend/app/services/tcg_distribution_svc.py に tcg_type は 0 件。d.tcg_type は backend/app/routers/inventory_offers.py:294-298 で作られる。tcg_distribution_svc.py:365 は既に `LEFT JOIN public.type_master ser ON ser.id = p.work_id` と work_id で結ぶ。
- 前例 ADR-1026 の recon にあった NULL 件数（73）は古く、今回の実測は 79（§d）。

## a. products.tcg_type を読む・書く箇所
同名で別物（対象外）: public.tcg_series_master.tcg_type（backend/app/routers/super_admin_tcg.py:36,37,58-60,65,87-88,256、backend/app/schemas/central_masters.py:150,163、scripts/seed_tcg_series*.py）。

### a-1 バックエンド（読む）と今のコード

**inventory_offers.py（GET /inventory。在庫表の本体）**

_BASE_SELECT（:60-80）。使われるのは :96（`WHERE i.id = :id` の単票）と :535（一覧 `{_BASE_SELECT} {where}`）の 2 か所だけで、GET /inventory ではない。
```
:60  _BASE_SELECT = """
:61      SELECT i.id, i.supplier_id, i.product_id, ...
:72           p.category AS category,
:73           p.mark AS mark,
:74           p.tcg_type AS tcg_type
:75      FROM public.inventory i
:76      LEFT JOIN public.suppliers s ON s.id = i.supplier_id
:77      LEFT JOIN public.products  p ON p.id = i.product_id
```
注: 抜粋の行頭の数字は目安。`p.tcg_type AS tcg_type` の実位置は :73（g_tcg_type_all.txt）。応答の型は backend/app/schemas/inventory_offers.py:111（`tcg_type: str | None = None`、InventoryOffer 系。コメント「ADR-093: オファー画面の列順を在庫表に揃えるため products 由来の表示列」）。

GET /inventory の配信行（本命）:
```
inventory_offers.py:293  join = "LEFT JOIN public.products pp ON pp.id = x.product_id"
:296  ctes.append(f"rows_x AS (SELECT x.*, pp.tcg_type AS tcg_type, pp.category AS category FROM rows_main x {join})")
:298  ctes.append(f"rows_xp AS (SELECT x.*, pp.tcg_type AS tcg_type, pp.category AS category FROM rows_plain x {join})")
```
```
:188  *, q, tcg_type, category, ... (_build_view_filters の引数)
:195  if tcg_type:
:196      conditions.append("d.tcg_type = :tcg_type")
:197      params["tcg_type"] = tcg_type
:332  tcg_type: str | None = Query(default=None, max_length=50, description="TCG種別 (public.products.tcg_type)"),
:377  q=q, tcg_type=tcg_type, category=category, ...   (_build_view_filters へ渡す)
:173  tcg_type=row.get("tcg_type"),                    (応答行 InventoryViewRow へ詰める)
```
応答スキーマ: backend/app/schemas/inventory_offers.py:152 `tcg_type: str | None = None       # TCG 種別（フィルタ用 = public.products.tcg_type）`。

**応答の tcg_type を frontend が読むか（事実）**: `git grep -n tcg_type -- frontend/src`（テスト除く）の結果は次の 13 行のみ。
- InventoryPage.tsx:189 だけが tcg_type を使う（送る側。`params.set("tcg_type", activeTab)`）。
- 在庫表の行型 frontend/src/features/inventory/inventoryColumns.tsx:34 `tcg_type: string | null;` は型宣言だけで、同ファイルとその利用先に `.tcg_type` で値を読む箇所は 0 件。
- frontend/src/components/InventorySearchBar.tsx:56 `tcg_type?: string | null;` も型宣言だけ。値を読む箇所 0 件（grep の全行は r3.txt）。
- 値を読んで画面に出すのは ProductsPage.tsx:366 と ProductEditPage.tsx:65,131,243-244 のみ（§a-3）。
つまり GET /inventory の応答の tcg_type を読む画面は無い（テスト fixture には現れる: §e）。

**tcg_type 絞り込みの「配信行」にある work_id**: tcg_distribution_svc.py:365 の JOIN `ser ON ser.id = p.work_id` は既存（`p` は products）。配信行（d.*）に work_id 列が既にあるかは未確認【未確認】。

**inventory_aggregated 系（GET /inventory/aggregated）**
```
backend/app/services/inventory_aggregated_service.py:28-45 (_load_products)
  """in_stock 在庫を持つ商品を一括取得。category 指定時は tcg_type で絞る。N+1 回避。"""
  SELECT DISTINCT p.id, p.name, p.tcg_type
  FROM public.products p JOIN public.inventory i ON i.product_id = p.id
  WHERE p.is_archived IS NOT TRUE AND i.status = 'in_stock'
  ... if category is not None:  base_sql += "  AND p.tcg_type = :category\n"
:76-78  "tcg_type": product.tcg_type,                       (行 dict に詰める)
:88-90  series_to_tcg = {p.name: p.tcg_type for p in products}   # product.name -> tcg_type
:96-102 # タブ (distinct tcg_type, 昇順)   tabs = sorted(tabs_set)
:110    "tcg_type": series_to_tcg.get(series),
```
- 呼び出し元: backend/app/main.py:625 でルータ登録のみ。frontend/src に `inventory/aggregated` の呼び出し 0 件（`git grep -E "inventory/aggregated|inventory_aggregated" -- frontend/src` が 0）。用途は「series（商品名）×コンディションのピボット」で、tabs は tcg_type の重複なし昇順（応答 backend/app/schemas/inventory_aggregated.py:6,22,33）。
- backend/app/services/inventory_aggregation.py:44,71（データクラスの項目 `tcg_type: str | None = None`）、:247（`tcg_type=_optional_text(_get_value(source, ("tcg_type",)))` 入力辞書から読む）、:352（`tcg_type=selected.tcg_type` 結果へ持ち回す）。集計ロジック自体は tcg_type で分岐しない（集計規則は :389 の public.inventory_aggregation_rules）。呼び出し元は inventory_aggregated_service.py:12 のみ。

**inventory_search（GET /inventory/search）**
```
backend/app/services/inventory_search.py:104-107  # mark=型番 / tcg_type=TCG 種別。見積/請求の明細行に引き込んで使う。
                                       mark: str | None = None
                                       tcg_type: str | None = None
:346-347  p.mark,
          p.tcg_type,
:445      tcg_type=r.get("tcg_type"),
```
- backend/app/routers/inventory_search.py:125 と backend/app/schemas/inventory_search.py:65 で応答に出す。呼び出し元の画面: frontend/src/components/InventorySearchBar.tsx:179（`/inventory/search?q=...`）。応答型は :56 で宣言されるが値は読まない。InventorySearchBar を import する画面は git grep で .stories.tsx 以外に見つからない（`git grep -n InventorySearchBar -- frontend/src` が同ファイル自身と stories のみ）。見積・請求の明細に取り込む処理（バックエンド側）が tcg_type を使うかは未確認【未確認】。

**products API**
```
backend/app/routers/products.py:61-80 (_UPDATABLE_COLUMNS) ... # ADR-090 PR5a: TCG 種別マスタ統一  "tcg_type",
:112-133 async def _validate_tcg_type(db, tcg_type): type_master.code に無ければ 400
         "tcg_type は type_master.code に存在する値か NULL のみ指定できます"
:152   SELECT 列に tcg_type（一覧）        :186 Query tcg_type    :246-248 filter `tcg_type = :tcg_type`
:402-403 POST の検査  :437,447 INSERT 列と値
:525-526 PATCH: if "tcg_type" in update_data: await _validate_tcg_type(db, update_data.get("tcg_type"))
```
**list_product_tcg_types（GET /products/tcg-types。タブ・絞り込み・編集のプルダウンの出どころ）全文** products.py:285-312:
```
@router.get("/products/tcg-types", dependencies=[Depends(require_permission("products.view"))])
async def list_product_tcg_types(db, current_user):
    """在庫表の TCG 絞り込みフィルタ用に、有効な TCG 種別マスタ一覧を返す（ADR-090 PR5a）。..."""
    if is_postgresql(db):
        exists = await db.execute(text("SELECT to_regclass('public.type_master') IS NOT NULL"))
        if not exists.scalar(): return []
        ref = "public.type_master"
    else:  (SQLite: sqlite_master に type_master が無ければ [] 、ref = "type_master")
    result = await db.execute(text(f"SELECT code, name_ja FROM {ref} WHERE is_active ORDER BY sort_order, code"))
    return [{"code": r["code"], "name_ja": r["name_ja"]} for r in result.mappings().all()]
```
返す形は `[{"code": str, "name_ja": str}]`。id は返さない。

### a-2 バックエンド（書く）
- 書く経路は products.py の PATCH（:71,525）と POST（:402,437,447）のみ。work_id は `_UPDATABLE_COLUMNS`（:61-80）に無く、PATCH で更新できない。backend/app/schemas/product.py に work_id は 0 件で、products API は work_id を受け取りも返しもしない。
- POST /products（PG）は :419 で `"work_id": None` を検査に渡すため必ず 422（REQUIRED_FIELDS_MISSING:work_id）になる（docs/specs/product-master/registration-rules.md:76 も同旨）。
- backend/app/services/tcg_product_master_svc.py:566-573 の共用商品登録は work_id を入れ、tcg_type は入れない（79 件 NULL の原因）。
- CSV 取り込み・書き出し（tcg_product_import*、tcg_product_roundtrip_svc）、Celery、discord_gateway、scripts（seed_tcg_series* 以外）、.github に products.tcg_type を書く処理は 0 件（g_tcg_type_all.txt）。
- backend/app に products の ORM モデルは無い（`class Product`/`__tablename__ = "products"` が 0 件）。

### a-3 フロントエンドと今のコード

**InventoryPage.tsx（在庫表）**
```
:113  const [activeTab, setActiveTab] = useState<string>("pokemon_booster_box");
:149-150 // 種別マスタ（tcg_type コード → 日本語名）。カテゴリー列を日本語表示するために使う。
         const [tcgTypes, setTcgTypes] = useState<{ code: string; name_ja: string }[]>([]);
:189  if (activeTab !== "all") params.set("tcg_type", activeTab);
:231-239 api.get<{ code: string; name_ja: string }[]>("/products/tcg-types").then(setTcgTypes)
         .catch(() => { /* 取得失敗時は生の category 表示にフォールバック */ });
```
タブ定義の全文（:533-560）:
```
{/* TCG種別タブ: すべて/ポケモン/ワンピース/ドラゴンボール（4ボタン）＋その他ドロップダウン ＋ 警告（右端固定） */}
{/* ui-allow: TCG type tab bar from main back-merge, ADR-143 D-1 inventory v2 (#2624) */}
<div className="tabs" style={{...}}>
  <div style={{...}}>
    {(["all", "pokemon_booster_box", "one_piece", "dragon_ball"] as const).map((code) => {
      const label = code === "all" ? t("common.all") : (tcgTypes.find((tt) => tt.code === code)?.name_ja ?? code);
      return (<button key={code} className={activeTab === code ? "tab active" : "tab"}
                onClick={() => { setActiveTab(code); setPage(1); }}>{label}</button>);
    })}
    {tcgTypes.filter((tt) => !["pokemon_booster_box","one_piece","dragon_ball"].includes(tt.code)).length > 0 && (
      <SelectControl size="sm"
        value={["pokemon_booster_box","one_piece","dragon_ball","all"].includes(activeTab) ? "" : activeTab}
        onChange={(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }}
        aria-label={t("inventory.filter.otherTypes")}>
        <option value="">{t("inventory.filter.otherTypes")}</option>
        {tcgTypes.filter(...除外同じ3つ).map((tt) => (<option key={tt.code} value={tt.code}>{tt.name_ja}</option>))}
      </SelectControl>)}
```
- 固定 3 つの code: pokemon_booster_box / one_piece / dragon_ball（type_master の id 1/2/3: §c）。その他プルダウンの出どころ: GET /products/tcg-types の残り（固定 3 つ以外の active 行）。
- i18n キー: common.all（ja.json:133 「すべて」）、inventory.filter.otherTypes（ja.json:1488 「その他」/ en.json:1488 "Other"）。固定 3 つのラベルは API の name_ja で i18n キーなし。
- 部品: 4 つのタブは生の `<button className="tab">`（コメントで ui-allow: ADR-143 D-1 #2624）。components/ には Tabs.tsx（金型）があるが InventoryPage は import していない（import は SelectControl・Button・HeaderButton・Drawer・TextFieldControl・MultiSelect・DataTable など。:13-31）。プルダウンは SelectControl（frontend/src/components/Select）。

**ProductsPage.tsx（商品一覧）**
```
:50-51 // ADR-090 PR5a: TCG種別マスタによる絞り込み   const [tcgType, setTcgType] = useState("");
:52    const [tcgTypes, setTcgTypes] = useState<{ code: string; name_ja: string }[]>([]);
:55-60 api.get("/products/tcg-types").then(setTcgTypes)
:64    const tcgTypeName = new Map(tcgTypes.map((t) => [t.code, t.name_ja]));
:139   if (tcgType) params.set("tcg_type", tcgType);
:222-231 {tcgTypes.length > 0 && (<SelectControl className="field-w-sm" value={tcgType}
           onChange=... aria-label={t("products.filterByTcgType")} data-testid="products-tcg-type-filter">
           <option value="">{t("products.allTcgTypes")}</option>
           {tcgTypes.map((tt) => (<option key={tt.code} value={tt.code}>{tt.name_ja}</option>))}
:366   <td>{p.tcg_type ? (tcgTypeName.get(p.tcg_type) ?? p.tcg_type) : (p.category || "-")}</td>
```
- つまり ProductsPage の絞り込みは「タブ」ではなく SelectControl のプルダウン。値の出どころは GET /products/tcg-types（固定値ではない）。「カテゴリー」列（:364-366）は tcg_type が NULL のときだけ products.category を表示する。
- ProductsPage の URL は /admin/products（行クリックで /admin/products/:id/edit、:9 コメント）。

**ProductEditPage.tsx（商品編集）**
- ルート: frontend/src/App.tsx:211 `/admin/products/new`、:212 `/admin/products/:id/edit`。ProductsPage.tsx:197 の「新規」ボタンと行クリックから開く。
- 編集対象: `api.get<Product>("/products/${id}")`（ProductEditPage.tsx:58-59）。バックエンドは products.py:98-105 の `_products_ctx` で、PG のとき必ず `public.products`（共用カタログ。コメント「ADR-090: public.products は中央カタログ（tenant_id=NULL）」:405-407）を読み書きする。テナント別 products 表（tenant_00x.products）をこの画面で編集する経路はコード上に無い。
- work_id（中分類）の入力欄: ProductEditPage.tsx に `work_id`/`workId`/「中分類」の文字列は 0 件（grep 済み）。画面の「カテゴリ」欄が tcg_type を編集する:
```
:65   tcg_type: p.tcg_type || "",
:131  tcg_type: toNull(form.tcg_type),
:241-251 <label>{t("products.field.category")}</label>
         <SelectControl variant="product-edit" fullWidth value={form.tcg_type}
            onChange={(e) => setForm({ ...form, tcg_type: e.target.value })} data-testid="product-edit-tcg-type">
           <option value="">{t("common.notSet")}</option>
           {tcgTypes.map((tt) => (<option key={tt.code} value={tt.code}>{tt.name_ja}</option>))}
```
- PATCH で work_id を更新できるか: できない（`_UPDATABLE_COLUMNS` に無い。products.py:61-80）。
- 型: frontend/src/pages/products/products.types.ts:34（`tcg_type: string | null;` 応答）、:59（`tcg_type: string;` フォーム）、:94（フォーム初期値 `tcg_type: ""`）。

### a-4 GAS・scripts・その他
- 在庫一覧 GAS 3 リポジトリ（~/tcg-viewer-1hc-release、~/tcg-viewer-1tb-head、~/tcg-client-viewer）: `tcg_type|work_id|type_master` は 0 件（gas_grep.txt）。§g に動作の実物を記す。
- リポジトリ内の GAS は docs/feedback_form_to_github.gs のみ。
- テナント別 products 表: §h。

## b. タブの定義元と URL パラメータ
- タブの定義: InventoryPage.tsx:533-560（§a-3）。値は type_master.code。一覧の出どころは GET /products/tcg-types（products.py:285-312）。
- URL パラメータ名 `tcg_type` を送る画面は InventoryPage.tsx:189（→GET /inventory）と ProductsPage.tsx:139（→GET /products）の 2 つだけ。GAS・外部・.github・docs/ai-agents に `tcg_type=` の呼び出し 0 件。
- GET /inventory/aggregated は別名 `category`（backend/app/routers/inventory_aggregated.py:51 付近）で、frontend の呼び出し 0 件。
- frontend/api-contract/openapi.json に tcg_type が 27 行。api-contract-check.yml が差分で失敗にする。

## c. type_master の構造（本番）
- 16 行、id 16 種、code 16 種、全 active（c1.out）。id=code: 1 pokemon_booster_box／2 one_piece／3 dragon_ball／4 union_arena／5 yugioh／6 other／19 gundam／20 weiss_schwarz／21 digimon／22 hololive／23 lorcana／24 xross_stars／8981 duel_masters／8982 detective_conan／9043 wuthering_waves／9044 magic_the_gathering。
- 列: id・code・name_ja・name_en・sort_order・is_active（products.py:312 と migrations/085）。
- work_id は FK `fk_products_work_id FOREIGN KEY (work_id) REFERENCES type_master(id)`（e7.out）。
- work_id→code は 1 対 1。tcg_type が非 NULL の行で work_id の指す code と違うもの 0 件（c2.out）。互換ビュー public.tcg_type_master は 2026-12-21 以降に削除予定（migrations/20260921_070000_rename_tcg_type_master_to_type_master.sql）。

## d. tcg_type が NULL の商品（本番 public.products）
c4.sql の結果（c4.out）: 総数 1426、tcg_type NULL = 79、うち work_id あり = 79、work_id NULL = 0、tcg_type あり work_id NULL = 0、テナント行（tenant_id 非 NULL）= 0。
NULL 79 件の内訳（c6.out、work_id: 件数）: 1:16／2:14／3:2／4:3／5:4／6:22／19:1／20:3／21:1／24:3／8981:3／8982:3／9043:1／9044:3。
- 現状の在庫表での見え方: `d.tcg_type = :tcg_type`（inventory_offers.py:196）は NULL と等しくならないため、NULL の 79 行はどのタブにも出ず「すべて」でだけ出る。
- 配信 SQL での tcg_type の作り方: §0 と §a-1（pp.tcg_type を JOIN で足す）。

## e. 関連テスト・CI
**tcg_type を使うテスト**（g_tcg_type_all.txt）
- backend/tests: test_products_tcg_type_fk.py（28 行）、test_products.py（19）、test_inventory_distribution_rows_pg.py（13。:43 付近でテスト DB に列を足す）、test_inventory_aggregated.py（8）、test_inventory_distribution_rows.py:49,241、test_product_packagings_pg.py:27、test_products_required_fields_pg.py:25、conftest.py:812（SQLite の products 表に `tcg_type VARCHAR(50) REFERENCES type_master(code)`）。
- migration を名前で流す準備コード: backend/tests/rls_bootstrap.py:19-32,266,307（20260602_020000・20260616_000000・20260623_060000）、test_products_tcg_type_fk.py、test_value_migrations_neutralized.py。
- frontend: InventoryPage.{noechopatch,rowdrawer,settings,singlefetch,tablelayout}.test.tsx（fixture に tcg_type）、CommerceNavigationButtonMigration.test.tsx（URL に tcg_type=pokemon_boo… を含む期待）、CommerceSubmitButtonMigration.test.tsx、InventoryRowDrawer.test.tsx、inventoryColumns.test.tsx、tests-e2e/product-edit-tcg-type.spec.ts、tests-e2e/inventory-table-layout.spec.ts:41。

**CI の流し方（実物）**
- .github/workflows/test.yml:207-242: Postgres 16 サービス＋ `pytest -q --tb=short`（working-directory backend、全件）。backend/pyproject.toml:54 `testpaths = ["tests"]` なので backend/tests/test_products_tcg_type_fk.py は全件実行に含まれる（個別指定なし）。env の RLS_TEST_DATABASE_URL / RLS_ADMIN_DATABASE_URL（test.yml:224-230 付近）で PG 用テストが動く。TEST_PG_URL は意図的に未設定（test.yml のコメント）。PG を使うテストが実際に走るか skip されるかは各テスト次第で未確認【未確認】。
- .github/workflows/migration-test.yml: migrations/** か scripts/run_all_migrations.sh が変わった PR で起動（:41-45）。ジョブ `migration-full-dryrun`（:1111-）が run_all_migrations.sh の run_sql の並び順どおりに全件を実 Postgres 16 で流す。ほかに「変更された migration を 2 回流して冪等性を見る」ジョブ（:1034,1046,1089,1099）。.github 配下に tcg_type の文字列は 0 件。
- .github/workflows/schema-check.yml: backend/app/models.py・migrations/・scripts/migrate_*・scripts/db/・scripts/setup_tenant.py が変わると起動（:40）。公開スキーマの最小定義（:107）と tenant_1〜4 を作り dry-run 差分を見る（:177-202）。tcg_type の記述 0 件で、products.tcg_type の有無は見ていない。
- migration-guard.yml: Check 2（run_all_migrations.sh への登録）、Check 6（列削除は PR 本文に ADR 番号。:335-392）、Check 10（同じ列の ADD の後に DROP があると失敗。scripts/check-migration-column-churn.js。:518 以降）。
- api-contract-check.yml: openapi.json を `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で作り直した結果と一致しないと失敗。ほか deprecated-columns-check.yml、frontend-check.yml、e2e.yml。

## f. 既存 ADR 検索
実行: `git grep -n -i -E "tcg_type|work_id|中分類" -- docs/adr docs/specs`（adr_grep.txt、91 行）と docs/adr/FEATURE-INDEX.md。
- ADR-083（docs/adr/ADR-083-tcg-type-master.md:12,16,17,18,40）: tcg_type_master 新設。対象は tcg_series_master.tcg_type の値集合。products.tcg_type の記述なし。
- ADR-090（docs/adr/ADR-090-products-central-unification.md:97）: tcg_type_master 統一に言及。products.tcg_type を足した migration の見出しは「ADR-090 PR5a」。
- ADR-156（docs/adr/ADR-156-product-classification-tree-and-master-separation.md:12,26,39,46,63,71）: type_master＝中分類。互換ビュー。
- ADR-1020（docs/adr/ADR-1020-shared-product-required-fields.md:22）: 中分類（work_id）は必須 9 項目。
- ADR-1026（docs/adr/ADR-1026-drop-products-type-master-id.md:17）: 「作品（中分類）は products.work_id だけに置く」。:22 に「画面・API・解析・在庫一覧 GAS はすべて work_id か tcg_type を使い」。
- docs/specs/master-ssot-migration/design.md:13,22,43-138（tcg_type→work_id の写し）。docs/specs/product-master/registration-rules.md:25,76。docs/specs/README.md:38。
- FEATURE-INDEX.md に tcg_type・中分類の専用行なし（行 18=在庫/商品マスタ、行 19=共用商品の登録）。
- products.tcg_type の廃止を決めた ADR・設計: 0 件。

## g. 在庫一覧 GAS（3 リポジトリ）の実物
- 在庫の読み先は **スプレッドシートのタブ「在庫集計」**（`SHEET_NAME = '在庫集計'`、Code.js:SpreadsheetApp.getActiveSpreadsheet().getSheetByName）。アプリの API は呼ばない（UrlFetch・api.salesanchor の記述 0 件）。
- 返す列は許可リスト ALLOWED_HEADERS（ヘッダー名で列を特定。`sheetHeader.indexOf(col)`）。
  - ~/tcg-viewer-1hc-release/Code.js:10-24 と ~/tcg-viewer-1tb-head/コード.js:10-24（13 列）: 投稿日時／Mark／Japanese Title／English Title／Condition／Unit Price／Quantity／Note_JA／Status／Release Date／提供者／**Series**／Search Keywords。
  - ~/tcg-client-viewer/src/Code.js:10-22（10 列）: 投稿日時／Mark／Japanese Title／English Title／Condition／Unit Price／Quantity／Note_JA／Status／Release Date／提供者 の 11 項目（コメントは「10 列」と書くが配列は 11 項目）。Series なし。
- 作品の絞り込み: tcg-viewer-1hc-release/index.html:934 `var activeSeries = ''`、:981 `series: 11`（列番号 11＝Series 列）、:1173-1200 buildSeriesTabs（Series 列の値ごとのタブ）、:919 `<div id="seriesTabs" class="series-tabs">`、:832 モバイル用 `<select id="seriesSelect" aria-label="シリーズ">`。tcg-viewer-1tb-head も同じ構成。値は列名 Series（シートの列）で、アプリの tcg_type・work_id とは別物。
- tcg-client-viewer/src/index.html は Series 列なし。絞り込みは「コンディション」「提供者」のプルダウンと「新しいものだけ」チェック（:254-263,336-338）。
- Series 列の値をシートに書く側（誰が何の値で書くか）は未確認【未確認】。

## h. 列の削除を妨げるもの（本番 DB のカタログ。d*.out / e*.out）
対象 public.products.tcg_type（attnum 36）。products は最大 attnum 1600・生きている列 56・消した列 1544（e5/e6.out）。
| 種類 | 実測 |
|---|---|
| 外部キー | fk_products_tcg_type FOREIGN KEY (tcg_type) REFERENCES type_master(code)（d1.out） |
| 索引 | idx_public_products_tcg_type btree（d2.out） |
| CHECK | tcg_type を含むものは上の FK のみ |
| トリガー | 定義に tcg_type を含むもの 0 |
| RLS ポリシー | 0 |
| 関数 | 本文に tcg_type を含むもの 0（d5.out） |
| ビュー | 依存は ai_ro.public__products の 1 つだけ（d3.out）。ai_ro は scripts/run_all_migrations.sh の冒頭で作り直し対象（EXIT trap で再作成）で、列は pg_attribute から自動列挙 |
| マテビュー | products に依存するもの 0 |
| 毎デプロイで流れる ADD | migrations/20260602_020000_add_products_tcg_type.sql:7 `ADD COLUMN IF NOT EXISTS tcg_type VARCHAR(50)`、:14 `CREATE INDEX IF NOT EXISTS idx_public_products_tcg_type`（run_all_migrations.sh:248 登録）。FK は migrations/20260623_060000_add_products_tcg_type_fk.sql（登録 run_all_migrations.sh:487。列が無ければ飛ばす分岐あり）。products は attnum 1600 に達しているため、列を消した後にこの ADD が流れると失敗する |
| 無力化済みの関連 migration | 20260616_000000_fix_tcg_type_dedup.sql（run_all_migrations.sh:471）ほか |
| テスト準備 | rls_bootstrap.py・test_products_tcg_type_fk.py・conftest.py:812（§e） |
- テナント別 products 表（f2.out）: tenant_001／003／004／005／006 の 5 つに products 表が存在し、列 work_id・tcg_type は **どれにも無い**（category 列のみ該当）。tcg_type 列を持つ表は public.products と public.tcg_series_master（とその ai_ro ビュー）だけ（e2.out）。work_id 列を持つテナント別 products 表は 0。

## i. tcg_type を書く・返す箇所（全部）
- 入力: ProductCreate/ProductUpdate（backend/app/schemas/product.py:63,111）、PATCH 更新可能列（products.py:71）。
- 出力: ProductResponse（backend/app/schemas/product.py:181）、GET /inventory の行（backend/app/schemas/inventory_offers.py:152、inventory_offers.py:173）、InventoryOffer 系（backend/app/schemas/inventory_offers.py:111、inventory_offers.py:73）、GET /inventory/aggregated（backend/app/schemas/inventory_aggregated.py:22,33）、GET /inventory/search（backend/app/schemas/inventory_search.py:65）。
- 画面の入力: ProductEditPage.tsx:241-251 のみ。work_id の入力画面は products 系に無い。work_id を入れるのは TCG 商品マスタ登録（tcg_product_master_svc.py:566-573）と CSV（tcg_product_import*）。
- CSV・seed・scripts・Celery・GAS・外部連携: products.tcg_type を書く・返すものは 0 件。openapi.json の 27 行は API 契約の写し。

## j. 前例 ADR-1026（type_master_id 削除）の進め方
- 1 つの PR（#4471）に ADR・recon・design・migration・登録行をまとめた。docs/handoff/drop-products-type-master-id/design.md が設計。
- 手順: ①元の ADD 文を migration から消し「戻さない」コメントを残す（migrations/20260922_010000 の節）②新規 migrations/20261017_210000_drop_products_type_master_id.sql（FK 制約・索引・列を IF EXISTS で外す 3 文）③scripts/run_all_migrations.sh の末尾に run_sql 登録 1 行④消す前に id・旧値・work_id を CSV に退避（~/CC報告ファイル-keep/）。デプロイ前に deploy.yml:195-216 が pg_dump を取る。①と②は同じ PR（ADD が残ると attnum 上限で毎デプロイ失敗）。
- K 項目: K1 CI 緑／K2 退避 CSV の行数＝本番総行数／K3 リポジトリに ADD 文 0／K4 デプロイ後に列・FK・索引 0 と ai_ro ビューから列が消える／K5 デプロイ成功／K6 /health 200・API が 500 でなく 401・backend ログにエラー 0／K7 次のデプロイも成功。
- 違い（事実の比較）: type_master_id は参照するコードが 0 件だった。tcg_type は §a のとおり backend の複数ファイル・frontend の 3 ページ・多数のテスト・API の入出力・画面の入力が読み書きする。したがって前例の「コードを触らない 1 便」の型はそのまま当てはまらず、先に API・画面・テスト・openapi.json が tcg_type を使わない状態にする必要がある。

## k. 列削除 migration の置き場所・命名・GO 手順
- 置き場所と命名: migrations/YYYYMMDD_HHMMSS_description.sql（backend/CLAUDE.md:50）。最新は migrations/20261018_100000_create_product_packagings.sql。前例は migrations/20261017_210000_drop_products_type_master_id.sql。
- 登録: scripts/run_all_migrations.sh の末尾に run_sql 行を足す（migration-guard Check 2 が未登録を止める）。
- ADR: 列削除は PR 本文に ADR 番号が必要（migration-guard.yml:335-392）。ADR 追加後は `node scripts/generate-adr-index.js` で docs/adr/README.md を再生成（CLAUDE.md）。
- GO 手順: CLAUDE.md:57（ADR-136。マージ前にチャットで対象・変更 3 行・直前バックアップ確認を PO に提示→「GO #PR番号」受領まで適用しない→PR 本文に `### GO記録`→GO 権限は PO 単独）、docs/STANDARD-WORKFLOW.md:140 と :142（本文の引用は省略。行番号のみ）。
- 退避対象（前例に倣う場合）: id・tcg_type・work_id。本番 1426 行、テナント行 0（c4.out）。

## 外部事例
不要と判断。社内の二重管理列の整理であり、判断材料は自社 DB と参照箇所の実測。

## 未確認
- 配信行（d.*）に work_id 列が既にあるか。
- InventorySearchBar（/inventory/search）の呼び出し側画面と、見積・請求の明細処理が tcg_type を使うか。
- PG を使うテスト（test_products_tcg_type_fk.py ほか）が CI で skip されず実行されるか。
- 画面での実際の表示（タブとプルダウンが code と一致して動くか）。
- 在庫一覧 GAS の Series 列をシートに書く側。
- リポジトリと GAS の外にある URL（ブックマーク・外部ツール）が tcg_type= を呼ぶか。

フック誤検知の記録: agent-danger-hook が文書本文中の語に反応（Bash heredoc）→ Write ツールで作成
