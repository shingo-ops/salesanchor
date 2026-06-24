# recon — D-2: 新テナント own_inventory provisioning 欠如修正

**仕事名**: d2-own-inventory-provisioning  
**日付**: 2026-06-24  
**対象ADR**: ADR-034  
**担当**: Terminal CC

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tenant.py:142` | `_TENANT_TABLES_SQL` 宣言開始（テナントDDL文字列） |
| `backend/app/services/tenant.py:1062` | `_TENANT_TABLES_SQL` 閉じ三重引用符（追加位置） |
| `backend/app/services/tenant.py:1067` | `_RLS_ENABLE_SQL` 宣言開始（ALTER TABLE ENABLE RLS 群） |
| `backend/app/services/tenant.py:1078` | `_RLS_ENABLE_SQL` 内の products RLS有効化（書式例） |
| `backend/app/services/tenant.py:1109` | `_RLS_ENABLE_SQL` の lead_playbook 行（末尾追加位置） |
| `backend/app/services/tenant.py:1115` | `_RLS_POLICY_SQL` 宣言開始（DO$$内ポリシー群） |
| `backend/app/services/tenant.py:1173` | `_RLS_POLICY_SQL` 内の products ポリシーブロック（書式例） |
| `backend/app/services/tenant.py:1536` | `create_tenant_schema()` — `_TENANT_TABLES_SQL` 実行箇所 |
| `backend/app/services/tenant.py:1547` | `create_tenant_schema()` — `_RLS_ENABLE_SQL` 実行箇所（; 分割ループ） |
| `backend/app/services/tenant.py:1554` | `create_tenant_schema()` — `_RLS_POLICY_SQL` 実行箇所（DO$$単一ステートメント） |
| `backend/app/services/tenant.py:1563` | `create_tenant_schema()` — `ON ALL TABLES IN SCHEMA` GRANT（per-table GRANT 不要の根拠） |
| `migrations/20260604_140000_create_own_inventory.sql:1` | `own_inventory` 正本DDL（14列・制約6・RLS・ポリシー） |

---

## 確認結果

### A-4: own_inventory の不在確認
`grep -n "own_inventory" backend/app/services/tenant.py` → 出力なし（0件）。確認済み。

### A-1: 実行機構
テーブル追加の書き先は3箇所（GRANT は `ON ALL TABLES` 一括のため追加不要）:
1. `_TENANT_TABLES_SQL`（`backend/app/services/tenant.py:142`）= CREATE TABLE
2. `_RLS_ENABLE_SQL`（`backend/app/services/tenant.py:1067`）= ALTER TABLE ENABLE RLS
3. `_RLS_POLICY_SQL`（`backend/app/services/tenant.py:1115`）= CREATE POLICY（DO$$内・`pg_policies`で冪等）

### B: 正本DDL確認
`migrations/20260604_140000_create_own_inventory.sql:1` — 14列・制約6（PK/FK/CHECK×3/chk_reserved_le_physical）・RLS有効化・ポリシー `own_inventory_tenant_isolation` 確認。

### C: tenant_006 実測（B との照合）
制約6件・index 1件（pkey のみ）→ migration B と差分0。Bが基準形で正しいことを実測で裏取り済み。

### D: 関連ADR
- ADR-034: 新テナント作成時の不変条件チェック（新テナント作成経路に関する制約）
- ADR-SA-18: app-db least-privilege（GRANT一括カバーの根拠）
- own_inventory 新テナント provisioning を扱うADRは既存なし

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | ポリシー名を既存（migration由来）と provisioning内どちらに揃えるか | PO決定（案A: `own_inventory_tenant_isolation`） | ✅ 解消済み（2026-06-24 PO承認） |
| 2 | GRANT は per-table 追加が要るか | `backend/app/services/tenant.py:1563` の `ON ALL TABLES` 一括で自動カバーを確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
