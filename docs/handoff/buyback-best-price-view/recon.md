# recon: buyback by-product view improvements

## 対象ファイル

- `backend/app/routers/buyback_prices.py:374-580` — `list_by_product` エンドポイント
- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx:115-207` — カラム定義
- `frontend/src/pages/buyback-prices/buybackTypes.ts:96-114` — `ByProductItem` 型
- `frontend/src/locales/ja.json:391-401` — buybackPrices.byProduct セクション
- `frontend/src/locales/en.json:391-401` — buybackPrices.byProduct セクション

## 既存実装の確認

- `p.mark` カラムは `public.products` テーブルに存在（`backend/app/routers/products.py:54`）
- LATERAL JOIN で homura/shinsoku の最新価格を取得する実装は既存（buyback_prices.py:496-523）
- カテゴリは小文字で格納されているが混在の可能性あり（UPPER正規化で吸収）
- 既存フィールド（homura_*/shinsoku_*）はHistoryDrawerが利用中のため保持

## 関連ADR

- ADR-157: 買取相場ログ
