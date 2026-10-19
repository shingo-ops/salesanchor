# recon: 同じ商品のまとまりの中で、最安値の行と在庫最多の行に小さいバッジを付ける

基準は origin/main 66ef0cc58 で、調査は Sonnet が行った（`git show origin/main:<path>` で読んだ）。GAS は ~/tcg-viewer-1tb-head/index.html を読んだ。行番号は origin/main のもの。

## 既存 ADR の検索
- 「バッジ」「最安」「badge」で grep した。在庫表の最安バッジ・在庫最多バッジを決めた ADR は無い。
- 関係する ADR:
  - ADR-1019:26（閲覧ページはアプリの Badge などの金型を使う）
  - ADR-067:52-53（Badge の余白トークン）
  - ADR-1014（在庫表と閲覧ページの並び、GAS との揃え）
- ADR-099:57 と ADR-102:57 の「最安値優先」は発注の最安提供元の話で、別の機能。

## 1. 在庫表（サーバーでページを切る）
【事実】`backend/app/routers/inventory_offers.py:280-320` の `_build_inventory_view_sql`。
- rows_f は利用者の絞り込みを当てた後の行（:298）。
- rows_pg は `SELECT d.*, ROW_NUMBER() OVER ({order_by}) AS __ord FROM rows_f d {order_by} LIMIT :limit OFFSET :offset`（:302-303）。
  - SELECT 句のウィンドウ関数は LIMIT より前に計算される。そのため、ここに足した値はページをまたいで rows_f 全体が基準になる。
- 3枝の列の並びは共通で、__kind、__total、行の列、__ord、__f_* の5列（q_total :305-309、q_page :311-314、q_facet :315-319）。
- ページは行の単位で切る（:303、per_page の既定は50、最大200 :354）。1つの商品のまとまりが、2ページにまたがることがある。
- 行の列には price_num（単価）、qty_num（数量）、product_id がある（`backend/app/services/tcg_distribution_svc.py:286-301`）。
- まとめモード（merge_same_post、:345、既定は False）では、数量が SUM、単価が MAX になる（`backend/app/services/tcg_distribution_svc.py:397-398`）。
- 行を画面向けに変換する所（`_project_inventory_rows` :153-185）:
  - 価格が NULL なら unit_price は 0 になる（:172）。
  - 数量は None のことがある（:173-174）。
  - "__" で始まる列は、ページの行から外している（:406-407）。
- 行のスキーマは `backend/app/schemas/inventory_offers.py:129-160` の InventoryRow（unit_price :150、quantity :151、merged_count :159）。

## 2. 画面
【事実】
- 在庫表の列は `frontend/src/features/inventory/inventoryColumns.tsx` で定義している。
  - 価格のセルは :121-126。
  - 数量のセルは :133-139 で、まとめ件数の小さい2行目は :140-145。
  - 画面は API の行をそのまま出しており、まとまりの計算はしていない。
- 閲覧ページの列は `frontend/src/pages/viewer/viewerColumns.tsx` で定義している（価格 :74-80、数量 :82-88）。
  - 閲覧ページは、作り置きの全行をブラウザで絞り込み、並べ、ページを切る（`frontend/src/pages/viewer/InventoryView.tsx:94-98`）。
  - 行（`frontend/src/pages/viewer/types.ts:11-27`）には product_id が無い。unit_price と quantity は文字列で、空のときは ''。
  - 2画面の列の並びは viewerColumns.parity.test.tsx が縛っている。
- Badge の金型は `frontend/src/components/Badge.tsx`。
  - variant は neutral、info、success、warning、danger、purple。
  - appearance は soft（既定）と solid。
  - size は sm と md。sm は高さ 20px で、`--comp-badge-height-sm`（`frontend/src/tokens.css:496`）。
  - Storybook は `frontend/src/components/Badge.stories.tsx`。
- 表の行の高さは既定で 44px（`--comp-table-row-h-default`、tokens.css:509）。sm のバッジ（20px）は1行に収まる。
- 在庫表のセルの CSS は `frontend/src/features/inventory/inventoryColumns.css`。768px 以上では折り返さない（:13-20）。
- i18n:
  - 在庫表向けの「最安」「在庫最多」のキーは無い。
  - frontend/src/locales/ja.json:1957 の inventoryAggFilterCheapest は、別の機能のキー。
  - 閲覧ページは別の辞書（frontend/src/locales/viewer/ja.json と en.json）を使う。

## 3. GAS 在庫一覧
【事実】~/tcg-viewer-1tb-head/index.html（全1635行）。
- 列は COL.unitPrice が 5、COL.quantity が 6（:975-976）。
- ブラウザで ALL_ROWS を絞り込み（:1356）、並べてから描画する（renderTable、数値セルは :1503-1505）。
- 既存のバッジの CSS は .badge（:461-473）。状態列とステータス列だけに使っている（:1498・:1500）。

## 4. 同じ値・空の値
【事実】最安と在庫最多を判定するコードは、今は無い。
- 同じ値の扱い、価格が空の行、数量が空の行の扱いは、設計で決める。
- 参考として、並べ替えでは空を末尾に置いている（`frontend/src/pages/viewer/viewerFilter.ts:21-31`、SQL は NULLS LAST）。

## PO の決定
2026-10-19 に「y」をもらった。問いは次のとおり。

> 絞り込んだ後の行の中で、同じ商品の最安値の行に「最安」、在庫が一番多い行に「在庫最多」を小さいバッジで付ける。同じ値の行が複数あれば全部に付け、価格や在庫が空の行は比べる対象から外す。アプリ・閲覧ページ・GAS の3つに同じように付ける。
