# design: buyback-product-view

## 参照ADR
- ADR-157: 買取相場ログ

## KGI
同一商品のホムラ/シンソク買取価格（Sグレード）を横並びで比較できる。

## KPI / 検証方法

| 基準 | 検証方法 |
|------|---------|
| GET /buyback-prices/by-product が200を返す | curl/ブラウザで確認 |
| release_date DESCで並んでいる | レスポンスの先頭3件の発売日が降順 |
| homura_price_s / shinsoku_price_s が横並びで返る | レスポンスのJSONフィールド確認 |
| カテゴリタブの件数が正しい | counts_by_categoryの合計とitemsの件数が一致 |

## 外部事例
該当なし

## 弊害・ロールバック
- APIエンドポイント追加のみ。既存エンドポイントに変更なし
- git revert で即時復元可能
- DBマイグレーション不要

## 実装計画
1. backend: GET /buyback-prices/by-product を /pending-reviews の前に追加
2. frontend/types: ByProductItem, ByProductResponse 型追加
3. frontend: BuybackByProductPage.tsx 新規作成
4. frontend: BuybackPricesPage.tsx にモード切替追加
5. i18n: ja.json / en.json にキー追加
