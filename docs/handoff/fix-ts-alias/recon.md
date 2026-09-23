# Recon: Undefined Table Alias 'ts' in Supplier Quality Query

## Problem Statement
The 解析精度管理 (Accuracy Management Panel) returns database error:
```
データベースエラーが発生しました
GET /api/v1/tcg/supplier-quality-summaries - 500 Internal Server Error
```

## Root Cause Investigation

### Production Error Log
From VPS backend logs (2026-09-19):
```
Database error: GET /api/v1/tcg/supplier-quality-summaries - 
(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) 
<class 'asyncpg.exceptions.UndefinedTableError'>: 
missing FROM-clause entry for table "ts"
    COALESCE(ts.code, sc.id::text)  AS supplier_id,
    COALESCE(ts.name, '不明')        AS supplier_name,
JOIN tenant_004.supplier_channels sc ON sc.id = sm.supplier_channel_id
LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
GROUP BY sc.id, ps.supplier_code, ps.name
```

### Source File
`backend/app/services/tcg_supplier_quality_svc.py:16-63`

### Query Structure Analysis
Lines 29-50 contain the SQL that joins:
- `{TCG_SCHEMA}.source_messages sm` (main table)
- `{TCG_SCHEMA}.supplier_channels sc` (foreign key join)
- `public.suppliers ps` (left join)

**Bug**: Line 31-32 reference `ts.code` and `ts.name` but alias `ts` is never defined in FROM clause.

**Correct alias**: Line 43 shows `LEFT JOIN public.suppliers ps` - should use `ps` not `ts`.

### Column Mapping
- Query groups by: `ps.supplier_code, ps.name` (line 48)
- COALESCE should match: `COALESCE(ps.supplier_code, ...)` and `COALESCE(ps.name, ...)`

## Files Involved
- `backend/app/services/tcg_supplier_quality_svc.py` - Query definition
- `backend/app/routers/tcg_supplier_quality.py` - Router calling the service
- No migrations or structural changes needed

## Fix
Replace undefined alias `ts` with correct alias `ps`:
- Line 31: `COALESCE(ts.code, ...)` → `COALESCE(ps.supplier_code, ...)`
- Line 32: `COALESCE(ts.name, ...)` → `COALESCE(ps.name, ...)`

## Test Vector
When frontend calls GET `/api/v1/tcg/supplier-quality-summaries`, query should:
1. Join source_messages → supplier_channels → public.suppliers
2. Aggregate extraction_items and analysis_results
3. Return supplier summaries with counts (analysis_count, needs_review_count, etc.)
4. No SQL error should occur

---

**設計**: docs/handoff/fix-ts-alias/design.md
