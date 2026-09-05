# recon: tenant_006 テーブル作成（QA-01）

## 目的

tenant_006 に TCG 解析パイプライン全テーブルを作成し、QA を開始できる状態にする。

---

## 2026-09-05 実測: TCG系 migration の現状

### ファイル一覧（全 _t004 ファイル）

```
migrations/20260831_110000_create_tcg_analysis_tables_t004.sql
migrations/20260901_090000_add_condition_resolution_columns.sql
migrations/20260901_120000_add_unit_inference_columns_t004.sql
migrations/20260902_110000_tcg_classification_masters.sql
migrations/20260902_110100_tcg_products_classification_ids.sql
migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql
migrations/20260903_130000_tcg_note_master_t004.sql
migrations/20260903_150000_tcg_status_master_t004.sql
migrations/20260903_160000_tcg_normalization_rules_t004.sql
migrations/20260903_170000_item_corrections_t004.sql
migrations/20260903_180000_tcg_products_mark_en_t004.sql
migrations/20260903_190000_tcg_normalization_rules_nr0136.sql
migrations/20260903_200000_tcg_distribution_targets_t004.sql
migrations/20260903_210000_tcg_distribution_settings_t004.sql
migrations/20260903_220000_create_tcg_analysis_history_t004.sql
migrations/20260904_160000_tcg_magazine_promo_products_t004.sql
migrations/20260905_010000_tcg_pokemon_master_batch1_t004.sql
migrations/20260905_020000_tcg_fix_product_names_t004.sql
migrations/20260905_120000_register_15_suppliers_t004.sql
migrations/20260905_140000_import_jobs_review_stage_t004.sql
migrations/20260905_150000_record_manual_supplier_fixes_t004.sql
```

### スキーマ指定方法

**全ファイルが `_schema TEXT := 'tenant_004'` + `EXECUTE format(...%I..., _schema)` で変数化済み。**
直書きなし。スキーマ名を差し替えるだけで他テナントへ適用可能。

### CREATE TABLE を含む migration（スキーマ骨格に関わるもの）

| ファイル | 作成テーブル / 追加列 |
|---------|----------------------|
| `20260831_110000_create_tcg_analysis_tables_t004.sql` | 18 テーブル（骨格） |
| `20260901_090000_add_condition_resolution_columns.sql` | conditions +3 列（priority/search_kw/exclude_kw） |
| `20260901_120000_add_unit_inference_columns_t004.sql` | analysis_results +4 列（unit_inferred/unit_basis/unit_confidence/unit_infer_reason） |
| `20260902_110000_tcg_classification_masters.sql` | tcg_major_categories / tcg_series / tcg_manufacturers / tcg_product_categories |
| `20260902_110100_tcg_products_classification_ids.sql` | tcg_products FK 制約 ADD（division/work/manufacturer/product_category） |
| `20260903_170000_item_corrections_t004.sql` | item_corrections |
| `20260903_180000_tcg_products_mark_en_t004.sql` | tcg_products +2 列（mark/english_title） |
| `20260903_200000_tcg_distribution_targets_t004.sql` | tcg_distribution_targets |
| `20260903_210000_tcg_distribution_settings_t004.sql` | tcg_distribution_settings |
| `20260903_220000_create_tcg_analysis_history_t004.sql` | analysis_runs / analysis_run_snapshots |
| `20260905_140000_import_jobs_review_stage_t004.sql` | import_jobs +5 列（pending_messages/window_start/window_end/unresolved_names/review_status） |

### 006 にテーブルが存在しない事実

2026-09-05 時点で `tenant_006` スキーマは存在しない（サーバー未作成）。
テーブルが 0 件のため QA が始められない。
本 PR でテーブルを作成してから QA を開始する。

---

## 既存 ADR 検索結果

```
git grep -i "tenant_006\|qa.*tenant\|schema.*qa" docs/adr/ -- "*.md"
```

該当なし。QA テナントスキーマに関する ADR は未起票。

---

## 影響ファイル（本 PR で変更するもの）

| ファイル | 変更内容 |
|---------|----------|
| `migrations/20260906_100000_create_tcg_tables_t006.sql` | 新規作成 |
| `scripts/run_all_migrations.sh` | 末尾に `run_sql` 1行追記 |
| `docs/handoff/qa-tenant-006-tables/recon.md` | 新規作成（本ファイル） |
| `docs/handoff/qa-tenant-006-tables/design.md` | 新規作成 |

---

## 守り手

人手で守る（migration 実行後に RAISE NOTICE のテーブル数=27 を目視確認）。
