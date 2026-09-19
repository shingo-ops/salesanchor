# design: backfill-work-id-nulls

**recon**: docs/handoff/backfill-work-id-nulls/recon.md

## KGI
デプロイ時に `20260916_130000_work_id_not_null.sql` が成功し、全商品の work_id が NOT NULL になること。

## 変更方針
NOT NULL マイグレーション直前に、7件の NULL work_id を既存の UUID→INTEGER 対応表で埋める。

| 基準 | 検証方法 |
|------|---------|
| products.work_id に NULL が0件 | `SELECT COUNT(*) FILTER (WHERE work_id IS NULL) FROM public.products` が 0 |
| デプロイが migration step を通過 | deploy.yml ワークフローが成功完了 |
| 既存データに影響なし | UPDATE は WHERE work_id IS NULL のみ対象 |

## 外部・過去事例の参照と我々への応用
PostgreSQL NOT NULL 制約追加前のデータ補完は標準的なマイグレーションパターン。DO $$ ブロックで列型・存在チェックを行い冪等性を確保。

## 守り手（ロールバック）
UPDATE は work_id IS NULL → 値設定のみ。ロールバックは `UPDATE SET work_id = NULL WHERE id IN (127269,...,440586)` で即時可能。

## 維持の仕組み
NOT NULL 制約適用後は新規 NULL 挿入が DB レベルで阻止される。

## 触らないもの
- backend/app/ のコード一切
- frontend/ 一切
- 既存マイグレーションファイル
