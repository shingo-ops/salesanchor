# Recon: fix-units-view-index

## 調査日時
2026-09-22

## 障害概要

デプロイが migration 252/280 `migrations/20260919_020000_master_ssot_public_tables.sql` で失敗。

```
NOTICE: relation "units" already exists, skipping
ERROR: cannot create index on relation "units"
DETAIL: This operation is not supported for views.
```

## 根本原因

### VIEW 化の経緯

`migrations/20260922_080000_rename_line_analysis_tables.sql:32` が以下を実行済み（本番環境にて）:

```sql
CREATE VIEW public.units AS TABLE public.line_units;
CREATE VIEW public.unit_aliases AS TABLE public.line_unit_aliases;
CREATE VIEW public.conditions AS TABLE public.line_conditions;
CREATE VIEW public.condition_aliases AS TABLE public.line_condition_aliases;
```

このマイグレーションは `scripts/run_all_migrations.sh` に**未登録**（`git grep -n "20260922" scripts/run_all_migrations.sh` で出力なし）であったが、本番環境で別経路（SSH手動等）で実行済み。

### migration 順序の競合

| タイムスタンプ | ファイル | 影響 |
|---|---|---|
| `20260919_020000` | master_ssot_public_tables.sql | `public.units` を BASE TABLE として作成 + INDEX 作成 |
| `20260922_080000` | rename_line_analysis_tables.sql | `public.units` を `line_units` にリネームし `public.units` VIEW を作成 |

本番では `20260922_080000` が先に実行された状態で `20260919_020000` が再実行される形となり、`CREATE TABLE IF NOT EXISTS` は VIEW の存在によりスキップされるが、その後の `CREATE INDEX IF NOT EXISTS` が VIEW に対して実行されエラーになる。

### 影響テーブル（VIEW対象・全4テーブル）

- `public.units` — `20260919_020000` 行65-66: `uq_units_code`, `idx_units_is_active`
- `public.unit_aliases` — `20260919_020000` 行81-82: `idx_unit_aliases_unit_id`, `uq_unit_aliases_unit_lang`（＋FK `REFERENCES public.units(id)` も問題）
- `public.conditions` — `20260919_020000` 行102-104: `uq_conditions_code`, `idx_conditions_is_active`, `idx_conditions_priority`
- `public.condition_aliases` — `20260919_020000` 行119-120: `idx_condition_aliases_condition_id`, `uq_condition_aliases_cond_lang`（＋FK `REFERENCES public.conditions(id)` も問題）

### 影響しないテーブル（VIEW化されない）

- `public.tcg_note_master` — Step 5: VIEW化なし、INDEX作成は安全
- `public.tcg_status_master` — Step 6: VIEW化なし
- `public.tcg_product_categories` — Step 7: VIEW化なし
- `public.product_search_keywords` — Step 8: VIEW化なし
- `public.product_exclude_keywords` — Step 9: VIEW化なし

## 既存ADR検索結果

`git grep -i "view\|relkind\|migration.*guard" docs/adr/` — VIEW-TABLE共存に関する専用ADRなし（ADR-155はmigration guard全般）

## 変更ファイル

- `migrations/20260919_020000_master_ssot_public_tables.sql` — VIEW/TABLEガード追加
