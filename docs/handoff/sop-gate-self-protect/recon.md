# Recon: 関所の自己保護（DANGEROUS_PATTERNS 拡張）

日付: 2026-06-24
正本: docs/handoff/sop-gate-self-protect/design.md

---

## 1. classifyFile() の評価順（file:line 実引用）

- 定義: `scripts/check-process-artifacts.js:73-78`
- 評価順:
  1. `DANGEROUS_PATTERNS` — `scripts/check-process-artifacts.js:74`
  2. `DOCS_PATTERNS` — `scripts/check-process-artifacts.js:75`
  3. `REAL_CODE_PATTERNS` — `scripts/check-process-artifacts.js:76`
  4. `'unknown'`（fallthrough）— `scripts/check-process-artifacts.js:77`
- **DANGEROUS_PATTERNS は DOCS_PATTERNS より先に評価される**（`:74` < `:75`）

## 2. DANGEROUS_PATTERNS 現在の全行（追加前）

- 定義: `scripts/check-process-artifacts.js:47-52`
  - `:48` `/^migrations\//` — DBマイグレーション
  - `:49` `/^scripts\//` — 本番スクリプト全般
  - `:50` `/^\.github\/workflows\/deploy\.yml$/` — デプロイワークフロー
  - `:51` `/^frontend\/src\/pages-layout\.css$/` — 全ページ共通レイアウト

## 3. hasDocsOnly 早期passの制御（file:line 実引用）

- `hasDocsOnly` 算出: `scripts/check-process-artifacts.js:83`
  ```js
  const hasDocsOnly = !hasDangerous && !hasRealCode;
  ```
- 早期pass条件: `scripts/check-process-artifacts.js:541-544`
  ```js
  if (hasDocsOnly) {
    console.log('✅ 書類のみの変更 — 自動スキップ（pass）');
    process.exit(0);
  }
  ```
- `hasDangerous` 算出: `scripts/check-process-artifacts.js:81`
  ```js
  const hasDangerous = files.some(f => classifyFile(f) === 'dangerous');
  ```
- **ファイルが1つでも `'dangerous'` を返せば `hasDangerous=true` → `hasDocsOnly=false` → 早期passしない**

## 4. 保護対象ファイルの現在の分類（追加前）

| ファイル | DOCS_PATTERNS 一致パターン | 追加前分類 |
|---|---|---|
| `docs/STANDARD-WORKFLOW.md` | `/^docs\//`（`:37`）+ `/\.md$/`（`:38`） | `docs` → 早期pass |
| `.github/workflows/process-artifacts-gate.yml` | DOCS 不一致、`REAL_CODE` `/^\.github\/workflows\//`（`:60`）一致 | `real-code` |
| `.github/PULL_REQUEST_TEMPLATE.md` | `/^\.github\/(?!workflows\/)/`（`:44`）+ `/\.md$/`（`:38`） | `docs` → 早期pass |
