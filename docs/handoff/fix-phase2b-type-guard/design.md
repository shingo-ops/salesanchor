# design: fix-phase2b-type-guard

## KGI

デプロイが step 222/277 で停止しない。マイグレーションスクリプトが最後まで完走する。

| 基準 | 検証方法 |
|------|---------|
| migration が型エラーなく通過する | ステージング環境でマイグレーション実行し `ERROR` が出ないことを確認 |
| Phase 3 完了済み環境でスキップログが出る | `RAISE NOTICE 'Phase2b bootstrap: public.products.work_id already INTEGER ...'` がログに出力される |
| Phase 3 未完了環境では従来通り INSERT が実行される | `work_id` が UUID のままの環境でデータコピーが動作する |

## 修正内容

`migrations/20260909_000000_public_products_phase2b_columns.sql`（50-64行、新規追加）

ループ内の INSERT の直前に `pg_attribute` を参照して `public.products.work_id` の型が `integer` であれば `CONTINUE` でスキップするガードを追加する。

```sql
IF EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'products'
      AND a.attname = 'work_id'
      AND a.atttypid = 'integer'::regtype::oid
      AND a.attnum > 0
      AND NOT a.attisdropped
) THEN
    RAISE NOTICE 'Phase2b bootstrap: public.products.work_id already INTEGER (Phase 3 complete), skipping schema %', schema_record.schema_name;
    CONTINUE;
END IF;
```

## 外部・過去事例の参照と我々への応用

PostgreSQL `pg_catalog.pg_attribute` による型チェックは公式カタログの標準利用パターン。
`atttypid = 'integer'::regtype::oid` は型名から OID を解決する慣用パターンで、PostgreSQL の公式ドキュメント
（https://www.postgresql.org/docs/current/catalog-pg-attribute.html）に記載された手法。

過去事例として ADR-1002 Phase 2b/3 の migration 設計では migration 順序と型変換の冪等性について言及しているが、
ガード句のパターンは明示されていなかった。本修正で「Phase N 完了済みチェック」パターンを確立する。

## 維持の仕組み

- ガードは `pg_attribute` を読むだけで副作用なし（冪等）
- Phase 3 未完了環境では `work_id` が UUID のままなので条件不一致→ガード非発動（従来動作を維持）
- 戻し方: ガードブロック（14行）を削除するだけで元に戻る

## 触るファイル / 削除するファイル

| 操作 | ファイル | 内容 |
|------|---------|------|
| 修正 | `migrations/20260909_000000_public_products_phase2b_columns.sql` | ガード追加（50-64行） |
| 追加 | `docs/handoff/fix-phase2b-type-guard/recon.md` | 新規 |
| 追加 | `docs/handoff/fix-phase2b-type-guard/design.md` | 新規（本ファイル） |
