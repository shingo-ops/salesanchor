# PARITY-03 Phase 2 FE — design

対象ADR: ADR-154 (GAS→Python migration policy)

## 設計方針

### 削除 vs 保持の判断

- **削除**: StatusTabBar, reviewTabs, AnalysisReviewWorkspace, ReviewListPanel, reviewListColumns, reviewListViewModel, analysis-review.css — 比較ビュー専用。仕入元サマリーには不要
- **保持**: ItemComparison, SourceRawPane, DataList — 仕入元詳細ビューで再利用

### ページ遷移モデル（SPA 内 master-detail）

`TcgSupplierQualityPage` が `selected` state を持ち、null=一覧、非null=詳細。React Router ネストなし（URL変化なし）。GAS の `SupplierQualityPage + SupplierDetailPage` の画面遷移をそのまま再現。

### Phase 2 スコープ外（Phase 3+ 以降）

- `ProductMasterDrawer` — 商品登録ドロワー（B-1〜B-5 GAS 関数）
- 詳細ビューの「修正する →」ボタンは disabled プレースホルダで表示

### snake_case → camelCase 変換

BE は snake_case (FastAPI Pydantic デフォルト)。FE の `mapSummary()` で変換。`SupplierQualityList.tsx:21-29` に集約。

## 受入基準

| 基準 | 検証方法 |
|------|---------|
| `/super-admin/tcg-supplier-quality` にアクセスすると仕入元一覧が表示される | ブラウザ手動確認 |
| SP0057 (Hiroshi) が analysisCount=0 で一覧に表示される | API レスポンスに supplier_id=SP0057 が含まれることを確認 |
| 仕入元行クリックで詳細ビューに遷移し、原文パネルとアイテムリストが表示される | ブラウザ手動確認 |
| 「← 一覧に戻る」で一覧に戻る | ブラウザ手動確認 |
| `conditionFallbackCount=null` の行は「集計準備中」と表示される | 一覧で確認 |
| `nav.superAdminTcgAnalysisReview` キーが削除され、`superAdminTcgSupplierQuality` が追加されている | `grep -r superAdminTcgAnalysisReview frontend/` が 0 件 |
| TypeScript コンパイルエラーなし | `cd frontend && npx tsc --noEmit` |

## 外部・過去事例

- GAS SupplierQualityPage の master-detail パターンを直接移植（同一プロジェクト内）
- DataList コンポーネントは Phase 1 で実装済み。Phase 2 は拡張なしで再利用
