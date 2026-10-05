# Recon: Phase 2c（tenant_004.tcg_products DROP）が定常状態で毎回FKブロックされる（第5便）

**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装・recon)
**インシデント**: PR #3961(`b2fed15ec`) デプロイ成功（run 37138350951）後、次のデプロイ
PR #3962(`5bd251366`、migration変更なし) run **37139483973** がステップ244
`migrations/20260915_010000_drop_tcg_products_phase2c.sql` で
`Phase 2c blocked: 2 FK(s) still reference tenant_004.tcg_products` により失敗。

---

## 1. 事実（設計担当 Opus が本番 read-only で確認）

- `tenant_004.tcg_products` を参照しているFKは厳密に2件:
  `product_exclude_keywords_product_id_fkey`（`tenant_004.product_exclude_keywords`）
  ・`product_search_keywords_product_id_fkey`（`tenant_004.product_search_keywords`）。
- `tenant_004.tcg_products` は0行。
- `tenant_004.product_exclude_keywords`・`tenant_004.product_search_keywords` も0行
  （第4便で確認済み、今回も変化なし）。

## 2. 原因

これは1回限りの不具合ではなく**定常状態そのものの構造的な問題**:
- 前回の成功デプロイ（run 37138350951）が
  `migrations/20260915_010000_drop_tcg_products_phase2c.sql`（登録: `scripts/run_all_migrations.sh:668`）
  まで到達し、`tenant_004.tcg_products` と関連コピーを DROP した。
- 次のデプロイは `scripts/run_all_migrations.sh` を**先頭から全件再実行**する。
  `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql`（登録:530/536、
  `CREATE TABLE IF NOT EXISTS`）が `tenant_004.tcg_products`・
  `product_search_keywords`・`product_exclude_keywords`・`analysis_results` を
  **UUID・0行で新規に再作成**する（既に DROP されているため IF NOT EXISTS が実際に
  CREATE する）。再作成時、`product_search_keywords`/`product_exclude_keywords` は
  CREATE文に書かれた `REFERENCES tenant_004.tcg_products(id)` によって
  tcg_products への FK を自動的に持つ。
- `migrations/20260914_140000_unify_tcg_products_to_public.sql` Step3
  （登録:661、本来はこのFKを `tcg_products` から `public.products(tcg_uuid)` へ
  張り替える役目）は、`public.products.tcg_uuid` が既に存在しないため
  （`migrations/20260916_120000_phase_c_drop_tcg_uuid.sql` で永久 DROP 済み）、
  型チェックで即座に `RETURN` し、何もしない（第2便で確認済みの既存挙動）。
  結果、FKは `tcg_products` を指したまま残る。
- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql`（登録:665）は
  `analysis_results` の同種の古いFK（`analysis_results_product_id_fkey`）だけを
  無条件で DROP するため、`analysis_results` 分はこの時点で解消される
  （designer確認の「2件」に `analysis_results` が含まれない理由）。しかし
  `product_search_keywords`/`product_exclude_keywords` には同等の無条件クリーンアップが
  存在しない。
- `migrations/20260915_010000_drop_tcg_products_phase2c.sql`（登録:668）自身の安全チェック
  （残存FK件数の確認）が、この2件のFKを検出して `RAISE EXCEPTION` する。

## 3. 既存ADR検索

ADR-1001（tcg_products → public.products 統合）が関連。新規 ADR は起票しない。
