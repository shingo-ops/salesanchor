# Recon: ADR-156 Phase 3B — tcg_product_categories SSOT to public schema

## ADR 検索結果

- `git grep -i "product_categories" docs/adr/` → ADR-155, ADR-156 に記載あり（Phase 3A 完了済み）
- ADR-155: DDL-only migrations — tcg_product_categories の INTEGER PK 化設計
- ADR-156: Phase 3A = tcg_major_categories/product_kinds SSOT 完了。Phase 3B = tcg_product_categories SSOT

## 現状把握（file:line）

### 問題箇所

#### 1. `backend/app/services/tcg_product_master_svc.py:97-112`

```python
for key, table, name_col in [
    ("manufacturer_id", "tcg_manufacturers", "display_name"),
    ("product_category_id", "tcg_product_categories", "display_name"),
]:
    schema = "public" if table == "product_kinds" else TCG_SCHEMA
```

`table == "product_kinds"` は `tcg_product_categories` と一致しないため、常に `TCG_SCHEMA` を使用。
`product_category_id` のルックアップが tenant_004 の UUID テーブルを参照していた。

#### 2. `backend/app/routers/tcg_product_import.py:330-343`

```python
for key, table, name_col in [
    ("manufacturer_id", "tcg_manufacturers", "display_name"),
    ("product_category_id", "tcg_product_categories", "display_name"),
]:
    schema = "public" if table == "product_kinds" else TCG_SCHEMA
```

GET `/tcg/products/lookups` エンドポイントが同じ問題を持つ。

#### 3. `backend/app/services/tcg_work_comparison_svc.py:129`

```python
_PUBLIC_MASTER = frozenset({"tcg_normalization_rules"})
```

`MASTER_TABLES`（line 31-35）に `"tcg_product_categories"` が含まれるが、`_PUBLIC_MASTER` に含まれておらず `TCG_SCHEMA` から読んでいた。

### 正常箇所（参照）

- `backend/app/services/tcg_product_detail_svc.py:18-23` — `PUBLIC_INTEGER_LOOKUPS` に `product_category_id` が含まれ正しく `public` を使用
- `backend/app/services/tcg_product_import_svc.py:178-183` — `load_lookup_maps` で `public.tcg_product_categories` を上書き（Phase 3 SSOT 対応済み）
- `backend/app/services/tcg_product_roundtrip_svc.py:24` — `_PUBLIC_LOOKUP_TABLES` に `"product_category_code"` が含まれ正しく処理

### テスト確認

- `backend/tests/test_tcg_schema_qualification.py` — 7 テスト全 PASSED（LOOKUP_TABLES 構造変更なし）
- `backend/tests/test_tcg_work_matching_integration.py:248-252` — 既に `public.tcg_product_categories` を参照（テスト変更不要）
- `backend/tests/test_tcg_completion_safety.py:147` — 既に `public.tcg_product_categories` を参照（テスト変更不要）
