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
   - Phase 2c（`migrations/20260915_010000_drop_tcg_products_phase2c.sql`）の直前に本マイグレーション追加
3. `docs/handoff/fix-phase2c-fk-blocker/recon.md`（新規）
4. `docs/handoff/fix-phase2c-fk-blocker/design.md`（新規）

## 影響範囲

- FK DROP のみ。データ変更なし
- `public.analysis_results.product_id` は引き続き `public.products.tcg_uuid` を参照

## 外部・過去事例の参照と我々への応用

- `migrations/20260914_140000_unify_tcg_products_to_public.sql`（Phase 2a）: tenant スキーマの FK 張替えパターンを踏襲
- Phase 2a が `tenant_%` ループで `public` を漏らした構造的な問題。同手法を `public` にも適用

## 維持の仕組み

- 本マイグレーションは冪等（`DROP CONSTRAINT IF EXISTS` + `IF NOT EXISTS` ガード）
- Phase 2c 直前実行により、デプロイ順序依存の問題を防ぐ

## 戻し方

FK DROP は冪等。ロールバックが必要な場合は旧FK（`analysis_results_product_id_fkey`）を手動で再追加。
