# recon — Phase 2c FK ブロッカー修正

**対象ADR**: ADR-1001

## 問題の特定

- `migrations/20260914_140000_tcg_products_phase2a.sql` — Phase 2a は `tenant_%` スキーマのみループ（`public` スキーマを対象外）
- `migrations/20260915_010000_drop_tcg_products_phase2c.sql:38-42` — Phase 2c はFKが残存している場合 `RAISE EXCEPTION` でブロック
- `scripts/run_all_migrations.sh:526` — Phase 2c DROP が早期実行エントリとして配置済み

## 残存FK（推定）

1. `public.analysis_results.analysis_results_product_id_fkey` → `tenant_004.tcg_products`
2. `tenant_004.analysis_results.analysis_results_product_id_fkey` → `tenant_004.tcg_products`

## 修正方針

- 新マイグレーション `20260922_010000_fix_phase2c_fk_blocker.sql` で両FK DROP
- Phase 2a が tenant スキーマに追加した `fk_analysis_results_product_public` と同等のFKを `public.analysis_results` に追加
- `run_all_migrations.sh` で Phase 2c の直前に実行
