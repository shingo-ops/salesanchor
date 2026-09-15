---
sprint: 便D-1
title: deals DDL/RLS/ビュー定義/catch-up migration のコード側除去
親リンク: docs/specs/db-ssot/deal-removal/design.md
date: 2026-07-28
ADR: ADR-138（deals廃止段階）
---

# 便D-1 recon.md

deals テーブルの「新規テナント作成定義」からの除去（DDL・RLS・catch-up migration）を確実に行うための事前調査。  
本番 DB のビュー付け替えは **便D-2**、deals テーブル本体の DROP は **便E**。

---

## 1. deals DDL 所在

| ファイル | 行 | 内容 |
|---------|----|------|
| `backend/app/services/tenant.py` | L426-449 | deals CREATE TABLE + indexes（除去対象） |
| `backend/app/services/tenant.py` | L451-463 | fk_leads_converted_deal FK ブロック（除去対象） |
| `backend/app/services/tenant.py` | 旧L1207 | `ALTER TABLE deals ENABLE ROW LEVEL SECURITY`（除去対象） |
| `backend/app/services/tenant.py` | 旧L1262-1265 | `tenant_isolation_deals` RLS ポリシー（除去対象） |
| `backend/tests/conftest.py` | L413-435 | SQLite deals DDL（除去対象） |
| `backend/tests/conftest.py` | 旧L1341 | `DELETE FROM deals`（除去対象） |

## 2. catch-up migration の deals 依存確認

| ファイル | 依存内容 | 判定 |
|---------|---------|------|
| `migrations/20260613_010000_funnel_deals_closed_at.sql` | `ALTER TABLE deals ADD COLUMN closed_at` のみ | deals 専用 → 除去 |
| `migrations/20260613_020000_funnel_close_reasons.sql` | `CREATE TABLE deal_close_reasons (deal_id REFERENCES deals(id))` + `ALTER TABLE deals` | deals 依存あり → 除去 |

**20260613_020000 の close_reasons への影響**:
- `close_reasons` テーブル作成を含む（deals 非依存部分）
- ただし `close_reasons` は **tenant.py L847-855 に既に定義済み**（IF NOT EXISTS = 新規テナントは重複スキップ）
- `deal_close_reasons` も **tenant.py L857-863 に `lead_id` で定義済み**（deal_id ではない）
- よって catch-up から除去しても新規テナントの `close_reasons` / `deal_close_reasons` テーブル作成に影響なし
- **既知の副作用**: デフォルト close_reasons シードデータ（won:7件/lost:8件）が新規テナントの catch-up 段階で投入されなくなる。既存テナントは影響なし（既に適用済み）。この gap は別途 seed 関数追加（便E以降）で対処予定。

## 3. v_company_stats の deals 参照

| ファイル | 内容 |
|---------|------|
| `migrations/20260612_120000_fix_company_stats_ssot.sql` | 現在の v_company_stats 定義（deal_count・total_deal_amount あり） |

**重要**: v_company_stats は `tenant.py` / `setup_tenant.py` には定義がなく、migration ファイル管理のみ。  
コード側除去の対象ではない → **便D-2（本番 DB ビュー付け替え）で対処**。

## 4. close_reasons / deal_close_reasons の現在スキーマ確認

```
tenant.py L847-855: close_reasons（type/label/sort_order/is_active）
tenant.py L857-863: deal_close_reasons（lead_id REFERENCES leads.id / reason_id / is_primary）
conftest.py L1187-1194: deal_close_reasons（lead_id REFERENCES leads.id）← 既に lead_id
```

`deal_close_reasons` は deals(id) を参照していない（lead_id 化済み）。  
conftest.py の deals 除去は `deal_close_reasons` に影響しない。

## 5. 便D-1 / 便D-2 / 便E の境界

| 便 | 内容 |
|----|------|
| **便D-1（本カード）** | テナント作成定義から deals DDL/RLS/catch-up 除去。コードのみ |
| **便D-2（別カード）** | 本番 DB の v_company_stats ビュー付け替え（deal_count 除去） |
| **便E（別カード）** | DROP TABLE deals（+ deal_close_reasons FK 解除 → drop） |

## 6. 既存テナントへの影響（便D-1）

- **なし**。便D-1 は tenant.py / conftest.py / catch-up リストの変更のみ
- 本番 DB の deals テーブルは触らない
- 既存テナントは deals テーブルを保持したまま（便E まで）
