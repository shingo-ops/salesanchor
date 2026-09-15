# PARITY-03 Phase 2 FE — design

**対象ADR**: ADR-154 (GAS→Python migration policy)
**recon**: docs/handoff/parity03-supplier-quality-fe/recon.md
**日付**: 2026-09-02

---

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

BE は snake_case (FastAPI Pydantic デフォルト)。FE の `mapSummary()` で変換。`frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx:21` に集約。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `/super-admin/tcg-supplier-quality` にアクセスすると仕入元一覧が表示される | ブラウザ手動確認 |
| SP0057 (Hiroshi) が analysisCount=0 で一覧に表示される | API レスポンスに supplier_id=SP0057 が含まれることを確認 |
| 仕入元行クリックで詳細ビューに遷移し、原文パネルとアイテムリストが表示される | ブラウザ手動確認 |
| `conditionFallbackCount=null` の行は「集計準備中」と表示される | 一覧で確認 |
| `nav.superAdminTcgAnalysisReview` キーが削除され `superAdminTcgSupplierQuality` が追加されている | `grep -r superAdminTcgAnalysisReview frontend/` が 0 件 |
| TypeScript コンパイルエラーなし | `cd frontend && npx tsc --noEmit` |

---

## 技術 How・KPI

- KPI: 仕入元サマリー一覧が 45 件表示される（source-first 集計により SP0057 含む）
- 技術選択: GAS SupplierQualityPage を React + FastAPI API 呼び出しに直接移植

---

## 弊害・トレードオフ

- 旧URL `/super-admin/tcg-analysis-review` はブックマーク無効化 → ロールバックは git revert で即時可能

---

## 外部・過去事例

- GAS SupplierQualityPage の master-detail パターンを直接移植（同一プロジェクト内 ADR-154）
- DataList コンポーネントは Phase 1 で実装済み。Phase 2 は拡張なしで再利用（DRY 原則）

---

## 維持の仕組み

守り手: 人手で守る（PARITY-03 は GAS→Python 段階移植。dangling-route gate が URL ルート整合を監視）

- URL 変更時は `frontend/src/App.tsx` のルートと `locales/*.json` のキーを同時更新
- 新規 API 追加時は recon.md と design.md の GAS→FE マッピング表を更新

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 比較ビュー9ファイル削除 | Generator |
| 2 | supplierQuality.ts / SupplierQualityList.tsx / SupplierDetailView.tsx 作成 | Generator |
| 3 | TcgSupplierQualityPage 作成 | Generator |
| 4 | App.tsx ルート変更・i18n キー差し替え | Generator |

---

## 継続

- Phase 3: ProductMasterDrawer (B-1〜B-5 GAS 関数) の実装
- Phase 4: 詳細ビューの「修正する →」ボタン有効化
