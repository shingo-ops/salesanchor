# recon: fix-phase3-fk-guard

## 調査起点

デプロイ失敗 CI run 35645576032 にて `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql` が `tenant_004.units` を参照しようとしたが、SSOT移行（PR #3585 相当）によって tenant_004.units は public.units に移動済みであるためテーブルが存在しない状態でエラー。

## 失敗箇所

```
migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:63-67
  UPDATE %I.analysis_results ar
  SET unit_int_id = pu.id
  FROM %I.%I tu       -- tenant_004.units ← 存在しない
  JOIN public.%I pu ON pu.code = tu.code
  WHERE ar.unit_id = tu.id
```

同様に tenant_004.conditions も public.conditions に移動済みのため condition_id 変換も同じ問題。

## 関連ファイル

- `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql` — 修正対象
- `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql` — 後続で analysis_results を DROP（修正後の migration は後続に依存しない）
- `docs/adr/ADR-155-product-master-ssot-csv-app.md` — 対象ADR（SSOT移行設計）

## 既存パターン確認

`$phase3b$` ブロック（同ファイル L246-253）にて `to_regclass` + EXISTS チェックによるテナントテーブル不在ガードが実装済み。同パターンを `$phase3$` ブロックの unit_id / condition_id にも適用する。
