# recon: 並び替えで状態のまとまりが崩れる件（在庫表・閲覧ページ・GAS 在庫一覧）

基準: origin/main 837245a2d。生出力は /tmp/CC報告ファイル/inventory-sort-cond-block/（summary.txt・gas_grep.txt・gas_sort_1385-1465.txt・test_lines.txt）。

## 既存 ADR の検索
- docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:40-48・:70-76（商品のまとまり）・:98-104（印の単位＝商品・ステータス・状態）。
- docs/adr/ADR-1023 :65-73（value_rank を並び順の正本に使う。状態の中は価格の安い順）。
- 前便の設計 docs/handoff/inventory-sort-block-order/design.md。

## 現在地（origin/main 時点）
- アプリ: /Users/tanizawashingo/salesanchor/backend/app/routers/inventory_offers.py:264 `_build_view_order_by`。:279 `ORDER BY {group}, {sort_col} {order_dir} NULLS LAST, d.sort_ord ASC`。状態の価値順は sort_ord にしか無く、選んだ列より後ろ（これが原因）。rows_x の定義は :299。
- sort_ord の式: /Users/tanizawashingo/salesanchor/backend/app/services/tcg_result_order.py:36-42（発売日→商品→状態の価値順→状態名→価格）、採番は /Users/tanizawashingo/salesanchor/backend/app/services/tcg_distribution_svc.py:348。
- 閲覧ページ: /Users/tanizawashingo/salesanchor/frontend/src/pages/viewer/viewerFilter.ts:172 `sortRows`（発売日→英語名→日本語名→選んだ列→idx）。同じ原因。
- GAS: ~/CC報告ファイル-keep/inventory-block-pill-gas/gas/test_stage/index.html:1393-1453（prod_stage と同一）。シートに状態の順位の列は無い（14列）。
- 試験: /Users/tanizawashingo/salesanchor/backend/tests/test_inventory_distribution_rows.py:117-120（`_VIEW_SQL_BEFORE`）・:134-135（期待文字列）、/Users/tanizawashingo/salesanchor/backend/tests/test_inventory_distribution_rows_pg.py:318-322（旧側 rows_sql）。

## 結論
状態ブロック番号（同じ商品・同じ状態の最小 sort_ord／最小 idx）を各画面でその場で求め、商品キーと選んだ列の間に挟む。新しい列・表は作らない。詳細は design.md。
