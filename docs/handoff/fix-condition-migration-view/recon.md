# recon: fix-condition-migration-view

## 調査日
2026-09-25

## 問題
PR #3768 マージ後デプロイ時に migration が失敗:
`ERROR: cannot alter view "conditions"`

`migrations/20260925_010000_conditions_add_match_type.sql` が
`ALTER TABLE public.conditions` を実行しようとしたが、
`public.conditions` は VIEW（実テーブルではない）。

## 失敗箇所（file:line）

`migrations/20260925_010000_conditions_add_match_type.sql:19`
```sql
ALTER TABLE public.conditions ADD COLUMN match_type TEXT NOT NULL DEFAULT 'KEYWORD';
```

## 根本原因

- `migrations/20260922_080000_rename_line_analysis_tables.sql` で
  `public.conditions` → `public.line_conditions` にテーブルリネーム後、
  `CREATE VIEW public.conditions AS TABLE public.line_conditions` でVIEWを作成済み。
- PR #3768 の migration は VIEW作成前の命名規則で書かれており、
  VIEW に対して `ALTER TABLE` を実行 → PostgreSQL エラー。

## 参照 ADR

- `docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md`
  — migration 互換性修正パターン（既存テーブル/VIEW の状態を事前チェック）

## 影響範囲

- `migrations/20260925_010000_conditions_add_match_type.sql` のみ（1ファイル修正）
- 呼び出し元: `scripts/run_all_migrations.sh`（デプロイ時自動実行）
- 実テーブル `public.line_conditions` への `ALTER TABLE ADD COLUMN` は安全（additive-only）
- VIEW の `CREATE OR REPLACE` で新カラムが反映される
