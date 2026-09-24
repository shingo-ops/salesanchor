# Design: fix-supplier-dashboard-severity

## KGI

LINE解析ダッシュボード > インポートタブ > 提供者別状況テーブルの severity バッジが、
raw key ではなく日本語/英語ラベル（「要対応」「注意」「正常」）で表示される。

## 変更方針

| 基準 | 検証方法 |
|------|----------|
| severity バッジに raw key が表示されない | ブラウザで表示確認（「要対応」「注意」「正常」が見える） |
| 抽出エラー列が表示される | エラー数が数値またはバッジで表示される |
| ja/en キー一致 | grep で両ファイルに supplierSeverity キーが存在すること |

## 実装詳細

1. getImportSeverity() 関数を削除（フロント独自計算廃止）
2. row.severity をそのまま使用（バックエンド計算値 danger/warning/success）
3. i18n キー追加:
   - supplierSeverity_danger: 「要対応」/ "Critical"
   - supplierSeverity_warning: 「注意」/ "Warning"
   - supplierSeverity_success: 「正常」/ "OK"
   - supplierExtractionErrors: 「抽出エラー」/ "Extraction Errors"

## 外部・過去事例の参照と我々への応用

ADR-027（i18n強制）・ADR-067（UIガバナンス）準拠（全UIテキストは t() 経由・生select/生input禁止）。
同様パターンは既存バッジコンポーネント全般で採用済み。
本PJでは StatusBadge/severity バッジの i18n 化を複数箇所で実施済み（deals, inbox 等）。
同じアプローチ（バックエンドから severity 文字列を受け取り、フロントで i18n キーに変換して表示）を踏襲する。

recon: docs/handoff/fix-supplier-dashboard-severity/recon.md

## 維持の仕組み

CI i18n key sync check（ja/en キー不一致でビルド失敗）。
フロント独自ロジックを削除し SSOT をバックエンドに一本化することで、今後の severity 定義変更はバックエンド側のみで完結する。

## 守り手

CI i18n key sync check（ja/en キー不一致でビルド失敗）

## 弊害・影響範囲

- 変更ファイル: 3件（tsx + 2 json）
- バックエンド変更なし
- 他コンポーネントへの影響なし
