# recon: buyback-manual-trigger

## 既存ADR検索
- `git grep -i "buyback" docs/adr/` → ADR-157 が該当（買取相場ログ設計）
- `ADR-157` は `backend/app/routers/buyback_prices.py:4` で参照済み

## 変更対象ファイル（file:line）

### Backend
- `backend/app/routers/buyback_prices.py:30` — import: `require_super_admin` を追加
- `backend/app/routers/buyback_prices.py:31` — import: `fetch_all_buyback_prices` を追加
- `backend/app/routers/buyback_prices.py:45-47` — `TriggerResponse` モデル追加
- `backend/app/routers/buyback_prices.py:89-99` — `POST /buyback-prices/trigger` エンドポイント追加

### Frontend
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:9` — `Button` import 追加
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:10` — `useSuperAdmin` import 追加
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:99` — `isSuperAdmin` state 追加
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:107-108` — `fetching`, `fetchMsg` state 追加
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:180-194` — `handleManualFetch` ハンドラ追加
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:307-322` — ContentToolbar `right` slot 追加

### i18n
- `frontend/src/locales/ja.json` — `buybackPrices.fetchNow/fetchStarted/fetchFailed` 追加
- `frontend/src/locales/en.json` — `buybackPrices.fetchNow/fetchStarted/fetchFailed` 追加

## 参照パターン
- `backend/app/routers/reports.py` — `Celery .delay() + 202` パターンの正本
- `frontend/src/pages/super-admin/FxRatePage.tsx` — `useSuperAdmin` フックの使用例
- `backend/app/auth/dependencies.py:453-481` — `require_super_admin` の定義（`is_super_admin=True` 必須）
- `frontend/src/components/Button.tsx:20` — `variant: "secondary"`, `size: "sm"` が有効

## 触らないファイル
- `backend/app/tasks/buyback_scraper.py` — タスク定義は変更なし（`fetch_all_buyback_prices` をimportのみ）
- `frontend/src/pages/buyback-prices/BuybackPricesPage.module.css` — 既存 `.statusMsg` クラスを再利用
