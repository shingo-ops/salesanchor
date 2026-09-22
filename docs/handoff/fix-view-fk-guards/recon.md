# recon: fix-view-fk-guards

## 調査日
2026-09-22

## 問題の根本原因

`scripts/run_all_migrations.sh` の末尾に `rename_line_analysis_tables` マイグレーションがある（origin/main:scripts/run_all_migrations.sh:768）。  
このマイグレーションは `public.units` / `public.unit_aliases` / `public.conditions` / `public.condition_aliases` を BASE TABLE から backward-compat VIEW に変換する。

**本番環境では `rename_line_analysis_tables` が既にデプロイ済み**。  
その後に追加されたマイグレーション群が `public.units` / `public.conditions` を VIEW の状態で実行され、以下のエラーで失敗する:
- `ALTER TABLE` on a VIEW → `ERROR: cannot alter view "units"`
- `CREATE INDEX` on a VIEW → `ERROR: cannot create index on view "units"`
- `ADD CONSTRAINT ... REFERENCES public.units(id)` → `ERROR: referenced relation "units" is not a table`

## 影響マイグレーション（run_all_migrations.sh 行番号順、origin/main 基準）

| run_all_migrations.sh 行 | ファイル | 問題のある操作 |
|---|---|---|
| 696 | `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql` | FK REFERENCES public.units/conditions(id) — VIEW target |
| 702 | `migrations/20260920_040000_conditions_ssot_phase1.sql` | ALTER TABLE public.conditions ADD COLUMN, CREATE INDEX on VIEW |
| 705 | `migrations/20260920_030000_units_add_tenant_id.sql` | ALTER TABLE public.units ADD COLUMN, CREATE INDEX on VIEW |
| 730 | `migrations/20260921_100000_add_analysis_master_fk.sql` | ALTER TABLE public.conditions/units ADD COLUMN, CREATE INDEX on VIEW |
| 733 | `migrations/20260921_110000_pipeline_tables_public.sql` | CREATE TABLE ... REFERENCES public.units/conditions(id) |

## キー参照（file:line、本ブランチ内ファイル）

- `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:112` — FK unit_id REFERENCES public.units(id)（VIEW guard 追加済み）
- `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:206` — FK condition_id REFERENCES public.conditions(id)（VIEW guard 追加済み）
- `migrations/20260920_030000_units_add_tenant_id.sql:11` — ALTER TABLE public.units ADD COLUMN（DO ブロックに包み VIEW guard 追加済み）
- `migrations/20260920_040000_conditions_ssot_phase1.sql:57` — ALTER TABLE public.conditions ADD COLUMN（VIEW guard 追加済み）
- `migrations/20260921_100000_add_analysis_master_fk.sql:66` — ALTER TABLE public.conditions ADD COLUMN（VIEW guard 追加済み）
- `migrations/20260921_100000_add_analysis_master_fk.sql:70` — ALTER TABLE public.units ADD COLUMN（VIEW guard 追加済み）
- `migrations/20260921_110000_pipeline_tables_public.sql:208` — REFERENCES public.units(id)（DO ブロックで VIEW guard 追加済み）

## 安全なマイグレーション（対応不要）

- `rename_line_analysis_tables`（origin/main のみ・本ブランチ外）: VIEW 作成元。対応不要。
- `product_unit_condition_infra`（origin/main のみ・本ブランチ外）: COMMENT ON TABLE のみ。VIEW でも動作。対応不要。
- Phase 3B (`migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql` 内 $phase3b$): `tcg_product_categories` は VIEW に変換されていない。対応不要。

## ADR 検索結果

- `docs/adr/ADR-155-product-master-ssot-csv-app.md` — shared master SSOT（関連）
- `docs/adr/ADR-156-product-classification-tree-and-master-separation.md` — 商品分類ツリー（関連）
