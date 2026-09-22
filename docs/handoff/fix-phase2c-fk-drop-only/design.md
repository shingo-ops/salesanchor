# design: fix-phase2c-fk-drop-only

## 変更内容

| 基準 | 検証方法 |
|---|---|
| 旧FK DROP 成功 | マイグレーション実行ログに ERROR なし |
| Phase 2c 通過 | `migrations/20260915_010000_drop_tcg_products_phase2c.sql` が正常完了 |
| 後続マイグレーション成功 | buyback tables 等が ERROR なし |

## 外部・過去事例の参照と我々への応用

前回の fix (PR #3655) が `ADD CONSTRAINT ... REFERENCES public.products(tcg_uuid)` を実行したが、`tcg_uuid` カラムは `scripts/run_all_migrations.sh` の後段で追加される。PostgreSQL は FK 追加時に参照先カラムの実在を即時チェックするため、カラム追加より前に FK を張ることはできない。解決策として ADD FK を削除し DROP のみに限定する（FK 再追加は Phase 2b 完了後に別途対応）。

## 維持の仕組み

- 守り手: `scripts/run_all_migrations.sh` の実行順序
- `DROP CONSTRAINT IF EXISTS` により二重実行しても無害
- CI の migration-guard が順序異常を自動検知
