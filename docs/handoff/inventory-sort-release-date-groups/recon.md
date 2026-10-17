# recon: 在庫表の既定の並び順（発売日の早い順・商品ごとのまとまり）

基準: origin/main（2026-10-18 fetch 後）。生出力: /tmp/CC報告ファイル/inventory-sort-order/ と同 gas/（社外に出さない作業記録）。

## 既存 ADR 検索
- `git grep -i "並び\|sort" docs/adr/` → 並び順の決定は docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:37 の1行のみ「並び替えの第1キーを英語タイトルにした（GAS 方式）。タイトル列を並べるときは英語タイトルの昇降を切り替える。」
- 発売日・空欄・まとまり同士の順序の記述は ADR に無い。

## アプリ在庫表（/inventory）
- backend/app/routers/inventory_offers.py:115-127 `_SORT_COLUMNS`。release_date は `NULLIF(d.release_date, '')`。
- backend/app/routers/inventory_offers.py:271-277 ORDER BY:
  - name: `ORDER BY d.english_title {order_dir}, d.japanese_title {order_dir} NULLS LAST, d.sort_ord ASC`
  - それ以外: `ORDER BY d.english_title ASC, {sort_col} {order_dir} NULLS LAST, d.sort_ord ASC`
- backend/app/routers/inventory_offers.py:335-339 sort の既定 "release_date"、order の既定 "asc"。:371-372 で order_dir / sort_col を決定。
- backend/app/routers/inventory_offers.py:61 `i.product_id` を選択。:278 `LEFT JOIN public.products pp ON pp.id = x.product_id`。
- backend/app/services/tcg_distribution_svc.py:330 `COALESCE(p.release_date::text, '') AS release_date`（発売日は商品マスタ p の値＝同じ商品の行は同じ発売日）。:348 `sort_ord = ROW_NUMBER() OVER (ORDER BY result_order_sql())`。
- backend/app/services/tcg_result_order.py:23-35 result_order_sql: `p.release_date DESC NULLS LAST, p.id ASC, 状態ランク, ...`。
- frontend/src/pages/inventory/InventoryPage.tsx:111-112 既定 sortField="release_date"・sortDir="desc"、:331-332 リセットも同じ、:183-184 API へ sort/order を渡す、:585 見出しクリック。
- 並び替えプルダウン: InventoryPage.tsx:53-54, 442-457。選択肢は unit_price:asc「価格が安い順」/ quantity:desc「在庫が多い順」/ offered_at:desc「投稿が新しい」（ja.json:1559-1564）。release_date の選択肢は無く、既定のときプルダウンは空表示（:445 `includes ? value : ""`）。

## 閲覧ページ（viewer）
- frontend/src/pages/viewer/viewerFilter.ts:12-13 DEFAULT_SORT_KEY="release_date"・DEFAULT_SORT_DIR="desc"、:14-15 プルダウン3択（在庫表と同じ）。
- viewerFilter.ts:170-189 sortRows: name 以外は english_title 昇順（空は先頭）→ 選択列 → 元の順 idx。:159-160・:120-131 release_date は空を常に末尾。
- frontend/src/pages/viewer/types.ts:11-27 ViewerRow に product_id は無い（english_title / japanese_title など文字列14列）。

## GAS 在庫一覧（本番 1hc、リポジトリ外 ~/tcg-viewer-1hc-release/index.html）
- :835-838 プルダウン4択（新しい順=発売日降順 / 価格が安い順 / 在庫が多い順 / 投稿が新しい）、既定は「新しい順」(:1180-1182)。
- :1386-1420 sort: 第1キーは English Title の昇順で固定、同じ英語名の行どうしだけ選択列で比べる。まとまり同士は英語名のアルファベット順で、発売日では決まらない。空欄は常に末尾(:1404-1407)。
- GAS の列（~/tcg-viewer-1hc-release/Code.js:10-24）に product_id は無い。

## 観測された症状
- PO 報告: 「25th Anniversary Golden Box がアビスアイの下に配置」。原因は第1キーが英語名で、英語名が空の商品が先頭側に来るため（前回調査 /tmp/CC報告ファイル/inventory-sort-order/）。
- 稼働中の商品 1398 件のうち name_en が空のものは 867 件（前回調査の本番読み取り）。

## 未確認
- 配信行 d に product_id 列が含まれるか（:278 の x.product_id から rows_main には有る。d から ORDER BY で参照できるかは実装時に確認）。
