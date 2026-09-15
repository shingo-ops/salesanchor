# ADR-1002 Phase C Recon: Drop tcg_uuid from public.products

**日付**: 2026-09-15
**ブランチ**: release/adr-1002-phase-c
**ベース**: origin/main (4e0c8083)
**前提**: Phase B (PR #3522) マージ・本番デプロイ済み

---

## 1. tcg_uuid 参照箇所（全量）

### 1-1. バックエンドコード（3箇所）

| ファイル | 行 | 内容 | 変更要否 |
|---------|---|------|---------|
| `backend/app/tasks/tcg_mirror.py` | 145 | `JOIN public.products p ON p.tcg_uuid = k.product_id` | **要** → `p.id = k.product_id` |
| `backend/app/tasks/tcg_mirror.py` | 154 | `JOIN public.products p ON p.tcg_uuid = k.product_id` | **要** → `p.id = k.product_id` |
| `backend/app/services/tcg_product_detail_svc.py` | 138-140 | `_uuid_col = "tcg" + "_uuid"` / `product.get(_uuid_col) or str(uuid4())` | **要** → `str(uuid4())` に簡素化 |

### 1-2. テストコード（13箇所）

| ファイル | 行 | 内容 | 変更要否 |
|---------|---|------|---------|
| `backend/tests/conftest.py` | 768 | `tcg_uuid UUID,`（SQLite products テーブル定義） | **要**: 行削除 |
| `backend/tests/fixtures/public_products_test.sql` | 10 | `tcg_uuid UUID UNIQUE DEFAULT gen_random_uuid(),` | **要**: 行削除 |
| `backend/tests/fixtures/public_products_test.sql` | 29 | `ADD COLUMN IF NOT EXISTS tcg_uuid UUID;` | **要**: 行削除 |
| `backend/tests/fixtures/public_products_test.sql` | 38-39 | `CREATE UNIQUE INDEX ... uq_public_products_tcg_uuid` | **要**: 行削除 |
| `backend/tests/test_tcg_work_matching_integration.py` | 90 | `WHERE p.tcg_uuid = sk.product_id` (_rewire内) | **要**: 後述 |
| `backend/tests/test_tcg_work_matching_integration.py` | 104 | `WHERE p.tcg_uuid = ek.product_id` (_rewire内) | **要**: 後述 |
| `backend/tests/test_tcg_work_matching_integration.py` | 118 | `WHERE p.tcg_uuid = ar.product_id` (_rewire内) | **要**: 後述 |
| `backend/tests/test_tcg_work_matching_integration.py` | 141 | `WHERE p.tcg_uuid = ars.product_id` (_rewire内) | **要**: 後述 |
| `backend/tests/test_tcg_work_matching_integration.py` | 767 | `INSERT INTO public.products (...,tcg_uuid)` | **要**: tcg_uuid を除去 |
| `backend/tests/test_tcg_product_detail_pg.py` | 183 | `audit["record_id"] == product.get("tcg_uuid")` | **要**: UUID 型チェックに変更 |
| `backend/tests/test_tcg_product_roundtrip.py` | 22 | `"tcg_uuid": "00000000-..."` テストデータ | **要**: キー削除 |

### 1-3. マイグレーション（46箇所・7ファイル）

歴史的なマイグレーション内の参照。**変更不要**（冪等性のため残置）。
Phase B 検出ロジック（`_pid_col := 'tcg_uuid'` 分岐）は tcg_uuid カラムの有無ではなく `pg_attribute.atttypid` で判定しているため、カラム削除後も安全。

### 1-4. フロントエンド・スクリプト

参照なし（grep 確認済み）。

---

## 2. _rewire_keyword_fks 問題の分析

### 現状

`_rewire_keyword_fks()` は Phase B migration をテスト内で再現するヘルパー関数（`backend/tests/test_tcg_work_matching_integration.py:45-148`）。

**フロー**:
1. `provision()` → `20260906_120000_create_tcg_tables_t001.sql` を実行 → keyword テーブルを `product_id UUID REFERENCES tcg_products(id)` で作成
2. `_PUBLIC_PRODUCTS_DDL` → `public_products_test.sql` で public.products を作成
3. `_rewire_keyword_fks()` → keyword テーブルの product_id を UUID→INTEGER に変換（`p.tcg_uuid = sk.product_id` で JOIN）

**安全装置**: 行56-66 に早期リターンあり。`product_search_keywords.product_id` が既に INTEGER (atttypid=23) ならスキップ。

**Phase C 後の問題**: public.products から tcg_uuid を削除すると、_rewire の UPDATE JOIN (`p.tcg_uuid = sk.product_id`) が失敗する。

### 解決策

_rewire に tcg_uuid 存在チェックを追加:
- tcg_uuid が存在する場合: 現行ロジック（Phase B パス）
- tcg_uuid が存在しない場合: テーブルは provision() 直後で空 → product_id カラムを直接 INTEGER に置換 + FK 追加

---

## 3. DB 状態（本番・Phase B 完了後）

| 項目 | 値 |
|-----|---|
| tcg_uuid カラム | 存在（public.products） |
| NOT NULL 行数 | 297 |
| NULL 行数 | 1533 |
| UNIQUE 制約 | `uq_products_tcg_uuid` |
| 部分 UNIQUE INDEX | `idx_products_tcg_uuid` |
| FK 参照元 | なし（Phase B で全て public.products(id) に張替え済み） |
| VIEW/FUNCTION 参照 | なし |

---

## 4. tcg_mirror.py の現状（本番影響）

【事実】Phase B マージ後、`tcg_mirror.py:145,154` は `p.tcg_uuid = k.product_id` で JOIN。Phase B で `k.product_id` は INTEGER に変換済み。UUID と INTEGER の結合は PostgreSQL で型不一致エラーになる。

【未確認】tcg_mirror タスク（celery beat, AM 02:00 JST）が Phase B 後に実行されたかどうか。実行されていれば既にエラーが発生しているはず。
