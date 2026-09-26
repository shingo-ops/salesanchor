---
sprint: 便D-1
title: deals DDL/RLS/catch-up migration のコード側除去 — 設計書
親リンク: docs/specs/db-ssot/deal-removal/design.md
recon: docs/handoff/deal-removal-serviceD/recon.md
ADR: ADR-138（deals廃止段階）
date: 2026-07-28
---

# 便D-1 design.md

## 素人向け1行説明

「新しいテナントを作るコード」から deals（案件）テーブルを作る定義を消す。既存テナントの deals は今回は触らない。

---

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| 新規テナント作成スクリプト（setup_tenant.py）が deals テーブルを作成しない | CI: pytest + schema-check（PostgreSQL 実機依存）、または手動: 新テナント作成後 `SELECT * FROM tenant_NNN.deals` がエラー |
| deals catch-up migration（20260613_010000・020000）が実行リストにない | `grep "20260613_010000\|20260613_020000" scripts/setup_tenant.py scripts/db/sync_tenant_schema.py` → ヒットなし |
| close_reasons テーブルが新規テナントに存在する | tenant.py DDL に残存確認済み（L847-855） |
| backend pytest が deals DDL 除去後も主要テストを PASS する | `pytest backend/tests/ -x --ignore=backend/tests/test_orders.py -q` ← 既存不安定事象除く |
| 本番 DB・既存テナントに変更なし | 本カードではコードのみ変更。DB 操作なし |

---

## 変更内容詳細

### backend/app/services/tenant.py

| 対象 | 変更内容 |
|------|---------|
| L426-449 deals CREATE TABLE + インデックス | **除去**（コメントに置換） |
| L451-463 fk_leads_converted_deal FK ブロック | **除去**（コメントに置換） |
| _RLS_ENABLE_SQL 中 `ALTER TABLE deals ENABLE ROW LEVEL SECURITY` | **除去**（コメントに置換） |
| _RLS_POLICY_SQL 中 `tenant_isolation_deals` ポリシーブロック | **除去**（コメントに置換） |
| close_reasons DDL（L847-855）| **維持**（deals 非依存） |
| deal_close_reasons DDL（L857-863, lead_id）| **維持**（deals 非依存） |
| v_company_stats | **非対象**（tenant.py 非定義。便D-2 で migration 経由対処） |

### backend/tests/conftest.py

| 対象 | 変更内容 |
|------|---------|
| L413-435 deals CREATE TABLE（SQLite） | **除去** |
| L1341 `DELETE FROM deals`（teardown） | **除去** |
| deal_close_reasons DDL（L1187-1194, lead_id）| **維持** |
| `DELETE FROM deal_close_reasons`（L1340）| **維持**（deal_close_reasons は deals 非依存） |

### scripts/setup_tenant.py / scripts/db/sync_tenant_schema.py

| 対象 | 変更内容 |
|------|---------|
| `20260613_010000_funnel_deals_closed_at.sql` エントリ | **除去** |
| `20260613_020000_funnel_close_reasons.sql` エントリ | **除去** |

**除去理由の補足（20260613_020000）**:
- `close_reasons` テーブルは tenant.py DDL（L847-855）に定義済み → catch-up 不要
- `deal_close_reasons` テーブルも tenant.py DDL（L857-863）に `lead_id` で定義済み → catch-up 不要
- 残るのはデフォルトシードデータ（won/lost 各理由）の欠落。既存テナントは影響なし。新規テナントは close_reasons が空で起動するため、管理者が手動追加 or 便E 以降に seed 関数を追加する必要あり。

---

## 外部事例欄

| 項目 | 内容 |
|------|------|
| 類似先行事例 | ADR-089: customers テーブル廃止（`20260601_140000_drop_customers_tables.sql` で DROP・catch-up からも除去）の前例あり |
| PostgreSQL FK CASCADE | `deal_close_reasons.lead_id REFERENCES leads(id)` は維持。便E で `deal_close_reasons` も DROP 予定 |

---

## 受入基準表

| # | 受入条件 | 検証コマンド / 方法 | 判定 |
|---|---------|-----------------|------|
| 1 | tenant.py に deals DDL が存在しない | `grep "CREATE TABLE.*deals" backend/app/services/tenant.py` → ヒットなし | ✓ |
| 2 | tenant.py に deals RLS/FK が存在しない | `grep "tenant_isolation_deals\|fk_leads_converted_deal" backend/app/services/tenant.py` → ヒットなし | ✓ |
| 3 | conftest.py に deals CREATE TABLE が存在しない | `grep "CREATE TABLE.*deals" backend/tests/conftest.py` → ヒットなし | ✓ |
| 4 | catch-up リストに 20260613_010000/020000 が存在しない | `grep "20260613_0[12]" scripts/setup_tenant.py scripts/db/sync_tenant_schema.py` → ヒットなし | ✓ |
| 5 | close_reasons DDL が tenant.py に存在する | `grep "CREATE TABLE.*close_reasons" backend/app/services/tenant.py` → ヒット | ✓ |
| 6 | pytest が主要テストを PASS | `pytest backend/tests/ -x -q`（詳細は手順4） | CI で確認予定 |
| 7 | 本番 DB 未変更 | 本カードは push/PR/DB 操作なし | ✓（本カードスコープ外） |

---

## 維持の仕組み欄

| リスク | 対策 |
|-------|------|
| 新たな deals 依存 catch-up が追加される | migration-guard.yml + setup_tenant.py の diff review で検出 |
| close_reasons seed 欠落（新規テナント） | 便E 以降に `seed_close_reasons()` を setup_tenant.py の seed ステップに追加する |
| 旧セッションが deals DDL を復活させる | active-work.d 台帳 + CI schema-check で検出 |

---

## 便D-1 / 便D-2 / 便E の境界（再掲）

```
便D-1（本カード）: コード側のみ。deals DDL/RLS/catch-up 除去 → commit, push, PR
便D-2（別カード）: 本番 DB ビュー付け替え（v_company_stats から deal_count 除去）
便E  （別カード）: DROP TABLE deals + deal_close_reasons + analytics/companies コード清掃
```
