# recon — fix-extraction-ranking-api-shape

## 問題箇所

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1019-1030` — `useEffect` 内の `api.get<ExtractionProductRankingItem[]>()` 呼び出し
- `backend/app/routers/tcg_analysis_dashboard.py:323-325` — `ExtractionProductRankingResponse` モデル定義（`items` フィールドを持つラッパー型）

## 根拠

バックエンドは `ExtractionProductRankingResponse` = `{ items: list[ExtractionProductRankingItem] }` を返すが、
フロントエンドは `ExtractionProductRankingItem[]`（配列）として受け取り、`res` をそのまま state に格納していた。

## 触れないファイル

他のAPI呼び出し・他のタブのコンポーネントには変更しない。
