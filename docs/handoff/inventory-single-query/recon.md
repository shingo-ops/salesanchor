# recon: 在庫表 GET /inventory を1文にする（便 inventory-single-query）

実測時の origin/main: d1dd0ad62edfa1b3ce63ad5273da8ff5ee11e1d7（作業ブランチの土台は 4803be06712f31b7590da7d768aa838626316ee4）。事実のみ。調査の原本は /tmp/CC報告ファイル/same-post-rows/sp2/perf2/（RESULT-experiment2.md、experiment2.py。リポジトリ外・設計者保管）。

## 対象 ADR 検索
- `git grep -il "list_inventory_view\|distribution_rows_sql\|/inventory" docs/adr/` の該当: docs/adr/ADR-093-inventory-table-product-master-redesign.md、docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md（在庫表が配信行を出す決定）、ほかに ADR-1004・ADR-140（言及のみ）。本便は決定を変えず性能のみ。新規 ADR なし。

## 事実
- 在庫表 1回の表示は配信行 SQL を3回走らせる（COUNT・ページ・facets）: backend/app/routers/inventory_offers.py（変更前 list_inventory_view 内の3つの db.execute）。
- 配信行 SQL の定義は1か所: backend/app/services/tcg_distribution_svc.py の distribution_rows_sql（変更前 :256-355）。WITH 句（base。merge 時は dist_merged まで）と最終 SELECT（_distribution_final_select）からなる。
- 本番実測（perf2/RESULT-experiment2.md）: dist_base を共有する1文（S2）が現行3文（S0）と全12通りで total・page・facets 一致。1回の表示は約1.5秒から約0.5秒。
- 既存テストが distribution_rows_sql のソース文字列を検査している: backend/tests/test_tcg_distribution.py（flag_filter_exclude、search_keywords 13列目、ship_ja 14列目の3件）。SQL 本文は distribution_rows_parts へ移るため、検査対象の関数名を差し替えた。
- 文字列不変の根拠: 変更前（4803be067）の distribution_rows_sql を age_condition=" AND x = :y" で4通り（include_flag_single × merge）呼んだ出力の長さと SHA-256 を backend/tests/test_inventory_distribution_rows.py の _GOLDEN に固定（旧実装をテスト内で再現しない）。

## 未確認
- PostgreSQL が要るテスト（test_inventory_distribution_rows_pg.py）は手元で未実行（CI 専用）。
