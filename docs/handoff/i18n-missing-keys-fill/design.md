# design — i18n 欠落64キー追加

## 関連ドキュメント
- recon: docs/handoff/i18n-missing-keys-fill/recon.md
- 対象ADR: ADR-027（ADR-027-ui-internationalization.md）

## 概要
ADR-027 で定めた「全 UI 文字列は `t("key")` 経由」ルールに従い実装されたコードが呼ぶ翻訳キーが、ja.json・en.json に未定義のまま残っていた。本作業でそれらを追加し TRUE_MISSING=0 を達成する。

## 変更内容
- `frontend/src/locales/ja.json`: badges / buddy / goals / leads セクションに計64キー追加
- `frontend/src/locales/en.json`: 同上（ja と同一キー構成）
- プログラムファイル（.tsx/.ts）・migrations・deploy.yml への変更なし

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| TRUE_MISSING = 0 | recon-i18n2.cjs 相当スクリプトを実行し count 0 を確認 |
| ja / en ASYMMETRY = 0 | node -e で ja.size === en.size かつ非対称キーなしを確認 |
| JSON 構文エラーなし | JSON.parse で両ファイルをパースし例外なしを確認 |
| 変更ファイルが翻訳2ファイルのみ | git diff --stat で2ファイル以外が出ないことを確認 |

## 検証結果（実施済み）
```
ja 2816  en 2816  ASYMMETRY 0
TRUE_MISSING count 0
JSON OK
2 files changed, 134 insertions(+), 6 deletions(-)
```
削除6行はセクション末尾カンマ付け替えのみ（既存値変更なし）。

## 外部・過去事例の参照と我々への応用
i18next の missingKeyHandler は開発環境で `console.warn` を出力するのみ（`frontend/src/i18n.ts:41-46`）。本番ではキー名がそのまま表示される（例: "leads.initiative" という文字列がUIに出る）。今回の追加により該当ページのラベル欠損が解消される。過去事例として react-i18next 公式ドキュメントでは「キー追加は翻訳ファイルのみの変更で完結し、コード変更不要」とされており、今回もその原則に従い翻訳2ファイルのみを変更した。
