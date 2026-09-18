# Design: 仕入元マスタ SSOT Phase 2 — テーブル統合

recon: `docs/handoff/supplier-ssot-phase2/recon.md`
ADR参照: ADR-090（products 中央化）, ADR-093（マスタ再設計）, ADR-085（supplier_prompts）

## KGI

仕入元データを `public.suppliers` 1テーブルに統合し、3テーブル分散（SSOT違反）を解消する。

## KPI（PO が○×を判定できる粒度）

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | `public.suppliers` に `tenant_id` 列が存在する | `\d public.suppliers` で確認 |
| 2 | 旧 `tenant_NNN.suppliers` の全行が `public.suppliers` に存在する | `SELECT count(*) FROM public.suppliers WHERE tenant_id IS NOT NULL` ≧ 旧テナント行数合計 |
| 3 | `tenant_NNN.suppliers` テーブルが DROP されている | `\dt tenant_004.suppliers` で「not found」 |
| 4 | `tenant_NNN.tcg_suppliers` テーブルが DROP されている | `\dt tenant_004.tcg_suppliers` で「not found」 |
| 5 | `purchase_orders.supplier_id` が `public.suppliers(id)` を参照する FK を持つ | `\d tenant_004.purchase_orders` で FK 確認 |
| 6 | テナント CRUD（GET/POST/PATCH/DELETE /suppliers）が動作する | API テスト |
| 7 | 発注作成（POST /purchase-orders）が動作する | API テスト |
| 8 | PO PDF 生成が正しい仕入元名・敬称を出力する | PDF 出力確認 |
| 9 | TCG LINE取込の仕入元照合が動作する | 既存テスト全通過 |
| 10 | CI 全チェック通過 | GitHub Actions 緑 |

## 対象と対象外

### 対象
- `public.suppliers` への `tenant_id` 追加
- `tenant_NNN.suppliers` → `public.suppliers` データ移行
- `purchase_orders.supplier_id` FK 張り替え（tenant → public）
- `products.supplier_default_id` FK 張り替え（tenant → public）
- テナント CRUD（`suppliers.py`）の参照先変更
- `_resolve_tenant_supplier_id()` 廃止
- `po_renderer.py` の 2段階照合を直接参照に簡素化
- `tcg_suppliers` 参照の全ファイル移行（12ファイル + 5テスト）
- `tenant_NNN.suppliers` DROP
- `tenant_NNN.tcg_suppliers` DROP

### 対象外
- `public.supplier_prompts`（既に public.suppliers 参照、変更不要）
- `public.supplier_aliases`（既に public.suppliers 参照、変更不要）
- `supplier_channels`（Phase 1 で移行済み、変更不要）
- `super_admin_suppliers.py`（既に public.suppliers 直接操作、変更不要）
- フロントエンド（管理画面の変更なし。API レスポンス形式は維持）
- RLS の public.suppliers への追加（アプリ層 WHERE 句で分離。PO承認済み）

## 変更前後

### テーブル構造

**変更前:**
```
public.suppliers (20列, tenant_id なし)
tenant_NNN.suppliers (12列, tenant_id あり, RLS有効)
tenant_NNN.tcg_suppliers (UUID PK, TCG専用)
```

**変更後:**
```
public.suppliers (21列, tenant_id INTEGER 追加)
  - tenant_id = NULL → 共有カタログ（旧 public.suppliers）
  - tenant_id = N → テナント固有仕入元（旧 tenant_NNN.suppliers）
```

### FK チェーン

**変更前:**
```
purchase_orders.supplier_id → tenant_NNN.suppliers(id)
products.supplier_default_id → tenant_NNN.suppliers(id)
supplier_channels.supplier_id → public.suppliers(id)  [Phase 1 済]
supplier_prompts.supplier_id → public.suppliers(id)
```

**変更後:**
```
purchase_orders.supplier_id → public.suppliers(id)
products.supplier_default_id → public.suppliers(id)
supplier_channels.supplier_id → public.suppliers(id)  [変更なし]
supplier_prompts.supplier_id → public.suppliers(id)  [変更なし]
```

### コード変更

**`backend/app/routers/purchase_orders.py`:**
- 変更前: `_resolve_tenant_supplier_id()` で public→tenant コピー
- 変更後: 関数廃止。`data.supplier_id` を直接使用（public.suppliers.id）

**`backend/app/services/po_renderer.py`:**
- 変更前: tenant.suppliers → public.suppliers 2段階照合
- 変更後: `public.suppliers WHERE id = :supplier_id` 直接取得

**`backend/app/routers/suppliers.py`:**
- 変更前: `{schema}.suppliers` に CRUD
- 変更後: `public.suppliers WHERE tenant_id = :tenant_id` に CRUD

**tcg_suppliers 参照 12ファイル:**
- 変更前: `JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ...`
- 変更後: `JOIN public.suppliers s ON s.id = sc.supplier_id`（supplier_channels 経由は変更なし）

## マイグレーション計画

### Sprint 1: DDL + データ移行（SSH 手動 + マイグレーション）

**Step 1: public.suppliers に tenant_id 追加**
```sql
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS tenant_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_suppliers_tenant_id ON public.suppliers (tenant_id);
```

**Step 2: データ移行（SSH 手動実行）**
```sql
-- tenant_NNN.suppliers → public.suppliers にコピー
-- supplier_code 重複チェック後、新 id を発番
INSERT INTO public.suppliers (tenant_id, supplier_code, name, contact_name, email, phone, address, notes, is_active, created_at, updated_at)
SELECT tenant_id, supplier_code, name, contact_name, email, phone, address, notes, is_active, created_at, updated_at
FROM tenant_NNN.suppliers
WHERE NOT EXISTS (
    SELECT 1 FROM public.suppliers p
    WHERE p.supplier_code = tenant_NNN.suppliers.supplier_code
    AND p.tenant_id = tenant_NNN.suppliers.tenant_id
);
```

**Step 3: purchase_orders.supplier_id の値更新（SSH 手動実行）**
```sql
-- 旧 tenant id → 新 public id にマッピング
UPDATE tenant_NNN.purchase_orders po
SET supplier_id = (
    SELECT p.id FROM public.suppliers p
    WHERE p.supplier_code = ts.supplier_code
    AND p.tenant_id = :tenant_id
)
FROM tenant_NNN.suppliers ts
WHERE ts.id = po.supplier_id;
```

**Step 4: FK 張り替え（マイグレーション DDL）**
```sql
-- purchase_orders FK: tenant.suppliers → public.suppliers
ALTER TABLE tenant_NNN.purchase_orders DROP CONSTRAINT purchase_orders_supplier_id_fkey;
ALTER TABLE tenant_NNN.purchase_orders
    ADD CONSTRAINT purchase_orders_supplier_id_fkey
    FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id);

-- products FK: tenant.suppliers → public.suppliers
ALTER TABLE tenant_NNN.products DROP CONSTRAINT IF EXISTS products_supplier_default_id_fkey;
ALTER TABLE tenant_NNN.products
    ADD CONSTRAINT products_supplier_default_id_fkey
    FOREIGN KEY (supplier_default_id) REFERENCES public.suppliers(id);
```

**Step 5: テーブル DROP（SSH 手動実行、PO許可後）**
```sql
DROP TABLE IF EXISTS tenant_NNN.suppliers CASCADE;
DROP TABLE IF EXISTS tenant_NNN.tcg_suppliers CASCADE;
```

### Sprint 2: コード変更

- `purchase_orders.py`: `_resolve_tenant_supplier_id()` 廃止
- `po_renderer.py`: 直接参照に簡素化
- `suppliers.py`: `public.suppliers WHERE tenant_id = ?` に変更
- tcg_suppliers 参照 12ファイル: `public.suppliers` に移行
- テスト 5ファイル: seed データ・参照更新

## 代替案と選択理由

| 案 | 内容 | 採否 | 理由 |
|---|---|---|---|
| A | public.suppliers に tenant_id 追加、全テーブル統合 | **採用** | SSOT 達成。拡張時の列追加が1箇所で済む |
| B | tenant.suppliers を残し public からの参照を維持 | 却下 | PO 決定で撤回。データ分散が継続 |
| C | tenant_suppliers にリネームして残す | 却下 | 3テーブル目が残る。SSOT 違反継続 |

## リスクと対処

| リスク | 影響 | 対処 |
|---|---|---|
| supplier_code 重複（テナント間で同一コード） | データ移行時に衝突 | **本番確認済み: 重複なし（0件）**。単純コピーで対応 |
| purchase_orders FK 張り替え中のダウンタイム | 発注機能停止 | 1トランザクション内で DROP→ADD |
| products.supplier_default_id の旧id参照 | 商品マスタ不整合 | **本番確認済み: products 0行**。DDL のみで対応 |
| tcg_suppliers の UUID→INTEGER id 変換 | supplier_channels 経由の参照崩壊 | Phase 1 で解決済み（supplier_channels は既に public.suppliers.id 参照） |
| テナント間のデータ漏洩 | 他テナントの仕入元が見える | アプリ層 WHERE tenant_id = ? で分離（PO承認済み） |

## 受入条件と検証方法

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | tenant_id 列が存在 | SSH: `\d public.suppliers` |
| 2 | 旧データが移行済み | SSH: `SELECT count(*) FROM public.suppliers WHERE tenant_id IS NOT NULL` |
| 3 | tenant.suppliers が DROP 済み | SSH: `\dt tenant_004.suppliers` → not found |
| 4 | tcg_suppliers が DROP 済み | SSH: `\dt tenant_004.tcg_suppliers` → not found |
| 5 | purchase_orders FK が public 参照 | SSH: `\d tenant_004.purchase_orders` |
| 6 | テナント CRUD 動作 | API テスト: GET/POST/PATCH/DELETE /suppliers |
| 7 | 発注作成動作 | API テスト: POST /purchase-orders |
| 8 | PDF 出力正常 | PO PDF の仕入元名・敬称確認 |
| 9 | LINE取込動作 | 既存テスト全通過 |
| 10 | CI 緑 | GitHub Actions |

## 本番データ確認結果（2026-09-18）

| 項目 | 結果 |
|---|---|
| tenant_NNN.suppliers 行数 | tenant_006: 47件、他4テナント: 0件 |
| supplier_code 重複（テナント横断） | なし（0件） |
| products.supplier_default_id | 未使用（products テーブル 0行） |
| 移行対象データ | 47件のみ（tenant_006）|

## ロールバック手順

### Sprint 1（DDL + データ移行）のロールバック
1. `public.suppliers` から `tenant_id IS NOT NULL` の行を DELETE（移行した47件）
2. `ALTER TABLE public.suppliers DROP COLUMN tenant_id`
3. FK を `public.suppliers` → `tenant_NNN.suppliers` に戻す
4. `tenant_NNN.suppliers` テーブルを再作成（バックアップから COPY）

### 事前バックアップ
- DROP 前に `pg_dump --table=tenant_006.suppliers jarvis_db > /tmp/tenant_006_suppliers_backup.sql` を SSH で実行
- `pg_dump --table=tenant_NNN.tcg_suppliers jarvis_db > /tmp/tcg_suppliers_backup.sql`

### Sprint 2（コード変更）のロールバック
- git revert で Sprint 2 コミットを巻き戻し
- Sprint 1 のロールバック後にデプロイ

## 外部・過去事例と応用

Phase 1（PR #3539）で同パターンを実施済み:
- `supplier_channels.supplier_id` UUID → INTEGER への型変更
- `public.suppliers` への FK 張り替え
- DDL のみマイグレーション + 値マッピングは SSH 手動実行
- 結果: 本番稼働確認済み（2026-09-17）

ADR-090（products 中央化）で同パターン:
- テナント固有テーブル → public テーブルへの統合
- public.products は全テナント共有、tenant_id による分離

## 維持の仕組み

### 守り手
- `scripts/check-process-artifacts.js:67` — `scripts/` 配下変更を危険パスとして検出
- `.github/workflows/migration-guard.yml` — マイグレーション SQL の ADR-155 チェック
- `backend/tests/` — 既存テスト群（supplier 参照の整合性）

### 運用
- 新規仕入元追加: super_admin_suppliers.py（共有）または suppliers.py（テナント固有、tenant_id 付与）
- カラム追加: `public.suppliers` への ALTER 1箇所で全テナントに反映（SSOT の利点）
