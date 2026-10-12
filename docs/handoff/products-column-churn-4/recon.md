# Recon: tenant_004 の UUID→INTEGER 変換が tcg_uuid 依存で失敗（第4便）

**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装・recon、本番 read-only 確認も実施)
**インシデント**: PR #3958/#3959/#3960 マージ後、2026-10-04 デプロイ run **37136832562** が
ステップ244で `tenant_004.tcg_products` の DROP に成功したが、ステップ245
`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`（schema tenant_004、
`product_search_keywords.product_id` の UUID→INTEGER 変換中）で
`ERROR: column p.tcg_uuid does not exist` により失敗。

これまでのレビュー（第2便・第3便）は「`tenant_004` を含む全テナントの `product_id` は
既に INTEGER に変換済み」と**未確認のまま前提**にしていた。これは誤りで、`tenant_004` の
4テーブルは UUID のまま残っていた。

---

## 0. 本番 read-only 確認（Sonnet 自身が実行。設計担当 Opus の確認とは別に独立して再確認）

コマンド形式（designer 承認済みの唯一の形）で実行:
```
ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46 "docker exec astro-webapp-postgres-1 sh -c 'psql -U \"\$POSTGRES_USER\" -d jarvis_db -c \"SELECT \\\$\\\$tenant_004.analysis_results\\\$\\\$ AS tbl, count(*) FROM tenant_004.analysis_results UNION ALL SELECT \\\$\\\$tenant_004.analysis_run_snapshots\\\$\\\$, count(*) FROM tenant_004.analysis_run_snapshots UNION ALL SELECT \\\$\\\$tenant_004.product_exclude_keywords\\\$\\\$, count(*) FROM tenant_004.product_exclude_keywords UNION ALL SELECT \\\$\\\$tenant_004.product_search_keywords\\\$\\\$, count(*) FROM tenant_004.product_search_keywords\"'"
```
生出力:
```
                 tbl                 | count
-------------------------------------+-------
 tenant_004.analysis_results         |     0
 tenant_004.analysis_run_snapshots   |     0
 tenant_004.product_exclude_keywords |     0
 tenant_004.product_search_keywords  |     0
(4 rows)
```
**確認結果**: 4テーブルすべて0行。designer 提示の「analysis_results・analysis_run_snapshots
は0行のはず」という期待と一致し、他の2テーブル（product_exclude_keywords・
product_search_keywords、designer が別途確認済みとして提示していた0行）とも一致した。

型情報（public.*・tenant_001.* は INTEGER、tenant_004.analysis_results/
analysis_run_snapshots/product_exclude_keywords/product_search_keywords は UUID、
tenant_004.products_logistics は INTEGER）は**設計担当 Opus が確認した事実**として
扱う（本書では Sonnet 自身は型情報を再クエリしていないため、行数以外は Opus 確認分を
そのまま引用）。

---

## 1. 4テーブルのライフサイクル表（登録順、file:line付き）

### tenant_004.analysis_results

| 登録行 | file:line | 操作 | tcg_uuid依存 | product_id=INTEGER前提 |
|---|---|---|---|---|
| 527 | `migrations/20260922_050000_fix_phase2c_fk_drop_only.sql:15-16` | 旧FK（tcg_products参照）を `DROP CONSTRAINT IF EXISTS` のみ | No | No |
| 530, 536（重複登録） | `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:292-315` | **CREATE TABLE**（`product_id UUID REFERENCES tenant_004.tcg_products(id)`, NULLABLE） | No | No |
| 665 | `migrations/20260922_040000_fix_phase2c_fk_blocker.sql:18-20` | 旧FK（tcg_products参照）を `DROP CONSTRAINT IF EXISTS` のみ（tenant_004側はDROPのみ、再ADDは `public.analysis_results` 側だけ） | No | No |
| **671** | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:298-384`（Table4） | **UPDATE/ALTER**: `product_id` UUID→INTEGER 変換（`public.products.tcg_uuid` 経由の JOIN が無ガード→本PRで修正） | **Yes（修正対象）** | No（変換対象そのもの） |
| 707 | `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:23-126`（Column1: unit_id）・`:130-222`（Column2: condition_id） | **ALTER/UPDATE**: `unit_id`/`condition_id` UUID→INTEGER（`product_id` とは無関係の別変換） | No | No |
| **747** | `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql:18` | **DROP TABLE IF EXISTS** | No | No |

### tenant_004.analysis_run_snapshots

| 登録行 | file:line | 操作 | tcg_uuid依存 | product_id=INTEGER前提 |
|---|---|---|---|---|
| 578 | `migrations/20260903_220000_create_tcg_analysis_history_t004.sql:54-77` | **CREATE TABLE**（`product_id UUID`, NULLABLE, FK無し） | No | No |
| **671** | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:386-417`（Table5） | **UPDATE/ALTER**: `product_id` UUID→INTEGER（`tcg_uuid` JOIN、無ガード→本PRで修正） | **Yes（修正対象）** | No |
| **747** | `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql:17` | **DROP TABLE IF EXISTS** | No | No |

### tenant_004.product_search_keywords

| 登録行 | file:line | 操作 | tcg_uuid依存 | product_id=INTEGER前提 |
|---|---|---|---|---|
| 530, 536（重複登録） | `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:171-179` | **CREATE TABLE**（`product_id UUID NOT NULL REFERENCES tenant_004.tcg_products(id)`） | No | No |
| 651 | `migrations/20260913_200000_tcg_cardset_exclusion.sql:16-28`（第3便で既にガード済み） | **読み取りのみ**（`product_id` の型を判定して `_pid_col` を選ぶ。UUIDのままなら `tcg_uuid` 分岐、第3便でガード） | Yes（既にガード済み・PR #3960） | No |
| 652 | `migrations/20260913_210000_tcg_cardset_bundle_registration.sql:18-30`（同上） | 同上 | Yes（既にガード済み・PR #3960） | No |
| **671** | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:41-126`（Table1） | **UPDATE/ALTER**: `product_id` UUID→INTEGER（`tcg_uuid` JOIN、無ガード→本PRで修正） | **Yes（修正対象）** | No |
| 698 | `migrations/20260919_020000_master_ssot_public_tables.sql:301-310`（Step8） | `public.product_search_keywords` を**新規に空で CREATE**（tenant_004からのデータコピーは無い。コメントに「708 rows」とあるが古い記録であり、本DDL自体はデータに依存しない） | No | コメント上は想定しているが実行文は非依存 |
| **759** | `migrations/20260921_130000_drop_tenant004_master_copies.sql:27` | **DROP TABLE IF EXISTS ... CASCADE** | No | No |

### tenant_004.product_exclude_keywords

| 登録行 | file:line | 操作 | tcg_uuid依存 | product_id=INTEGER前提 |
|---|---|---|---|---|
| 530, 536（重複登録） | `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:156-163` | **CREATE TABLE**（`product_id UUID NOT NULL REFERENCES tenant_004.tcg_products(id)`） | No | No |
| 651 | `migrations/20260913_200000_tcg_cardset_exclusion.sql`（第3便で既にガード済み） | **読み取り+INSERT**（マッチする商品があればキーワード1行追加。現在0行なので実質不作動） | Yes（既にガード済み・PR #3960） | No |
| 652 | `migrations/20260913_210000_tcg_cardset_bundle_registration.sql`（同上） | 同上（複数キーワード） | Yes（既にガード済み・PR #3960） | No |
| **671** | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:128-200`（Table2） | **UPDATE/ALTER**: `product_id` UUID→INTEGER（`tcg_uuid` JOIN、無ガード→本PRで修正） | **Yes（修正対象）** | No |
| 698 | `migrations/20260919_020000_master_ssot_public_tables.sql:317-326`（Step9） | `public.product_exclude_keywords` を新規に空で CREATE（同上、非依存） | No | コメント上のみ |
| **759** | `migrations/20260921_130000_drop_tenant004_master_copies.sql:28` | **DROP TABLE IF EXISTS ... CASCADE** | No | No |

### （参考）tenant_004.products_logistics — UUID→INTEGER 変換は既に完了済み（本番確認済み、INTEGER）

| 登録行 | file:line | 操作 |
|---|---|---|
| 530, 536 | `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:188-193` | CREATE TABLE（`product_id UUID`、PK） |
| 671 | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:202-296`（Table3） | `_atttypid = _int_oid` ガードで即スキップ（既にINTEGERのため、tcg_uuid分岐には入らない） |
| （DROP無し） | — | このテーブルは Phase 2c の DROP 対象リストに含まれていない（`migrations/20260921_050000`・`migrations/20260921_130000` のどちらにも無い）ため、永続的に残る。これが「他の3テーブルだけが UUID のまま残り、products_logistics だけ INTEGER になっている」理由: products_logistics は DROP→再CREATE のサイクルに入らず、過去の成功デプロイでの変換結果がそのまま保持されている。他の4テーブルは `migrations/20260831_110000`・`migrations/20260903_220000` が毎デプロイ `CREATE TABLE IF NOT EXISTS` で再作成を試み、かつ Phase 2c の DROP（747/759）に過去一度も到達していないため、再作成された素の UUID 状態で止まっている。 |

---

## 2. なぜ `tenant_004` の4テーブルだけ UUID のまま残っているか

`scripts/run_all_migrations.sh` には `set -e`（`:19`）があり、どのステップで失敗しても
その場でスクリプト全体が停止する。直近のデプロイ失敗は段階的に後ろへ進んでいる
（第1便: 列数上限 → 第2便: tcg_uuid再ADD → 第3便: 651/652の未ガード参照 → 今回:
671の phase_b で tenant_004 の4テーブル変換）。これらの失敗点は全て
`migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`（747）・
`migrations/20260921_130000_drop_tenant004_master_copies.sql`（759）より**手前**にある
ため、この2つの DROP migration は一度も実行完了に到達していない。一方 CREATE TABLE
IF NOT EXISTS（530/536/578）は毎デプロイ再実行されるが、テーブルが既に存在する限り
no-op（冪等）であり、現在の UUID のまま維持されている。

## 3. 既存ADR検索

ADR-1002（マスタ SSOT 型統一、Phase B）が該当。新規 ADR は起票しない。
