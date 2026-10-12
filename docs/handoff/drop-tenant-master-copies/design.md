# Design: ADR-156 Phase 5 — Drop tenant_004 master table copies

## ADR references

- ADR-155 (`docs/adr/ADR-155-product-master-ssot-csv-app.md`): SSOT migration strategy
- ADR-156 (`docs/adr/ADR-156-product-classification-tree-and-master-separation.md`): product classification tree and master separation

## Scope

10 tenant_004 tables dropped. All code reads from public schema (SSOT) before this change lands.

| Table | Dropped | SSOT location |
|-------|---------|---------------|
| tenant_004.conditions | YES | public.conditions |
| tenant_004.units | YES | public.units |
| tenant_004.condition_aliases | YES | public.condition_aliases |
| tenant_004.unit_aliases | YES | public.unit_aliases |
| tenant_004.product_search_keywords | YES | public.product_search_keywords |
| tenant_004.product_exclude_keywords | YES | public.product_exclude_keywords |
| tenant_004.tcg_product_categories | YES | public.tcg_product_categories |
| tenant_004.tcg_major_categories | YES | public.product_kinds (ADR-156 Phase 3A) |
| tenant_004.tcg_note_master | YES | public.tcg_note_master |
| tenant_004.tcg_status_master | YES | public.tcg_status_master |

## Code changes

### backend/app/services/tcg_work_comparison_svc.py

`_PUBLIC_MASTER` expanded from 2 to 8 tables. All MASTER_TABLES now route to `public.*`.

### backend/app/tasks/tcg_mirror.py

`_fetch_db_structure` OR clause changed from `table_schema = '{TCG_SCHEMA}'` to `table_schema = 'public'` for keyword/alias tables.

## Migration

`migrations/20260921_130000_drop_tenant004_master_copies.sql`

DROP order (children before parents within tenant_004):
1. `condition_aliases` (FK → conditions)
2. `unit_aliases` (FK → units)
3. `product_search_keywords`, `product_exclude_keywords` (FK → tcg_products, kept)
4. `conditions`, `units` (parents)
5. `tcg_product_categories`, `tcg_major_categories` (parents; CASCADE removes FK from tcg_products)
6. `tcg_note_master`, `tcg_status_master` (standalone)

All DROPs use `IF EXISTS CASCADE` → idempotent.

## Acceptance criteria

| # | Criterion | Verification method |
|---|-----------|-------------------|
| 1 | All 10 tables absent from tenant_004 after migration | `SELECT table_name FROM information_schema.tables WHERE table_schema='tenant_004' AND table_name IN (...)` → 0 rows |
| 2 | Public tables unaffected | `SELECT count(*) FROM public.conditions` → same as before |
| 3 | tcg_work_comparison_svc routes all MASTER_TABLES to public | Code review: `_PUBLIC_MASTER` set covers all 8 table names |
| 4 | tcg_mirror DB構造 tab shows public schema for keyword/alias tables | Run tcg_mirror task post-deploy, inspect mirror sheet |
| 5 | CI tests pass | All existing tests pass (no test DB uses production data) |

## Rollback

Tables were copies (data already in public). DROP TABLE IF EXISTS is idempotent — re-running is safe.
To recreate tenant_004 copies: re-run `migrations/20260906_120000_create_tcg_tables_t001.sql` for the schema, then copy data from public. Not expected to be needed.

## Non-targets (explicitly NOT dropped)

- `tenant_004.tcg_products` (operational reference table — separate decision needed)
- `tenant_004.tcg_series`, `tenant_004.tcg_manufacturers` (used by operational queries)
- `tenant_004.item_notes`, `tenant_004.unparsed_lines` (operational)
- Any other tenant schemas (tenant_003, tenant_006, etc.) — not in scope

## 外部・過去事例の参照と我々への応用

**過去事例（同リポジトリ）**: ADR-1002 Phase 4→5 pipeline table migration — `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`。`DROP TABLE IF EXISTS ... CASCADE` パターンを採用済みで、同一アプローチを本 migration に適用。

## 維持の仕組み

守り手: tcg_work_comparison_svc.py の `MASTER_TABLES` tuple と `_PUBLIC_MASTER` frozenset のコードレビュー（新テーブル追加時は両方更新必須）。

migration 登録漏れ防止: `scripts/run_all_migrations.sh` に必ず記載。CI の migration check が登録を検証。
