# Recon: weekly_advisor_defensive 外科的復元

## 発端

`#2455`（`ef87c486` "feat: add priority prospects analytics"）が `analytics.py` を 629行削除・216行追加する
丸ごと作り直しを行い、`weekly_advisor_defensive` を巻き添えで消した。
frontend は `frontend/src/api/funnel.ts:210` で `/analytics/weekly-advisor-defensive` を今も呼んでおり、W-1 が develop で壊れている。

## ADR 検索

```
git grep -i "weekly.advisor\|weekly_advisor" docs/adr/
→ 該当なし（weekly-advisor 専用 ADR なし・ADR-072 テナント分離が適用される）
```

## 削除元コミットの特定

- 削除コミット: `ef87c486` (PR #2455, 2026-06-22 11:06 JST)
- 消える直前の状態: `27642d33` "Merge pull request #2453" (2026-06-22 12:52 JST) → `ef87c486` の parent

## transitive 依存の特定（27642d33 から抽出）

| 対象 | 27642d33 の行 | 現行 analytics.py に存在？ |
|-----|--------------|--------------------------|
| `WeeklyAdvisorReason` モデル | 119 | **なし** → 復元 |
| `WeeklyAdvisorAction` モデル | 135 | **なし** → 復元 |
| `WeeklyAdvisorResponse` モデル | 147 | **なし** → 復元 |
| `_normalize_date` | 153 | **なし** → 復元 |
| `_customer_orders_period_bounds` | 165 | **なし** → 復元（`_advisor_period_bounds` の依存） |
| `_advisor_period_bounds` | 176 | **なし** → 復元 |
| `_order_count_drop_score` | 194 | **なし** → 復元 |
| `_revenue_drop_score` | 206 | **なし** → 復元 |
| `_pace_score` | 218 | **なし** → 復元 |
| `_contact_score` | 232 | **なし** → 復元 |
| `_normalized_urgency` | 243 | **なし** → 復元 |
| `weekly_advisor_defensive` EP | 578–811 | **なし** → 復元 |
| `from datetime import datetime` | 17 | **なし**（`date, timedelta` のみ）→ 追加 |

## 死蔵2本との依存確認

`_customer_orders_period_bounds` は `customer_orders_report`（死蔵）も呼んでいたが、
`weekly_advisor_defensive` の transitive 依存として **ヘルパーのみ** 復元。
`customer_orders_report` 本体・`revenue_segments_report` 本体は **復元しない**。

全域参照ゼロを確認済み（grep 0件）：
- `customer_orders_report` / `/analytics/customer-orders-report`
- `revenue_segments_report` / `/analytics/revenue-segments-report`

## 既存関数との重複チェック

```
grep -n "WeeklyAdvisor\|_advisor_period\|_order_count_drop\|_revenue_drop\|_pace_score\|_contact_score\|_normalized_urgency\|_normalize_date\|_customer_orders_period" analytics.py
→ 0件（重複なし）
```

## frontend 型整合

`frontend/src/api/funnel.ts:210`:
```typescript
return api.get<WeeklyAdvisorResponse>(`/analytics/weekly-advisor-defensive?${params}`);
```

復元する `WeeklyAdvisorResponse.actions[].type` は `"reorder" | "churn_risk" | "comm_low"`。
`WeeklyAdvisorAction.reason` は `WeeklyAdvisorReason`。
フィールド構成は frontend 型定義と一致（27642d33 実装から直接復元）。

## 触らない範囲の確認

- `priority_prospects`（`backend/app/routers/analytics.py:1779-1893`）: 変更なし
- `_fetch_attribute_conversion_axis` / `/conversion-by-attribute`: 変更なし
- `channels_summary`: 変更なし
- `compute_prospect_rank` / `priority_score`: 変更なし
