# recon: 在庫表の行から解析パネルを開く

> この文書は、在庫表の行クリックで「原文・Gemini抽出・システム解析」のパネルを開くために、今のコードがどうなっているかを調べた記録です。
> 親（あるべき姿）: [../../specs/inventory-management/README.md](../../specs/inventory-management/README.md)（在庫管理。開発区分＝既存の延長）
> 設計: [design.md](design.md)

- 調査基準: origin/main `16babf52c`（2026-10-16 fetch 後）。worktree `release/inventory-row-drawer`
- 調査担当: Sonnet（読み取りのみ）。生出力: `/tmp/CC報告ファイル/inventory-slide-recon.txt`, `/tmp/CC報告ファイル/inventory-fix-propagation.txt`, `/tmp/CC報告ファイル/inv-drawer-recon-raw.txt`
- 設計担当（Opus）が要所を再確認した箇所には【Opus再確認】を付けた。

## 0. PO の依頼（原文）

> superadminのワタシが在庫表をクリックするとスライドページが表示されて原文とgemini抽出結果、システムの解析結果が見れるようにしてほしい、要確認ページのスライドページと同じ仕組み（2026-10-16）

パネルから直す機能（修正→DB→シート反映）は PO から実現可否の質問があり「可能」と回答済み。採否は PO 未回答のため本便の対象外（design.md §2）。

## 1. 既存 ADR 検索

- `git grep -il -e 在庫表 -e スライド -e drawer -e 要確認 origin/main -- docs/adr/` 命中: ADR-057, 090, 093, 1014, 105, 138, 139, 140。
- 関係するもの:
  - `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md`（在庫表＝配信行。行の定義は1か所）
  - `docs/adr/ADR-093-inventory-table-product-master-redesign.md`（:3 で ADR-1014 に置換済み）
  - `docs/adr/ADR-027-ui-internationalization.md`（i18n）、ADR-144（UI ガバナンス。`docs/CC_UI_GOVERNANCE.md`）
- 138/139/140/057/090/105 は在庫表の行からパネルを開く話ではない。
- `docs/adr/FEATURE-INDEX.md` には 在庫表/要確認/ReviewItemDrawer の命中なし。
- 要確認パネル自体の ADR は見つからなかった。

## 2. 要確認パネル（再利用元）

- 置き場所: `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:164`（`<NeedsReviewTabsPanel />`）
- 行クリック: `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:222` `onRowClick={(item) => setDrawerItemId(item.extraction_item_id)}`。パネルの呼び出しは :233-240。
- パネル本体: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`
  - props（:27-36）: `item: ReviewDrawerItem`, `onClose`, `onRefresh: () => Promise<void>`（必須）, `removedFromList?`, `ackedView?`
  - item 型: `ReviewDrawerItem = AnalysisReviewItem & {...}`（:25）。`AnalysisReviewItem` は `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:22`
  - `<Drawer … size="wide">`（:146）。共通の金型は `frontend/src/components/Drawer.tsx:22-32`
  - 原文: `item.raw_text` を ShadowSourcePane に渡す（:191）
  - Gemini 抽出・システム解析: ItemComparison（:195、`readOnly={true}` 固定）
  - 操作:
    - 「確認済みにする」（:170-176。`canKeep`＝`ackableReasonCodes(...)`、`frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx:26-31`、v102 だけ）
    - 取消（:179-180）
    - ReviewFixWizard（:201-211。比較表の行を押すと `selectRow` :64-73 で scope が入る）
  - 押せる行: `frontend/src/features/tcg-analysis-review/reviewFixRows.ts:25-45`
  - **「見るだけ」にする既存 prop は無い。**
  - 理由が空のとき: `t("reviewItem.noReasons")`（:151。ja「理由はありません」`frontend/src/locales/ja.json:3792`）
- データ: 一覧 API の1件をそのまま渡す。パネルを開くときの追加の取得は無い（NeedsReviewTabsPanel.tsx:96-102, :79）。

## 3. 解析結果 API（`GET /api/v1/tcg/analysis-results`）

- ルーター: `backend/app/routers/tcg_analysis_review.py:117-136`
  - 権限 `Depends(require_super_admin)`（:133）
  - limit は 1〜500（既定10）
  - response_model は `AnalysisResultsResponse`（:96-103）
  - item 型は `AnalysisResultItem`（:81-93）
- サービス: `backend/app/services/tcg_analysis_review_svc.py:165` `fetch_analysis_results` 【Opus再確認】
  - `_BASE_FROM`（:52-62）は `JOIN source_messages sm ON sm.id = ej.source_message_id AND sm.is_active = TRUE`（:56）と `review_joins(schema=TCG_SCHEMA)`（:61）
  - 3本の SQL が `source_cte(schema=TCG_SCHEMA)` を先頭に置く: count :196、providers :200、items :210
  - `_build_where`（:69-128）
    - status_tab ごとの条件: :95-112
    - ID を指定して取る引数は無い
  - items_sql（:210-267）は `ei.id` 単位で1行を返す
  - `public.analysis_results.extraction_item_id` は UNIQUE（`migrations/20260923_050000_add_indexes_public_analysis_results.sql:8-9`）
- `source_cte`: `backend/app/services/tcg_condition_review_svc.py:61-74` 【Opus再確認】
  - `include_inactive=False`（既定）なら `WHERE is_active IS TRUE`
  - True なら絞らない
- 既知の別件（本便の対象外）: サービスは `manual_values` を返す（svc:319）。しかし `AnalysisResultItem` にそのフィールドが無く、pydantic 既定で落ちている可能性がある。本番レスポンスは未確認。

## 4. 在庫表（`/inventory`）

- ページ: `frontend/src/pages/inventory/InventoryPage.tsx`（ルート `frontend/src/App.tsx:206`）
  - DataTable: :593-617
  - `onRowClick` は無い
  - `selectable` あり（:598-600）
  - `useSuperAdmin` は未使用
  - merge_same_post の既定は false（:151, :288）
- 列定義と型: `frontend/src/features/inventory/inventoryColumns.tsx`
  - `InventoryRow` :12-35
  - `extraction_item_id` は無い
- API: `GET /api/v1/inventory`
  - `backend/app/routers/inventory_offers.py:314-424`
  - 権限 `products.view`（:317）
  - 行の変換は `_project_inventory_rows` :156-187
  - `row.get` で読むので、列を足しても壊れない
- スキーマ: `backend/app/schemas/inventory_offers.py:129-159` `InventoryRow`（id＝analysis_results.id、:138 コメント）
- 行の定義（唯一）: `backend/app/services/tcg_distribution_svc.py:274-371` `distribution_rows_parts` 【Opus再確認】
  - `source_cte(..., include_inactive=True)`（:285）
  - dist_base は ar→ei→ej→sm→sc を JOIN する。sm.is_active で絞らない
  - `ar.id::text AS row_key`（:308）
  - `ei` は FROM にある（:318）が、`ei.id` は SELECT していない
  - WHERE（:333-341）: pid_resolved, is_current, `cr.needs_review IS FALSE`, 除外, 単位, 価格, 投稿日時, 状態, Sold out
  - merge_same_post=True の流れ（:343-371）
    - gkey（ej.id＋商品＋状態＋単位＋メモ＋発送＋販売状況）が同じ2行以上をまとめる
    - `dist_agg` の window で、数量の合計・単価の最大・件数を出す
    - `rn=1` だけ残す
    - **まとめた他の行の ID は捨てられる**
    - まとめは1投稿の中だけ（gkey に ej.id）
  - 最終 SELECT: `_distribution_final_select`（:257-266）
- GAS 配信: `fetch_output_rows`（`backend/app/services/tcg_distribution_svc.py:390-412`）は `merge_same_post=False` の SQL を包む。`_GAS_COLUMNS`（:251-254、固定14列）だけを取り出す。**列を足しても GAS の出力は変わらない。**
- SQL 固定テスト: `backend/tests/test_inventory_distribution_rows.py:197` `test_distribution_rows_sql_is_pinned`。pg の同一性テスト: `backend/tests/test_inventory_distribution_rows_pg.py`。
- 在庫表の行は全部 analysis_results 由来。手入力・GAS 由来の行が混ざる経路は無い。
- 在庫表の行は needs_review=FALSE なので、要確認一覧（`status_tab=NEEDS_REVIEW`）には出ない。在庫表の行は非アクティブな投稿由来もありうる（要確認一覧は is_active=TRUE だけ）。非アクティブ由来の件数は未確認。設計は件数に依存しない形にする（design.md §4-1）。

## 5. 部品・金型

- `frontend/src/components/DataTable.tsx:100` `onRowClick?: (row: T) => void`
  - Enter/Space でも発火する
  - セル内の button/a/input/select/textarea/label では発火しない（:95-99）
- `frontend/src/components/Drawer.tsx:22-32`（size default 480 / wide 1100）
- `frontend/src/components/Tabs.tsx:25-46`（items, activeKey, onChange, variant）、`Stack`、`Callout`、`Card`
- `frontend/src/hooks/useSuperAdmin.ts:19-44`（`{ isSuperAdmin, loading }`）
- UI ガバナンス `docs/CC_UI_GOVERNANCE.md`
  - :7-17 金型を先に探す。無ければ止める
  - :19-27 生 select・生 input・自作タブ・色直値・生 px は CI が赤
  - :31-40 例外は ui-allow（理由＋番号）

## 6. 並行作業

- open PR で対象ファイルを触るもの: #2692（`backend/app/routers/inventory_offers.py`、2026-06-29 から更新なし）だけ。
- #4358（閲覧ページ段1）は対象ファイルを触らない。
- active-work.d に対象ファイルを触る進行中の作業は無い（192件を grep）。

## 7. テストと実行コマンド

- 関係する既存テスト:
  - フロント: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`、`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.acked.test.tsx`, `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`, `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.test.tsx`、`frontend/src/pages/inventory/InventoryPage.noechopatch.test.tsx`, `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx`, `frontend/src/pages/inventory/InventoryPage.settings.test.tsx`, `frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx`, `frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx`
  - バックエンド: `backend/tests/test_inventory_distribution_rows.py`、`backend/tests/test_inventory_distribution_rows_pg.py`、`backend/tests/test_inventory_list_view.py`、`backend/tests/test_inventory_offers_rbac.py`、`backend/tests/test_tcg_analysis_review.py`
- コマンド:
  - フロント `npm run build` / `npm run lint` / `npm run test:unit`（`frontend/package.json`）
  - バックエンド `pytest -q --tb=short`（`backend/Makefile:29-31`）/ `make lint`

---

## 便2 追補 recon（2026-10-16・Gemini 列「—」・システム商品名・Gemini 要約）

PO 指摘（2026-10-16、便1 本番反映後の画面確認）: 「商品名が未解決になっているのだがこれはなぜ？」→ PO 決定「geminiは原文を抽出するだけなので行番号と数量と単価以外は"-"と表示するのが正解でシステムが未解決になっているのは修正したい。それとgeminiの要約もスライドページ内に表示することは出来る？見える化したい」→ 進め方に「合意」。

基準: origin/main 539b0fe41。本番 DB は 2026-10-16 に SELECT のみで確認（生出力 /tmp/CC報告ファイル/inv-drawer-name-db*.txt, inv-drawer-summary-db2.txt, inv-drawer-fix-db.txt）。

### R2-1 なぜ「未解決」か（事実）
- 本番の既定エンジンは v102（docker-compose.yml:226 `LINE_ANALYSIS_ENGINE=${LINE_ANALYSIS_ENGINE:-v102}`、2026-10-10 537cb910c 便E で既定切替）。
- v102 の extraction_items INSERT は id, extraction_job_id, line_start, line_end, raw_price, raw_quantity, source_lines, gemini_index, created_at のみ（backend/app/services/line_analysis_v102_svc.py:497-510）。raw_product_name / raw_unit / raw_state / raw_memo は書かない。設計上も「v102 の件の名前は Gemini の出力ではないので入れない」（docs/handoff/v102-prod-switch/design.md:72）。
- 本番 DB: raw_product_name が空の件数は 10/9 まで 1日0〜3件、10/10 から全件（10/10 1336/1336 … 10/16 433/433）。例 extraction_items 4b3ba85d-…（L11-12「◎30th CELEBRATIONカードセット 9種セット / 23,000@20」）は raw_quantity=20・raw_price=23,000 以外は空文字。analysis_results.product_id=440301、products.name「MEGA 30th CELEBRATION カードセット（9種セット）」。
- API: backend/app/services/tcg_analysis_review_svc.py:240,308 `gemini.name = ei.raw_product_name or ""`、:309-314 unit/state/memo も同様。:252,320 で `system.product_title = p.name`（商品マスタ名）を既に返している。:268 `is_v102 = starts_with(ej.prompt_version, :v102_prefix)` を返している。
- 表示: frontend/src/features/tcg-analysis-review/ItemComparison.tsx:56-57 Gemini 列は `rawValue(item.gemini[key]) || unresolved`。:39 systemCell は name を `item.gemini.name || unresolved`、採用元 geminiExtracted。system.product_title は ItemComparison.tsx で一度も参照されていない（`git log -S product_title -- ItemComparison.tsx` 0件）。この判定の起源は 4b5d526c9（2026-09-02、v6 時代）で、v102 切替時に見直した記録は見つからない。
- 在庫表タイトルは tcg_distribution_svc.py:293 `COALESCE(p.name,'')`（同じ商品マスタ）。在庫表の名前とスライドの「未解決」が食い違う理由はここ。
- 比較表は要確認ページ（ReviewItemDrawer.tsx:199）・仕入元詳細（SupplierDetailView.tsx:116）・在庫表スライドで共用。要確認ページの 10/10 以降の行も同じ症状。

### R2-2 i18n キー（事実）
- `tcgAnalysisReview.notApplicable` = "—"（frontend/src/locales/ja.json:4694, en.json:4694）。ItemComparison.tsx:52 で `na` として作品・商品ID・販売状況の Gemini 列に使用中。
- `tcgAnalysisReview.unresolved` :4686、`tcgAnalysisReview.systemConfirmed` :4701「System確定」、`tcgAnalysisReview.geminiExtracted` :4700。
- 既存テスト frontend/src/features/tcg-analysis-review/ItemComparison.test.tsx:38-44, :49, :64-66 が現行の判定を固定している。

### R2-3 Gemini の要約（事実）
- 保存先は public.extraction_attempts.thought_summaries（jsonb 配列。migrations/20261012_200000_add_extraction_attempts_thought_summaries.sql:2）。書き込みは backend/app/services/tcg_extraction_record_svc.py:133-170。
- 本番: 記録ありの試行は 10/12 29/78、10/13 以降は全件（10/16 33/33）。配列要素数は最大1、文字数は平均 2541・最大 4126。英語。1つの抽出ジョブ（＝投稿）に1つ。completed の試行が2件以上あるジョブは 228。
- 索引 ix_pub_extraction_attempts_job_started (extraction_job_id, started_at DESC, id DESC) が本番にある。
- 画面で表示している部品は無い（frontend で `thought_summar|thoughtSummar` 0件）。読み出しは super admin 専用の診断 API の個別取得（tcg_extraction_record_svc.py:273-295、routers/tcg_diagnostics.py:113-129）だけ。
- 「ジョブの最新の試行」を選ぶ既存 SQL の型: backend/app/routers/tcg_analysis_dashboard.py:1089-1094 の LEFT JOIN LATERAL（failed 版）。
- analysis-results の応答型 AnalysisResultItem（backend/app/routers/tcg_analysis_review.py:81-93）。未定義キーは response_model で落ちるため、足すなら型にも足す必要がある。
- 要確認ページの1ページは20件（NeedsReviewTabsPanel.tsx:25 PAGE_SIZE）、API の上限は 500（tcg_analysis_review.py:126）。

### R2-4 部品（事実）
- frontend/src/components/ に折りたたみ（Accordion/Disclosure/Details）と長文表示の金型は無い。
- ReviewItemDrawer.tsx の構成: 理由ブロック :155-191 → TwoColumn（原文 | 比較）:192-206 → 修正ウィザード :207-217。原文・比較の見出しは同ファイルの既存見出しの型を使っている。
- 原文の折り返し表示の既存 CSS: frontend/src/features/tcg-analysis-review/source-raw-pane.css:56（white-space: pre-wrap）。

## 便3 追補 recon（2026-10-16・スライドで直す機能）

PO 決定（2026-10-16）: 質問「スライドから直したら、DB・シート・閲覧ページも更新されるようにしますか？（y/n）」に「y」。
調査: Sonnet（読み取りのみ）＋本番の読み取り2件（Opus）。生出力: /tmp/CC報告ファイル/inv-edit-recon-*.txt、inv-edit-recon2-*.txt、inv-edit-recon3-*.txt、inv-edit-env.txt、inv-edit-engine-count.txt。

### R3-1 直す操作と書き込み先（正本は analysis_results）
| 操作 | API | 書き込み |
|---|---|---|
| 商品の付け替え | POST /tcg/items/{id}/corrections（field_name=product_id） | item_corrections に INSERT＋同じ取引で public.analysis_results の product_id・pid_basis='MANUAL'・pid_resolved を UPDATE（backend/app/services/item_corrections_svc.py:59-73） |
| 状態 | 同上（condition_review） | item_corrections INSERT（backend/app/services/tcg_condition_review_svc.py:373-376）＋ analysis_results の condition_* を UPDATE（:378-388） |
| 数量・単価・単位・メモ・販売状況 | POST /tcg/items/{id}/value-override | item_corrections INSERT＋ analysis_results UPDATE（backend/app/services/v102_human_decisions_svc.py:480-487） |
| 商品マスタ登録・検索ワード追加 | POST /tcg/products、/tcg/products/{id}/search-keywords | public.products 等（analysis_results は書かず、画面がそのあと付け替えを呼ぶ: frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx:205,259） |
- 権限: 書き込み API はすべて `require_super_admin`（backend/app/routers/item_corrections.py:148,199,231,273,301）。在庫表のスライドは super admin かつ PC のときだけ開く（frontend/src/pages/inventory/InventoryPage.tsx:603）。
- 無効なソース由来・is_current=FALSE・v6 の行を拒否する条件は無い（review-ack だけ v6 を 409: v102_human_decisions_svc.py:455-466）。拒否は item 無し 404 と source_message_id 不一致 422（:446-452）。

### R3-2 再解析で人の修正は消えない
- run_v102_analysis は item_corrections を読んで反映する（backend/app/services/line_analysis_v102_svc.py:1293 → v102_human_decisions_svc.py:231、商品 :808-809、状態 :810-818、値 :954-956）。v6 の解析も値の修正を読む（backend/app/services/tcg_analyzer_svc.py:1477）。
- 固定テスト: backend/tests/test_v102_human_decisions_pg.py:116,143,195、backend/tests/test_v102_value_overrides_pg.py:93。

### R3-3 直したあとに続いて起きること（コード上）
| 経路 | v102 の行 | v6 の行 |
|---|---|---|
| 商品付け替え | 再解析を積む（item_corrections.py:180-181）→ 再解析後に tcg.review の合図（backend/app/tasks/tcg_extraction.py:696-703）とシート配信の予約（:670-693） | analysis_results の UPDATE だけ。**配信予約も合図も無い**（item_corrections.py:180-181 は v102 だけ） |
| 状態 | 同上（item_corrections.py:159-160 → :124-131） | **同上（配信予約なし）** |
| 値5項目 | 再解析→合図・配信予約。middleware も合図（backend/app/realtime/topics.py:15-22） | 配信予約を直接呼ぶ（item_corrections.py:288-290）。middleware が合図 |
- 定期的なシート配信は無い（backend/app/celery_app.py の beat に配信タスクなし）。したがって v6 の商品・状態の修正は、次に別の投稿の抽出や修正が配信を予約するまでシートに出ない。
- 本番の TCG_AUTO_DISTRIBUTE: backend と celery-worker の両方で `1`（2026-10-16 読み取り、/tmp/CC報告ファイル/inv-edit-env.txt）。
- 配信予約は60秒後に1回（Redis キー nx・TTL 600秒）。解析中（analysis_runs 未完了など）は保留（backend/app/services/tcg_distribution_svc.py:867-927）。

### R3-4 在庫表・閲覧ページの出どころ
- アプリ在庫表 GET /inventory は、読むたびに analysis_results を直接読む（backend/app/routers/inventory_offers.py:314-424、tcg_distribution_svc.py:274〜）。写しは無い。画面の再読み込みは検索・絞り込みの変更時だけで、合図の購読も定期取得も無い（InventoryPage.tsx:195-247）。
- 閲覧ページ（ADR-1019）は1分ごとに build_distribution_rows の結果を Redis に置き、それを返す（backend/app/tasks/viewer_inventory_cache.py:72-99、backend/app/celery_app.py:181-185、backend/app/routers/viewer.py:205-218）。analysis_results が直れば最大約1分で変わる。
- 合図 tcg.review は global 範囲で、super admin の接続だけに届く（backend/app/realtime/hub.py:32-41）。購読フック useRealtimeRefresh(topics, reload)（frontend/src/hooks/useRealtimeRefresh.ts:15）は自分が出した合図を無視し、1.5秒まとめて1回 reload する。

### R3-5 スライド部品の現状
- InventoryRowDrawer は ReviewItemDrawer に item・viewOnly・onClose・onRefresh={load}・headerSlot を渡す。load は ID 指定でスライドの中身だけ取り直し、在庫表の一覧は取り直さない（frontend/src/features/inventory/InventoryRowDrawer.tsx）。InventoryPage から InventoryRowDrawer への props は row・onClose だけ（InventoryPage.tsx:622）。
- ReviewItemDrawer に key が無く、タブを切り替えても内部の state（選んだ行 scope など、ReviewItemDrawer.tsx:50-62）が持ち越される。
- viewOnly を外すと、理由が空の行でも比較表の行クリックで修正ウィザードが出る（ReviewItemDrawer.tsx:70,205,214-223、reviewFixRows.ts）。商品行は「付け替え」（未登録系の理由があれば「マスタ登録」も）、値の行は「値の修正」、状態は isConditionFixable のときだけ（ReviewFixWizard.tsx:37-62）。
- 直したあと onRefresh が呼ばれる: ReviewProductFixForm.tsx:81、ReviewRegisterProductForm.tsx:175、ConditionReviewPanel.tsx:74、ReviewValueFixForm.tsx:89。

### R3-6 本番の在庫表の行（まとめ前・簡略条件）
| 由来 | 行 | 投稿 | うち無効なソース由来 |
|---|---|---|---|
| v102 | 1861 | 348 | 1019 |
| v6 | 1619 | 450 | 1405 |
（/tmp/CC報告ファイル/inv-edit-engine-count.txt。条件は distribution_rows_sql の簡略版。状態の除外・投稿の古さ・まとめを省いたため、画面の件数とは一致しない。v6 の行が現に多数あることの確認に使う）

### R3-7 既存 ADR
- ADR-1014（在庫表＝配信行）、ADR-154（配信は needs_review=false）、ADR-158（is_current）、ADR-1016（即時反映の合図）、ADR-1019（閲覧ページ・写しを作らない）。「在庫表のスライドで直したら配信される」を決めた ADR は無い（git grep -i docs/adr distribution|配信|item_corrections|human_decision、FEATURE-INDEX.md）。

## 便4 追補 recon（2026-10-16・原文だけのタブ）

PO 決定（2026-10-16）: 質問「この理解で設計に進めてよいですか？（y/n）」に「y」。理解の中身: super admin はスライドに「解析」「原文」の2タブ、在庫表を見られるその他の人（admin と、admin が在庫表の閲覧権限を付けた人）は原文だけのスライド、PC のみ。
調査: Sonnet（読み取りのみ・本番は \d と pg_class の読み取り）。生出力: /tmp/CC報告ファイル/drawer-rawtext-tab-recon.txt、drawer-rawtext-tab-recon2.txt。

### R4-1 今スライドを開ける人（事実）
- 入口: frontend/src/pages/inventory/InventoryPage.tsx:603 `onRowClick={isSuperAdmin && !isMobile ? (row) => setDrawerRow(row) : undefined}`（isSuperAdmin は :137 useSuperAdmin、isMobile は :136）。
- スライドが呼ぶ API はすべて `require_super_admin`（backend/app/auth/dependencies.py:516-544）。読み込みは GET /tcg/analysis-results（backend/app/routers/tcg_analysis_review.py:138）。
- 非 super admin のクリックで開かないことは frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx:79-88（F2）が固定している。

### R4-2 在庫表を見られる人（事実）
- GET /inventory は `require_permission("products.view")`（backend/app/routers/inventory_offers.py:310-314）。フロントの画面側に role の門は無く、左メニューは `hasPermission("products.view")`（frontend/src/components/DesktopShell.tsx:267）。
- require_permission は全ロールの権限キーの和集合で判定し、内部で get_current_tenant を通す（dependencies.py:623-649、:636-638）。owner/admin のシステムロールは全キー（admin は system.manage 除く: backend/app/auth/system_roles.py:22-37）。ロールの権限は admin が PUT /roles/{role_id}/permissions で付ける（backend/app/routers/roles.py:403-）。
- 結論: 「admin と、admin が在庫表を見る権限を付けた人」＝ products.view を持つ人。新しい権限キーは要らない。

### R4-3 原文の出どころ（事実）
- public.source_messages.raw_text（投稿全体。送信者名は入らない: backend/app/services/tcg_line_import_svc.py:195,318,361）。該当行は extraction_items.line_start/line_end。
- 既存の取得 SQL: backend/app/services/tcg_analysis_review_svc.py:239-304（raw_text :252、line_start/line_end :260-261）、span 作成 :317-321。
- 表示部品: frontend/src/features/tcg-analysis-review/ShadowSourcePane.tsx（props rawText・blockRange・headingRange :18-22。行番号つき・該当行を強調してスクロール :34-39）。ReviewItemDrawer.tsx:193-199 で `<ShadowSourcePane rawText={item.raw_text} blockRange={parseSourceLineRange(item.gemini.span)} />`。

### R4-4 テナントの区別（事実・設計を左右する）
- 本番 \d: public.analysis_results / extraction_items / extraction_jobs / source_messages / supplier_channels に tenant_id 列なし、RLS なし（pg_class relrowsecurity=f）。
- GET /inventory も tenant の WHERE を持たない。行の定義は distribution_rows_parts（backend/app/services/tcg_distribution_svc.py:286-）の dist_base だけで、テナント差は suppliers・products の RLS（名前が空になる）だけ。
- 「extraction_item_id が在庫表の行か」を確かめる既存関数は無い。dist_base の item_key（ei.id::text、:321）で判定できる。
- 結論: 原文 API の門は「GET /inventory と同じ配信行の定義（dist_base）に含まれる extraction_item だけ返す」。これで在庫表に出ていない投稿の原文は返らない（ID の総当たりで全投稿を読めない）。在庫表そのもののテナント分けは今回の範囲外（現状どおり）。

### R4-5 在庫行から原文への鍵（事実）
- /inventory の各行に `extraction_item_ids: list[str]` がある（backend/app/schemas/inventory_offers.py:160、組み立て inventory_offers.py:179、SQL tcg_distribution_svc.py:277）。まとめ行は全件。

### R4-6 部品・テスト・ADR（事実）
- タブの金型: frontend/src/components/Tabs.tsx:25-44（items/activeKey/onChange、variant underline|pill、size sm|md）。InventoryRowDrawer.tsx:67-72 がまとめ行の切替に pill を使用中。
- i18n: inventory.rowDrawer.{title, loadError, notFound, itemTab}（frontend/src/locales/ja.json:1456-1461）、reviewItem.sourceHeading（:3798）。
- テスト: frontend は `cd frontend && npx vitest run --config vitest.unit.config.ts --project unit <path>`、backend は `cd backend && pytest -q --tb=short <path>`。RBAC の前例 backend/tests/test_inventory_offers_rbac.py、実 PG の前例 backend/tests/test_inventory_distribution_rows_pg.py。
- ADR: ADR-1014（在庫表＝配信行・定義は1か所）、ADR-027、ADR-144、ADR-072（新規 router の tenant 文脈）。在庫表スライドの権限を決めた ADR は無い（docs/adr/FEATURE-INDEX.md・git grep）。

## 便5 追補（2026-10-17）原文枠の高さ（事実）
- frontend/src/features/tcg-analysis-review/shadow-source-pane.css:35-41 `.shadow-source-lines { --shadow-source-max-h: 320px; max-height: var(--shadow-source-max-h); overflow-y:auto; ... }`、:3-10 `.shadow-source-pane` は display:flex; flex-direction:column。
- 前例: frontend/src/features/tcg-analysis-review/review-item-drawer.css:19-29 が親配下で `.shadow-source-lines { flex:1; min-height:0; max-height:none; }` と上書き。
- frontend/src/components/Drawer.css:25-41 パネルは height:100dvh・flex column、:85-89 `.comp-drawer-body { flex:1; overflow-y:auto; padding: var(--space-5) var(--space-6) }`（block）。
- frontend/src/components/Stack.tsx:13-21 は className を受けて結合する。InventoryRowDrawer.tsx の RawTextPane は `<Drawer><Stack gap="4">{modeTabs}{itemTabs}{状態表示}{ShadowSourcePane}</Stack></Drawer>`。

## 便6 追補（2026-10-17）原文スライドの見出しと凡例（事実）
- 詳細調査: /tmp/CC報告ファイル/rawtext-header-recon.md
- frontend/src/features/tcg-analysis-review/ShadowSourcePane.tsx:18-22 Props は rawText/blockRange?/headingRange?。:43-54 で div.shadow-source-legend を常に描画。呼び出し元は frontend/src/features/inventory/InventoryRowDrawer.tsx・frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx・frontend/src/features/tcg-analysis-review/V102PostEditModal.tsx の3か所。
- frontend/src/features/inventory/InventoryRowDrawer.tsx:171 付近 RawTextPane の Drawer title は t("inventory.rowDrawer.tabRawText")。:204 付近のモード切替タブも同キー。
- frontend/src/features/inventory/inventoryColumns.tsx:12-35 InventoryRow に supplier_id/supplier_name/offered_at/posted_at。:151-163 提供者列は仕入元名（:160）と fmtOfferedAt(it.offered_at)（:161）。
- frontend/src/pages/inventory/InventoryPage.tsx:172-178 に fmtOfferedAt がローカル定義（YYYY-MM-DD HH:mm・無効は "-"）。
- frontend/src/components/Drawer.tsx:25 title は string。
- 出どころ: distribution_rows_parts の dist_base（provider=public.suppliers.name、posted_ts=source_messages.line_posted_at）（backend/app/services/tcg_distribution_svc.py:300-313）。まとめ行は同一投稿内のみ（:326-328）なので1行で仕入元・投稿日時は1つ。
