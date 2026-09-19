# ADR-1002 Phase C Design: Drop tcg_uuid from public.products

**日付**: 2026-09-15
**ブランチ**: release/adr-1002-phase-c
**Recon**: [recon.md](recon.md)
**ADR**: ADR-1001 §Phase 2c（「tcg_uuid カラムの除去は後日判断」→ 本設計で実施）
**PO承認**: 2026-09-15 設計相談にて「推奨で進める」（選択肢A: そのまま DROP）

---

## 1. 目的

Phase B 完了により、全テナントの keyword/analysis テーブルは `public.products(id)` (INTEGER) を FK 参照している。`public.products.tcg_uuid` はどこからも参照されておらず、残置はコード複雑性の原因になっている（tcg_mirror.py の JOIN が型不一致で本番エラーの可能性）。

**利用者に見える変化**: なし（tcg_uuid は内部カラムで UI に露出していない）。
**開発者に見える変化**: tcg_uuid 関連の条件分岐・fallback コードが消え、保守が単純化される。

---

## 2. 対象と対象外

### 対象
- `public.products.tcg_uuid` カラム・制約・インデックスの削除（本番 migration）
- `tcg_mirror.py` の JOIN 修正（p.tcg_uuid → p.id）
- `tcg_product_detail_svc.py` の audit_log record_id 生成の簡素化
- テストフィクスチャ・ヘルパーからの tcg_uuid 除去

### 対象外
- 既存マイグレーション SQL 内の tcg_uuid 参照（歴史的記録として残置。冪等実行に影響なし）
- `tcg_products` テーブルの削除（ADR-1001 Phase 2c で別途実施済み）
- フロントエンド変更（tcg_uuid 参照なし）

---

## 3. 変更一覧

### 3-1. Migration SQL（新規）

**ファイル**: `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql`

```sql
-- ADR-1002 Phase C: Drop tcg_uuid column from public.products
-- 前提: Phase B 完了済み（全テナント FK → public.products(id)）
-- 参照元: なし（recon.md §3 で確認済み）

ALTER TABLE public.products DROP CONSTRAINT IF EXISTS uq_products_tcg_uuid;
DROP INDEX IF EXISTS idx_products_tcg_uuid;
ALTER TABLE public.products DROP COLUMN IF EXISTS tcg_uuid;
```

### 3-2. バックエンドコード修正

#### tcg_mirror.py（2箇所）

**変更前** (行145):
```python
JOIN public.products p ON p.tcg_uuid = k.product_id
```
**変更後**:
```python
JOIN public.products p ON p.id = k.product_id
```
同じ変更を行154にも適用。

#### tcg_product_detail_svc.py（行138-140）

**変更前**:
```python
# audit_log.record_id is UUID type; use tcg_uuid if available, else generate one
_uuid_col = "tcg" + "_uuid"  # Phase C drops this column from public.products
_audit_pid = product.get(_uuid_col) or str(uuid4())
```
**変更後**:
```python
_audit_pid = str(uuid4())
```

### 3-3. テスト修正

#### public_products_test.sql
- 行10: `tcg_uuid UUID UNIQUE DEFAULT gen_random_uuid(),` → 削除
- 行29: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS tcg_uuid UUID;` → 削除
- 行38-39: `CREATE UNIQUE INDEX ... uq_public_products_tcg_uuid ...` → 削除

#### conftest.py
- 行768: `tcg_uuid UUID,` → 削除

#### test_tcg_work_matching_integration.py

**_rewire_keyword_fks 修正** (行50-148):
tcg_uuid 存在チェックを追加。tcg_uuid がない場合（Phase C 後）は、空テーブルの product_id カラムを直接 INTEGER に置換する。

```sql
-- Early return if already INTEGER
IF EXISTS (...atttypid = 23...) THEN RETURN; END IF;

-- Phase C path: tcg_uuid doesn't exist, tables are empty after provision()
IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
) THEN
    -- Drop FK → Drop UUID column → Add INTEGER column → Add FK
    ... (各テーブルに適用)
    RETURN;
END IF;

-- Legacy Phase B path (tcg_uuid exists): existing logic unchanged
...
```

**seed_guard_dictionary** (行767):
INSERT 列リストから `tcg_uuid` を除去、`gen_random_uuid()` を除去。

#### test_tcg_product_detail_pg.py（行183）

**変更前**:
```python
assert audit["changed_by"] == "ci-reviewer" and audit["record_id"] == product.get("tcg_uuid")
```
**変更後**:
```python
assert audit["changed_by"] == "ci-reviewer"
# record_id is now always a fresh uuid4(), just verify it's a valid UUID
import uuid; uuid.UUID(audit["record_id"])
```

#### test_tcg_product_roundtrip.py（行22）

**変更前**:
```python
"tcg_uuid": "00000000-0000-4000-8000-000000000001",
```
→ 行削除

---

## 4. 触るファイル

- `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql`（新規）
- `migrations/20260916_130000_work_id_not_null.sql`（新規）
- `backend/app/tasks/tcg_mirror.py`
- `backend/app/services/tcg_product_detail_svc.py`
- `backend/tests/fixtures/public_products_test.sql`
- `backend/tests/conftest.py`
- `backend/tests/test_tcg_work_matching_integration.py`
- `backend/tests/test_tcg_product_detail_pg.py`
- `backend/tests/test_tcg_product_roundtrip.py`
- `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx`
- `scripts/run_all_migrations.sh`
- `docs/handoff/adr-1002-phase-c/recon.md`（新規）
- `docs/handoff/adr-1002-phase-c/design.md`（新規）

## 削除するファイル

なし

---

## 5. 受入条件

| # | 基準 | 検証方法 |
|---|------|---------|
| C-1 | public.products に tcg_uuid カラムが存在しない | `\d public.products` でカラム不在を確認 |
| C-2 | tcg_mirror.py が p.id で JOIN し、エラーなく実行可能 | コードレビュー + テスト |
| C-3 | audit_log の record_id が UUID で記録される | test_tcg_product_detail_pg テスト PASS |
| C-4 | 全テスト PASS | CI pytest |
| C-5 | フロントエンドに影響なし | tcg_uuid 参照なし（recon §1-4） |

---

## 6. リスクと対処

| リスク | 影響 | 対処 |
|-------|------|------|
| tcg_uuid データ消失 | 297行の UUID 値が失われる | Phase B で FK 切替済み、参照元なし。バックアップから復元可能 |
| tcg_mirror.py 本番エラー | 日次ミラータスクが Phase B 後に既に壊れている可能性 | Phase C で修正。修正前に celery ログを確認推奨 |
| _rewire テストヘルパー | CI で fresh DB 時に _rewire が失敗する | tcg_uuid 存在チェックを追加し、Phase C パスを分岐 |

---

## 7. 外部事例

該当なし（内部 DB スキーマの整理作業のため、外部事例は不要）。

---

## 8. 守り手

- Migration の冪等性: `IF EXISTS` / `IF NOT EXISTS` ガードを全操作に適用
- テストの _rewire: `information_schema.columns` チェックで tcg_uuid 有無を動的判定
- 既存マイグレーション: 変更なし（`_pid_col` 検出は `pg_attribute.atttypid` ベースで tcg_uuid カラム自体に依存しない）
