# Recon: 既存行の削除検知（削除ファイル宣言 vs 実diff）

日付: 2026-06-24
正本: docs/handoff/sop-delete-detect/design.md

---

## 1. 削除行数の取得手段

- 既存の `git diff --name-only` 呼び出し: `scripts/check-process-artifacts.js:530`
  ```js
  changedFiles = execSync(`git diff --name-only "${base}...${head}"`, { encoding: 'utf8' })
  ```
- `git diff --numstat "${base}...${head}"` は同じ `BASE_SHA`/`HEAD_SHA` で実行可能（追加env・yml変更不要）
- 出力形式（実行確認済み）: `追加行数\t削除行数\tファイルパス`（例: `9\t0\t.claude-pipeline/active-work.md`）
- `BASE_SHA` / `HEAD_SHA` の取得元: `.github/workflows/process-artifacts-gate.yml:33-34`
- ファイル丸ごと削除（git rm）は削除行のみ・追加0で現れる。`--name-only` と同形式のパスで出力される

---

## 2. parseSOPDeclaration の現在の戻り値構造

- 関数定義: `scripts/check-process-artifacts.js:127`（`origin/develop` 版）
- `touchFiles` 追加: PR #2544（`scripts/check-process-artifacts.js:138-145` の `touchFilesMatch` 抽出〜`touchFiles` フィールド）
- 現在の戻り値フィールド（`origin/develop`）:
  ```js
  { isExempt, adr, adrs, reconPath, designPath, mode, touchFiles }
  ```
- `touchFiles` の抽出パターン（`origin/develop:scripts/check-process-artifacts.js:17`相当）:
  ```js
  const touchFilesMatch = section.match(/触るファイル:\s*([^\n]*(?:\n(?![-*#\s])[^\n]*)*)/);
  ```
- `deleteFiles` は同型のパターンで追加可能（`触るファイル:` → `削除するファイル:` に変えるだけ）

---

## 3. PRテンプレートの挿入位置

- `origin/develop:.github/PULL_REQUEST_TEMPLATE.md:26-34`:
  ```
  :26  ### 標準ワークフロー確認
  :28  - [ ] 免除（自律クラフト：<理由>）
  :29  - recon: <!-- ... -->
  :30  - 設計: <!-- ... -->
  :31  - 対象ADR: <!-- ADR-XXX -->
  :32  - 触るファイル: <!-- ... -->   ← PR #2544 で追加済み
  :33                                  ← 「削除するファイル:」の挿入位置
  :34  <!-- 書類のみのPRは... -->
  ```
- 挿入位置: `:32`（触るファイル行）の直後、`:33`（空行）の前

---

## 4. 既存流用部品（追加配線不要）

- `GRACE_THRESHOLD_PR = 2600`: `scripts/check-process-artifacts.js:606`（PR #2544 で追加）
- `TOUCH_FILE_EXCLUDE_PATTERNS`（3パターン）: `scripts/check-process-artifacts.js:607-611`
  - `/package-lock\.json$/`
  - `/-snapshots\/.*\.png$/`
  - `/^\.claude-pipeline\/active-work\.md$/`
- `printFailure` 定義: `scripts/check-process-artifacts.js:434`（`process.exit(1)` で終了）
- 照合ブロック挿入後の位置: `// 危ない変更の処理（GO記録チェック）` コメント直前（`:628`相当）

---

## 5. 変数スコープ（新チェックから参照可能）

- `prBody`: `scripts/check-process-artifacts.js:571`（`main()` 内ローカル）
- `changedFiles`: `scripts/check-process-artifacts.js:520`（`main()` 内ローカル）
- `declaration`: `scripts/check-process-artifacts.js:585`（`parseSOPDeclaration(prBody)` の戻り値）
- `prNumber`: `scripts/check-process-artifacts.js:547`（`process.env.PR_NUMBER`）
- `base` / `head`: `scripts/check-process-artifacts.js:524-525`（`BASE_SHA`/`HEAD_SHA`）— ただし `changedFiles` 取得ブロック内のローカル変数のため、numstat 実行時は `process.env.BASE_SHA`/`process.env.HEAD_SHA` を直接参照する
