# recon: fix-buyback-category-key

## 問題

買取 by-product カテゴリタブが重複して表示される。

**根本原因**: `products.category` は自由記述 VARCHAR。同一カードゲームでも
'Pokemon' / 'ポケモンカードゲーム' / 'Pokemon TCG' 等の表記揺れが存在し、
UPPER(p.category) で GROUP BY しても別タブになってしまう。

## 証拠（file:line）

対象ファイル: backend/app/routers/buyback_prices.py

| 行 | 変更前 |
|----|--------|
| 413 | SELECT UPPER(p.category), count(DISTINCT p.id) (swing CTE variant) |
| 419 | GROUP BY UPPER(p.category) (swing CTE variant) |
| 424 | SELECT UPPER(p.category), count(DISTINCT p.id) (non-swing variant) |
| 428 | GROUP BY UPPER(p.category) (non-swing variant) |
| 439 | UPPER(p.category) = UPPER(:category) (filter condition) |
| 479 | UPPER(p.category) AS category (main SELECT) |

## SSOTの問題

- buyback_shop_products.card_game カラムはパイプラインが正規化済みの値を格納
- フロントエンドの CATEGORY_LABELS キーは card_game の値と一致
- ストア別ビュー (list_by_shop) はすでに bsp.card_game を使用 — SSOT違反

## ADR検索結果

- git grep -i buyback docs/adr/ → 該当なし
- docs/adr/FEATURE-INDEX.md で "buyback" 検索 → 該当なし
- ADR競合なし

## 触らない範囲

- products.category のデータ自体（変更不要・参照を切るだけ）
- フロントエンドコード（card_game 値はすでに CATEGORY_LABELS と対応）
- 他エンドポイント（list_by_shop はすでに bsp.card_game 使用・変更不要）
