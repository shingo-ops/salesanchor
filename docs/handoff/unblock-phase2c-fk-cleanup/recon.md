# recon: unblock-phase2c-fk-cleanup

## 本番 DB の現在の状態（事実）

- `scripts/run_all_migrations.sh:661` に `20260915_010000_drop_tcg_products_phase2c.sql` が登録済み
- 本番デプロイがこのマイグレーションでブロックされている（POより報告）
- ブロック原因: `tenant_*.product_search_keywords` および `tenant_*.product_exclude_keywords` が `tenant_*.tcg_products` を参照する FK を保持している

## Phase 2c ブロッカーの根本原因

- Phase 2a (`20260914_140000_unify_tcg_products_to_public.sql`) は `public.products(tcg_uuid)` への UNIQUE 制約 `uq_products_tcg_uuid` を作成するはずだった
- この制約が作成されなかったため、FK の張り替え（tcg_products → public.products）が完了しなかった
- 結果として `product_search_keywords.product_tcg_id` / `product_exclude_keywords.product_tcg_id` が旧 `tcg_products` を参照したまま残存
- Phase 2c の `DROP TABLE tcg_products` が FK 制約違反でブロックされる

## 関連マイグレーションの実行順序の問題

- `scripts/run_all_migrations.sh:524` — `20260922_050000_fix_phase2c_fk_drop_only.sql`（analysis_results FK 修正）
- `scripts/run_all_migrations.sh:661` — `20260915_010000_drop_tcg_products_phase2c.sql`（問題のブロック箇所）
- 既存の `20260922_050000` は `analysis_results` の FK のみ対象であり、`product_search_keywords` / `product_exclude_keywords` の FK は対象外

## 調査ファイル・行番号

- `scripts/run_all_migrations.sh:524` — fix_phase2c_fk_drop_only の登録位置
- `scripts/run_all_migrations.sh:661` — drop_tcg_products_phase2c の登録位置（ブロック箇所）
- `migrations/20260915_010000_drop_tcg_products_phase2c.sql` — 問題の DROP 対象
