# recon: buyback-category-type-master

## 問題

カテゴリタブの駆動源が `bsp.card_game`（文字列）でありSSOTではない。
フロントの `CATEGORY_LABELS` にカテゴリ名がハードコードされており、新カテゴリ追加時にフロントコード変更が必要。

## 根拠（file:line）

### バックエンド

- `backend/app/routers/buyback_prices.py:379` — `category: str | None` (変更前: 文字列型)
- `backend/app/routers/buyback_prices.py:413` — swing variant の `SELECT bsp.card_game, count(DISTINCT p.id)` (変更前)
- `backend/app/routers/buyback_prices.py:423-430` — non-swing variant の `SELECT bsp.card_game, count(DISTINCT p.id)` (変更前)
- `backend/app/routers/buyback_prices.py:431-432` — `counts_by_category = {row[0]: row[1] for row in counts_result}` (変更前: 2カラム)
- `backend/app/routers/buyback_prices.py:438-439` — `bsp_f.card_game = :category` フィルタ (変更前)
- `backend/app/routers/buyback_prices.py:479` — `SELECT bsp_cg.card_game ... AS category` (変更前)
- `backend/app/routers/buyback_prices.py:589` — `"category": r[3]` (変更前)
- `backend/app/routers/buyback_prices.py:609-613` — レスポンスオブジェクト（`category_names` なし、変更前）

### フロントエンド

- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx:26-33` — `CATEGORY_LABELS` ハードコード6件（変更前）
- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx:107` — `CATEGORY_LABELS[key] ? t(CATEGORY_LABELS[key]) : key`（変更前）
- `frontend/src/pages/buyback-prices/buybackTypes.ts:100` — `category: string;`（変更前）
- `frontend/src/pages/buyback-prices/buybackTypes.ts:120-124` — `ByProductResponse`（`category_names` なし、変更前）
- `frontend/src/pages/buyback-prices/buybackTypes.ts:130` — `CardGame` ハードコード6値（変更前）

## ADR

- ADR-157: 買取相場機能設計（buyback feature SSOT）
