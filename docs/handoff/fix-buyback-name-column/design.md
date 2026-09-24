# design: fix-buyback-name-column

## 設計

### 変更内容
`backend/app/routers/buyback_prices.py` の SQL クエリ内で誤参照されている `pr.name_ja` を `pr.name` に修正。

### 変更箇所（修正前 → 修正後）
- 店舗別ビュー SQL: `pr.name_ja` → `pr.name`
- 商品別ビュー SQL: `pr.name_ja` → `pr.name`

### 検証方法

| 基準 | 検証方法 |
|------|---------|
| 店舗別ビューが 200 を返す | GET /buyback-prices がデータ付きで正常応答 |
| 商品別ビューが 200 を返す | GET /buyback-prices/by-product が正常応答 |
| 価格推移グラフが表示される | フロントエンドでグラフが描画される |

### 外部事例
PostgreSQL `column "name_ja" does not exist` エラーは SQL typo の標準パターン。カラム名を実定義に合わせるのみ。

### マイグレーション
不要（スキーマ変更なし）

### ロールバック方法
`pr.name` を `pr.name_ja` に戻す（ただし再び 500 エラーになる）

### 守り手
- なし（SQL typo 修正のみ・設計変更なし）
