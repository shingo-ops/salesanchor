# recon: Advisor Phase 1 / PR-3 顧客別 接触集計API

**仕事名**: Advisor Phase 1 / PR-3 顧客別 接触集計API
**日付**: 2026-06-20
**対象ADR**: ADR-139
**担当**: architect

## file:line 引用表

| 引用先 path:line | 確認内容 |
|------------------|---------|
| backend/app/routers/analytics.py:97-110 | 顧客接触 API の response model（CustomerContactItem / CustomerContactsResponse）を追加 |
| backend/app/routers/analytics.py:146-154 | 1m / 3m / 6m / 12m の期間境界 helper を流用 |
| backend/app/routers/analytics.py:382-430 | /analytics/customer-contacts が period / scope / stale_days を受けて read-only 集計を返す |
| backend/app/routers/analytics.py:400-430 | 担当者向けスコープでは companies テーブルの sales_rep_id で担当会社に絞り、最終接触日時の最大値から last_contact_at を導出 |
| backend/tests/test_analytics.py:86-194 | tenant_006 fixture、conversation_logs / public.data_access_events の SQLite 互換テーブルを追加 |
| backend/tests/test_analytics.py:627-759 | team / mine / stale_days の pytest を追加 |

## 事実メモ

- 最終接触日は conversation_logs.occurred_at の MAX から導出する。v_company_stats は使わない。
- 接触回数は period 内の conversation_logs 件数。
- is_communication_low は last_contact_at がない場合も true にする（no-contact 顧客も低接触扱い）。
- tenant_006 のテスト実行時は tenant_id=6 を使い、tenant_4 は使っていない。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | last_contact_at を date 表示にするか datetime 表示にするか | 既存 dashboard の日付表示に合わせて date 化 | 解消済み |
| 2 | no-contact 顧客を low とみなすか | 0接触を low 扱いにするテストで固定 | 解消済み |

**未解決ゼロ確認**: 全て解消済み

## 補足

- read-only の集計 API 追加で、DB migration は不要。
- 担当者向けスコープの基準は customer-level のため、companies テーブルの sales_rep_id に統一した。
- PayPal smoke は本 PR の必須チェックではないため、マージ判定から除外する。
