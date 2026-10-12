# Recon: ADR-156 Phase 5 — Drop tenant_004 master table copies

## Evidence: app code reads from public schema

All non-test backend code confirmed to reference `public.*` (not `tenant_004.*`) for all 10 tables being dropped.

### tcg_analyzer_svc.py — public schema confirmed

- `backend/app/services/tcg_analyzer_svc.py:90` — `FROM public.unit_aliases`
- `backend/app/services/tcg_analyzer_svc.py:111` — `FROM public.unit_aliases`
- `backend/app/services/tcg_analyzer_svc.py:128` — `FROM public.condition_aliases`
- `backend/app/services/tcg_analyzer_svc.py:190` — `FROM public.product_search_keywords`
- `backend/app/services/tcg_analyzer_svc.py:208` — `FROM public.product_exclude_keywords`
- `backend/app/services/tcg_analyzer_svc.py:668` — `FROM public.conditions`

### super_admin_status_master.py — public schema confirmed

- `backend/app/routers/super_admin_status_master.py:143` — `FROM public.tcg_status_master`
- `backend/app/routers/super_admin_status_master.py:165` — `INSERT INTO public.tcg_status_master`

### note_master.py — public schema confirmed

- `backend/app/routers/note_master.py:143` — `FROM public.tcg_note_master`
- `backend/app/routers/note_master.py:166` — `INSERT INTO public.tcg_note_master`

### tcg_work_comparison_svc.py — rewired in this PR

- `backend/app/services/tcg_work_comparison_svc.py:130` (before) — `_PUBLIC_MASTER = frozenset({"tcg_normalization_rules", "tcg_product_categories"})`
- After: `_PUBLIC_MASTER` now includes all 8 tables

### tcg_mirror.py — rewired in this PR

- `backend/app/tasks/tcg_mirror.py:228` (before) — `table_schema = '{TCG_SCHEMA}'` for keyword/alias tables
- After: `table_schema = 'public'`

## Zero app code references to tenant_004 master tables

```
grep -rn "tenant_004\.\(conditions\b\|units\b\|condition_aliases\|unit_aliases\|product_search_keywords\|product_exclude_keywords\|tcg_note_master\|tcg_status_master\|tcg_major_categories\|tcg_product_categories\)" backend/app/ --include="*.py"
# → (no output)
```

## Test references (CI disposable DB only — not production)

Test files that reference tenant_004 master tables use `provision()` to create the schema fresh in a disposable CI DB. They test migration idempotency behavior, not production data. They are unaffected by dropping tables in the production DB.

- `backend/tests/test_tcg_work_matching_integration.py:566` — inserts into freshly-created tenant_004.tcg_note_master (tests migration collision)
- `backend/tests/test_tcg_work_matching_integration.py:1118,1176,1192,1369,1377,1382` — reads/inserts into freshly-created tenant_004.product_* tables (tests migration behavior)
- `backend/tests/test_tcg_condition_review.py:84-85,171,175,179,183` — reads from freshly-created tenant_004.conditions (tests migration idempotency)

## ADR references

- ADR-155: `docs/adr/ADR-155-product-master-ssot-csv-app.md`
- ADR-156: `docs/adr/ADR-156-product-classification-tree-and-master-separation.md`

## Already-dropped tables (not in this migration)

`tenant_004.analysis_results`, `extraction_items`, `extraction_jobs`, `source_messages`, etc. were dropped by `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`.

## FK dependency order for DROP

Original FK graph within tenant_004 (relevant to this migration):
- `condition_aliases.condition_id` → `conditions.id` (ON DELETE CASCADE)
- `unit_aliases.unit_id` → `units.id` (ON DELETE CASCADE)
- `product_search_keywords.product_id` → `tcg_products.id` (tcg_products NOT dropped)
- `product_exclude_keywords.product_id` → `tcg_products.id` (tcg_products NOT dropped)
- `tcg_products.division_id` → `tcg_major_categories.id` (tcg_products NOT dropped)
- `tcg_products.product_category_id` → `tcg_product_categories.id` (tcg_products NOT dropped)
- `analysis_results.unit_id` → `units.id` (analysis_results already dropped)
- `analysis_results.condition_id` → `conditions.id` (analysis_results already dropped)

Drop order: aliases first, then keyword tables, then parent masters. CASCADE handles FK cleanup.
