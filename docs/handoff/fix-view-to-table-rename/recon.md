# Recon: VIEW → TABLE 修正

## 調査日: 2026-09-22

### 問題
Deploy workflow 35719639345 がマイグレーション [252/280] で失敗。
migrations/20260919_020000_master_ssot_public_tables.sql の
`CREATE INDEX IF NOT EXISTS uq_units_code ON public.units (code)` が
ERROR: cannot create index on relation "units" / DETAIL: This operation is not supported for views.

### 本番DB実測
- `public.units` = VIEW → `SELECT * FROM line_units` (8行)
- `public.unit_aliases` = VIEW → `SELECT * FROM line_unit_aliases` (39行)
- `public.conditions` = VIEW → `SELECT * FROM line_conditions` (11行)
- `public.condition_aliases` = VIEW → `SELECT * FROM line_condition_aliases` (31行)
- VIEWはリポジトリのどのマイグレーションにも定義なし（手動SSH作成）
- `grep -rn "line_units" backend/` → 出力なし（コードは`line_*`を参照していない）
- FK: `analysis_results.unit_id` → `line_units`, `analysis_results.condition_id` → `line_conditions`

### 影響範囲
252番以降の6ファイルが同じVIEWをTABLEとして操作:
- migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql
- migrations/20260920_030000_units_add_tenant_id.sql
- migrations/20260920_040000_conditions_ssot_phase1.sql
- migrations/20260921_100000_add_analysis_master_fk.sql
- migrations/20260921_110000_pipeline_tables_public.sql
- migrations/20260922_060000_product_unit_condition_infra.sql

### アプリ状態
- コードデプロイは成功（docker compose完了）
- バックエンド `/api/health` → 200
- エラーログ直近30分 → なし
