# ADR-1014: 在庫表は LINE 解析の配信行を出す

**Status**: Accepted  
**Date**: 2026-10-13  
**Author**: Hikky-dev  
**PO**: shingo-ops

---

## What（何を）

`/inventory`（在庫表）が表示する行を、`public.inventory` ではなく LINE 解析の「配信行」（`distribution_rows_sql`）に切り替える。

- 配信行（GAS 出力と在庫表）の定義は `backend/app/services/tcg_distribution_svc.py` の `distribution_rows_sql` の1か所だけ。`inventory_offers.py` に配信の WHERE を書かない。配信プレビューの件数は変更前の問い合わせを残している（products を結合しないため）。状態の条件だけ `_condition_filter` を共有する。件数と出力のずれは `test_tcg_condition_review.py` の output_count と len(fetch_output_rows) の比較を CI が止める。
- 同じ投稿・同じ商品・同じ状態（`cr.condition_id` / `cr.basis`）の行は、`merge_same_post`（既定 OFF。2026-10-14 改訂で ON から変更）でまとめて表示する。ユーザー別設定（`/me/inventory-filters`）で切り替える。
- 在庫表の列に備考（`note_ja`）と発送（`ship_ja`）を足す。状態・形態は canonical の値をそのまま出す。
- 行 ID は文字列（`InventoryRow.id: str`）。

## Why（なぜ）

ADR-093 は「`/inventory` は `public.inventory` を表示する」と定めたが、利用者が見たいのは GAS 配信と同じ LINE 解析の結果である。2つの正本があると行数・内容が食い違うため、配信行（GAS 出力と在庫表）の定義を1か所に集める。

## Scope

- 対象: `backend/app/services/tcg_distribution_svc.py`、`backend/app/routers/inventory_offers.py`、`backend/app/routers/me_inventory_filters.py`、`backend/app/schemas/inventory_offers.py`、`frontend/src/pages/inventory/InventoryPage.tsx`、ja/en ロケール。
- `fetch_output_rows` / `fetch_preview_data` の引数・GAS 出力列（14列）は変えない。
- 対象外: migrations、deploy.yml、本番 scripts。

## 置き換える決定

ADR-093「/inventory は public.inventory を表示する」を本 ADR が置き換える（ADR-093 の他の部分は有効）。

## 改訂 2026-10-14（便1: 在庫表と GAS 在庫一覧の揃え）

- まとめ（`merge_same_post`）の既定を OFF にした。保存済みの設定（`user_inventory_filters.filters`）は書き換えない。true を保存済みの人は ON のまま、キーが無い人は OFF になる。
- Sold out の除外を配信行の定義に入れた。`tcg_distribution_svc._sold_out_filter()` の1か所に判定を置き（`ar.` の別名が前提。status の前後の空白と大文字小文字を無視し 'sold out' / 'soldout' を除く）、dist_base と配信プレビューの件数クエリの両方が使う。
- 並び替えの第1キーを英語タイトルにした（GAS 方式）。タイトル列を並べるときは英語タイトルの昇降を切り替える。
- 在庫表に「24時間以内」(`fresh_only`、既定 ON、画面側のみ・保存しない)を足した。窓は `FRESH_WINDOW_HOURS = 24`。

## 改訂 2026-10-18（在庫表の既定の並びを発売日の早い順・商品ごとのまとまりにする）

PO 決定（2026-10-18）。上の 2026-10-14 改訂の「並び替えの第1キーを英語タイトルにした」を本改訂が上書きする（上の行は書き換えない）。ただしタイトル列（`sort=name`）の並びは 2026-10-14 のまま維持する。

- まとまり（商品）の順: 発売日 ASC（空欄は末尾）→ english_title ASC → japanese_title ASC → product_id ASC（在庫表のみ。閲覧ページは product_id を持たないので題名2つまで）。発売日の向きは `sort=release_date` を選んだときだけ `order` に従い、それ以外の並び替えでは常に ASC。
- まとまりの中の順: 既定（`release_date`）は `sort_ord`。それ以外は `{選んだ列} {向き} NULLS LAST → sort_ord`。プルダウンの並び替えはまとまりの中だけで効く（GAS 在庫一覧と同じ仕組み）。
- 既定の向きを asc にした（在庫表 `InventoryPage.tsx`、閲覧ページ `viewerFilter.ts` の `DEFAULT_SORT_DIR`）。並び替えプルダウンの先頭に `release_date:asc`「発売日が早い順」を追加し、既定のとき空表示にならないようにした。
- 実装: `backend/app/routers/inventory_offers.py` の `_build_view_order_by`、`frontend/src/pages/viewer/viewerFilter.ts` の `sortRows`。配信行の定義・GAS 出力14列・API 応答形は変えない。
- 守り: backend の ORDER BY 単体試験と viewerFilter の `sortRows` 試験。

## 改訂 2026-10-18（2）（既定の向きを発売日の新しい順に改める）

PO 決定（2026-10-18）「発売日の新しい順にしてほしい、いまは古い順になっている」。上の「改訂 2026-10-18」の既定の向き（asc）を desc に改める（前の改訂節の本文は書き換えない）。

- 既定の向きを desc にした（在庫表 `InventoryPage.tsx` の既定・リセット、閲覧ページ `viewerFilter.ts` の `DEFAULT_SORT_DIR`、API `inventory_offers.py` の `order` 既定）。
- プルダウンの先頭は `release_date:desc`「発売日が新しい順」。旧 `releaseAsc` キーは ja/en とも削除。
- 変えないもの: 同じ発売日の中（english_title → japanese_title → product_id）、同じ商品の中の価値順（ADR-1023）、発売日が空の商品は末尾、`_build_view_order_by` の組み立て。
- 守り: InventoryPage.tablelayout.test.tsx・viewerFilter.test.ts・InventoryView.test.tsx が既定の向き desc を固定する。
