# design — fix-extraction-ranking-api-shape

## 対象ADR: ADR-144（コンポーネント金型遵守）

## 原因

`ExtractionProductRankingResponse` は FastAPI Pydantic ラッパー型でレスポンスを `{ items: [...] }` に包む。
フロントエンドの型注釈が `ExtractionProductRankingItem[]`（配列）のままだったため TypeScript は通過するが、
ランタイムで `res.slice()` 呼び出しが失敗する。

## 修正方針

フロントエンド側で正しい型 `{ items: ExtractionProductRankingItem[] }` に変更し、`res.items ?? []` でアンラップする。

| 基準 | 検証方法 |
|------|---------|
| `/super-admin/analysis-rules` が白画面にならない | ブラウザで Extraction タブを開いてエラーなし |
| `productRanking.slice()` が動作する | 商品ランキングセクションが表示される |

## 外部事例

FastAPI + Pydantic のレスポンスモデルがリスト型のラッパーになるパターンは公式ドキュメント記載のベストプラクティス。

## 維持の仕組み

TypeScript の型注釈が `{ items: ExtractionProductRankingItem[] }` になることで、今後同APIを呼ぶ場合は型エラーで検出可能。
