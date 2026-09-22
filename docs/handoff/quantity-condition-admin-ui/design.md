# design — quantity-condition-admin-ui

**仕事名**: quantity-condition-admin-ui
**日付**: 2026-09-22
**対象ADR**: ADR-027（i18n）, ADR-144（UI金型）

---

## KGI / KPI

| 基準 | 検証方法 |
|-----|---------|
| 状態定義マスタ CRUD が管理画面で操作できる | AnalysisRulesPage → 状態定義マスタ選択 → CRUD 操作確認 |
| 販売単位マスタに状態数・ライン数カラムが表示される | AnalysisRulesPage → 販売単位マスタ選択 → テーブルにカラム確認 |

## 変更方針

- ConditionDefsMasterPanel.tsx を既存 QuantityUnitsMasterPanel.tsx と同パターンで新規作成
- AnalysisRulesSidebar に condition-defs-master エントリ追加
- AnalysisRulesPage に ConditionDefsMasterPanel 組み込み
- i18n キー追加（ja/en 両方）

## 影響範囲

- 呼び出し元: AnalysisRulesPage のみ（ルーティングなし）
- 新規追加のみ。既存コードの動作変更なし

## 外部・過去事例

- 既存の WeightClassesMasterPanel, QuantityUnitsMasterPanel が同パターンの先行実装

## 維持の仕組み

- ADR-027: i18n キー追加時は ja/en 両ファイルに同一キーを追加するルール
- ADR-144: 新規 UI コンポーネントは金型コンポーネントのみ使用

## 戻し方

- ConditionDefsMasterPanel.tsx 削除
- AnalysisRulesSidebar / AnalysisRulesPage の追加行を revert
- i18n の追加キーを削除
