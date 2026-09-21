# design: fix-phase3-fk-guard

## 参照

- recon: `docs/handoff/fix-phase3-fk-guard/recon.md`
- ADR: ADR-155（shared master SSOT）

## 問題

`tenant_004.units` / `tenant_004.conditions` は SSOT移行で `public.units` / `public.conditions` に移動済み。
Phase 3 migration がテナントテーブルを JOIN しようとして `relation does not exist` で失敗。

## 修正方針

`unit_id` / `condition_id` 変換ブロックの ELSIF 分岐に `to_regclass` 存在ガードを追加。
テナントテーブルが存在しない場合は NOTICE + スキップ（analysis_results 自体は後続 migration で DROP されるため安全）。

| 基準 | 検証方法 |
|------|---------|
| migration が ERROR なく完了する | CI Backend Tests が green |
| 既存データが変更されない | ELSIF ガードは RAISE NOTICE のみ（DML なし） |
| 他テナントへの影響なし | ループ内の ELSIF は _schema ごとに独立評価 |

## 変更内容

### unit_id ガード（L51-52 追加）

```sql
ELSIF to_regclass(format('%I.%I', _schema, _tbl_u)) IS NULL THEN
    RAISE NOTICE '  %.% not found (SSOT-moved to public), skipping unit_id rewire', _schema, _tbl_u;
```

### condition_id ガード（L137-138 追加）

```sql
ELSIF to_regclass(format('%I.%I', _schema, _tbl_c)) IS NULL THEN
    RAISE NOTICE '  %.% not found (SSOT-moved to public), skipping condition_id rewire', _schema, _tbl_c;
```

## 外部事例

N/A（内部マイグレーション修正・既存パターンの適用）

## 守り手

- `scripts/run_all_migrations.sh` の実行順序は変更なし
- `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql` が後続で analysis_results を DROP するため、unit_id/condition_id が UUID のままでもデプロイは完了する
- `to_regclass` は存在しないテーブルで NULL を返す（例外なし）
