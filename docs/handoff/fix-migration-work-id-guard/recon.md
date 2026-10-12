# Recon: fix-migration-work-id-guard

## 観測事実

- deploy run 35804254612 が `[80/284] 20260602_010000_repoint_downstream_fk_to_public_products.sql` で失敗
- エラー: `null value in column "work_id" of relation "products" violates not-null constraint`
- `public.products.work_id` は `migrations/20260916_130000_work_id_not_null.sql` (step 669) で NOT NULL化済み
- `20260602_010000` の INSERT 文に `work_id` 列が含まれていない
- `tenant_006.products` に新行 `QA ポケモンカードA` が追加され、WHERE NOT EXISTS で INSERT が発火
- 前回 deploy (35793902445, 2026-09-22) は成功（この行が存在しなかったため）
- tenant→public 移行は `migrations/20260914_140000_unify_tcg_products_to_public.sql` が正式に担当

## 影響ファイル

- `migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql:64-83` — INSERT ブロック
