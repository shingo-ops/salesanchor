# Design: fix-supplier-dashboard-severity

## KGI

LINE解析ダッシュボード > インポートタブ > 提供者別状況テーブルの severity バッジが、
raw key ではなく日本語/英語ラベル（「要対応」「注意」「正常」）で表示される。

## 変更方針

| 基準 | 検証方法 |
|------|----------|
| severity バッジに raw key が表示されない | ブラウザで表示確認（「要対応」「注意」「正常」が見える） |
| 抽出エラー列が表示される | エラー数が数値またはバッジで表示される |
| ja/en キー一致 | `grep -r supplierSeverity frontend/src/locales/` で両ファイルに存在確認 |

## 実装詳細

1. `getImportSeverity()` 関数を削除（フロント独自計算廃止）
2. `row.severity` をそのまま使用（バックエンド計算値 `danger/warning/success`）
3. i18n キー追加:
   - `supplierSeverity_danger`: 「要対応」/ "Critical"
   - `supplierSeverity_warning`: 「注意」/ "Warning"
   - `supplierSeverity_success`: 「正常」/ "OK"
   - `supplierExtractionErrors`: 「抽出エラー」/ "Extraction Errors"

## 外部事例

ADR-027準拠（全UIテキストは `t()` 経由）。同様パターンは既存バッジコンポーネント全般で採用済み。

## 守り手

CI i18n key sync check（ja/en キー不一致でビルド失敗）

## 弊害・影響範囲

- 変更ファイル: 3件（tsx + 2 json）
- バックエンド変更なし
- 他コンポーネントへの影響なし
