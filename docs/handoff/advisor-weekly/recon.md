# recon: Advisor Weekly / W-1 守り3種 集計＋離脱スコア＋ランク API

**仕事名**: Advisor Weekly / W-1 守り3種 集計＋離脱スコア＋ランク API
**日付**: 2026-06-20
**対象ADR**: ADR-139
**担当**: architect

## file:line 引用表

| 引用先 path:line | 確認内容 |
|------------------|---------|
| backend/app/routers/analytics.py:148-159 | weekly advisor の response model（WeeklyAdvisorAction / WeeklyAdvisorResponse）を追加 |
| backend/app/routers/analytics.py:231-260 | 週次ランキングの定数と helper（scope clause / 直前期間 / pace / contact / decline）を追加 |
| backend/app/routers/analytics.py:463-633 | customer-orders / customer-contacts が既存の PR-1 / PR-3 の土台であることを確認 |
| backend/app/routers/analytics.py:903-1069 | `/analytics/weekly-advisor-defensive` が reorder / churn_risk / comm_low を rank して返す |
| backend/tests/test_analytics.py:214-266 | deal + order を日付指定で投入するテスト helper を追加 |
| backend/tests/test_analytics.py:1235-1476 | weekly advisor の tenant_006 pytest（rank / dedup / scope / single-order boundary）を追加 |

## 事実メモ

- reorder は `days_since_last_order >= avg_interval_days * 0.8` を満たす company のみを対象にする。
- churn_risk は `pace_score + contact_score + decline_score` を合算し、`expected_value × 0.5 × (total_score/100)` で score を出す。
- comm_low は `days_since_last_contact >= 14` を対象にするが、churn_risk に入った company は除外する。
- `scope=mine` は customer-orders 側の `deals.assigned_to` と customer-contacts 側の `companies.sales_rep_id` をそれぞれ既存流儀で使う。
- 受注 0/1 件の company は `avg_interval_days` が無いので reorder / churn_risk をスキップする。
- テストは `client_tenant_006` を使い、tenant_4 は使っていない。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | reorder / churn / comm の score の細かな係数を将来どう調整するか | 定数化済み。係数変更は helper 内の定数で調整 | 解消済み |
| 2 | comm_low の expected_value を 0 でも返すか | sales 顧客として意味のある order history が無いものは score 0 で除外 | 解消済み |

**未解決ゼロ確認**: 全て解消済み

## 補足

- read-only の集計 API 追加で、DB migration / deploy.yml 変更は不要。
- customer-orders / customer-contacts をそのまま再利用し、週次の ranking だけを追加した。
- PayPal smoke は本 PR の必須チェックではないため、マージ判定から除外する。
