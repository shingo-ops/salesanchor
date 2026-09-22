# Recon: fix-phase2c-fk-type-guard

## 問題

`migrations/20260922_040000_fix_phase2c_fk_blocker.sql` の Step 3 DO ブロックで
`public.analysis_results.product_id`（INTEGER型）を `public.products(tcg_uuid)`（UUID型）に
外部キー参照しようとした結果、型不一致エラーが発生。

```
ERROR: foreign key constraint "fk_analysis_results_product_public" cannot be implemented
DETAIL: Key columns "product_id" and "tcg_uuid" are of incompatible types: integer and uuid.
```

デプロイログ: GitHub Actions run #35691903538（PR #3676 マージ後）

## 根拠

- `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql` が `analysis_results.product_id` を UUID → INTEGER に変換済み
- `20260922_040000_fix_phase2c_fk_blocker.sql` は型チェックなしで FK 追加を試みていた
- `20260914_140000` の Step3 では同ファイル内で型ガード追加済み（PR #3676）
- `20260922_040000` は別ファイルのため別途ガード追加が必要

## 影響ファイル

- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql`: DO ブロックに型チェックガード追加（line 24-58: DO ブロック全体を置換）
