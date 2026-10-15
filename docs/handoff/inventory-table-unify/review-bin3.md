# 便3 検索と提供者 コード審査（Opus・2026-10-15）

対象: release/inventory-table-bin3 e5f244ce4（実装は Sonnet。設計 design.md「便3 検索と提供者」3-1〜3-3、審査 N-r3-8）

判定: **APPROVE**

## 照合した点（実物）
- 3-1 検索（backend/app/routers/inventory_offers.py）: normalize_search_text は NFKC → lower → ひらがな+0x60。_SEARCH_MAX_TERMS = 10、空語を捨てる、語が0個なら条件なし。各語は strpos(translate(lower(normalize(concat_ws(E'\n', japanese_title, english_title, mark, search_keywords), NFKC)), CAST(:kana_from AS text), CAST(:kana_to AS text)), CAST(:qt{i} AS text)) > 0 の AND。provider・product_id・category は対象外。q の description を更新。値はすべて bind。
- 3-2 提供者: supplier_ids Query（max_length 2000）、_build_view_filters に既定値 None のキーワード引数、整数だけ IN、整数0個なら絞らない。hide_supplier_ids の引数と処理は残る。_build_view_filters の呼び出し元は list_inventory_view の1か所（grep）。
- frontend: 検索ボタン削除・Enter で runSearch（setDebouncedQ + page=1）・250ms 待ちは残る。プレースホルダは新キー inventory.view.searchNameCode。selectedSupplierIds は保存しない、選択があれば supplier_ids を送る、変えたら page=1。PC はツールバー、スマホは InventoryFilterPanel 先頭に MultiSelect（testId inventory-supplier-filter）。仕入元除外欄と hide_supplier_ids の送信を削除、旧 props（supplierFacet・hiddenSupplierIds・toggleHiddenSupplier）を削除（N-r3-8）。buildFilterPayload は不変。
- 共通ベクタ frontend/src/features/inventory/searchNormalize.vectors.json を Python と JS の両テストが読む。
- 追加差分に style= / 色の直値 / 生 select・input・table は 0 件（grep）。日本語リテラルはテストで String.fromCodePoint に変更（ADR-027 の ESLint 警告対応、eslint-disable なし）。

## 速さ（本番 DB・読み取り専用 EXPLAIN ANALYZE、q="ポケモン"。生出力 /tmp/CC報告ファイル/inventory_bin3/baseline_*.txt）
- 変更前の SQL: 452.718 / 456.525 / 456.388 ms
- 変更後の SQL: 508.969 / 514.990 / 510.878 ms（基準 1 秒未満を満たす。約 +56ms）
- 反映後に本番で同じ語を3回測る（3-3）。

## 検査（Sonnet 実行・生出力 /tmp/CC報告ファイル/inventory_bin3/）
- PG テスト test_inventory_distribution_rows_pg.py: 47 passed（pytest_pg_all.txt）。非 PG: 78 passed / 24 skipped。
- tsc 0 / lint 0 / check:all 0 / generate:api-types 0 / eslint（変更6ファイル）0。
- vitest（在庫表・features/inventory）: 7 ファイル 36 件成功。全件はマシン負荷で待ち時間切れが出るため CI で確認する。
- 途中でディスク満杯（ENOSPC）によりコミットが中断。index に残った全変更から作業ツリーを復元し、lint-staged の退避と差が修正1行だけであることを確かめてから退避を削除した。

## 残す点
- 本番で PO 目視（KGI 1・2・3）。反映後の速さの実測。
