# recon — 商品マスタの新規追加が 500 になる（便 F1）

**日付**: 2026-11-10
**基準**: origin/main e27b1a522（カードの行番号）・直しの後の行番号はこのブランチ
**対象ADR**: ADR-1020（共用マスタの必須項目）

## 既存ADRの検索
- `docs/adr/ADR-1020-shared-product-required-fields.md` — 新規登録の必須項目。今回の入口 create_product はこの ADR の便で作られた。
- `docs/adr/ADR-155-product-master-ssot-csv-app.md` — 商品マスタの正本は1つ。今回は書き方を変えない。

## 観測（本番・読み取りだけ）
- 2026-11-10 商品マスタ画面の「新規追加」で作成を押すと 500。記録の文: asyncpg.exceptions.DataError: invalid input for query argument $4: '1' ('str' object cannot be interpreted as an integer)。
- 止まった SQL は重複の確かめ。本番 DB で新しい商品は0件（何も書かれていない）。

## コード（file:line）
- 画面は商品区分を文字で送る: `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:202`（saveCreate の中）。
- 入口は3つとも文字で受ける: `backend/app/routers/tcg_product_import.py:406`・`backend/app/routers/tcg_product_master.py:99`・`backend/app/routers/tcg_product_master.py:117`。
- 入口は ValueError を 422 で返す: `backend/app/routers/tcg_product_import.py:445`。
- 重複の確かめの比べ: `backend/app/services/tcg_product_master_svc.py:413`。2026-09-20 の 90367c1a3 で `::text` が外れ、数の列と文字の値の比べになっていた（直しの前）。直しで文字どうしの比べに戻した。
- 書く側: `backend/app/services/tcg_product_master_svc.py:525` で数に直し、`backend/app/services/tcg_product_master_svc.py:589` の INSERT に数を渡す。
- 実 DB の試験は数だけを渡していた（文字の道を試していなかった）。`backend/tests/test_tcg_completion_safety.py:185` に文字の道の試験を足した。

## 未確認
- 2026-10-30 の最後の登録がどの入口から入ったか。
