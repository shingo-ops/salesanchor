# Design: fix-migration-work-id-guard

recon: docs/handoff/fix-migration-work-id-guard/recon.md

## 方針

`20260602_010000` の tenant_006 INSERT ブロックに `pg_attribute` ガードを追加。
`public.products.work_id` が NOT NULL の場合は INSERT をスキップする。
tenant→public 移行は後続マイグレーション (20260914) が正式に担当するため、このINSERTは不要。

## 変更前後

| 基準 | 検証方法 |
|---|---|
| deploy が [80/284] を通過する | deploy workflow の成功 |
| 既存データに影響しない | INSERT は条件付きスキップのみ（DELETE/UPDATE なし）|

## 外部・過去事例の参照と我々への応用

PostgreSQL の `pg_attribute` を使って列の attnotnull フラグを確認するパターンは、既存マイグレーション `migrations/20260916_130000_work_id_not_null.sql` の実装例（ガード付きALTER TABLE）と同様のアプローチ。後続マイグレーションが正式移行を担う場合、前段マイグレーションの INSERT を条件付きスキップする手法はプロジェクト内の migration-guard パターン（ADR-1002）に準拠する。

## 維持の仕組み

守り手: `migrations/20260916_130000_work_id_not_null.sql`（NOT NULL制約の定義元）
ガードは `pg_attribute` の attnotnull フラグを検査するため、将来 work_id の NOT NULL が解除された場合は自動的に INSERT が再発火する。ただしその状況は ADR-090 の方針変更を意味するため、その時点で再評価する。

## 触るファイル

- migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql（ガード追加）

## 触らないファイル

- scripts/run_all_migrations.sh（変更不要・既に登録済み）
- backend/（コード変更なし）
- frontend/（コード変更なし）
