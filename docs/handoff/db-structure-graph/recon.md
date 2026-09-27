# DB構造グラフ — recon

## 調査対象
- LINE解析パイプラインのテーブル関連をビジュアルマップで表示する機能

## 参照ファイル
- frontend/src/pages/super-admin/components/DbViewerPanel.tsx:1 — 既存のテーブル一覧ビューア（スプレッドシート形式）
- frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:32 — サイドバーキー型定義
- frontend/src/pages/super-admin/AnalysisRulesPage.tsx:47 — パネル分岐
- backend/app/routers/super_admin_db_schema.py:1 — DB構造API（テーブル・カラム・FK取得）
- frontend/src/components/Drawer.tsx:1 — ドロワーコンポーネント
- frontend/src/components/DataTable.tsx:1 — テーブル表示コンポーネント
- frontend/src/tokens.css:241 — パイプラインマップ用サイズトークン追加箇所

## ADR検索結果
- ADR-144（UIガバナンス）: 生select/生input禁止、CSS変数必須 → 準拠
- ADR-027（i18n）: 全テキストt()経由 → 準拠
- ADR-067（デザイントークン）: CSS変数のみ使用 → 準拠（tokens.cssに専用トークン追加）

## FK関係（本番DB実測）
本番PostgreSQLのinformation_schema.table_constraintsから取得した35本のFK関係をマップのエッジとして使用（推測なし）。

## ADR-067チェック修正箇所
- PipelineMapPanel.css の min-height: 600px → var(--size-pipeline-map-min-h)
- PipelineMapPanel.css の min-width: 160px → var(--size-substep-nav)（既存トークン流用）
- PipelineMapPanel.css の max-width: 220px → var(--size-pipeline-node-max-w)
- PipelineMapPanel.css の width/height: 8px → var(--space-2)
