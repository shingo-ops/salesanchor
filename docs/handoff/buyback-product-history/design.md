## 設計

### 変更前後
- 変更前: 商品別画面の行クリックで BuybackPriceHistoryDrawer（shop_product_id 単体）が開く
- 変更後: ホムラ・シンソクの価格推移を重ねたグラフが BuybackProductHistoryDrawer（product_id 軸）で表示される

### recon 相互参照
- `backend/app/routers/buyback_prices.py` — `GET /buyback-prices/by-product/{product_id}/history` エンドポイントを `/buyback-prices/{shop_product_id}/history` の前に追加
- `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx` — 新規Drawer実装（recharts/Tabs パターン）
- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx` — `handleRowClick` を新 Drawer に切替

### 基準・検証方法

| 基準 | 検証方法 |
|------|---------|
| 行クリックで Drawer が開く | BuybackByProductPage の行をクリック → Drawer 表示確認 |
| ホムラ・シンソクの線が重ねて表示される | 両店舗にデータがある商品で Drawer を開き、2本の線を目視確認 |
| 期間タブ（7/30/90日）が動作する | タブ切替でグラフデータが更新されることを確認 |
| デザイントークンのみ使用（色直値禁止） | TypeScript コンパイルエラーなし・ruff エラーなし |

## 外部・過去事例の参照と我々への応用

該当なし。既存の `BuybackPriceHistoryDrawer.tsx` の recharts LineChart + Tabs パターンを踏襲。

## 維持の仕組み

既存のスクレイパー（1日3回）がデータを蓄積し続けるため、グラフは自動更新される。

守り手: `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx`, `backend/app/routers/buyback_prices.py`
