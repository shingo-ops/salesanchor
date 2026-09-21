# Design: ADR-156 Phase 3B — tcg_product_categories SSOT to public schema

## KGI

`public.tcg_product_categories`（INTEGER PK）が全ルックアップパスで唯一のソース。
`{TCG_SCHEMA}.tcg_product_categories`（UUID PK）をルックアップに使うコードがゼロ。

## 変更一覧

### 変更1: `backend/app/services/tcg_product_master_svc.py:101`

**変更前:**
```python
schema = "public" if table == "product_kinds" else TCG_SCHEMA
```

**変更後:**
```python
_PUBLIC_TABLES = {"product_kinds", "tcg_product_categories"}
schema = "public" if table in _PUBLIC_TABLES else TCG_SCHEMA
```

**理由:** Phase 3A で `product_kinds` を同様に修正した前例と同じパターン。`in` セット検索で将来の追加も容易。

### 変更2: `backend/app/routers/tcg_product_import.py:334`

変更1 と同一パターン。GET `/tcg/products/lookups` エンドポイント用。

### 変更3: `backend/app/services/tcg_work_comparison_svc.py:129`

**変更前:**
```python
_PUBLIC_MASTER = frozenset({"tcg_normalization_rules"})
```

**変更後:**
```python
_PUBLIC_MASTER = frozenset({"tcg_normalization_rules", "tcg_product_categories"})
```

**理由:** `MASTER_TABLES` の中で `tcg_product_categories` が `TCG_SCHEMA` から読まれていた。スナップショットの整合性のため public SSOT から読む必要がある。

### 変更4: `backend/app/services/tcg_product_import_svc.py:63-67`

コメント追加のみ（動作変更なし）。`division_code` と `product_category_code` が `load_lookup_maps` で上書きされる旨を明記。

## 影響範囲

| ファイル | 変更種別 | 呼び出し元 |
|---|---|---|
| `tcg_product_master_svc.py` | schema 選択ロジック修正 | `tcg_product_import.py` → `create_product_standalone` |
| `tcg_product_import.py` | schema 選択ロジック修正 | GET `/tcg/products/lookups` |
| `tcg_work_comparison_svc.py` | `_PUBLIC_MASTER` 追加 | `read_snapshot` → `compare_snapshot` |
| `tcg_product_import_svc.py` | コメント追加（動作変更なし） | なし |

## 検証方法

| 基準 | 検証方法 |
|---|---|
| `public.tcg_product_categories` からルックアップが返る | GET `/tcg/products/lookups` で `product_category_id` リストの ID が INTEGER であること |
| 商品登録フォームで分類選択肢が表示される | GET `/tcg/products/master/form` の `lookups.product_category_id` が空でないこと |
| 比較スナップショットが公開テーブルを読む | `read_snapshot` のスナップショット JSON に `public.tcg_product_categories` データが入ること |
| 静的テスト通過 | `pytest backend/tests/test_tcg_schema_qualification.py` 全 PASSED |

## DB 変更

なし（コード変更のみ）。`public.tcg_product_categories` は既にデータ投入済み（Phase 3 移行完了済み）。

## 弊害・リスク

- `tcg_work_comparison_svc.py` の変更はスナップショット内容の変化を伴う。ただし既存の比較ジョブとの後方互換性は、スナップショットの `sha256` が変わることで自動的に検知される（不一致時に `INVALID_SAVED_REFERENCE` エラー）。

## 外部事例

Phase 3A（ADR-156、PR #3633）で `division_code` → `public.product_kinds` を同様の手法で修正済み。本 PR は同じパターンを `product_category` に適用する。

## 戻し方

コード変更のみのため、git revert で即時ロールバック可能。DB 変更なし。
