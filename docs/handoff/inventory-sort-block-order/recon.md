# recon: 価格などで並べたときの商品の順番（在庫表・閲覧ページ・GAS 在庫一覧）

基準: origin/main 66ef0cc58d2372e314925c008929e3240ce6724a。調査は Sonnet が行い、生出力は /tmp/CC報告ファイル/inventory-sort-block/recon/ にある。

## 既存 ADR の検索
- ADR-1014 は、改訂 2026-10-18 と改訂 2026-10-18（2）で、まとまり（商品）の順と、まとまりの中の順を決めている（`docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:40-57`）。
- ADR-1023 は、同じ商品の中の価値順（sort_ord）を決めている。
- ADR-1019 と docs/CC_UI_GOVERNANCE.md には、並び順の記述が無い（grep で 0 件）。

## 1. 在庫表（サーバーで並べる）
【事実】`backend/app/routers/inventory_offers.py:262-277` の `_build_view_order_by`。
- まとまりの順は 発売日 → english_title ASC → japanese_title ASC NULLS LAST → product_id ASC。
- 発売日の向きは、`sort=release_date` のときだけ order に従う。ほかの並び替えでは `group_dir = "ASC"`（:270）で、発売日の古い順になる。
- まとまりの中は、選んだ列 NULLS LAST → sort_ord（:277）。
- `sort=name` は、english_title と japanese_title を同じ向きで並べる（:268-269）。
- 既定は release_date desc（`frontend/src/pages/inventory/InventoryPage.tsx:122-123`）。
- 本番: このコードを含むコミット 698967013 と bef06874f は、d165f2178 の祖先である。Deploy 39127734950 は d165f2178 で success（2026-10-18 12:37:45Z、`git merge-base --is-ancestor` と `gh run view` で確かめた）。
- 試験: `backend/tests/test_inventory_distribution_rows.py:123-137`（価格で並べたときに group_asc を固定している）、`backend/tests/test_inventory_distribution_rows_pg.py:314`。

## 2. 閲覧ページ（ブラウザで並べる）
【事実】`frontend/src/pages/viewer/viewerFilter.ts:172-193` の `sortRows`。
- まとまりの順は在庫表と同じ。ほかの並び替えでは、発売日を `"asc"` で並べる（:178）。
- 試験は `frontend/src/pages/viewer/viewerFilter.test.ts:61-115`。:75-77 は、価格の安い順で [3,1,0,2]（発売日の古い順のまとまり）を固定している。

## 3. GAS 在庫一覧（リポジトリの外、shingo-ops/tcg-client-viewer）
【事実】読んだのは ~/tcg-viewer-1tb-head/index.html:1387-1432（テスト版23。本番版17 に push した ~/CC報告ファイル-keep/inventory-tab-work-id/gas6/prod_stage/index.html と diff 0）。
- 発売日で並べるときだけ、発売日でまとまりを並べる（:1391-1402）。
- ほかの並び替えでは、English Title の昇順だけでまとまりを並べる（:1404-1412）。
- まとまりの中は、選んだ列で並べる（:1414-1431）。
- 「商品名」見出しは COL.englishTitle（:1456）。降順を選んでも英語名は昇順のままで、向きが効かない。

## 4. 違い（PO の言葉）
PO（2026-10-19）「SAアプリの在庫表はテーブル全体で並び替える仕様になっている」。
【事実】
- アプリも GAS も、まとまりの中だけを並べている。
- 違うのは、価格などで並べたときのまとまりの順。アプリは発売日の古い順、GAS は英語名の順。
- 表全体を並べるのは、商品名の見出しだけ。
【未確認】PO がどの並べ方の画面を見たか。

## 未確認
- 本番 GAS の今の中身。push の前に、別のディレクトリへ clasp pull して確かめる（reference_tcg_client_viewer の手順）。
