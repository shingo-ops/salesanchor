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
252番以降の後続マイグレーションが同じVIEWをTABLEとして操作。
デプロイ設定: `.github/workflows/deploy.yml:153`（run_all_migrations.sh SSoT方針）
condition_aliases 参照: `backend/app/routers/conditions.py:493`

### 修正対象
本PRで新規追加: `docs/handoff/fix-view-to-table-rename/recon.md:1`
本PRで新規追加: `docs/handoff/fix-view-to-table-rename/design.md:1`

### アプリ状態
- コードデプロイは成功（docker compose完了）
- バックエンド `/api/health` → 200
- エラーログ直近30分 → なし
