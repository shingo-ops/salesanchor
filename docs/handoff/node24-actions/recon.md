# recon: GitHub Actions Node 24 対応（ADR-129）

> 実コード調査。推測禁止・引用は必ず `file:line`。

## 1. 旧バージョン（更新前）の所在

更新前のバージョンを記録する。本 PR によって下記が全て更新済み。

### 1-1. `actions/checkout@v4`（→ `@v5`）

代表的な使用箇所:

- `.github/workflows/deploy.yml:28`
- `.github/workflows/test.yml:38`
- `.github/workflows/test.yml:67`
- `.github/workflows/test.yml:148`
- `.github/workflows/migration-test.yml:36`
- `.github/workflows/migration-test.yml:77`
- `.github/workflows/frontend-check.yml:14`
- `.github/workflows/frontend-check.yml:74`
- `.github/workflows/e2e.yml:47`
- `.github/workflows/e2e.yml:66`
- `.github/workflows/e2e.yml:118`
- `.github/workflows/claude-pipeline.yml:205`
- `.github/workflows/claude-pipeline.yml:280`
- `.github/workflows/claude-pipeline.yml:471`
- `.github/workflows/claude-pipeline.yml:559`
- `.github/workflows/claude-pipeline.yml:703`
- `.github/workflows/claude-pipeline.yml:988`

全 64 箇所（48 ワークフロー中）。

### 1-2. `actions/setup-node@v4`（→ `@v5`）

- `.github/workflows/deploy.yml:46`
- `.github/workflows/frontend-check.yml:18`
- `.github/workflows/frontend-check.yml:76`
- `.github/workflows/chromatic.yml:22`
- `.github/workflows/e2e.yml:69`
- `.github/workflows/e2e.yml:121`
- `.github/workflows/karte-gate.yml:37`
- `.github/workflows/check-claude-size.yml:32`
- `.github/workflows/design-token-audit.yml:19`
- `.github/workflows/security-scan.yml:30`
- `.github/workflows/adr-index-check.yml:24`
- `.github/workflows/process-artifacts-gate.yml:26`
- `.github/workflows/sop-health-reporter.yml:29`
- `.github/workflows/qa-smoke.yml:73`
- `.github/workflows/brand-asset-monitor.yml:123`

全 15 箇所。

### 1-3. `dorny/paths-filter@v3`（→ `@v4`）

- `.github/workflows/deploy.yml:34`
- `.github/workflows/test.yml:39`
- `.github/workflows/migration-test.yml:37`
- `.github/workflows/e2e.yml:48`
- `.github/workflows/karte-gate.yml:20`

全 5 箇所。

### 1-4. `webfactory/ssh-agent@v0.9.0`（→ `@v0.10.0`）

- `.github/workflows/deploy.yml:62`

全 1 箇所。

## 2. 影響範囲の確定

| 対象 | 参照数 | 備考 |
|------|--------|------|
| `actions/checkout` | 64 箇所 | 48 ワークフロー中に分散 |
| `actions/setup-node` | 15 箇所 | Node.js を明示的に使うジョブのみ |
| `dorny/paths-filter` | 5 箇所 | paths 分岐チェックのあるジョブのみ |
| `webfactory/ssh-agent` | 1 箇所 | `deploy.yml` のみ |
| **合計** | **85 箇所** | **48 ファイル** |

## 3. 除外ファイル

- `.github/workflows/workflow-lint.yml`: CLAUDE.md §不可逆操作 対象のため今回除外（`@v4` のまま残留）
  - 根拠: `.github/workflows/workflow-lint.yml:24`（`uses: actions/checkout@v4` のまま）

## 4. Breaking changes 調査

| アクション | Breaking changes | 根拠 |
|-----------|-----------------|------|
| `actions/checkout@v4→v5` | なし | `@v6` から credentials 保存先変更。今回は v5 止まりのため非該当 |
| `actions/setup-node@v4→v5` | なし | API 互換維持 |
| `dorny/paths-filter@v3→v4` | なし | runtime 更新のみ（filter syntax 変更なし） |
| `webfactory/ssh-agent@v0.9.0→v0.10.0` | なし | minor version bump |
