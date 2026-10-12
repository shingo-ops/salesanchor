# design: unblock-phase2c-fk-cleanup

## 参照 ADR

- ADR-1001: TCG 商品マスタ統合（Phase 2a/2c）
- ADR-1002: Phase B FK 付替え UUID→INTEGER

## 変更前後

| 観点 | 変更前 | 変更後 |
|------|-------|-------|
| tenant_*.product_search_keywords の FK | tcg_products 参照（残存） | 削除済み |
| tenant_*.product_exclude_keywords の FK | tcg_products 参照（残存） | 削除済み |
| public.products(tcg_uuid) UNIQUE 制約 | 未作成の場合あり | 作成済み（冪等） |
| Phase 2c デプロイ | FK 制約違反でブロック | 通過可能 |

## 影響範囲

- 呼び出し元全走査: `scripts/run_all_migrations.sh` の 2 箇所に新エントリを追加
- 変更対象テーブル: tenant_*.product_search_keywords, tenant_*.product_exclude_keywords（FK 削除のみ）
- データ変更なし（DDL のみ）

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| 20260915_010000_drop_tcg_products_phase2c が成功する | デプロイログで ERROR なし |
| 後続の全マイグレーションが実行される | run_all_migrations.sh の完走ログ |
| 本番 tcg_products テーブルが存在しない | \dt tenant_*.tcg_products で 0 件 |
| 新規 FK（Phase B: integer参照）が正常動作する | 20260915_120000_phase_b_fk_rewire_uuid_to_int のエラーなし |

## 戻し方

- 本マイグレーションは FK を削除するのみ（tcg_products 自体は Phase 2c が削除）
- Phase 2c が完走する前であれば、FK を手動で再作成することで戻せる
- Phase 2c 完走後は tcg_products が存在しないため FK の戻しは不要（かつ不可能）

## 測り方

1. ステージング環境で run_all_migrations.sh を実行し全マイグレーションが通過することを確認
2. 本番デプロイ後に `SELECT * FROM pg_constraint WHERE conname LIKE '%tcg_products%'` で FK 残存がないことを確認

## 外部・過去事例の参照と我々への応用

該当なし。本変更は PostgreSQL 標準の ALTER TABLE ... DROP CONSTRAINT 操作のみを使用しており、特定ライブラリやフレームワーク固有の機能は使用していない。FK 削除による依存テーブルの DROP 解放はデータベース運用の標準的な操作パターン。

## 維持の仕組み

- 冪等実行ガード: DO $$ BEGIN ... EXCEPTION ... END $$ ブロックにより FK が既に削除済みでもエラーにならない
- run_all_migrations.sh の 2 箇所に登録することで Phase 2c 前に必ず実行される
