# ADR-1002 Phase B: 設計書

関連: `docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md`（PR #3517）
Recon: `docs/handoff/adr-1002-phase-b/recon.md`

## 目的

4テナントテーブルの `product_id` を UUID → INTEGER に変換し、FK 先を `public.products.id` に統一する。バックエンドコードの `tcg_uuid` 参照をすべて `id` 参照に書き換える。

## 変更前後

| 項目 | Before | After |
|-----|--------|-------|
| keyword/exclude/logistics/analysis の product_id | UUID | INTEGER |
| FK 参照先 | public.products(tcg_uuid) | public.products(id) |
| サービスの JOIN | `p.tcg_uuid = sk.product_id` | `p.id = sk.product_id` |
| 商品ID の SELECT | `tcg_uuid::text AS id` | `id::text` |
| 商品ID の WHERE | `WHERE tcg_uuid = CAST(:id AS uuid)` | `WHERE id = :id` |
| 新規商品登録の RETURNING | `RETURNING tcg_uuid::text AS id` | `RETURNING id::text` |
| product_code 採番 | Python `_next_pm_code()` | PostgreSQL SEQUENCE |

## 対象と対象外

### 対象
- Migration: 4テーブルの product_id 型変換 + FK 付替え（全 tenant_* スキーマ）
- Migration: product_code SEQUENCE 作成
- サービス層: 14ファイル・43箇所の tcg_uuid → id 書換え
- ルーター層: 1ファイル・2箇所
- テスト: 11ファイル・70箇所
- _next_pm_code() → SEQUENCE 化

### 対象外（Phase C/D で実施）
- `public.products.tcg_uuid` カラム削除
- `conftest.py:768` の tcg_uuid カラム定義削除
- `backend/scripts/`, `backend/tcg_migration/` の残存参照

## B-1: Migration SQL 仕様

ファイル名: `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`

### 処理手順（全 tenant_* スキーマをループ）

```
FOR EACH tenant_* schema that has product_search_keywords:
  1. ADD COLUMN product_int_id INTEGER
  2. UPDATE product_int_id = (SELECT p.id FROM public.products p WHERE p.tcg_uuid = product_id)
  3. 検証: product_id NOT NULL なのに product_int_id が NULL の行が 0 件
  4. DROP CONSTRAINT fk_*_product_public（tcg_uuid 向き FK）
  5. DROP COLUMN product_id（UUID）
  6. RENAME product_int_id → product_id
  7. ADD CONSTRAINT fk_*_product_id FOREIGN KEY (product_id) REFERENCES public.products(id)
  8. NOT NULL 制約を追加（元が NOT NULL だったテーブルのみ）
```

対象4テーブル:
- product_search_keywords（product_id NOT NULL）
- product_exclude_keywords（product_id NOT NULL）
- products_logistics（product_id = PK、NOT NULL）
- analysis_results（product_id NULLABLE）

### 冪等性
- ADD COLUMN IF NOT EXISTS
- 既に INTEGER なら変換スキップ（`pg_attribute` で型チェック）
- FK 存在チェック後に DROP/ADD

### B-3: product_code SEQUENCE

```sql
-- 現在の最大値から SEQUENCE 開始
DO $seq$
DECLARE max_num INTEGER;
BEGIN
  SELECT COALESCE(MAX(CAST(SUBSTRING(product_code FROM 3) AS INTEGER)), 0)
    INTO max_num
    FROM public.products
    WHERE product_code ~ '^PM[0-9]{4}$';

  EXECUTE format('CREATE SEQUENCE IF NOT EXISTS public.product_code_seq START WITH %s', max_num + 1);

  -- DEFAULT 句を設定
  ALTER TABLE public.products
    ALTER COLUMN product_code
    SET DEFAULT 'PM' || lpad(nextval('public.product_code_seq')::text, 4, '0');
END;
$seq$;
```

## B-2: コード変換ルール

### ルール 1: JOIN 条件
```
p.tcg_uuid = sk.product_id  →  p.id = sk.product_id
tp.tcg_uuid = ar.product_id →  tp.id = ar.product_id
cr_product.tcg_uuid::text   →  cr_product.id::text
```

### ルール 2: SELECT
```
SELECT tcg_uuid AS id        →  SELECT id
SELECT tcg_uuid::text AS id  →  SELECT id::text
p.tcg_uuid::text AS product_uuid → p.id::text AS product_uuid
p.tcg_uuid AS product_id    →  p.id AS product_id
```

### ルール 3: WHERE
```
WHERE tcg_uuid = CAST(:id AS uuid)  →  WHERE id = :id
WHERE tcg_uuid = CAST(:pid AS uuid) →  WHERE id = :pid
```

### ルール 4: INSERT (tcg_product_master_svc.py)
```
# Before:
INSERT INTO public.products (..., tcg_uuid) VALUES (..., gen_random_uuid())
RETURNING tcg_uuid::text AS id, id AS int_id

# After:
INSERT INTO public.products (...) VALUES (...)
RETURNING id::text, id
```
注: tcg_uuid カラムへの INSERT を除去。gen_random_uuid() 不要。int_id も不要（id が INTEGER そのまま）。

### ルール 5: dict アクセス
```
product["tcg_uuid"]         →  product["id"]
snapshot["product"]["tcg_uuid"] → snapshot["product"]["id"]
if "tcg_uuid" in product:   →  削除（id は常に存在）
  product["id"] = str(product.pop("tcg_uuid"))  →  削除
```

### ルール 6: ORDER BY
```
p.tcg_uuid ASC NULLS LAST   →  p.id ASC NULLS LAST
```

### ルール 7: GROUP BY
```
GROUP BY p.tcg_uuid, ...     →  GROUP BY p.id, ...
```

### ルール 8: _next_pm_code() 廃止
```
# Before:
pm_code = await _next_pm_code(db)

# After:
# product_code は DEFAULT で SEQUENCE から自動採番されるため、INSERT 時に省略可能。
# ただし既存の呼び出し元がコードを事前に必要とする場合は SELECT nextval('public.product_code_seq') で取得。
```

## テスト変換ルール

### テストの INSERT
```
# Before:
INSERT INTO public.products(..., tcg_uuid) VALUES (..., gen_random_uuid()) RETURNING tcg_uuid

# After:
INSERT INTO public.products(...) VALUES (...) RETURNING id
```

### テストの keyword INSERT
```
# Before:
INSERT INTO {schema}.product_search_keywords(id, product_id, keyword, position)
  SELECT %s, tcg_uuid, 'keyword', 99 FROM public.products WHERE product_code='PM0123'

# After:
INSERT INTO {schema}.product_search_keywords(id, product_id, keyword, position)
  SELECT %s, id, 'keyword', 99 FROM public.products WHERE product_code='PM0123'
```

### テストの FK 定義
```
# Before:
FOREIGN KEY (product_id) REFERENCES public.products (tcg_uuid)

# After:
FOREIGN KEY (product_id) REFERENCES public.products (id)
```

### テストの JOIN
```
# Before:
JOIN public.products p ON p.tcg_uuid = k.product_id

# After:
JOIN public.products p ON p.id = k.product_id
```

### conftest.py:768
```
tcg_uuid UUID,  →  残す（Phase C で削除）
```

## 受入条件

| 基準 | 検証方法 |
|-----|---------|
| 4テーブルの product_id が INTEGER | migration 内の pg_attribute 型チェック |
| FK が public.products(id) を参照 | migration 内の pg_constraint 検証 |
| pytest 全 PASS | CI |
| product_code が SEQUENCE で採番される | テストで確認 |
| grep -rn 'tcg_uuid' backend/app/ が 0 件 | CI 後に grep |
| デプロイ成功 + smoke PASS | deploy.yml |

## 外部事例

該当なし（内部のDB正規化作業のため）

## リスクと対処

| リスク | 対処 |
|-------|------|
| UUID → INTEGER 変換でデータ不整合 | migration 内で件数検証（変換前後で NOT NULL 行数一致） |
| 既存 API レスポンスの型変化 | tcg_uuid は API schemas に未露出（grep 0件確認済み） |
| SEQUENCE 開始値の重複 | MAX+1 で開始。ON CONFLICT で安全弁 |
| migration と code の同時デプロイ必須 | 1つの PR にまとめる |

## 維持する担当・仕組み

- Phase C（tcg_uuid DROP）は Phase B 完了後に別 PR で実施
- Phase D（残存参照クリーンアップ）は Phase C 後
- product_code SEQUENCE は DB 側で自動管理（Python 側の _next_pm_code は廃止）
