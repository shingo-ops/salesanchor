# recon — sop-kpi2

**仕事名**: sop-kpi2  
**日付**: 2026-06-09  
**対象ADR**: ADR-121  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/check-process-artifacts.js:43` | DANGEROUS_PATTERNS 定義（migrations/deploy.yml/本番スクリプト等の危険パスリスト） |
| `scripts/check-process-artifacts.js:63` | classifyFile() — 3層パス区分（dangerous/docs/real-code）の実装 |
| `scripts/check-process-artifacts.js:78` | parseSOPDeclaration() — PR本文の「標準ワークフロー確認」セクション解析 |
| `scripts/check-process-artifacts.js:130` | validateDesignDoc() — 設計doc検証（受入基準・外部事例・相互参照） |
| `scripts/check-process-artifacts.js:179` | createFollowupIssue() — 緊急承認時の宿題 issue 自動起票 |
| `scripts/tests/test-process-artifacts.js:1` | §7受け入れ基準テスト（AC1〜AC6、28ケース） |
| `.github/workflows/process-artifacts-gate.yml:1` | 非必須 CI ゲート定義（pull_request → develop/main） |
| `.github/PULL_REQUEST_TEMPLATE.md:16` | PRテンプレの「標準ワークフロー確認」申告書セクション |
| `docs/STANDARD-WORKFLOW.md:1` | 標準ワークフロー唯一の正本 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Ruleset API で必須チェック追加可能か | `gh api repos/.../rulesets/16619490` で確認 → 可能 | ✅ 解消済み |
| 2 | Teams が使えない個人アカウントでの承認チェック | CODEOWNERS + PR Reviews API で代替 → `validateFileCitations` 実装済み | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
