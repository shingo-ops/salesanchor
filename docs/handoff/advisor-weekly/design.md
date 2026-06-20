# Phase 1 設計 — Advisor Weekly / W-1 守り3種 集計＋離脱スコア＋ランク API

**対象ADR**: ADR-139
**recon**: docs/handoff/advisor-weekly/recon.md
**日付**: 2026-06-20
**担当**: Planner

## 目的

ダッシュボードの「今やること」に出す守り3種を、read-only の rank API で返す。

- ① そろそろ受注: days_since_last_order >= avg_interval_days * 0.8
- ② 離脱リスク: pace / contact / decline の合成スコア
- ③ コミュ低下声がけ: days_since_last_contact >= 14 かつ churn_risk と重複しない

## 実装方針

- 既存の customer-orders と customer-contacts をそのまま再利用する。
- churn の decline は current period と直前同長期の orders を比較して出す。
- 係数は helper 内の定数に集約し、将来の調整を容易にする。
- 0 / 1 件の order では avg interval が無いので reorder / churn をスキップする。

## API

- ルート: /api/v1/analytics/weekly-advisor-defensive
- クエリ:
  - scope: team / mine
  - period: 1m / 3m / 6m / 12m
- レスポンス:
  - actions[]
    - type: reorder / churn_risk / comm_low
    - company_id, company_name
    - score, expected_value
    - reason
    - suggested_action

## テスト

| 基準 | 検証方法 |
|------|---------|
| reorder / churn / comm_low が返る | pytest backend/tests/test_analytics.py -q -k weekly_advisor --no-cov |
| churn company は comm_low から除外される | 同上 |
| scope=mine で other company が混ざらない | 同上 |
| 1件注文では reorder / churn を出さない | 同上 |
| tenant_006 / tenant_4 厳禁 | fixture client_tenant_006 を使って確認 |

## 受け入れ基準

- API が rank 済みの actions を返す
- 週次の実装が既存の customer-orders / customer-contacts を壊さない
- CI で required checks が green
- process-artifacts gate で `docs/handoff/advisor-weekly/recon.md` と本 design が参照される

## 外部・過去事例の参照と我々への応用

該当なし: 本 API は外部サービスや過去事例のアルゴリズム移植ではなく、既存の受注履歴・接触履歴・担当者スコープを組み合わせた内部集計とランキングで完結する。応用すべき外部事例は不要で、調整対象は配点定数と閾値のみ。
