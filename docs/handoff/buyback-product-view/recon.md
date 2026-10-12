# recon: buyback-product-view

## 調査対象ADR
- ADR-157: 買取相場ログ（backend/app/routers/buyback_prices.py に実装済み）

## 既存コードのファイル:行番号

- `backend/app/routers/buyback_prices.py:300`: GET /buyback-prices/pending-reviews（固定パス、新エンドポイントをこの前に挿入）
- `frontend/src/pages/buyback-prices/buybackTypes.ts:96`: CardGame型定義（新型の挿入位置）
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:35`: export default function BuybackPricesPage（モード切替state追加先）
- `frontend/src/locales/ja.json:370`: matchStatusUnmatched（新キー追加位置）
- `frontend/src/locales/en.json:370`: matchStatusUnmatched（新キー追加位置）

## DBスキーマ確認

- `public.products`: id, product_code, name_ja, category, release_date, image_url（既存テーブル）
- `public.buyback_shop_products`: id(UUID), product_id(FK), shop_code, product_name（既存テーブル）
- `public.buyback_price_logs`: shop_product_id(FK), price_s, price_a, price_b, fetched_at（既存テーブル）

## 実装方針

PO直接指示に全仕様記載済み。
LATERAL JOINでhomura/shinsokuの最新価格を効率取得。
フロントはstateでモード切替（方法A）。
