# recon: analysis_rule publicスキーマ移行

## 調査日: 2026-09-20

---

## 既存ADR検索結果

- `git grep -i docs/adr/` で `analysis_rule` を検索 → 0件（analysis_ruleに特化したADRは未起案）
- 関連ADR:
  - `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`: テナントスキーマプレフィックス強制ルール（`{TCG_SCHEMA}.`）
  - `docs/adr/ADR-090-products-central-unification.md`: productsをpublicスキーマに統一した前例
  - `docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md`: TCG productsをpublicへ統一
  - `docs/adr/ADR-143-inventory-public-v2-canonical.md`: inventoryをpublicスキーマへ移行した前例
  - `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`: TCG parity02 GAS→Python移行（SQLスキーマ修飾必須）
  - `docs/adr/ADR-155-product-master-ssot-csv-app.md`: productマスタSSOT CSV管理（publicスキーマパターン）

---

## 現状

### テーブル所在
- 13テーブルは `migrations/20260917_000000_create_analysis_rule_tables.sql:13-358` で tenant_001 / tenant_004 スキーマに作成済み
- `public` スキーマには analysis_rule_* テーブルは存在しない

### tenant_004 seedなし
- `migrations/20260917_000000_create_analysis_rule_tables.sql:692`:
  `RAISE NOTICE '20260917_000000: 完了。schema % に analysis_rule 13 テーブル作成完了（seed なし）'`
  → tenant_004 ブロックはテーブル作成のみ（INSERT なし）

---

## 変更対象ファイルと行番号

| ファイル | 変更内容 | 行番号 |
|---------|---------|-------|
| `migrations/20260920_120000_analysis_rule_public_tables.sql` | 新規作成: 13テーブルをpublic.に作成 | 新規 |
| `backend/app/services/tcg_analysis_rule_svc.py:93,177-183,236,274,297,340,353,367,397,410,430,448,490,507,522,542,554,593,607,644,669-670,730,754,774,788,802,857-858,897-898,923-926` | `{TCG_SCHEMA}.analysis_*` → `public.analysis_*`（38箇所）| 複数行 |
| `backend/app/tasks/tcg_analysis_rule.py:93,123,154,185,222-225,302-303,330,399` | `{TCG_SCHEMA}.analysis_*` → `public.analysis_*`（10箇所）| 複数行 |
| `backend/app/services/item_corrections_svc.py:82` | `{_SCHEMA}.analysis_rule_run_results` → `public.analysis_rule_run_results` | 行82 |
| `backend/app/services/tcg_distribution_svc.py:725` | `{TCG_SCHEMA}.analysis_rule_runs` → `public.analysis_rule_runs` | 行725 |

### 変更しないテーブル参照（テナントスキーマのまま）
- `tcg_analysis_rule_svc.py:960-971`: `{TCG_SCHEMA}.extraction_jobs`, `{TCG_SCHEMA}.extraction_items`
- `tcg_analysis_rule.py:367-378`: `{TCG_SCHEMA}.extraction_jobs`, `{TCG_SCHEMA}.extraction_items`, `{TCG_SCHEMA}.source_messages`
- これらはテナントスキーマにある実データテーブル。cross-schema FKを避けるため変更しない

---

## 既存マイグレーションとの差分

元DDL: `migrations/20260917_000000_create_analysis_rule_tables.sql`

今回の変更:
1. `DO $$ ... $$` ブロックなし（直接DDL文に変更）
2. スキーマプレフィックスを `public.` に統一
3. FK後付けブロック（自己参照FK）は `DO $$` でIF NOT EXISTS付きで維持
4. `source_messages` / `extraction_items` への cross-schema FK は省略
5. `tenant_id` カラムなし（products パターン踏襲）
6. データINSERTなし（テーブルの有無のみ）
