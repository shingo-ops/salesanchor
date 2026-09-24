# design: extraction-rules-ui-improvement

- recon: docs/handoff/extraction-rules-ui-improvement/recon.md

## 参照ADR

- ADR-027: i18n強制（全UI文字列は t("key") 経由）
- ADR-144: UIガバナンス（金型コンポーネント必須）

## 設計方針

UIラベルと表示順の変更のみ。APIフィールド名・保存ロジック・マイグレーションは変更なし。

## 実装方法

| 項目 | 方法 |
|------|------|
| 折りたたみ | HTML native `<details>/<summary>`（ADR-144金型不要） |
| スタイル | デザイントークン変数のみ（raw数値禁止） |
| i18n | ja.json / en.json に同一キーを追加 |

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| フォーム上部に「Geminiへの抽出指示」が表示される | ブラウザ目視確認 |
| 詳細設定がデフォルト閉じ | ブラウザ目視確認 |
| 保存後にextraction_notesが正しく保存される | 保存→リロードで値が残る |
| ja/en両言語でキーが揃っている | grep確認済み |

## 外部・過去事例の参照と我々への応用

HTML native `<details>/<summary>` は同リポジトリ内で使用済み:
- `frontend/src/pages/super-admin/TcgSoldOutPage.tsx`
- `frontend/src/pages/goal-setting/GoalSettingPage.tsx`

「重要度の低い設定を折りたたみに格納してフォームを整理する」パターンはGitHub・Notion等の設定画面で広く採用されている。本PRでは同リポジトリの実績パターンをそのまま踏襲する。

## 維持の仕組み

- 守り手: .github/workflows/ui-governance-gate.yml（UIガバナンスgate）、frontend/scripts/check-i18n-missing-keys.js（i18nキー整合）
- i18n: ja.json / en.json 同一キー必須（CI「i18n key parity」チェックで自動検出）
- スタイル: デザイントークン変数のみ（ESLint no-restricted-syntax ルールで生値禁止）
- UIガバナンス: ADR-144準拠（金型コンポーネント使用・details はHTML標準タグ）

## 影響範囲

- 呼び出し元: `frontend/src/pages/super-admin/AnalysisRulesPage.tsx`（embedded=true で利用）
- APIへの影響: なし
- 他コンポーネントへの影響: なし

## 戻し方

`git revert <commit>` でフォーム順序が元に戻る。データ変更なし。
