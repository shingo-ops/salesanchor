# design: エラーログAPIパス二重prefix修正

recon: docs/handoff/fix-extraction-errors-path/recon.md

## 修正内容

| 対象 | 修正前 | 修正後 |
|------|--------|--------|
| backend/app/routers/tcg_analysis_dashboard.py:358 | "/api/v1/tcg/extraction-errors" | "/tcg/extraction-errors" |
| frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx:50 | api.get("/api/v1/tcg/extraction-errors?...") | api.get("/tcg/extraction-errors?...") |

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| CI全緑 | GitHub Actions で確認 |
| APIが404でなく401を返す | curl で https://api.salesanchor.jp/api/v1/tcg/extraction-errors → 401 を確認 |

## 影響範囲

呼び出し元: frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx のみ（grep確認済み）

## 外部・過去事例の参照と我々への応用

ADR-152（docs/adr/ADR-152-frontend-api-path-no-prefix.md）と同一パターンのバグ。
PR #3181 で TcgParallelReportPage.tsx が /api/v1/tcg/parallel-report を呼んで
本番 404 が発生した教訓を受け、ADR-152 が策定された。
本修正は ADR-152 の決定に準拠し、フロントとバックエンドの両方でプレフィックス重複を解消する。

## 維持の仕組み

守り手: ADR-152（docs/adr/ADR-152-frontend-api-path-no-prefix.md）

コードレビュー時に api.get("/api/v1/...") パターンを指摘する規約（ADR-152）。
frontend/src/lib/api.ts のコメントで API_BASE = "/api/v1" を明示しており、
エンドポイント定義側への /api/v1 混入を防ぐ。

## 戻し方

backend/app/routers/tcg_analysis_dashboard.py の "/tcg/extraction-errors" → "/api/v1/tcg/extraction-errors" に戻す。
frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx も同様に戻す。
