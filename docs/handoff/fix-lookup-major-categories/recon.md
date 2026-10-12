# 商品マスタCSV取り込みが参照する tcg_major_categories の現状

対象ADR: ADR-156（商品分類ツリーと共用マスタ分離）

## 事象

`backend/app/services/tcg_product_import_svc.py` の `load_lookup_maps()` が、実体の無いテーブルを引いている。

`backend/app/services/tcg_product_import_svc.py:186-194`（修正前）

```python
for column, table in LOOKUP_TABLES.items():
    result = await db.execute(
        text(f"SELECT code, id FROM {TCG_SCHEMA}.{table} WHERE is_active = TRUE")
    )
```

- `TCG_SCHEMA = "public"`（`backend/app/services/tcg_product_import_svc.py:30` 付近でモジュール内定義）
- `LOOKUP_TABLES["division_code"] = "tcg_major_categories"`（同ファイル `68-72`）
- よって `SELECT code, id FROM public.tcg_major_categories WHERE is_active = TRUE` が実行される

## 根拠（網羅確認）

1. **`public.tcg_major_categories` を作る DDL は存在しない。**
   `migrations/` 全 .sql を `CREATE TABLE[^;]*tcg_major_categories` で走査した結果、該当は2件のみ。
   - `migrations/20260902_110000_tcg_classification_masters.sql:25` … `_schema TEXT := 'tenant_004'`（同ファイル14行）で tenant_004 限定
   - `migrations/20260906_120000_create_tcg_tables_t001.sql:96` … tenant_001 向け
   ビュー・リネームでの生成も `public.tcg_major_categories` で走査して0件。
2. **tenant_004 側は削除済み。**
   `migrations/20260921_130000_drop_tenant004_master_copies.sql:36` で `DROP TABLE IF EXISTS tenant_004.tcg_major_categories CASCADE;`
3. 直後に正しい上書き処理がある（`public.product_kinds` / `public.tcg_product_categories`）が、
   1回目のクエリで例外になるため到達しない。

## 影響

`load_lookup_maps()` の呼び出し元は `preview()` と `commit_import()`。
ルータは `backend/app/routers/tcg_product_import.py` の
`POST /api/v1/tcg/products/import/preview` と `POST /api/v1/tcg/products/import/commit`（IMPORT-01 商品マスタCSV取り込み）。
`relation "public.tcg_major_categories" does not exist` は SQLAlchemyError として
`backend/app/main.py` のDBエラーハンドラに捕捉され HTTP 500 になる。

本番DBでの実際のエラー発生は**未確認**（当該APIは super_admin 認証が必要で、この環境から到達できない）。
コードと migrations の事実からは、実行すれば必ず失敗する。

## なぜ既存テストで検出されないか

- `backend/tests/test_tcg_product_import.py:226` 付近: `load_lookup_maps` 自体を `AsyncMock` に差し替えており実クエリを通さない
- `backend/tests/test_tcg_product_import_atomicity_pg.py:44-51`: `TCG_SCHEMA` を `tenant_901` に差し替え、旧テナントDDL（`tcg_major_categories` を含む）をリプレイした合成スキーマに対して実行するため、public の実態を再現していない。
  同じ構造が `backend/tests/test_tcg_product_detail_pg.py`、`backend/tests/test_tcg_product_roundtrip_pg.py`、`backend/tests/test_tcg_work_comparison_pg.py` にもある
- `backend/tests/test_tcg_schema_qualification.py` は静的検査で、テーブルの実在は検査しない

## 関連（同ADRの先行対応）

- PR #3663 / #3681: LINE取り込みの同種障害（削除済みテーブル参照・チャネル欠落）を復旧済み
- `backend/app/services/tcg_product_roundtrip_svc.py:31-34` は `_ROUNDTRIP_LOOKUP_TABLES` で
  `division_code` を `product_kinds` に事前上書きしており、同じ罠を踏んでいない
