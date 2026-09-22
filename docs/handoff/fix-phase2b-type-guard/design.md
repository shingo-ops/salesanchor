# design: fix-phase2b-type-guard

## KGI

デプロイが step 222/277 で停止しない。`run_all_migrations.sh` が最後まで完走する。

| 基準 | 検証方法 |
|------|---------|
| migration が型エラーなく通過する | ローカル or ステージングで `run_all_migrations.sh` を実行し `ERROR` が出ないことを確認 |
| Phase 3 完了済み環境でスキップログが出る | `RAISE NOTICE 'Phase2b bootstrap: public.products.work_id already INTEGER ...'` がログに出力される |
| Phase 3 未完了環境では従来通り INSERT が実行される | `work_id` が UUID のままの環境でデータコピーが動作する |

## 修正内容

`migrations/20260909_000000_public_products_phase2b_columns.sql:50-64` (新規追加)

ループ内の INSERT の直前に `pg_attribute` を参照して `public.products.work_id` の型が `integer` であれば `CONTINUE` でスキップするガードを追加。

## 外部事例

PostgreSQL `pg_attribute.atttypid` による型チェック: 公式カタログ `pg_catalog.pg_attribute` の標準利用。
`::regtype::oid` によるキャストは型名から OID を解決する慣用パターン。

## 守り手

- 冪等性: ガードは pg_attribute を読むだけで副作用なし
- Phase 3 未完了環境: `work_id` が UUID のままであればガードは発動しない（従来動作を維持）
- 戻し方: ガードブロック（14行）を削除するだけで元に戻る

## 触るファイル / 削除するファイル

| 操作 | ファイル | 行 |
|------|---------|-----|
| 修正 | `migrations/20260909_000000_public_products_phase2b_columns.sql` | 50-64 (追加) |
| 追加 | `docs/handoff/fix-phase2b-type-guard/recon.md` | 新規 |
| 追加 | `docs/handoff/fix-phase2b-type-guard/design.md` | 新規 |
