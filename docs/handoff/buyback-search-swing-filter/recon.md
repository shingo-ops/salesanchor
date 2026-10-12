# Recon: 買取相場検索＋変動フィルタ

## 調査対象
- `backend/app/routers/buyback_prices.py:153-298` — GET /buyback-prices（検索・変動パラメータなし）
- `backend/app/routers/buyback_prices.py:300-420` — GET /buyback-prices/by-product（同上）
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:44-67` — ステート定義（検索なし）
- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx:1-233` — 商品別ビュー（検索なし）
- `frontend/src/components/TextField.tsx:1-75` — 検索入力の金型（type="search" 対応確認済み）
- `frontend/src/components/Select.tsx:1-133` — セレクトの金型（size="sm" 対応確認済み）

## 既存バグ
- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx:172` — `var(--color-danger)` は tokens.css に未定義。`var(--danger)` に修正必要

## ADR
- ADR-027: i18n 強制（全UI文字列は t() 経由）
- ADR-144: UIガバナンス（金型登録コンポーネントのみ使用）
- ADR-157: 買取相場ログ機能
