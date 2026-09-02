# recon: PARITY-02 A-7 products_logistics 廃止

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "products_logistics" docs/adr/
```

ヒットなし。対象 ADR: なし。

---

## 2. テーブル現状（VPS 実測）

```sql
SELECT table_schema, table_name FROM information_schema.tables
WHERE table_name = 'products_logistics';
-- → tenant_004 | products_logistics (1 row)

SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema='tenant_004' AND table_name='products_logistics';
-- → product_id (uuid) / created_at (timestamptz) の 2列のみ

SELECT count(*) FROM tenant_004.products_logistics;
-- → 267 rows（product_id のみ、ロジスティクス実データなし）
```

**結論**: 2列のみ・ロジスティクス列ゼロ・意味のあるデータなし。廃止確定。

---

## 3. FK 依存

```sql
-- products_logistics → tcg_products（FK元のみ）
-- 他テーブルから products_logistics を参照するFK: なし
```

`products_logistics.product_id → tenant_004.tcg_products.id` の参照元 FK のみ。
他テーブルが products_logistics を参照していないため DROP TABLE は安全。

---

## 4. Python 参照（全走査）

| ファイル | 参照内容 | 対応 |
|---|---|---|
| `backend/tcg_migration/scripts/ingest_to_prod.py:54` | `TABLE_ORDER` リスト | 行削除 |
| `backend/tcg_migration/scripts/ingest_to_prod.py:72-74` | `CONFLICT_KEY` エントリ | エントリ削除 |
| `backend/tcg_migration/scripts/write_mirror_once.py:64` | `DB_TABLE_DESCRIPTIONS` エントリ | エントリ削除 |
| `backend/tcg_migration/scripts/write_mirror_once.py:279` | SQL IN 句 | `products_logistics` 削除 |

アプリケーションコード（`backend/app/`）内の参照: **ゼロ**（grep 確認済み）。

---

## 5. 変更前後

### 変更前

- `tenant_004.products_logistics` テーブル: 存在（2列・267行）
- `ingest_to_prod.py`: `TABLE_ORDER` + `CONFLICT_KEY` に `products_logistics` あり
- `write_mirror_once.py`: `DB_TABLE_DESCRIPTIONS` + SQL IN 句に `products_logistics` あり

### 変更後

- `migrations/20260903_140000_drop_products_logistics_t004.sql` 追加
  - `DROP TABLE IF EXISTS tenant_004.products_logistics` （冪等）
- `ingest_to_prod.py`: `products_logistics` のエントリを削除（コメントで廃止記録）
- `write_mirror_once.py`: `products_logistics` のエントリと SQL IN 句から削除
- `scripts/run_all_migrations.sh`: 上記 SQL を追記

---

## 6. VPS 実測（2026-09-03）

```
1回目: NOTICE: migration 20260903_140000: dropped tenant_004.products_logistics / DO
2回目: DO / NOTICE: migration 20260903_140000: tenant_004.products_logistics already absent, skipping
```

冪等確認済み。

---

## 7. 触らないファイル

- `backend/app/` 配下（アプリコードに `products_logistics` 参照なし）
- `20260831_110000_create_tcg_analysis_tables_t004.sql`（CREATE側 migration は変更しない・履歴保全）
