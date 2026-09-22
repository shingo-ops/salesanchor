# design: fix-view-fk-guards

## KGI
デプロイ時に `20260920_010000` 〜 `20260921_110000` の範囲のマイグレーションが VIEW 状態の本番 DB でもエラーなく完走する。

| 基準 | 検証方法 |
|---|---|
| `scripts/run_all_migrations.sh` が EXIT 0 で完了する | CI `backend-test` / `migration-test` のグリーン確認 |
| 本番デプロイ後にエラーログが出ない | `.github/workflows/deploy.yml` の migration ステップが SUCCESS |
| 既存データが破損していない | Phase 3 の `_bad_count` チェックが 0 のまま |

## KPI
- CI グリーン（backend-test・migration-test）: PR マージ前に確認
- 本番デプロイ EXIT 0: `.github/workflows/deploy.yml` ログで確認

## 変更方針

### ガードパターン
```sql
IF EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'units' AND c.relkind = 'r'
) THEN
    -- ALTER TABLE / CREATE INDEX / FK
ELSE
    RAISE NOTICE 'public.units は BASE TABLE でない — スキップ';
END IF;
```
`pg_class.relkind = 'r'` は「base table」のみ一致する。VIEW は `'v'`、Materialized View は `'m'`。

### 変更ファイル（5件）

1. **`migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql`**
   - Step 7 (unit_id FK): VIEW guard 追加
   - Step 8 (condition_id FK): VIEW guard 追加
   - INDEX 作成（`analysis_results` 自身）: VIEW の影響なし、変更不要

2. **`migrations/20260920_030000_units_add_tenant_id.sql`**
   - ファイル全体を DO $$ ... $$ ブロックに包み VIEW guard 追加

3. **`migrations/20260920_040000_conditions_ssot_phase1.sql`**
   - Step 1 ($step1$): VIEW guard 追加（ALTER TABLE）
   - Step 1 インデックス: 別 DO ブロック ($step1_idx$) で VIEW guard 追加
   - Step 2/3 (tenant テーブルの FK 張り替え): 変更不要（VIEW への FK ではない）

4. **`migrations/20260921_100000_add_analysis_master_fk.sql`**
   - conditions FK/INDEX: VIEW guard ($conditions_fk$) 追加
   - units FK/INDEX: VIEW guard ($units_fk$) 追加

5. **`migrations/20260921_110000_pipeline_tables_public.sql`**
   - `analysis_results` CREATE TABLE を DO $analysis_results_ddl$ に変換
   - units/conditions が VIEW の場合: unit_id/condition_id を FK なしの INTEGER で作成
   - テーブルが既に存在する場合は早期 RETURN（冪等性維持）

### 変更しないもの
- `migrations/20260922_060000_product_unit_condition_infra.sql`: COMMENT ON TABLE のみ、VIEW でも動作する
- Phase 3B ($phase3b$): `tcg_product_categories` は VIEW に変換されていない
- テナントスキーマの FK 張り替え（Step 2/3）: VIEW への参照ではないため安全

## 影響範囲

- **呼び出し元**: `scripts/run_all_migrations.sh` のみ
- **アプリコード変更**: なし
- **データ変更**: なし（DDL のみ）
- **ロールバック**: 変更前のコミット SHA に戻して再デプロイ（DDL guard を外すだけ）

## 外部・過去事例の参照と我々への応用

PostgreSQL 公式 `pg_class.relkind` カタログ:  
https://www.postgresql.org/docs/current/catalog-pg-class.html  
値: `'r'` = ordinary table, `'v'` = view, `'m'` = materialized view  

同プロジェクト先行事例: `migrations/20260919_020000_master_ssot_public_tables.sql:72-86` に同一パターンの VIEW guard が既に実装済み。今回はそのパターンを他の 5 マイグレーションに横展開する。

## 維持の仕組み

- CI `migration-test` が全マイグレーションを本番相当 DB で逐次実行する。VIEW 状態でも通過することを保証。
- `migrations/20260919_020000_master_ssot_public_tables.sql` の既存 VIEW guard パターンが規約として機能（同パターンを踏襲する）。
- `migrations/20260922_080000_rename_line_analysis_tables.sql` で `public.units/conditions` が BASE TABLE に昇格した後は、これらの VIEW guard は `ELSE` 分岐に入らず実質無効化される（正常動作）。

## 守り手
- CI migration-test: 本番相当の DB で全マイグレーションを順次実行
- `_bad_count` チェック（Phase 3 既存）: データ整合性保証
