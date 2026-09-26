# Design: extraction-ranking-cta

## 目的
抽出ランキングセクション（提供者ワースト・商品ワースト）にアクション導線（CTAボタン）を追加し、問題発見から改善操作へのナビゲーションを提供する。

## 受入条件

| 条件 | 検証方法 |
|------|---------|
| 抽出率ワースト提供者セクションにCTAが2つ表示される（「提供者マスタを確認」「抽出ルールを調整」） | ブラウザでExtractionタブを開き、ランキングセクション下部に2ボタン確認 |
| 照合率ワースト商品セクションにCTAが1つ表示される（「商品マスタを確認」） | 同上、商品ランキングセクション下部に1ボタン確認 |
| CTAクリックで対応ページに遷移する | 各ボタンクリックでサイドバー遷移を確認 |
| 全テキストがi18nキー経由である | コードにハードコード文字列なし |

## 変更内容

### AnalysisDashboardPanel.tsx
- 提供者ランキングセクション（line ~1252）: `analysis-dashboard-ctas` div + 2CTAボタン追加
  - `onNavigate("supplier-master")` — 提供者マスタを確認
  - `onNavigate("extraction-rules")` — 抽出ルールを調整
- 商品ランキングセクション（line ~1303）: `analysis-dashboard-ctas` div + 1CTAボタン追加（primary）
  - `onNavigate("product-master")` — 商品マスタを確認

### i18n
- ja.json: `extractionRankCtaSupplierMaster` / `extractionRankCtaExtractionRules` / `extractionRankCtaProductMaster`
- en.json: 同上（英語訳）

## 関連ADR
- ADR-027: ui internationalization（全UIテキストt()経由）
- ADR-138: extraction analysis design
- ADR-144: UI governance（既存CSSクラス使用）

## 外部事例
既存のImportTabContent・AnalysisTabContentにある同パターン（analysis-dashboard-ctas + analysis-dashboard-cta-btn）を踏襲。

## 守り手
- CI: TypeScript型チェック（node_modules利用時）
- ADR-027 grep チェック
