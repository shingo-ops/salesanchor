# design: fix-migration-blockers

## 参照ADR
- ADR-155: 商品データ存在前提の排除（冪等マイグレーション設計）

## recon参照
- docs/handoff/fix-migration-blockers/recon.md

## あるべき姿
マイグレーションは冪等。テーブルが不在の場合はスキップ（RETURN）するべきであり、RAISE EXCEPTION でデプロイを止めるべきではない。

## 変更前後

| ファイル | 変更前 | 変更後 |
|---------|--------|--------|
| 20260910_200000_tcg_condition_note_delivery_t004.sql | `RAISE EXCEPTION 'condition note: incomplete master structure'` | `RAISE NOTICE '... skipping (SSOT migration moved to public)', table_count; RETURN;` |
| 20260913_150000_tcg_empty_box_condition.sql | `RAISE EXCEPTION 'empty box: incomplete TCG structure'` | `RAISE NOTICE '... skipping (SSOT migration moved to public)', table_count; RETURN;` |
| 20260913_200000_tcg_cardset_exclusion.sql | `RAISE EXCEPTION 'tenant_004 incomplete TCG structure'` | `RAISE NOTICE '... skipping (SSOT migration moved to public)', table_count; RETURN;` |
| 20260913_210000_tcg_cardset_bundle_registration.sql | `RAISE EXCEPTION 'cardset bundle: incomplete TCG structure'` | `RAISE NOTICE '... skipping (SSOT migration moved to public)', table_count; RETURN;` |

## 影響範囲
- 実行順序: 変更なし
- 既存データ: 変更なし（INSERT/UPDATE文は変更していない）
- 冪等性: 維持（NOTICE+RETURNはロールバック不要）

## 検証方法
- デプロイがエラーなく完走すること
- NOTICE メッセージがログに出力されること

## 外部・過去事例の参照と我々への応用

該当なし（内部マイグレーション修正）。既存の同一ファイル内の冪等ガードパターン（`IF table_count = 0 THEN RETURN;` および `IF to_regclass(...) IS NULL THEN RAISE NOTICE ... RETURN;`）をそのまま適用した。

## 維持の仕組み

守り手: CIのBackend Tests（マイグレーション実行確認）
