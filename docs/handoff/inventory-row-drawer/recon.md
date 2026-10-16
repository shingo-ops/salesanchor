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
