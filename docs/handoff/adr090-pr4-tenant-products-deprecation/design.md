# Design: ADR-090 PR4 — tenant_NNN.products 廃止（FK 修正・将来安全担保）

**日時**: 2026-06-15  
**対象 ADR**: [ADR-090](../../adr/ADR-090-products-central-unification.md)  
**参照 recon**: [recon.md](./recon.md)

---

## KGI（PO 承認済み: ADR-090 承認が証跡）

| # | 指標 | 検証方法 |
|---|------|---------|
| G1 | 新テナント作成時の FK が `public.products` を指す | CI: `test_products_cross_tenant_fk.py` + migration ドライラン |
| G2 | 既存テナントへの影響ゼロ | CI: 全既存 migration の dry-run |
| G3 | `tenant.py` / `migrations/005,007` に `{schema}.products` FK 参照なし | grep で確認 |

---

## 外部事例・過去事例参照

**該当なし（理由）**: FK 定義修正のみの小規模変更。additive ではなく既存定義変更だが、
全テナントへの影響は 2026-06-13 実測で「既存テナントは 20260602_010000 で修正済み」と確認済み。
外部事例を参照するほどのリスク・新規性なし。

---

## 実装方針

### 方針の選択

| 案 | 内容 | 採用 |
|----|------|------|
| A | `tenant_NNN.products` を即 DROP | ❌ 不可逆・本番行数未確認（SSH 制限）・PO GO 必要 |
| **B** | **FK のみ修正（`public.products` へ）。テーブル自体は温存。** | ✅ 採用 |
| C | migration を追加して既存 FK を再修正 | ❌ 全テナント修正済みのため不要（recon 確認済み） |

### 採用理由

- 現時点で破損テナントはゼロ（recon 実測）
- `tenant_NNN.products` テーブル自体の DROP は別 PR（Phase B）で対応
- 今回のスコープ: コード定義の修正のみ（将来の新テナント作成が安全になる）

---

## 変更ファイルと具体的変更内容

### 1. `backend/app/services/tenant.py`

変更箇所（3か所）: `_TENANT_TABLES_SQL` 定数内の FK 定義

| 変更前 | 変更後 |
|-------|-------|
| `product_id INTEGER REFERENCES {schema}.products(id)` | `product_id INTEGER REFERENCES public.products(id)` |
| `product_id INTEGER REFERENCES {schema}.products(id)` | `product_id INTEGER REFERENCES public.products(id)` |
| `product_id INTEGER NOT NULL REFERENCES {schema}.products(id)` | `product_id INTEGER NOT NULL REFERENCES public.products(id)` |

対象テーブル: `quote_items`（行801）・`invoice_items`（行854）・`purchase_order_items`（行917）

また `tenant_NNN.products` CREATE TABLE（行705〜）に廃止予定コメントを追加。

### 2. `migrations/005_add_phase2_tenant_tables.sql`

変更箇所（2か所）:

| 行 | 変更前 | 変更後 |
|----|-------|-------|
| 100 | `product_id INTEGER REFERENCES {schema}.products(id)` | `product_id INTEGER REFERENCES public.products(id)` |
| 147 | `product_id INTEGER REFERENCES {schema}.products(id)` | `product_id INTEGER REFERENCES public.products(id)` |

### 3. `migrations/007_add_phase3_tenant_tables.sql`

変更箇所（1か所）:

| 行 | 変更前 | 変更後 |
|----|-------|-------|
| 50 | `product_id INTEGER NOT NULL REFERENCES {schema}.products(id)` | `product_id INTEGER NOT NULL REFERENCES public.products(id)` |

### 4. `.github/workflows/temp-fk-tenant-check.yml`

調査完了のため削除。

---

## 弊害・トレードオフ

| 弊害 | 対策 |
|------|------|
| `migrations/038` が `tenant_NNN.products` にインデックス追加 — テーブルが存在しない場合はエラー | テーブル自体は温存（Phase B で別途対応）のため問題なし |
| `tenant_NNN.products` への直接 SELECT が失敗する可能性 | アプリは `public.products` のみ参照（確認済み）、`tenant_NNN.products` へのアクセスはゼロ |

---

## 検証方法

| # | 検証 | 方法 |
|---|------|------|
| 1 | `tenant.py` の FK が `public.products` を指す | `grep -n "REFERENCES.*products" backend/app/services/tenant.py` |
| 2 | `migrations/005,007` の FK が `public.products` を指す | 同 grep |
| 3 | CI: cross-tenant FK テスト通過 | `test_products_cross_tenant_fk.py` |
| 4 | CI: migration dry-run 通過 | `migration-test.yml` |
