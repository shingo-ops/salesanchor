# recon — release-pr-migration-manifest

**仕事名**: release-pr-migration-manifest  
**日付**: 2026-06-12  
**対象ADR**: ADR-135  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/auto-release-pr.yml:39` | MIGRATION_FILES を git diff で検出するステップ |
| `.github/workflows/auto-release-pr.yml:41` | migrationなしの場合 ✅ バナーを挿入 |
| `.github/workflows/auto-release-pr.yml:53` | migrationあり検出時のログ出力 |
| `.github/workflows/auto-release-pr.yml:1` | auto-release-pr.yml ファイル全体（66行） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | PR_BODYをenv変数で渡すと複数行が壊れるか | run: 内インライン変数に変更して解消 | ✅ 解消済み |
| 2 | git diff origin/main..HEAD で正しくmigrationを検出できるか | auto-release-pr は develop→main PR のため origin/main..HEAD が適切 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
