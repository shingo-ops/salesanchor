# recon: backfill-work-id-nulls

## 調査日: 2026-09-19

## 現状
- `public.products` 全1,627件中7件の `work_id` (INTEGER) が NULL
- 対象: QAテスト商品5件 + LORCANA本番商品2件
- 全7件に `work_id_old_uuid` が存在し、`tenant_004.tcg_series` のUUIDと一致
- UUID→INTEGER の対応は既存商品（同UUID・work_id設定済み）から一意に確定

## 影響
- migration `migrations/20260916_130000_work_id_not_null.sql` が NOT NULL 制約追加で失敗
- デプロイが migration step で停止

## ADR調査
- ADR-1002: product ID type unification (UUID→INTEGER) — 本件の親設計
- ADR-1001: tcg_products→public.products unification
- ADR-090: products-central-unification

## 対象ファイル
- `migrations/20260916_125000_backfill_work_id_nulls.sql` — 新規作成（バックフィル）
- `scripts/run_all_migrations.sh` — 1行追加（バックフィル migration を NOT NULL 前に実行）

## 設計参照
設計: docs/handoff/backfill-work-id-nulls/design.md
