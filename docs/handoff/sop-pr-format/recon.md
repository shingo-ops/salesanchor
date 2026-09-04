# recon: sop-pr-format

## タスク概要

executor-preamble.md に PR作成手順（「### PR作成の手順（例外なし）」セクション）を追記する。
本日の実測で判明した process-artifacts gate の検査規則を文書化し、次便以降の失敗を防ぐ。

## 既存ADR検索結果

- `docs/adr/ADR-121-sop-process-artifacts-gate.md` — 既存: process-artifacts gate の設計根拠
- `docs/adr/ADR-050-release-pr-workflow-standardization.md` — 既存: リリースPRワークフロー標準化

## 対象ファイル

### 変更
- `docs/ai-agents/executor-preamble.md` — 末尾に PR作成手順セクションを追記（既存行変更なし）

### 新規作成
- `docs/handoff/sop-pr-format/recon.md` — 本ファイル
- `docs/handoff/sop-pr-format/design.md` — 設計doc

## process-artifacts gate 検査規則（実測）

### 触るファイル / 削除するファイル の正規表現

`scripts/check-process-artifacts.js:211` — 触るファイル: の正規表現:
```
/触るファイル:\s*([^\n]*(?:\n(?![-*#\s])[^\n]*)*)/
```
コロン同一行にカンマ区切りで書く。行頭 `-` （箇条書き）は取得されない。

`scripts/check-process-artifacts.js:219` — 削除するファイル: も同じ構造。
`scripts/check-process-artifacts.js:225` — `f !== 'なし'` でフィルタ済みのため、
`なし` と書いても deleteFiles=[] 扱いになる。
実際に diff の deletions があるファイルがあれば、そのパスを列挙しなければならない。

### 削除ファイルの照合ロジック

`scripts/check-process-artifacts.js:797` — `git diff --numstat` で deletions > 0 のファイルを抽出。
`scripts/check-process-artifacts.js:807` — `deleteFiles.length === 0` かつ `deletedFiles.length > 0` → エラー。

### ADR / recon / 設計 のパース

`scripts/check-process-artifacts.js:207` — `extractTargetADRs(section)` で ADR を抽出。
`scripts/check-process-artifacts.js:208` — `recon:\s*(docs\/handoff\/[^\s\n]+\.md)` で recon パスを取得。
`scripts/check-process-artifacts.js:209` — `設計:\s*([^\n（]+)` で設計 doc パスを取得。
平打ち形式が必須。テーブル記法（`| ADR | ADR-XXX |`）はパースされない。

### validateFileCitations（recon.md の内部チェック）

`scripts/check-process-artifacts.js:390` — `validateFileCitations(content)` の定義。
`scripts/check-process-artifacts.js:609` — recon.md の内容に対して呼び出される（design.md は対象外）。
バッククォート付きパスのうち、.md/.ts/.tsx/.js/.py/.yml/.yaml/.json を持つものが existsSync で検査される。
削除済み・存在しないファイルをバッククォートで書くと CI が落ちる。

### validateDesignDoc

`scripts/check-process-artifacts.js:402` — `validateDesignDoc(designContent, reconPath, adr)` の定義。
`scripts/check-process-artifacts.js:624` — design.md の内容に対して呼び出される。
`| 基準 | 検証方法 |` テーブルの存在、recon.md パスの本文中への記載、ADR 参照が必須。

## PR テンプレートの宣言欄

`.github/PULL_REQUEST_TEMPLATE.md` は既存（実在確認済み）。
`.github/PULL_REQUEST_TEMPLATE.md:26` — `### 標準ワークフロー確認` セクション。
`.github/PULL_REQUEST_TEMPLATE.md:33` — `触るファイル:` の宣言欄。
`.github/PULL_REQUEST_TEMPLATE.md:34` — `削除するファイル:` の宣言欄。

## 既存正本の場所

`docs/handoff/sop-kpi2/design.md` — sop-kpi2 の設計doc（§2〜§4 が process-artifacts gate の正本として参照される）。
