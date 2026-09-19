# Design: Fix Undefined Table Alias in Supplier Quality Query

**recon**: docs/handoff/fix-ts-alias/recon.md

## Overview
Simple bug fix: SQL query uses undefined table alias `ts` when the correct alias is `ps` (public.suppliers).

## KGI / KPI
| Criterion | Measurement |
|-----------|-------------|
| **KGI**: API returns supplier quality summaries without error | GET /api/v1/tcg/supplier-quality-summaries returns 200 with valid JSON array |
| **KPI**: No 500 error due to SQL syntax | Response status ≠ 500; response body has no "UndefinedTableError" or "missing FROM-clause" |

## Implementation Plan

### Step 1: Fix Query Aliases
**File**: `backend/app/services/tcg_supplier_quality_svc.py`
**Lines**: 31-32

Change from:
```sql
COALESCE(ts.code, sc.id::text)  AS supplier_id,
COALESCE(ts.name, '不明')        AS supplier_name,
```

To:
```sql
COALESCE(ps.supplier_code, sc.id::text)  AS supplier_id,
COALESCE(ps.name, '不明')        AS supplier_name,
```

**Rationale**:
- Query defines alias `ps` at line 43: `LEFT JOIN public.suppliers ps`
- No alias `ts` is defined anywhere in the query
- Correct columns from suppliers table: `supplier_code` (not `code`), `name`
- GROUP BY clause (line 48) already uses `ps.supplier_code, ps.name`

### Step 2: Verify No Other Aliases Missing
- Grep for other `ts.` references in the file: **None found**
- No cascading alias issues detected

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| Column name mismatch | Low | Already grouped by ps.supplier_code in same query |
| Regression in other endpoints | Low | Only one function affected; no shared query template |
| Data type mismatch | Low | Both return text (supplier_code::text fallback for NULL) |

## Testing Strategy

### Manual Test
1. Ensure backend running with fix
2. Call: `curl -s https://api.salesanchor.jp/api/v1/tcg/supplier-quality-summaries | jq '.[] | {supplier_id, supplier_name, analysis_count, needs_review_count}' | head -20`
3. Verify response: 200 OK, valid JSON array, no error messages

### Automated Test
- CI will run pytest on backend services
- No new test needed; existing endpoints should pass
- Migration tests do not apply (query-only, no schema change)

## 守り手（ロールバック）
If error occurs after fix:
```sql
-- Revert single commit
git revert -n <commit-hash>
git commit -m "revert: fix ts alias"
```
Change 2 lines back to original aliases. No migration needed.

## 外部・過去事例の参照と我々への応用

PostgreSQL公式ドキュメント（FROM句のテーブル別名）: JOINで定義した別名のみSELECT/WHERE/GROUP BYで使用可能。未定義別名は `missing FROM-clause entry for table` エラー。本件も同パターン。

### PostgreSQL Column Alias Guidelines
- Table aliases must be defined in FROM/JOIN clauses before use in SELECT/WHERE/GROUP BY
- Undefined alias references result in `ProgrammingError: missing FROM-clause entry for table`
- Fix: Match alias used in JOIN to alias used in column selection

### Our Application
This fix applies the standard PostgreSQL pattern: ensuring all column references use the correct, defined alias. No special treatment needed—just correct the alias name.

## 維持の仕組み

守り手: shingo-ops (PO)

### Code Review Checklist
When reviewing similar queries:
1. Verify each column prefix (ts, ps, sc, etc.) is defined in FROM/JOIN clause
2. Confirm column names match actual table schema (suppliers.supplier_code ≠ suppliers.code)
3. Check GROUP BY clause uses same aliases as SELECT

### Prevention
- Code review processes will catch undefined alias references at PR time
- PostgreSQL type checking at runtime prevents deployment of broken queries
- No additional test infrastructure needed (query validation happens at execution)

## Implementation Notes
- No migrations required
- No config changes required
- No frontend changes required
- Single backend service file change (2 lines)
