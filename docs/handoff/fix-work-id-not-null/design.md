# design: fix-work-id-not-null

**recon**: docs/handoff/fix-work-id-not-null/recon.md

## KGI
デプロイ時に `migrations/20260916_130000_work_id_not_null.sql` が成功し、全商品の work_id が NOT NULL になること。

## 変更方針
既存の未適用マイグレーションを修正し、バックフィル（Phase 1）→ NOT NULL 適用（Phase 2）の2段階にする。

| 基準 | 検証方法 |
|------|---------|
| products.work_id に NULL が0件 | デプロイ後に `SELECT COUNT(*) FILTER (WHERE work_id IS NULL) FROM public.products` が 0 |
| デプロイが migration step を通過 | deploy.yml ワークフローが成功完了 |
| 既存データに影響なし | UPDATE は WHERE work_id IS NULL のみ対象 |

## 外部・過去事例の参照と我々への応用
NOT NULL 制約追加前のデータ補完は標準的なマイグレーションパターン。DO $$ ブロックで列型チェック・NULL検査を行い冪等性を確保。

## 守り手（ロールバック）
`ALTER TABLE public.products ALTER COLUMN work_id DROP NOT NULL` + `UPDATE SET work_id = NULL WHERE id IN (127269,127270,127271,127272,127273,440585,440586)` で即時復元可能。

## 維持の仕組み
NOT NULL 制約適用後は新規 NULL 挿入が DB レベルで阻止される。
守り手: `ALTER TABLE public.products ALTER COLUMN work_id DROP NOT NULL` + UPDATE SET work_id = NULL WHERE id IN (127269,127270,127271,127272,127273,440585,440586) で即時復元可能
