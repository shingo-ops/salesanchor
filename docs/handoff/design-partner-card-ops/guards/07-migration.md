## 7. migration

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| ファイルを置くだけ → MIGRATION GUARD が落ちる | `scripts/run_all_migrations.sh` の末尾に `run_sql` を登録（現在188本） | CV-23・CARD-KW-RECON-03 |
| 検算に「スキーマ内の全テーブル数」等の全件カウント → 他の表を数えて例外 | 自分の担当範囲だけを数える | #3315（tenant_006）・常設指示 |
| テナントを推測 | tenant_001 = 空テスト、tenant_006 = Meta 審査専用（68表）。STANDARD-WORKFLOW.md:93 | #3315（未検証） |
| `migration-full-dryrun` は migrations 変更のある PR でしか走らない。集約は skipping を pass 扱い | 文書 PR の「pass」は実行ではない | CARD-KW-RECON-03 |
| 採番を推測 | root の `migrations/`。`YYYYMMDD_HHMMSS_説明_テナント.sql`。直近を実測してから採番 | CARD-BENCH-RECON-02 |
| アンカーが revert 済みで実在しない | `git show origin/main:` で実在確認 | CI-18（未検証） |
| migrations は CODEOWNERS で `@shingo-ops` 承認必須 | GO と承認は別。両方要る | 実測 |

