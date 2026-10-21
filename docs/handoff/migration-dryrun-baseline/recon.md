# recon: 試し実行（migration-full-dryrun）の失敗と除外行

> 実験 A〜F の結果と採用案は design.md を参照。

生出力: /tmp/CC報告ファイル/dryrun_recon/{e_errors2,b_create,d_reg,c_steps,g_adr,f_dump}.txt, exclusions.tsv（CI run 39009175807 の 2周目ログ, origin/main 基準）

## 1. 事実: 2周目で ❌ になったファイル（e_errors2.txt の `❌ [2周目 n/289]` 行を全数抽出）

基準の2周目失敗は 21 本（run 39009175807 ログ 6703行「2周目: 成功 268 / 失敗 21」を Opus が確認）。e_errors2.txt の抽出で ❌ 行が 16 本しか取れなかったのは抽出条件の差で、本数の正はログの集計行。

1. migrations/20260920_050000_status_master_add_tenant_id.sql（e_errors2.txt:6623）
2. migrations/20260920_060000_note_master_tenant_id.sql（:6624）
3. migrations/20260920_070000_product_categories_tenant_id.sql（:6625）
4. migrations/20260923_050000_add_indexes_public_analysis_results.sql（:6645）
5. migrations/20260923_120000_add_work_id_to_analysis_results.sql（:6646）
6. migrations/20260927_130000_add_extraction_token_cost_columns.sql（:6658）
7. migrations/20260930_130000_set_discord_welcome_template_english.sql（:6662）
8. migrations/20260930_150000_create_llm_usage_events.sql（:6663）
9. migrations/20261009_180000_v102_engine_columns.sql（:6676）
10. migrations/20261010_120000_create_analysis_soldout_extra_targets.sql（:6678）
11. migrations/20261011_150000_add_analysis_results_price_basis.sql（:6679）
12. migrations/20261012_100000_add_extraction_jobs_system_review_detail.sql（:6680）
13. migrations/20261012_200000_add_extraction_attempts_thought_summaries.sql（:6681）
14. migrations/20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql（:6682）
15. migrations/20261013_140000_add_analysis_results_ship_ja_ship_en.sql（:6687）
16. migrations/20261013_140100_add_tcg_note_master_label_template_en.sql（:6688）

## 2. 原因（DB ログの ERROR 行。e_errors2.txt）

- `relation "public.tcg_status_master" does not exist`（:7250）、`public.tcg_note_master`（:7252）、`public.tcg_product_categories`（:7255）
- `relation "public.analysis_results" does not exist`（:7270, :7273, :7276, :7364, :7375, :7383）
- `public.extraction_attempts`（:7303, :7313, :7379）、`public.source_messages`（:7305）、`public.extraction_jobs`（:7377）、`public.extraction_items`（:7362）、`public.tcg_distribution_targets`（:7381）、`public.llm_usage_events`（:7342）、`public.tenant_discord_ticket_config`（:7310）

## 3. 作成元 migration（b_create.txt）と登録位置（d_reg.txt）

| 表 | 作成元 | 作成元の除外行 |
|---|---|---|
| tcg_status_master / tcg_note_master / tcg_product_categories | migrations/20260919_020000_master_ssot_public_tables.sql:234,259,283 | scripts/migration-guard/dryrun-exclusions.tsv:27 |
| analysis_results / extraction_* / source_messages / tcg_distribution_targets | migrations/20260921_110000_pipeline_tables_public.sql:20,80,93,112,214,362 | scripts/migration-guard/dryrun-exclusions.tsv:30 |
| tenant_discord_ticket_config | migrations/20260602_120000_add_discord_ticket_config.sql:5 | scripts/migration-guard/dryrun-exclusions.tsv:13 |
| llm_usage_events | migrations/20260930_150000_create_llm_usage_events.sql:26（自身も失敗） | なし |

3本とも scripts/run_all_migrations.sh に登録済み（d_reg.txt: 20260921_110000 は :770、20260919_020000 は :724、20260602_120000 は :251）。

## 4. ベーススキーマ

.github/workflows/migration-test.yml:1150-1630 の「ベーススキーマを作成」は、上の表のうち public.tcg_status_master（:506）、tcg_note_master（:552）、tcg_product_categories（:700）、analysis_results（:728）、extraction_jobs（:770）、source_messages（:777）、extraction_items（:785）、extraction_attempts（:812）、llm_usage_events（:863）、tcg_distribution_targets（:906）、tenant_discord_ticket_config（:489）の CREATE を持つ行がある。ただし b_create.txt の行番号は migration-test.yml 全体の行番号。ジョブ開始は :1097、ベース作成ステップは :1150。:1150 未満の行は別ジョブ（migration-test-run）側の定義であり、migration-full-dryrun のベースには入っていない（推測ではなく行番号の比較。ジョブ内の実在確認は実験で行う）。

## 5. ADR
ADR-1007: docs/adr/ADR-1007-migration-structure-only-run-once.md。除外理由は「静的解析で見込み。未実行」（scripts/migration-guard/dryrun-exclusions.tsv:27,30）。
