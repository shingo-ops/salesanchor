# deal-removal service A recon

## 対象と実測

- `backend/app/routers/goals.py:380-407` は、従来 `deals.created_at` と `deals.status='won'` で `deal_count` と `close_rate` を算出していた。
- `backend/app/routers/goals.py:421-436` は、既に `leads.status IN ('negotiating', 'existing_customer', 'lost')` を分子、`status NOT IN ('out_of_scope', 'disqualified')` を分母として `conversion_rate` を算出していた。
- `backend/app/routers/leads.py:783-838` の商談化は deals を作らず、lead を `negotiating` に更新する。
- `backend/app/schemas/lead.py:33-39` は `existing_customer` を成約済み、`lost` を失注と定義する。
- `backend/app/services/priority_scoring.py:191-212` は失注サンプルに `deals.status='lost'` を使用していた。lead の `lost` が同じ失注状態の正本である。
- `backend/app/tasks/reports.py:88-106` は `deals` CSV を出力していた。報告種別の互換キーは維持し、商談段階にある leads を出力する。
- `backend/app/services/conv_log_writer.py:117-131` は company を deals 経由で取得していた。companies.lead_id による直接参照へ切り替えられる。

## 変更後の定義

| KPI | 定義 | 絞り込み |
|---|---|---|
| deal_count | `status IN ('negotiating', 'existing_customer', 'lost')` の件数 | 既存の担当者・作成期間 |
| close_rate | `existing_customer / (existing_customer + lost)` | 既存の担当者・作成期間、分母0は0.0 |
| conversion_rate | `(negotiating + existing_customer + lost) / (全リード - out_of_scope - disqualified)` | 既存の担当者・作成期間 |

## テスト

`backend/tests/test_conv_log_writer.py` は company 補完が `companies` を使用し、`deals` を使用しないことを静的に検証する。PostgreSQL依存のKPI実行はCIで確認する。
