# recon: fix-migration-guards

## KGI
デプロイ時に全マイグレーション(1-270+)が失敗なく完走すること。
具体的: `20260921_050000_drop_tenant004_pipeline_tables.sql` 適用後の再デプロイで、
以下6つのマイグレーションがエラーなく`SKIP`または正常完了すること。

## 現在地把握

### 問題の構造
- DROP migration (migrations/20260921_050000_drop_tenant004_pipeline_tables.sql) がパイプラインテーブル12種を削除
- `tenant_004` スキーマ自体は残存する
- 旧マイグレーションがスキーマ存在ガード (`pg_namespace WHERE nspname = 'tenant_004'`) のみ持つ
- スキーマガードはPASSするが、テーブルが消えているため ALTER/UPDATE/INSERT が失敗

### 調査対象ファイル全走査

対象テーブル12種:
`analysis_results`, `analysis_runs`, `analysis_run_snapshots`,
`extraction_items`, `extraction_jobs`, `extraction_attempts`,
`import_jobs`, `import_job_messages`, `source_messages`,
`supplier_channels`, `item_corrections`, `audit_log`

#### 既にガード済み（変更不要）

| ファイル | ガード方式 | 判定 |
|---------|-----------|------|
| migrations/20260901_120000_add_unit_inference_columns_t004.sql | `information_schema.columns` 列単位チェック | 安全 |
| migrations/20260906_230000_redact_extraction_error_keys_t004.sql | `information_schema.tables` テーブルガード | 安全 |
| migrations/20260917_010000_add_product_code_to_extraction.sql | `pg_class` ループ（存在テナントのみ） | 安全 |
| migrations/20260919_190000_fix_extraction_work_id_type.sql | `pg_tables` ループ（存在テナントのみ） | 安全 |
| migrations/20260917_020000_supplier_ssot_migration.sql | `pg_namespace JOIN pg_class` ループ | 安全 |
| migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql | `pg_namespace JOIN pg_class WHERE c.relname = 'analysis_results'` | 安全 |
| migrations/20260831_110000_create_tcg_analysis_tables_t004.sql | `CREATE TABLE IF NOT EXISTS`（再作成は安全） | 安全 |
| migrations/20260905_120000_register_15_suppliers_t004.sql | `to_regclass('.supplier_channels')` ガード済み | 安全 |
| migrations/20260903_170000_item_corrections_t004.sql | `CREATE TABLE IF NOT EXISTS` | 安全 |

#### 修正が必要なファイル（6件）

| ファイル | 問題 | 修正内容 |
|---------|------|---------|
| migrations/20260905_140000_import_jobs_review_stage_t004.sql:16-28 | スキーマガードのみ、`ALTER TABLE import_jobs` | `import_jobs` テーブルガード追加 |
| migrations/20260905_150000_record_manual_supplier_fixes_t004.sql:32-35 | `tcg_suppliers` ガードのみ、`INSERT INTO supplier_channels` | `supplier_channels` テーブルガード追加 |
| migrations/20260907_120000_tcg_dist_stale_jobs_terminate_t004.sql:29-32 | スキーマガードのみ、`UPDATE extraction_jobs` | `extraction_jobs` テーブルガード追加 |
| migrations/20260908_130000_tcg_sp0136_requeue_extraction_t004.sql:29-32 | スキーマガードのみ、`UPDATE extraction_jobs` | `extraction_jobs` テーブルガード追加 |
| migrations/20260908_210000_tcg_sp0136_supersede_old_message_t004.sql:40-43 | スキーマガードのみ、`UPDATE source_messages` | `source_messages` テーブルガード追加 |
| migrations/20260910_180000_tcg_interrupted_jobs_recovery_t004.sql:17-21 | `table_count < 3` で `RAISE EXCEPTION`（部分削除時に失敗） | `RAISE EXCEPTION` → `RETURN` に変更 |

## 関連ADR
- 該当ADRなし（既存マイグレーションへの安全ガード追加のみ）
- 参考: `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`
