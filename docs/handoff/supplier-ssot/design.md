# Design: 仕入元マスタ SSOT Sprint 1

## KGI
LINE取り込み仕入元照合先を public.suppliers(INTEGER) に一元化する。

## KPI（PO が○×を判定できる粒度）
1. `public.suppliers.supplier_code` に `SP-NNNNN` 形式の行が存在する
2. `{schema}.supplier_channels.supplier_id` カラムが INTEGER 型（pg_catalog.int4）であること
3. `{schema}.supplier_channels` に `fk_supplier_channels_supplier_id` 制約が存在し、参照先が `public.suppliers(id)` であること
4. `public.line_supplier_source_names` テーブルが存在しないこと
5. CI migration-guard（チェック1/2/3）が全て green であること

## 変更内容

### Migration: 20260917_020000_supplier_ssot_migration.sql

**ステップ1: データコピー（冪等）**
- `tenant_*` スキーマの `tcg_suppliers` を走査
- `supplier_code = 'SP-' || LPAD(SUBSTRING(code FROM 3), 5, '0')` で public.suppliers に INSERT
- ON CONFLICT(supplier_code) DO UPDATE: line_name が NULL の場合のみ更新
- 前提: public.suppliers と public.suppliers.line_name が存在すること（migration 056 + 20260603_010000 実行済み）

**ステップ2: supplier_channels FK UUID→INTEGER 変換（冪等）**
- supplier_channels.supplier_id が INTEGER ならスキップ
- ADD COLUMN supplier_int_id INTEGER
- UPDATE via tcg_suppliers → public.suppliers JOIN でマッピング
- NULL チェック（マッピング漏れがあれば RAISE EXCEPTION）
- DROP CONSTRAINT（旧FK）
- DROP COLUMN supplier_id（UUID）
- RENAME supplier_int_id → supplier_id
- ALTER COLUMN SET NOT NULL
- ADD CONSTRAINT FK → public.suppliers(id) ON DELETE CASCADE
- CREATE INDEX

**ステップ3: DROP TABLE IF EXISTS public.line_supplier_source_names**

### テスト変更（TDD: Sprint 2 サービスコード更新の RED フェーズ）

| ファイル | 変更内容 |
|---------|---------|
| test_tcg_import_progress_pg.py | _PUBLIC_SUPPLIERS_DDL 追加, Sprint 1 migration 適用, supplier_channels に INTEGER id を使用 |
| test_tcg_line_import.py | mock判定: "tcg_suppliers" → "public.suppliers" |
| test_line_source_names.py | assert: "tcg_suppliers" → "public.suppliers" |
| test_tcg_result_order.py | public.suppliers INSERT + migration 適用, ANALYZE list から tcg_suppliers 削除 |
| test_tcg_sold_out_results.py | public.suppliers DDL + migration 適用, INTEGER supplier id 使用 |

## 弊害・リスク
- **Sprint 1 後サービスコード未更新のため、`test_tcg_line_import.py` の mock-based tests は RED になる**（Sprint 2 で GREEN にする）
- `tcg_suppliers.code` が 'SP' 以外で始まる場合、`SUBSTRING(code FROM 3)` は予期しない値を返す可能性がある（本番データは 'SP' 始まりであることを前提）
- 本番適用前に dry-run で NULL チェックが 0 件であることを確認すること

## 外部事例
- 同プロジェクトの ADR-1002 Phase B（`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`）が UUID→INTEGER FK 変換の先行実装として参照可能

## 戻し方
- ステップ1: public.suppliers から SP-NNNNN 行を削除（影響小）
- ステップ2: supplier_channels に UUID カラムを戻す必要あり（手動DDL + データ復元）
- ステップ3: public.line_supplier_source_names を再作成（migration 20260912_170000 を再実行）

## 測り方
```sql
-- KPI 2確認
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema LIKE 'tenant_%' AND table_name = 'supplier_channels' AND column_name = 'supplier_id';
-- KPI 3確認
SELECT conname, confrelid::regclass FROM pg_constraint
WHERE conrelid = 'tenant_004.supplier_channels'::regclass AND contype = 'f';
-- KPI 4確認
SELECT to_regclass('public.line_supplier_source_names');
```
