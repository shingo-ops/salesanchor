## recon

### 調査結果
- `backend/app/routers/buyback_prices.py` — 既存エンドポイント構成確認。固定パス `/buyback-prices/pending-reviews`, `/buyback-prices/by-product`, `/buyback-prices/rematch` が `{shop_product_id}` パスより前に定義済み。新エンドポイント `/buyback-prices/by-product/{product_id}/history` を `/buyback-prices/{shop_product_id}/history` の前に定義が必要。
- `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx` — 新規Drawer実装（recharts LineChart、Tabs期間切替 7/30/90日）。
- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx` — 商品別表示（行クリックは現在 BuybackPriceHistoryDrawer を使用中）。`ByProductItem` 型を使用。`product_id` を持つ。
- `frontend/src/pages/buyback-prices/buybackTypes.ts` — `ByProductItem` に `product_id: number` 存在確認。`formatChartDate` 関数も確認。
- `frontend/src/locales/ja.json` — `buybackPrices.byProduct` セクション確認。`priceHistory`, `homura`, `shinsoku`, `noHistory` キーは未存在。
- `frontend/src/locales/en.json` — 同上。

### ADR
- ADR-157: 買取相場ログ
