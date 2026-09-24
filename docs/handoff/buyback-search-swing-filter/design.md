# Design: 買取相場検索＋変動フィルタ

## recon参照
docs/handoff/buyback-search-swing-filter/recon.md

## ADR参照
ADR-027, ADR-144, ADR-157

## 目的
買取相場ページに商品名検索と期間内価格変動フィルタを追加し、価格変動のある商品を効率的に発見可能にする。

## 変更内容

### バックエンド
- GET /buyback-prices: `q`（ILIKE検索）、`swing_days`（変動計算期間）、`min_swing`（最小変動額）パラメータ追加
- GET /buyback-prices/by-product: 同上
- price_swing CTE を条件付きで動的追加（swing_days 指定時のみ）
- パラメータ化クエリ（SQLインジェクション対策）

### フロントエンド
- TextField type="search" で商品名検索（ContentToolbar left）
- SelectControl × 2 で変動期間・閾値選択
- DataTable に変動額カラム（swing_days 指定時のみ表示）
- var(--color-danger) → var(--danger) 既存バグ修正

### i18n
- ja.json / en.json に 8 キー追加（buybackPrices.* 名前空間）

## 対象外
- マイグレーション（不要）
- 新テーブル・カラム（不要）
- trgm インデックス（460件程度で ILIKE 十分）

## 受入条件
| 基準 | 検証方法 |
|------|---------|
| 商品名で絞り込みできる | 検索欄に入力→該当商品のみ表示 |
| 期間内変動でフィルタできる | 期間＋閾値選択→変動商品のみ表示 |
| 変動額が表示される | 変動額カラムに円額表示 |
| i18n 準拠 | ハードコード日本語なし |
| デザイントークン準拠 | var(--color-danger) 消滅 |

## 維持の仕組み
守り手: CI の i18n チェック（`frontend/scripts/check-i18n.js`）、eslint
- 変動計算は既存 buyback_price_logs インデックス `(shop_product_id, fetched_at DESC)` を活用

## 外部・過去事例の参照と我々への応用
該当なし（内部機能の拡張。既存 buyback_price_logs インデックスを活用した価格変動計算は過去事例参照不要）
