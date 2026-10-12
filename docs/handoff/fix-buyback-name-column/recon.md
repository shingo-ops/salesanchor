# recon: fix-buyback-name-column

## 調査日
2026-09-24

## 問題
買取相場ページ（/buyback-prices）の全エンドポイントで 500 エラーが発生。

## 原因特定

### エラー箇所
- `backend/app/routers/buyback_prices.py:233` — 店舗別ビュー SQL: `pr.name_ja AS product_name_ja`
- `backend/app/routers/buyback_prices.py:399` — 商品別ビュー SQL: `"name_ja": r[2]`

### SQL 内の誤ったカラム名
- 誤: `pr.name_ja`（2箇所）
- 正: `pr.name`

### 根拠
- `backend/app/routers/buyback_prices.py:233` で `pr.name_ja AS product_name_ja` と誤参照
- products テーブルの実カラム名は `name`（文字列型）
- `name_ja` というカラムは products テーブルに存在しない

## 影響範囲
- buyback_prices.py の SQL クエリ 2箇所のみ
- フロントエンド変更なし
- マイグレーション変更なし

## 関連 PR
- PR #3718: products テーブルとの LEFT JOIN 追加時に `name` を `name_ja` と誤記
