# recon — ui-governance-gate

**仕事名**: ui-governance-gate  
**日付**: 2026-06-25  
**対象ADR**: ADR-144  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/check-ui-governance.js:36` | `PAGES_DIR = 'frontend/src/pages/'` — スキャン対象ディレクトリ定義 |
| `scripts/check-ui-governance.js:60` | `getChangedFiles()` — `git diff --name-status -M` で変更ファイル取得 |
| `scripts/check-ui-governance.js:106` | `isValidUiAllow()` — `/ui-allow:\s+\S+.*\(#\d+\)/` 正規表現 |
| `scripts/check-ui-governance.js:153` | `countSelect()` — `/<select[\s>/]/g` で生selectを検出 |
| `scripts/check-ui-governance.js:223` | `countInput()` — `extractInputTags()` + `isDetectableInput()` でtype判定 |
| `scripts/check-ui-governance.js:248` | `countTab()` — `/tab/ && !/table/` トークン判定で自作タブ検出 |
| `scripts/tests/test-ui-governance.js:1` | 自動テスト 22件（T1〜T22）。`require.main` パターンでエクスポートを利用 |
| `.github/workflows/ui-governance-gate.yml:26` | `fetch-depth: 0`（全歴史取得）、`node-version: '22'` |
| `.github/workflows/ui-governance-gate.yml:37` | `BASE_SHA` / `HEAD_SHA` 環境変数でCI実行 |
| `docs/adr/ADR-144-ui-component-governance.md:1` | ADR本文（Status: Accepted、Date: 2026-06-25）|
| `docs/CC_UI_GOVERNANCE.md:1` | CC遵守テンプレ（禁止事項・例外コメント書式）|
| `frontend/eslint.config.js:40` | `no-restricted-syntax`（ADR-067）— インラインstyle色/pxの既存ゲート |

## 既存との関係（テンプレ踏襲元）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/dangling-route-gate.yml:1` | 非必須ゲートの前例（本ゲートのテンプレ）|
| `scripts/check-dangling-routes.js:1` | `git show <sha>:path` パターンの踏襲元 |

---

## recon 実測値（2026-06-25 時点 develop ブランチ）

| 種別 | 件数 |
|------|------|
| 生 `<select>` in `pages/` | 118 件 |
| 生 `<input type="text\|search">` in `pages/` | 16 件 |
| 自作タブ（tab系className）in `pages/` | 20 件 |

→ これら既存件数は BASE/HEAD 比較方式のため **赤化しない**（HEAD増分のみ検出）

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `ui-allow:` の課題番号体系 | GitHub Issue 番号を想定。本番運用前に PO 確認 | 🔄 未確定（本PR非blocking）|

**未解決ゼロ確認（本PR範囲）**: 実装上の不明点はゼロ。番号体系は運用前に確定予定。
