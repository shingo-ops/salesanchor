# PARITY-03 Phase 2 FE — recon

対象ADR: ADR-154 (GAS→Python migration policy)

## 削除対象ファイル（比較ビュー専用・Phase 1 で実装・Phase 2 で不要と判断）

| ファイル | 役割 |
|---------|------|
| `frontend/src/features/tcg-analysis-review/AnalysisReviewWorkspace.tsx` | 比較ビュー全体レイアウト |
| `frontend/src/features/tcg-analysis-review/ReviewListPanel.tsx` | 比較ビュー解析リスト |
| `frontend/src/features/tcg-analysis-review/reviewListColumns.ts` | 比較ビュー列定義 |
| `frontend/src/features/tcg-analysis-review/reviewListViewModel.ts` | 比較ビュー VM |
| `frontend/src/features/tcg-analysis-review/reviewTabs.ts` | ステータスタブ定義 |
| `frontend/src/features/tcg-analysis-review/analysis-review.css` | 比較ビュー CSS |
| `frontend/src/features/tcg-analysis-review/components/StatusTabBar.tsx` | ステータスタブバー |
| `frontend/src/features/tcg-analysis-review/components/status-tab-bar.css` | タブバー CSS |
| `frontend/src/pages/super-admin/TcgAnalysisReviewPage.tsx` | Phase 1 ページ |

## 既存の再利用ファイル（変更なし）

| ファイル | 役割 | 理由 |
|---------|------|------|
| `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:1` | アイテム比較カード | SupplierDetailView で readOnly=true で使用 |
| `frontend/src/features/tcg-analysis-review/SourceRawPane.tsx:7` | 原文パネル | SupplierDetailView で使用 |
| `frontend/src/features/tcg-analysis-review/components/DataList.tsx:4` | 汎用リスト | SupplierQualityList で使用 |
| `frontend/src/features/tcg-analysis-review/components/DataList.tsx:4` | DataListColumn 型 | supplierQuality.ts で import |

## GAS → FE マッピング

| GAS 関数 | BE エンドポイント | FE コンポーネント |
|---------|----------------|----------------|
| `api_getSupplierQualitySummaries` | `GET /api/v1/tcg/supplier-quality-summaries` | `SupplierQualityList.tsx` |
| `api_getSupplierSource(supplierId)` | `GET /api/v1/tcg/suppliers/{id}/source` | `SupplierDetailView.tsx` |
| `getAnalysisReviewPage({provider, stripRawText})` | `GET /api/v1/tcg/analysis-results?provider=&strip_raw_text=true` | `SupplierDetailView.tsx` |

## URL 変更

| Before | After |
|--------|-------|
| `/super-admin/tcg-analysis-review` | `/super-admin/tcg-supplier-quality` |

## i18n キー変更

| Before | After |
|--------|-------|
| `nav.superAdminTcgAnalysisReview` | `nav.superAdminTcgSupplierQuality` |
