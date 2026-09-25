# release-buyback-category-type-master

## 概要

買取相場ページのカテゴリタブ駆動源を `bsp.card_game`（文字列）から `products.work_id` → `type_master`（中分類マスタ）に切り替え。

## ブランチ

`release/buyback-category-type-master`

## ステータス

- [x] recon.md 作成
- [x] design.md 作成
- [x] バックエンド実装（buyback_prices.py）
- [x] フロントエンド実装（BuybackByProductPage.tsx, buybackTypes.ts）
- [x] ruff lint pass
- [x] コミット
- [x] PR 作成（Draft）

## 関連

- ADR-157（買取相場SSOT）
