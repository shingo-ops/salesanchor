# design.md — Advisor Phase 1 / PR-3 顧客別 接触集計API

**対象ADR**: ADR-139
**recon**: docs/handoff/advisor-phase1/recon.md
**日付**: 2026-06-20
**担当**: Planner

## 目的

顧客ごとの接触頻度を read-only で返し、目標設定アドバイザーの「維持・離脱予兆」基盤にする。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| GET /api/v1/analytics/customer-contacts が返る | pytest backend/tests/test_analytics.py -q -k customer_contacts --no-cov |
| period / scope / stale_days がレスポンスに反映される | pytest backend/tests/test_analytics.py -q -k customer_contacts --no-cov |
| last_contact_at / days_since_last_contact / contact_count / is_communication_low が正しい | pytest backend/tests/test_analytics.py -q -k customer_contacts --no-cov |
| scope=mine で担当外会社が混ざらない | pytest backend/tests/test_analytics.py -q -k customer_contacts --no-cov |
| no-contact 顧客が low 扱いになる | pytest backend/tests/test_analytics.py -q -k customer_contacts --no-cov |
| process-artifacts gate が通る | GitHub Actions の process-artifacts gate |

## 技術方針

- KPI: 顧客ごとの最終接触日、days_since_last_contact、接触回数、is_communication_low を period / scope / stale_days 別に read-only で返す
- 期間: 1m / 3m / 6m / 12m。1m は JST 暦月境界、他は日数ベース
- scope: team / mine。mine は customer-level のため companies.sales_rep_id で担当会社に絞る
- 接触回数: period 内の conversation_logs 件数
- 最終接触日: conversation_logs.occurred_at の MAX
- low 判定: last_contact_at が null、または days_since_last_contact >= stale_days

## 外部・過去事例の参照と我々への応用

該当なし。今回の PR は既存の conversation_logs と companies.sales_rep_id を read-only で集計するだけで、外部ライブラリや追加の過去事例を参照して設計を変える必要はない。

## API

- ルート: /api/v1/analytics/customer-contacts
- クエリ:
  - period: 1m / 3m / 6m / 12m
  - scope: team / mine
  - stale_days: 既定 30
- レスポンス:
  - period, scope, stale_days
  - items: company_id, company_name, contact_count, last_contact_at, days_since_last_contact, is_communication_low

## 変更範囲

- backend/app/routers/analytics.py: 集計 API 追加
- backend/tests/test_analytics.py: tenant_006 の pytest 追加
- docs/handoff/advisor-phase1/: recon / design を PR-3 用に更新

## 検証メモ

- tenant_006 を使う。tenant_4 は使わない。
- DB migration / deploy.yml 変更なし。
- PayPal smoke は必須ではないため、CI 判定から外してよい。
