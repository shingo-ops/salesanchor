# design: fix-buyback-name-column

## 設計

### 変更内容
buyback_prices router の SQL クエリ内で誤参照されている `pr.name_ja` を `pr.name` に修正。

### 変更箇所（修正前 → 修正後）
- 店舗別ビュー SQL: `pr.name_ja` → `pr.name`
- 商品別ビュー SQL: `pr.name_ja` → `pr.name`

### 検証方法

| 基準 | 検証方法 |
|------|---------|
| 店舗別ビューが 200 を返す | GET /buyback-prices がデータ付きで正常応答 |
| 商品別ビューが 200 を返す | GET /buyback-prices/by-product が正常応答 |
| 価格推移グラフが表示される | フロントエンドでグラフが描画される |

## 外部・過去事例の参照と我々への応用

PostgreSQL で `column does not exist` エラーが発生するのは SQL 内のカラム名 typo の典型パターン。
修正方法はカラム名を実テーブル定義に合わせるのみ（マイグレーション不要）。
今回の原因: PR #3718 で LEFT JOIN 追加時に `name` を `name_ja` と誤記した。

## 維持の仕組み

守り手: コードレビュー時に SQL カラム名と実テーブル定義の一致を確認（SQL 文字列は静的解析対象外のため人的確認が必要）

## マイグレーション
不要（スキーマ変更なし）

## ロールバック方法
`pr.name` を `pr.name_ja` に戻す（ただし再び 500 エラーになる）
