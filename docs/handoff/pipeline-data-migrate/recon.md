# recon: pipeline-data-migrate (Step 3/5)

## 対象ADR
- ADR-100: `docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md` — パイプライン設計
- ADR-072: `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md` — テナントスキーマ分離

## 既存実装の現在地

### tenant_004 スキーマのパイプラインテーブル（17テーブル）
Step 1/5 DDL により public スキーマにテーブルが作成済み（PR #3625）。
Step 3/5 は tenant_004 → public へのデータコピーを担当する。

### 移植対象テーブルとFK依存関係
```
supplier_channels          (no FK deps)
source_messages            (→ supplier_channels)
import_jobs                (no FK deps on migrating tables)
import_job_messages        (→ import_jobs, source_messages)
extraction_jobs            (→ source_messages)
extraction_items           (→ extraction_jobs)
extraction_attempts        (→ extraction_jobs)
analysis_runs              (→ extraction_jobs)
analysis_results           (→ extraction_items)
analysis_run_snapshots     (→ analysis_runs)
item_corrections           (BIGSERIAL PK, → extraction_items)
tcg_normalization_rules    (TEXT PK)
tcg_distribution_settings  (TEXT PK)
tcg_distribution_targets   (no FK deps)
tcg_product_import_jobs    (no FK deps)
tcg_product_import_rows    (→ tcg_product_import_jobs)
audit_log                  (BIGSERIAL PK)
```

### 影響範囲
- 作成ファイル: `scripts/migrate-pipeline-data-to-public.sh`
- 既存コード変更: なし
- DB変更: tenant_004 は読み取りのみ（INSERT先はpublic）
