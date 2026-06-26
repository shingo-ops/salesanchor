# Recon: 指差呼称＋機械照合（触るファイル宣言 vs 実diff）

日付: 2026-06-24
正本: docs/handoff/sop-touch-files-guard/design.md

---

## 1. 既存の宣言パーサ

- `parseSOPDeclaration` 定義位置: `scripts/check-process-artifacts.js:124-146`
- 読む見出し: `### 標準ワークフロー確認`（正規表現: `/###\s*標準ワークフロー確認\s*\n/` — `scripts/check-process-artifacts.js:127`）
- 抽出項目（戻り値フィールド）:
  - `isExempt` — `- [x] 免除` チェック（`scripts/check-process-artifacts.js:132`）
  - `adrs` — `対象ADR:` 行（`scripts/check-process-artifacts.js:133`）
  - `reconPath` — `recon: docs/handoff/...` 行（`scripts/check-process-artifacts.js:134`）
  - `designPath` — `設計:` 行（`scripts/check-process-artifacts.js:135`）
  - `mode` — `モード: 些細|緊急`（`scripts/check-process-artifacts.js:136`）
- **「触るファイル」項目は存在しない（未抽出）**

---

## 2. 既存の照合の不在

- `runFullCheck` 定義: `scripts/check-process-artifacts.js:437`
- `runFullCheck` が検証する項目:
  - a. ADR参照（ファイル実在確認）: `scripts/check-process-artifacts.js:449-466`
  - b. recon.md 存在 + `file:line` 引用チェック: `scripts/check-process-artifacts.js:468-483`
  - c. 設計doc 存在 + `validateDesignDoc`: `scripts/check-process-artifacts.js:486-498`
- `runFullCheck` のシグネチャ: `function runFullCheck(declaration, { allowExempt = true } = {})` — `changedFiles` 引数なし（`scripts/check-process-artifacts.js:437`）
- **`changedFiles` と宣言ファイルリストの照合は `runFullCheck` 内で未実装**

---

## 3. 利用できる既存部品（追加配線不要）

- `prBody`: `scripts/check-process-artifacts.js:571`（`let prBody = ''` — `main()` 内ローカル変数、`:583` まで取得処理、`:585` 以降利用。新チェックから直接参照可）
- `changedFiles`: `scripts/check-process-artifacts.js:520`（`let changedFiles` — `main()` 内ローカル変数、`:531` までに確定。新チェックから直接参照可）
- `PR_NUMBER`: `scripts/check-process-artifacts.js:547`（`process.env.PR_NUMBER`。ワークフローから `.github/workflows/process-artifacts-gate.yml:35` で渡し済み）
- **挿入候補: `:584` 直後**（`prBody`・`changedFiles` 両方確定済み、かつ `hasDangerous → process.exit(0)` の `:612` より前＝危険PRにも適用される）

---

## 4. PRテンプレート

- `### 標準ワークフロー確認` セクション: `.github/PULL_REQUEST_TEMPLATE.md:26-33`
- 現在の内容（`:28-31`）:
  ```
  - [ ] 免除（自律クラフト：<理由>）
  - recon: <!-- docs/handoff/<task>/recon.md -->
  - 設計: <!-- docs/handoff/<task>/design.md -->
  - 対象ADR: <!-- ADR-XXX -->
  ```
- **「触るファイル:」行は存在しない**

---

## 5. 誤爆防止：除外対象（git管理下で実在確認済み）

- `frontend/package-lock.json` — npm自動更新（`git ls-files` 確認済み）
- `lp/package-lock.json` — npm自動更新（`git ls-files` 確認済み）
- `frontend/tests-e2e/funnel-dashboard-subpages.spec.ts-snapshots/*.png`（4ファイル）— ビジュアルテスト自動生成（`git ls-files` 確認済み）
- `frontend/tests-e2e/funnel-dashboard.spec.ts-snapshots/*.png`（2ファイル）— ビジュアルテスト自動生成
- `frontend/tests-e2e/karte-visual-gate.spec.ts-snapshots/*.png`（2ファイル）— ビジュアルテスト自動生成
- `.claude-pipeline/active-work.md` — `scripts/new-worktree.sh` 作成時・`.github/workflows/active-work-auto-review.yml` PR open時・マージ後に自動追記。作業者が宣言不能
- **既存の除外パターンは `scripts/check-process-artifacts.js` に存在しない**（`ignore`/`exclude`/`skip`/`lock` で grep → 0件）
