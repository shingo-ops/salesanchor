# recon — アプリの在庫表を GAS 在庫一覧と同じ作りにする（2026-10-15）

照合の基準: origin/main 4866be5bf（作業ブランチ release/inventory-table-unify の HEAD e1cdbc468 と frontend/src・backend/app の差は 0 件。`git diff --stat e1cdbc468 origin/main -- frontend/src backend/app` の出力が空）。
GAS の基準: 本番 GAS を clasp pull した index.html（以下 H）。生出力は /tmp/CC報告ファイル/app_inventory_recon_20261015/（gas_behavior.md・recon2〜4.md）。

## 0. 既存 ADR の検索結果

`git grep -il -e sticky -e DataTable -e 金型 -e fitTableZoom -- docs/adr/` と FEATURE-INDEX を照合した。関係するもの:

| ADR | 関係 |
|---|---|
| docs/adr/ADR-093-inventory-table-product-master-redesign.md | 在庫表の列・並び替え（全列ソート）。商品マスタの見出し固定の前例 |
| docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md | 在庫表は LINE 解析の配信行（GAS と同じ行）を出す。行の SSOT |
| docs/adr/ADR-067-design-token-enforcement.md | 色・寸法はトークンのみ |
| docs/adr/ADR-144-ui-component-governance.md | 金型を先に確認・生 input/select/自作タブ禁止・例外は ui-allow |
| docs/adr/ADR-027-ui-internationalization.md | 文言は t() のみ・ja/en 同一キー |
| docs/adr/ADR-087-hub-shell-layout-standard.md / ADR-140-mobile-nav-bottom-tabs.md | PC とスマホの外枠。スマホ判定は useIsMobile（767px 以下） |
| ADR-1019（旧番号 ADR-1017。2026-10-15 に付け替え）（Draft PR #4283 側） | 閲覧専用ページ。本件の部品を共用する予定 |

## 1. GAS の動き（本番）

- 検索: frontend 側で入力ごとに絞る。正規化は NFKC → 小文字 → ひらがなをカタカナ（H:987-993）。対象は日本語名・英語名・Mark・Search Keywords（H:1170-1172）。空白で区切った語をすべて含む行だけ（H:1345-1346, 1364-1366）。プレースホルダ「商品名・型番で検索」（H:818）。
- 並び替え: プルダウン4択（H:834-839）。見出しクリックでも並べ替え（H:1572-1588）。第1キーは英語名の昇順（H:1388-1421）。
- 提供者: 複数選択のチェック一覧。選んだ人だけを出す。未選択なら全員。保存しない。先頭に「選択をクリア」。ボタン表示は 0件「提供者: すべて」／1件 名前／2件以上「N件」（H:884-887, 1256-1328, 1369-1370）。
- 見出し固定: thead sticky top:0、商品名列 sticky left（H:405, 427-434）。
- 幅に合わせて縮める: fitTableZoom（H:1506-1569）。768px 以上のみ。定数 MAX_ZOOM_ADJUST_STEPS=200 / ZOOM_ADJUST_DECREMENT=0.001 / ZOOM_PRECISION=1000。natural = scroll.scrollWidth + card の左右 border、frame = #content.clientWidth、z = floor(min(1, frame/natural)×1000)/1000、その後 scrollWidth > clientWidth の間 0.001 ずつ下げる（最大200回）。resize は rAF で間引き、matchMedia change でも再計算。
- スマホ（767px 以下）: 縦のカード、項目7個（H:700-760）。
- バッジ: 完全一致で sealed=緑・damaged=赤・case=青・他=グレー（H:461-473, 1591-1605）。
- ページ送り: なし（アプリはあり。PO 決定 12 でアプリ側を残す）。

## 2. アプリの今（origin/main）

### 2-1. 画面 frontend/src/pages/inventory/InventoryPage.tsx（771行）
- 保存する絞り込み: buildFilterPayload（:95-108）に hidden_supplier_ids を含む。列の出し分け候補 HIDEABLE_COLUMNS（:111-113）に "category" を含む。
- 状態: sortField "release_date" / sortDir "desc"（:134-135）、activeTab 既定 "pokemon_booster_box"（:136）、PER_PAGE 50。
- 読込 load（:204-255）: hide_supplier_ids はフィルタ有効のときだけ送る（:219-221）。提供者の候補は API の suppliers（:245）。
- 保存済み設定 GET（:273-326）／PATCH（:329-354）。
- 並べ替え onSort（:366-373、別列は asc から）。resetAll（:376-383）は sortField "name"・asc に戻す → 既定（release_date desc）と食い違う【事実】。
- ツールバー: 検索入力 :505-516、検索ボタン :517（testid inventory-search-btn）、リセット :520、24時間 :523-534、フィルタ :535-544。
- 自作タブ :596-624（ui-allow #2624）。
- 表は生の table（:641-746）。category 列 :651, :684-686。商品名 :688-694（日本語が上・英語は font-sm）。区分 :701-716（badge-negotiating）。数量・まとめ :717-726。単価 :728。仕入元と掲載時刻 :730-737。備考 :738、発送 :739、発売日 :740。sortTh :425-460 にインライン style。
- ページ送り :748-768（testid inventory-prev / inventory-next / inventory-pagination-label）。

### 2-2. フィルタパネル frontend/src/pages/inventory/InventoryFilterPanel.tsx（312行）
- 仕入元は「外したものを隠す」チェック（:152-173、checked={!hiddenSupplierIds.has(s.id)}）。生の checkbox とインライン style。

### 2-3. API backend/app/routers/inventory_offers.py
- 検索 q（:184-189）: `d.provider / japanese_title / english_title / product_id::text / category / mark` の ILIKE `%q%`。正規化なし・語の分割なし・検索ワード対象外。
- hide_supplier_ids（:190-195）: 整数だけ採って NOT IN。
- _SORT_COLUMNS（:118-130）。並び（:245-248）は第1キー english_title 昇順。
- 引数（:288-312）: sort 既定 release_date、order 既定 asc、per_page ≤200。
- 候補（facet）はまとめなし・絞り込みなしの配信行から作る（:370-378）→ 提供者で絞っても候補は消えない【事実】。
- 検索ワード: backend/app/services/tcg_distribution_svc.py:302-306 の dist_base に search_keywords（product_search_keywords を ' | ' で連結）がある。最終 SELECT は plain と merged で同じなので、在庫表の WHERE から d.search_keywords を参照できる【事実】。

### 2-4. 本番 DB（読み取り専用）
- server_encoding = UTF8。`SELECT normalize('ｱ１Ａ', NFKC)` → `ア1A`。PostgreSQL の normalize が使える【事実】。

## 3. 金型（frontend/src/components）

- 無いもの: checkbox・switch・chip・複数選択（MultiSelect）の金型【事実】（recon4 Q1）。
- Popover.tsx: props は children / content / placement / open / onOpenChange / className。document.body へ Portal、外側クリックで閉じる。:140 にインライン style（display:inline-flex）。
- DataTable.tsx（330行）: 列 props :29-46（key, header, width, ellipsis, sortable, renderCell）、本体 props :51-93（sortKey, sortDir, onSort, selectable, selectedKeys, onSelectChange, density, emptyState, className, onRowClick, page, hasNextPage, onPageChange, prev/nextPageLabel, pageInfo, rowClassName）。handleSort :158-163（同列は反転・別列は asc）。ラッパー :174 `<div class="comp-table" role="region">`。選択列に生 checkbox（:180, :268）。ページ送り :303-327。
- 見出し固定、幅に合わせて縮める、スマホのカード表示は DataTable に無い【事実】。
- 見出し固定の前例: frontend/src/components.css:136-155（`.products-master-table-wrap { max-height: calc(100vh - 18rem); overflow: auto }`、thead sticky top:0 z-index var(--z-base)）。
- Badge.tsx: variant = neutral / info / success / warning / danger。値→variant の対応は呼び出し側で決める（:11）。
- Select.tsx 内の SelectControl: options / placeholder / size / fullWidth / appearance / variant / indicator。placeholder は value="" の option。
- トークン frontend/src/tokens.css: --z-base 10 / --z-dropdown 50、--breakpoint-tablet-min 768px（:115）、--size-checkbox 16px（:226）、--dropdown-max-h 200px（:348）、--comp-table-*（:434, :507-521、check-col-w 40px・min-width 480px）。
- useIsMobile（frontend/src/hooks/useIsMobile.ts）: matchMedia max-width 767。BREAKPOINTS は frontend/src/constants/breakpoints.ts。

## 4. 影響を受けるテスト（recon3 f〜h）

- hidden_supplier_ids / hide_supplier_ids: AllLegacyButtonDynamicMigration.test（初期値に持つだけ :16。影響なし＝審査 r1 N-5）、InventoryPage.noechopatch.test、InventoryPage.singlefetch.test:57-63（hide_supplier_ids=1 を期待）、backend test_me_inventory_filters、test_inventory_distribution_rows(_pg)。
- testid: CommerceNavigationButtonMigration.test:58-71（inventory-prev/next）、InventoryPage.settings / noechopatch / singlefetch（inventory-row-*、-merged）。
- backend の test_inventory_search*.py は別 API（/inventory/search）のもので、/inventory の q とは無関係【事実】。

## 5. 未確認・PO 判断待ち（本件では決めない）

- 更新ボタン（PO 項目1）: 未決 → 入れない。
- 英語名が空の 33 商品: データの欠け。登録は候補を PO に見せてから（本件の外）。
- バッジの色を GAS の完全一致より広げるか: 未決 → GAS と同じ完全一致にする。
