# design — fix-extraction-ranking-api-shape

recon: docs/handoff/fix-extraction-ranking-api-shape/recon.md
対象ADR: ADR-138

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

## 外部・過去事例の参照と我々への応用

FastAPI + Pydantic のレスポンスモデルがリスト型のラッパーになるパターン（`{ items: list[...] }`）は公式ドキュメント記載のベストプラクティス。
フロントエンドは常にレスポンス型をバックエンドのモデル定義と一致させる必要がある。
今回の教訓: `api.get<T>` の型引数は必ず実際のAPIレスポンス形状に合わせること（配列を返すAPIは少なく、多くはラッパー型）。

## 維持の仕組み

TypeScript の型注釈が `{ items: ExtractionProductRankingItem[] }` になることで、今後同APIを呼ぶ場合は型エラーで検出可能。

守り手: .github/workflows/frontend-check.yml（tsc --noEmit）
