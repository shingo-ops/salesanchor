# Recon: ADR-090 PR4 — tenant_NNN.products 廃止

**日時**: 2026-06-15  
**担当**: Hikky-dev  
**対象 ADR**: [ADR-090](../../adr/ADR-090-products-central-unification.md)

---

## 既存 ADR 検索結果

| キーワード | 結果 |
|----------|------|
| `git grep -i "products" docs/adr/` | ADR-090（主軸）・ADR-093・ADR-099・ADR-014 |
| `docs/adr/FEATURE-INDEX.md` | 在庫/inventory → ADR-099 / ADR-093 / ADR-014 |
| PR4 直接言及 | ADR-090 §段階実装案 PR4 のみ |

---

## 重大発見: 新テナント作成時の FK が未修正

### 問題

`migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql` は
**実行時点で存在する** 全テナントスキーマに FK 張り替えを適用した（冪等 DO ブロック）。
しかし以下の**2か所**が未修正のまま残っており、**このマイグレーション実行後に新テナントを
作成すると quote_items 等の FK が `tenant_NNN.products(id)` を指したままになる**。

### 未修正箇所 1: `backend/app/services/tenant.py`

| 行番号 | 内容 |
|--------|------|
| `tenant.py:801` | `product_id INTEGER REFERENCES {schema}.products(id)` — quote_items |
| `tenant.py:854` | `product_id INTEGER REFERENCES {schema}.products(id)` — invoice_items |
| `tenant.py:917` | `product_id INTEGER NOT NULL REFERENCES {schema}.products(id)` — purchase_order_items |

`create_tenant_schema` 関数（`tenant.py:1457`）が呼び出す `_TENANT_TABLES_SQL`（`tenant.py:705〜`）に
上記 FK が含まれている。`admin.py:67` の `/tenants` POST エンドポイントがこれを呼び出す。

### 未修正箇所 2: マイグレーションファイル

| ファイル | 行番号 | 内容 |
|--------|--------|------|
| `migrations/005_add_phase2_tenant_tables.sql:100` | `product_id INTEGER REFERENCES {schema}.products(id)` — quote_items |
| `migrations/005_add_phase2_tenant_tables.sql:147` | `product_id INTEGER REFERENCES {schema}.products(id)` — invoice_items |
| `migrations/007_add_phase3_tenant_tables.sql:50` | `product_id INTEGER NOT NULL REFERENCES {schema}.products(id)` — purchase_order_items |

`migrations/005` と `007` はテナントセットアップスクリプト（`scripts/setup_tenant.py`
`scripts/setup_test_users.py`）から呼ばれる場合もある。

### 影響範囲

`20260602_010000` 実行後に作成された新テナントは:
- `quote_items/invoice_items/purchase_order_items.product_id` が `tenant_NNN.products(id)` を参照
- アプリは `public.products.id` を使って INSERT → **FK 違反で見積/請求/発注 作成が失敗する可能性**

---

## 現在の tenant_NNN.products の状態

### 既存テナントへの影響（`20260602_010000` 適用済み）

- `migrations/20260602_010000` が全既存テナントの FK を `public.products` へ張り替え済み
- 既存テナントは問題なし

### tenant_NNN.products テーブル自体の残存

- `migrations/005_add_phase2_tenant_tables.sql:22`: `CREATE TABLE IF NOT EXISTS {schema}.products` が残存
- `backend/app/services/tenant.py:705`: 同 CREATE TABLE が残存
- 全テナントに `tenant_NNN.products` テーブルが物理的に存在
- アプリ（router）は `public.products` を参照しており、`tenant_NNN.products` への読み書きは一切なし

### アプリが tenant_NNN.products を参照する箇所

`backend/app/routers/` 内を grep した結果、`tenant_NNN.products` への直接参照は**ゼロ**。
（`products.py:83` は明示的に `public.products` を返す）

---

## 関連するその他のファイル

| ファイル | 内容 | 対応方針 |
|--------|------|---------|
| `migrations/038_add_products_phase1c_columns.sql:96,100` | `tenant_NNN.products` にインデックス追加（`IF NOT EXISTS` 付き） | テーブル削除後は問題なし（テーブルが存在しなければスキップ可能に修正要） |
| `backend/app/routers/admin.py:67` | `create_tenant_schema` 呼び出し | tenant.py 修正で自動的に解決 |

---

## 本番テナント実測（2026-06-13 GitHub Actions 調査ワークフロー実行）

**取得元**: run ID 27465813335（`temp-tenant001-investigation.yml`、SELECT READ ONLY）

| id | tenant_code | tenant_name | is_active | created_at |
|----|------------|-------------|-----------|------------|
| 1 | test-corp | テスト株式会社 | t | 2026-04-10 |
| 3 | perm-check-zzz | 権限確認用 | t | 2026-04-14 |
| 4 | highlife-jpn | HIGH LIFE JPN | t | 2026-04-17 |
| 5 | test-tenant-2 | テストテナント2 | t | 2026-04-17 |
| 6 | tenant-review | Sales Anchor App Review | t | 2026-05-14 |

**全テナントが 2026-05-14 以前に作成済み**。`20260602_010000` 実行時（2026-06-02）には
全テナントが既存であり、FK 張り替えが完全に適用されている。

→ **現時点で破損テナントはゼロ**。`tenant.py` の FK 未修正は将来テナント作成時のリスクのみ。

---

## 結論と次アクション

**PR4 で対応すべき作業**:

| # | 作業 | 場所 | リスク |
|---|------|------|--------|
| 1 | `quote_items/invoice_items/purchase_order_items` の FK を `public.products` に修正 | `tenant.py:801,854,917` / `migrations/005:100,147` / `migrations/007:50` | 低（additive 変更） |
| 2 | 新マイグレーション: `20260602_010000` と同じ FK 再マップを再実行（冪等） | 新 migration ファイル | 低（冪等） |
| 3 | `tenant_NNN.products` テーブルの凍結（INSERT/UPDATE/DELETE トリガー） | 新 migration | 中（既存行があれば確認必要） |
| 4 | `tenant_NNN.products` の DROP（Phase B） | 別 PR | 高（不可逆・PO GO 必要） |
