# recon: 在庫表・閲覧ページの既定の並びを「発売日の新しい順」にする

- 基準: origin/main a89341670（git fetch 後）
- 調査の生出力: /tmp/CC報告ファイル/inventory-sort-desc/recon/（pr4499.diff、asc_refs.txt、main_sort_refs.txt、gas_index_1380_1425.txt ほか）

## 既存 ADR の検索
- `git grep -i release_date docs/adr/` と docs/adr/FEATURE-INDEX.md を確認
- docs/adr/ADR-1014-*.md:40-49「改訂 2026-10-18」: 既定の向きを asc（早い順）にした（#4499）。本件はこの向きを desc に改める
- docs/adr/ADR-1014-*.md:37「改訂 2026-10-14」: 第1キーを英語タイトルにした記述（2026-10-18 改訂で上書き済み）
- ADR-1023（状態の価値順）: 同じ商品の中の並び（sort_ord）。本件で変えない

## 現状（発売日の向きを決める箇所）
### backend
- backend/app/routers/inventory_offers.py:264-279 `_build_view_order_by`
  - :272 `group_dir = order_dir if sort_col == release_date else "ASC"`（発売日を選んだときだけ商品のまとまりの向きが order に従う）
  - :274-275 まとまり: `NULLIF(d.release_date,'') {group_dir} NULLS LAST → english_title ASC → japanese_title ASC → product_id ASC`
  - :277-278 発売日を選んだとき、まとまりの中は `d.sort_ord ASC`（#4502 の価値順）
- backend/app/routers/inventory_offers.py:349-354 API 既定 sort=release_date、order="asc"
- backend/app/routers/inventory_offers.py:385 `order_dir = "ASC" if order=="asc" else "DESC"`

### 在庫表（frontend/src/pages/inventory/InventoryPage.tsx）
- :54 `SORT_MENU_VALUES = ["release_date:asc","unit_price:asc","quantity:desc","offered_at:desc"]`
- :111-112 既定 sortField="release_date"、sortDir="asc"
- :331-332 resetAll で setSortField("release_date")・setSortDir("asc")
- :184 API へ order=sortDir を必ず送る
- :445 プルダウンの値は `${sortField}:${sortDir}`
- :454-457 選択肢のラベル。release_date:asc は `inventory.sortMenu.releaseAsc`

### 閲覧ページ（frontend/src/pages/viewer/）
- viewerFilter.ts:12-13 `DEFAULT_SORT_KEY="release_date"`、`DEFAULT_SORT_DIR="asc"`
- viewerFilter.ts:15 `SORT_MENU_VALUES`（4択）
- viewerFilter.ts:120-130 `nullsLast`（向きに関係なく空を末尾に置く）
- viewerFilter.ts:166-189 `sortRows`。:178 で発売日（発売日を選んだときは sortDir）を第1キーにする
- InventoryView.tsx:62-63 既定値は上の定数を使う。InventoryView.tsx:201、:210-213 プルダウンの release_date:asc は `viewer.sort.releaseAsc`

### i18n
- frontend/src/locales/ja.json:1561 `releaseAsc`「発売日が早い順」／en.json:1561 "Release date (oldest first)"
- frontend/src/locales/viewer/ja.json:30 「発売日が早い順」／viewer/en.json:30 "Release date (oldest first)"

### 試験
- frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx:51-64（release_date:asc を既定として assert）
- frontend/src/pages/viewer/InventoryView.test.tsx:55
- frontend/src/pages/viewer/viewerFilter.test.ts:69
- frontend/src/components/CommerceNavigationButtonMigration.test.tsx:47、:48、:62（#4499 で order=asc に変更）
- backend/tests/test_inventory_distribution_rows.py:59-68、backend/tests/test_inventory_distribution_rows_pg.py:306-308（ORDER BY の文字列。asc/desc の両方の場合）

## 保たれるもの（事実）
- 商品ごとのまとまり: 同じ発売日の中は english_title → japanese_title → product_id（inventory_offers.py:274-275、viewerFilter.ts:178-180）
- 同じ商品の中の価値順: まとまりの中は d.sort_ord ASC（inventory_offers.py:278）。閲覧ページは最後に idx（viewerFilter.ts:181）
- 発売日が空の商品: 向きに関係なく末尾（inventory_offers.py:274 の NULLS LAST、viewerFilter.ts:120-130）

## GAS 在庫一覧（リポジトリ外のローカル写し ~/tcg-viewer-1hc-release/）
- index.html:1386-1393 第1キーは英語タイトル昇順。既定のプルダウンは 9_desc「新しい順」（:835）で、発売日は同じ英語タイトルの中だけで使う
- 本件の対象外（PO の指示は「いまは古い順になっている」画面＝在庫表・閲覧ページ。GAS は古い順のまとまりを持たない）

## 未確認
- GAS 本番（1hc）とローカル写しの同一性
- 本番実画面の並び（PO 目視）
