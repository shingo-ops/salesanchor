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

## 外部・過去事例の参照と我々への応用
LATERAL JOIN による最新価格取得は PostgreSQL の標準的なパターン。既存の buyback_prices.py が DISTINCT ON で実装しているのと同等の意味を持つが、店舗別に独立してLATERAL JOINする構造の方が可読性が高い。

## 維持の仕組み
- 新しい買取店が増えた場合は、同パターンのLATERAL JOINをAPIに追加し、フロントの列定義も追加する
- categoryは products.category の値をそのまま使うため、新カテゴリは自動反映される

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
