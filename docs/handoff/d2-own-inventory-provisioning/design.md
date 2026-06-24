# 設計 — D-2: 新テナント own_inventory provisioning 欠如修正

**対象ADR**: ADR-034  
**recon**: docs/handoff/d2-own-inventory-provisioning/recon.md  
**日付**: 2026-06-24  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 先行実装: `_RLS_POLICY_SQL` 内 `tenant_isolation_products`（`backend/app/services/tenant.py:1173`）— 同じ `tenant_id = current_setting('app.tenant_id', true)::INTEGER` パターン。own_inventory は products と同一構造（直接 tenant_id カラム保持）なので完全踏襲。
- message_translations の RLS有効化（PR #2525）— `_RLS_ENABLE_SQL` への追加パターンの先行実績。同じ手順で own_inventory を追加。
- ADR-SA-18 least-privilege — `ON ALL TABLES IN SCHEMA` GRANT 一括方式の根拠。per-table GRANT を追加しないことで保守コストを抑制（同設計の全テナントテーブルで踏襲済み）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 新テナント作成後 own_inventory が14列で生成される | V2: `information_schema.columns` で列数・列名・型・nullable 一致 |
| 制約6種（PK/FK/CHECK×3/chk_reserved_le_physical）が揃う | V2: `pg_constraint` で conname・contype・constraintdef 確認 |
| RLS 有効（rowsecurity=t） | V3: `pg_class.relrowsecurity = t` |
| ポリシー `own_inventory_tenant_isolation` が存在 | V3: `pg_policies` でポリシー名・qual 確認 |
| 別テナント号室から own_inventory が見えない（越境漏れ0） | V4: 別 tenant_id で SELECT → 0件 or 42501 |
| 既存5テナント own_inventory が差分0 | V5: デプロイ前スナップと同一クエリを比較 |
| `create_tenant_schema()` が例外0で完走 | V1: 例外ログなし・戻り値 schema_name |

---

## 技術 How・KPI

- 変更箇所: `backend/app/services/tenant.py` 3箇所（`_TENANT_TABLES_SQL` / `_RLS_ENABLE_SQL` / `_RLS_POLICY_SQL`）
- KPI2-a: 新テナント own_inventory = 14列・制約6・RLS有効・ポリシー存在（既存テナントと差分0）
- KPI2-b: 既存5テナント own_inventory 無変更（provisioning は新テナント作成時のみ実行）
- KPI2-c: `create_tenant_schema()` 例外0・完走
- KPI2-d: 越境漏れ0（別号室から見えない）

---

## 弊害・トレードオフ

- `_TENANT_TABLES_SQL` に追加する CREATE TABLE は `CREATE TABLE IF NOT EXISTS` のため冪等。既存テナントへの影響ゼロ（既にテーブル存在 → スキップ）。
- `_RLS_POLICY_SQL` の IF NOT EXISTS により重複ポリシー作成エラーなし。
- ポリシー名を既存テナント（migration由来）の `own_inventory_tenant_isolation` に統一することで新旧テナント間の drift を防止（代替案の `tenant_isolation_own_inventory` は drift を作るため不採用）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `_TENANT_TABLES_SQL` 末尾に CREATE TABLE 追加 | Generator |
| 2 | `_RLS_ENABLE_SQL` 末尾に ENABLE RLS 追加 | Generator |
| 3 | `_RLS_POLICY_SQL` DO$$内 products 直後に CREATE POLICY 追加 | Generator |
| 4 | GRANT 変更なし（`ON ALL TABLES` 一括カバー確認） | Generator |
| 5 | KPI2-a〜d 検証（新テナント作成・構造確認・越境テスト） | Terminal CC |

---

## 継続

- 完了後の監視: 次回新テナントオンボード時に `information_schema.columns` で own_inventory 14列を確認
- 次フェーズへの引き継ぎ: ADR起案推奨（新テナント必須テーブル SSOT 定義・poka-yoke）
