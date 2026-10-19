# recon: 並び替えプルダウンの現状（基準 origin/main 70c3eda3d0d2dae68621637376aa65a3ad71f5b0、2026-10-19 実測）

生出力: /tmp/CC報告ファイル/inventory-sort-3choices/recon/（app.txt viewer.txt be_i18n.txt t.txt t2.txt gas_grep.txt gas_diff.txt SUMMARY.txt）。以下は要点のみ。

## 既存 ADR の検索（着手前）
- docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:46（改訂 2026-10-18「既定のとき空表示にならないようにした」）、:55（「先頭は release_date:desc」）。本便の改訂（6）が置き換える。

## アプリ（SAアプリ在庫表）
- frontend/src/pages/inventory/InventoryPage.tsx:58 SORT_MENU_VALUES（4値）
- frontend/src/pages/inventory/InventoryPage.tsx:127-128 既定 release_date / desc
- frontend/src/pages/inventory/InventoryPage.tsx:467-487 SelectControl（placeholder :472、表示値 :473、onChange :474-480、:476 `if (!field) return;`、選択肢 :481-486）
- frontend/src/components/Select.tsx:100-104 `<option value="" disabled={rest.required}>`（required を渡さないので見出しは選択可能）
- backend/app/routers/inventory_offers.py:374-379 既定 release_date desc（変更不要）

## 閲覧ページ
- frontend/src/pages/viewer/viewerFilter.ts:12-13 既定、:14 コメント「4択」、:15 SORT_MENU_VALUES
- frontend/src/pages/viewer/InventoryView.tsx:197-216 SelectControl（onChange :203-209、:205 `if (!k) return;`、:211 releaseDesc）

## i18n
- frontend/src/locales/ja.json:1563-1568、frontend/src/locales/en.json:1563-1568（inventory.sortMenu）
- frontend/src/locales/viewer/ja.json:28-34、frontend/src/locales/viewer/en.json:28-34（viewer.sort）

## GAS（リポジトリ外 ~/CC報告ファイル-keep/inventory-sort-cond-block/gas/test_stage/index.html、prod_stage と同一）
- :840-845 select、:938-939 sortCol=-1、:975 var COL、:1023-1028 change、:1187-1189 初期化、:1396 sortCol>=0 のとき並べる、:1670-1686 toggleSort
- テスト版 @25 の pull（pull_v25_1792391192）は test_stage と diff 0。本番公開版は @17。

## 試験
- frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx:51-69
- frontend/src/pages/viewer/InventoryView.test.tsx:51-59
