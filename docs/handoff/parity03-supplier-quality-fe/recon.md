# PARITY-03 Phase 2 FE — recon

対象ADR: ADR-154 (GAS→Python migration policy)

## 削除対象ファイル（比較ビュー専用・Phase 1 で実装・Phase 2 で不要と判断）

以下のファイルは本 PR で git rm により削除した（削除済みのためパス引用なし）:

- frontend/src/features/tcg-analysis-review/AnalysisReviewWorkspace.tsx — 比較ビュー全体レイアウト
- frontend/src/features/tcg-analysis-review/ReviewListPanel.tsx — 比較ビュー解析リスト
- frontend/src/features/tcg-analysis-review/reviewListColumns.ts — 比較ビュー列定義
- frontend/src/features/tcg-analysis-review/reviewListViewModel.ts — 比較ビュー VM
- frontend/src/features/tcg-analysis-review/reviewTabs.ts — ステータスタブ定義
- frontend/src/features/tcg-analysis-review/analysis-review.css — 比較ビュー CSS
- frontend/src/features/tcg-analysis-review/components/StatusTabBar.tsx — ステータスタブバー
- frontend/src/features/tcg-analysis-review/components/status-tab-bar.css — タブバー CSS
- frontend/src/pages/super-admin/TcgAnalysisReviewPage.tsx — Phase 1 ページ

## 既存の再利用ファイル（変更なし）

| ファイル | 役割 | 理由 |
|---------|------|------|
| `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:1` | アイテム比較カード | SupplierDetailView で readOnly=true で使用 |
| `frontend/src/features/tcg-analysis-review/SourceRawPane.tsx:7` | 原文パネル | SupplierDetailView で使用 |
| `frontend/src/features/tcg-analysis-review/components/DataList.tsx:4` | 汎用リスト | SupplierQualityList で使用 |

## 新規作成ファイル

| ファイル | 役割 |
|---------|------|
| `frontend/src/features/tcg-analysis-review/supplierQuality.ts:1` | 型定義・列定義 SSOT |
| `frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx:1` | 仕入元一覧（S-1 呼び出し） |
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:1` | 仕入元詳細（S-2 + A-1 呼び出し） |
| `frontend/src/pages/super-admin/TcgSupplierQualityPage.tsx:1` | master-detail ページ |

## GAS → FE マッピング

| GAS 関数 | BE エンドポイント | FE コンポーネント |
|---------|----------------|----------------|
| `api_getSupplierQualitySummaries` | `GET /api/v1/tcg/supplier-quality-summaries` | `frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx:31` |
| `api_getSupplierSource(supplierId)` | `GET /api/v1/tcg/suppliers/{id}/source` | `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:40` |
| `getAnalysisReviewPage({provider, stripRawText})` | `GET /api/v1/tcg/analysis-results?provider=&strip_raw_text=true` | `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:47` |

## URL 変更

| Before | After |
|--------|-------|
| `/super-admin/tcg-analysis-review` | `/super-admin/tcg-supplier-quality` |
| `frontend/src/App.tsx:310` 旧ルート | `frontend/src/App.tsx:310` 新ルート |

## i18n キー変更

| Before | After |
|--------|-------|
| `nav.superAdminTcgAnalysisReview` | `nav.superAdminTcgSupplierQuality` |
| `frontend/src/locales/ja.json:154` 旧キー | `frontend/src/locales/ja.json:154` 新キー |
