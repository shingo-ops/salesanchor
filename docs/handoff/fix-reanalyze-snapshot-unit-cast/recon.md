# recon: fix-reanalyze-snapshot-unit-cast

## 調査日時
2026-09-24

## 問題
`reanalyze_extraction_job()` を呼ぶと全ジョブで psycopg2.errors.DatatypeMismatch が発生。

## 直接観測
```
column "unit_id" is of type uuid but expression is of type integer
LINE 33: ar.unit_id,
```

## 型確認（information_schema.columns）
```
analysis_results.unit_id      = integer
analysis_results.condition_id = integer
analysis_run_snapshots.unit_id      = uuid
analysis_run_snapshots.condition_id = uuid
```

出典: `migrations/20260921_110000_pipeline_tables_public.sql:214`
> Note: unit_id/condition_id are UUID here (legacy snapshot format, differs from analysis_results integer)

## コード箇所
`backend/app/services/tcg_product_master_svc.py:614` — INSERT SELECT で ar.unit_id を直接参照（:617 も同様）

## 修正方針
スナップショットの unit_id/condition_id は比較用補助情報。
NULL::uuid にキャストして型不一致を回避する。
