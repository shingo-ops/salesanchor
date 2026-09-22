# recon: fix-view-fk-guards

## 調査日
2026-09-22

## 問題の根本原因

`scripts/run_all_migrations.sh:768` に `20260922_080000_rename_line_analysis_tables.sql` がある。  
このマイグレーションは `public.units` / `public.unit_aliases` / `public.conditions` / `public.condition_aliases` を BASE TABLE から VIEW に変換する（backward-compat VIEW）。

**本番環境では `20260922_080000` が既にデプロイ済み**。  
その後に追加されたマイグレーション群が `public.units` / `public.conditions` を VIEW の状態で実行され、以下のエラーで失敗する:
- `ALTER TABLE` on a VIEW → `ERROR: cannot alter view "units"`
- `CREATE INDEX` on a VIEW → `ERROR: cannot create index on view "units"`
- `ADD CONSTRAINT ... REFERENCES public.units(id)` → `ERROR: referenced relation "units" is not a table`

## 影響マイグレーション（run_all_migrations.sh 行番号順）

| run_all_migrations.sh 行 | ファイル | 問題のある操作 |
|---|---|---|
| 701 | `20260920_010000_phase3_fk_rewire_unit_condition.sql` | `REFERENCES public.units(id)` / `REFERENCES public.conditions(id)` (FK on VIEW target) |
| 707 | `20260920_040000_conditions_ssot_phase1.sql` | `ALTER TABLE public.conditions ADD COLUMN` / `CREATE INDEX` on VIEW |
| 710 | `20260920_030000_units_add_tenant_id.sql` | `ALTER TABLE public.units ADD COLUMN` / `CREATE INDEX` on VIEW |
| 735 | `20260921_100000_add_analysis_master_fk.sql` | `ALTER TABLE public.conditions/units ADD COLUMN` / `CREATE INDEX` on VIEW |
| 738 | `20260921_110000_pipeline_tables_public.sql` | `CREATE TABLE ... REFERENCES public.units(id) ... REFERENCES public.conditions(id)` |

## 安全なマイグレーション（対応不要）

- `20260922_060000_product_unit_condition_infra.sql` — `information_schema` で存在確認後 `COMMENT ON TABLE` のみ。VIEW でも COMMENT は可能。対応不要。
- Phase 3B (`20260920_010000` 内 $phase3b$) — `REFERENCES public.tcg_product_categories(id)` は VIEW に変換されていない。対応不要。

## 調査コマンド

```
git grep -n "CREATE.*VIEW.*units\|CREATE.*VIEW.*conditions\|CREATE.*VIEW.*unit_aliases\|CREATE.*VIEW.*condition_aliases" origin/main -- "migrations/"
→ origin/main:migrations/20260922_080000_rename_line_analysis_tables.sql:32: CREATE VIEW public.units AS TABLE public.line_units;
→ (他3件)

for f in $(git show origin/main:scripts/run_all_migrations.sh | grep -E 'migrations/.*\.sql' | tail -80 | awk '{print $NF}'); do
  echo "=== $f ==="; git show origin/main:$f 2>/dev/null | grep -in "public\.units\|public\.conditions|REFERENCES.*units|REFERENCES.*conditions" || echo "(no matches)"
done
```

## ADR 検索結果

- `docs/adr/FEATURE-INDEX.md` / `docs/adr/` で ADR-155（shared master SSOT）・ADR-156（商品分類ツリー）が関連。
- ADR-155: `docs/adr/ADR-155-shared-master-ssot.md` （参照のみ、変更なし）
- ADR-156: `docs/adr/ADR-156-product-classification-tree.md` （参照のみ、変更なし）
