# recon — migration-full-dryrun

**仕事名**: migration-full-dryrun  
**日付**: 2026-06-12  
**対象ADR**: ADR-135  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/migration-test.yml:554` | migration-full-dryrun ジョブ定義（ADR-135 強化） |
| `.github/workflows/migration-test.yml:860` | 全タイムスタンプSQLを順次実行するステップ |
| `.github/workflows/migration-test.yml:875` | 20260604以降のみ対象にするgrepフィルター |
| `.github/workflows/migration-test.yml:898` | migration-test aggregator が dryrun を needs に追加 |
| `scripts/run_all_migrations.sh:1` | run_sql の記載順が SSoT（この順序で実行） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 番号付きmigration（013〜100）がCI実行可能か | migrate_meta.py等Python依存のため不可と確認 | ✅ 解消済み |
| 2 | 20260602のSQL（category列依存）が失敗するか | 082番のPython依存migrationが先行しないため失敗。20260604以降に絞った | ✅ 解消済み |
| 3 | on: path filter で既存 migration-test との重複がないか | 同一pathフィルター。dryrunジョブはmigration変更時のみ起動 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
