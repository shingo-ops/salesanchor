# recon: fix-unify-type-mismatch

作成: 2026-09-22

## 問題

`migrations/20260914_140000_unify_tcg_products_to_public.sql` のデプロイが失敗した。

### エラー内容

- `tenant_004.tcg_products.work_id` は `uuid` 型
- `public.products.work_id` は `integer` 型（`20260919_010000` で変換済み）
- Step2 の INSERT が `t.work_id`（UUID）を INTEGER 列へ代入しようとして型ミスマッチ

同様に:
- `public.products.tcg_uuid` が `20260916_120000` で DROP 済みの場合、Step4 の `WHERE tcg_uuid IS NOT NULL` が列不在エラーになる可能性あり

## 原因

`run_all_migrations.sh` は全 migration を毎デプロイ再実行する（冪等前提）。

実行順（`run_all_migrations.sh` 内の順序）:
1. `20260914_140000_unify_tcg_products_to_public.sql`（本ファイル）
2. `20260915_010000_drop_tcg_products_phase2c.sql`
3. `20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`
4. `20260916_120000_phase_c_drop_tcg_uuid.sql`
5. `20260916_130000_work_id_not_null.sql`
6. `20260919_010000_master_ssot_work_id_recast.sql`

初回デプロイでは順序通り実行されるが、前回デプロイで後続 migration が適用済みの状態で再実行すると、`public.products.work_id` が既に INTEGER になっており型ミスマッチが発生する。

## 影響ファイル（file:line）

- `migrations/20260914_140000_unify_tcg_products_to_public.sql:79–119` — Step2 UPSERT（work_id の型チェックなし）
- `migrations/20260914_140000_unify_tcg_products_to_public.sql:126–243` — Step3 FK張替え（tcg_uuid 存在前提）
- `migrations/20260914_140000_unify_tcg_products_to_public.sql:323–375` — Step4 件数照合（tcg_uuid 存在前提）

## ADR 検索結果

- ADR-1001: Phase 2a/2c — tcg_products → public.products 統合
- ADR-1002: work_id UUID→INTEGER 型統一（Phase B）
- `docs/specs/master-ssot-migration/design.md` に設計詳細あり

## 関連 migration

- `20260916_120000_phase_c_drop_tcg_uuid.sql`: `public.products.tcg_uuid` を DROP
- `20260919_010000_master_ssot_work_id_recast.sql`: `work_id` を UUID→INTEGER スワップ
