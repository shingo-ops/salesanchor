# recon: fix-phase2b-type-guard

## 問題

デプロイが `migrations/20260909_000000_public_products_phase2b_columns.sql` (step 222/277) で失敗。

エラー: `column "work_id" is of type integer but expression is of type uuid`

## 原因

`public.products.work_id` は後続の Phase 3 migration によって UUID → INTEGER に型変換済みだが、
この Phase 2b bootstrap migration がマイグレーション順序上再実行される際、
`tenant_004.tcg_products.work_id` (UUID型) を `public.products.work_id` (INTEGER型) に INSERT しようとして型不一致が発生する。

## 調査ファイル

- `migrations/20260909_000000_public_products_phase2b_columns.sql:50-82` — INSERT ループ本体（今回修正対象）
- `migrations/20260909_000000_public_products_phase2b_columns.sql:13` — `work_id UUID` としてカラム追加

## 影響範囲

- 変更ファイル: `migrations/20260909_000000_public_products_phase2b_columns.sql` のみ（1ファイル）
- ロジック変更: ループ内に Phase 3 型変換済み判定ガードを追加（冪等性向上）
- 削除行: なし

## 既存 ADR 検索結果

`git grep -i "phase2b\|phase 2b\|work_id" docs/adr/` — 専用 ADR なし。
ADR-1002 (公開マスタ移行) が関連するが work_id 型変換ガードに関するルールは未定義。
