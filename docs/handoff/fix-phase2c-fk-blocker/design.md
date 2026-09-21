# design — Phase 2c FK ブロッカー修正

**対象ADR**: ADR-1001
**recon**: docs/handoff/fix-phase2c-fk-blocker/recon.md

## KGI

Phase 2c（`tenant_004.tcg_products` DROP）が成功すること（RAISE EXCEPTION が発生しないこと）

## KPI

| 基準 | 検証方法 |
|------|---------|
| `public.analysis_results_product_id_fkey` が存在しない | `\d public.analysis_results` で制約一覧確認 |
| `tenant_004.analysis_results_product_id_fkey` が存在しない | `\d tenant_004.analysis_results` で制約一覧確認 |
| Phase 2c マイグレーションが EXCEPTION なく完了 | デプロイログに `Phase 2c: dropped` 出力確認 |

## 変更内容

1. `migrations/20260922_010000_fix_phase2c_fk_blocker.sql`（新規）
   - `public.analysis_results` と `tenant_004.analysis_results` の旧FK DROP
   - `public.analysis_results` に正しいFK（`public.products(tcg_uuid)` 参照）を追加
2. `scripts/run_all_migrations.sh`
   - Phase 2c（`20260915_010000_drop_tcg_products_phase2c.sql`）の直前に本マイグレーション追加

## 影響範囲

- FK DROP のみ。データ変更なし
- `public.analysis_results.product_id` は引き続き `public.products.tcg_uuid` を参照

## 外部事例

- ADR-1001 Phase 2a 実装（`20260914_140000_tcg_products_phase2a.sql`）と同手法

## 戻し方

本マイグレーションは冪等。FK ADD は `IF NOT EXISTS` ガード付き。
ロールバックが必要な場合は旧FK（`analysis_results_product_id_fkey`）を手動で再追加。
