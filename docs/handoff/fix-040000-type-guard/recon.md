# recon: fix-040000-type-guard

## 調査日時
2026-09-22

## 障害再現
```
ERROR: foreign key constraint "fk_analysis_results_product_public" cannot be implemented
DETAIL: Key columns "product_id" and "tcg_uuid" are of incompatible types: integer and uuid.
```
242/279 `20260922_040000_fix_phase2c_fk_blocker.sql` がデプロイ時に失敗。

## 該当ファイル
- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql:52-58` — Step 3のFKを無条件で `product_id (INTEGER)` → `public.products(tcg_uuid) (UUID)` に張ろうとしていた

## 型の状態（実行順序から判定）

| 時点 | `public.analysis_results.product_id` の型 |
|------|--------------------------------------------|
| Phase 2a（20260914_140000）実行後 | INTEGER（変換なし。Phase 2aはtenant_%のみループ） |
| **040000実行時点（Phase 2aの直後）** | **INTEGER** |
| Phase B（20260915_120000）実行後 | tenant_*スキーマのみ INTEGER化。public.*は対象外 |

## 根拠
- `run_all_migrations.sh:657-662`: 実行順 = 20260914_140000 → 20260922_040000 → 20260915_010000 → 20260915_120000
- `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:L18-26`: Phase Bはtenant_%のみループ、`public.*`は非対象

## 既存の型ガードパターン（ADR参照）
- `migrations/20260914_140000_unify_tcg_products_to_public.sql:L333-401`: Phase 2aのStep 3で全4テーブルに `_pid_typid <> _uuid_oid` ガードを実装済み
- `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:L267-272`: Phase Bも同様のガード実装

## PR履歴
- a16370fa4: 040000ファイル作成（rename from 030000）
- 7772f3342: PR #3675 マージ（run_all_migrations.shに040000を登録）
- be414803b: PR #3676 マージ（Phase 2a Step 3の型ガード追加）— 同根問題の修正済み
