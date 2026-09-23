# recon: buyback-phase2-filters

## 対象ADR検索結果
- `git grep -i docs/adr/` で buyback 関連 ADR を検索
- ADR-157: 買取相場ログ（`docs/adr/ADR-157-buyback-price-logger.md` 参照）
- FEATURE-INDEX.md に buyback エントリあり

## 現在地（file:line）

### Backend
- `backend/app/routers/buyback_prices.py:66` — `BuybackPriceListResponse` モデル
- `backend/app/routers/buyback_prices.py:115-215` — `list_buyback_prices` エンドポイント
- `backend/app/routers/buyback_prices.py:120-121` — limit/offset Query params（sort/order を追加する行）
- `backend/app/routers/buyback_prices.py:179` — `ORDER BY` ハードコード行（sort_col/sort_dir に置換）
- `backend/app/routers/buyback_prices.py:206-207` — rows/total 取得後（counts_by_game クエリを挿入）

### Frontend
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:48-51` — `BuybackListResponse` 型定義
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:103-113` — state 宣言群
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:128-135` — API params 構築
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:155` — useEffect deps 配列
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:270-286` — SelectControl / Tabs 選択肢定義
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:306-321` — ContentToolbar left slot

### i18n
- `frontend/src/locales/ja.json:316` — fetchFailed の次（新キー追加先）
- `frontend/src/locales/en.json:316` — 同上

## 触らないファイル
- `backend/app/routers/buyback_prices.py` の history エンドポイント（line 218以降）
- `frontend/src/pages/buyback-prices/BuybackPricesPage.module.css`
- DB マイグレーションなし（既存カラム product_type を使うのみ）
